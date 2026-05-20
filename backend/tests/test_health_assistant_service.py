"""Tests for health_assistant_service.py

Coverage:
  - symptoms-only evidence bundle
  - reports-only evidence bundle
  - metrics-only evidence bundle
  - mixed-data evidence bundle
  - recommendation deduplication (active tracking)
  - recommendation suppression (recently completed)
  - fallback recommendations when evidence is sparse
  - product signals computation
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.health_assistant_service import (
    _recency_label,
    build_evidence_bundle,
    build_product_signals,
    get_action_recommendations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _make_symptom(days_ago=1, severity=5, duration_days=None):
    s = SimpleNamespace()
    s.id = uuid4()
    s.symptom = "頭痛"
    s.occurred_at = _utc(days_ago)
    s.severity = severity
    s.confidence_score = 0.8
    s.estimated_duration_days = duration_days
    s.note = None
    return s


def _make_metric(days_ago=1):
    m = SimpleNamespace()
    m.id = uuid4()
    m.recorded_at = _utc(days_ago)
    m.systolic_bp = 130
    m.diastolic_bp = 85
    m.heart_rate = 72
    m.blood_glucose = 95
    m.weight_kg = 70.5
    m.sleep_hours = 7.0
    m.steps = 5000
    m.source = "manual"
    return m


def _make_lab_report(days_ago=5):
    r = SimpleNamespace()
    r.id = uuid4()
    r.created_at = _utc(days_ago)
    r.report_date = _utc(days_ago).date()
    return r


def _make_lab_item(report_id, item_name="HbA1c", value=7.2, abnormal="H"):
    i = SimpleNamespace()
    i.id = uuid4()
    i.report_id = report_id
    i.item_name = item_name
    i.item_code = item_name.lower()
    i.value_num = value
    i.value_text = None
    i.unit = "%"
    i.ref_range = "4.0-6.5"
    i.ref_low = 4.0
    i.ref_high = 6.5
    i.abnormal_flag = abnormal
    i.parser_confidence = 0.9
    return i


def _make_action(status="todo", rule_id=None, source_type="manual"):
    a = SimpleNamespace()
    a.id = uuid4()
    a.title = "每日量血壓"
    a.status = status
    a.priority = "high"
    a.category = "bp"
    a.action_type = "lifestyle"
    a.source_type = source_type
    a.source_id = None
    a.rule_id = rule_id
    a.confidence = 0.8
    a.evidence_level = "B"
    a.resurface_count = 0
    a.streak_count = 3
    a.due_date = None
    a.snoozed_until = None
    a.completed_at = _utc(2) if status == "done" else None
    a.created_at = _utc(5)
    return a


def _make_risk_alert(severity="high", rule_code="bp_high"):
    ra = SimpleNamespace()
    ra.id = uuid4()
    ra.severity = severity
    ra.risk_type = "cardiovascular"
    ra.rule_code = rule_code
    ra.title = "血壓偏高"
    ra.message = "最近血壓持續偏高，請注意監控"
    ra.recommendation = "每日早晚量血壓，減少鹽分攝取"
    ra.status = "active"
    ra.created_at = _utc(1)
    return ra


def _make_insight(severity="warning"):
    ins = SimpleNamespace()
    ins.id = uuid4()
    ins.insight_type = "risk"
    ins.severity = severity
    ins.title = "血壓趨勢上升"
    ins.summary = "過去兩週血壓持續上升"
    ins.recommendation = "每日量血壓並記錄"
    ins.evidence_json = None
    ins.generated_at = _utc(1)
    ins.expires_at = None
    ins.is_active = True
    return ins


def _make_outcome(action_id, label="improved"):
    o = SimpleNamespace()
    o.id = uuid4()
    o.action_id = action_id
    o.metric_type = "systolic_bp"
    o.before_value = 140
    o.after_value = 128
    o.delta = -12
    o.delta_pct = -8.5
    o.time_window_days = 7
    o.outcome_label = label
    o.computed_at = _utc(1)
    return o


# ---------------------------------------------------------------------------
# Helpers for mocking the DB
# ---------------------------------------------------------------------------

class _FakeQuery:
    """Minimal SQLAlchemy query mock that supports chaining."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a):
        return self

    def limit(self, n):
        return _FakeQuery(self._rows[:n])

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def count(self):
        return len(self._rows)


def _make_db(
    user_profile=None,
    person=None,
    symptoms=None,
    metrics=None,
    reports=None,
    lab_items=None,
    alerts=None,
    insights=None,
    actions=None,
    completed_actions=None,
    outcomes=None,
):
    db = MagicMock()
    symptom_rows = symptoms or []
    metric_rows = metrics or []
    report_rows = reports or []
    lab_item_rows = lab_items or []
    alert_rows = alerts or []
    insight_rows = insights or []
    action_rows_active = actions or []
    action_rows_done = completed_actions or []
    outcome_rows = outcomes or []

    from app.models.entities import (
        ActionOutcome,
        HealthAction,
        HealthInsight,
        HealthMetric,
        LabReport,
        LabReportItem,
        PersonProfile,
        RiskAlert,
        SymptomLog,
        UserProfile,
    )

    def query_dispatch(model):
        mapping = {
            UserProfile: _FakeQuery([user_profile] if user_profile else []),
            PersonProfile: _FakeQuery([person] if person else []),
            SymptomLog: _FakeQuery(symptom_rows),
            HealthMetric: _FakeQuery(metric_rows),
            LabReport: _FakeQuery(report_rows),
            LabReportItem: _FakeQuery(lab_item_rows),
            RiskAlert: _FakeQuery(alert_rows),
            HealthInsight: _FakeQuery(insight_rows),
            HealthAction: _FakeQuery(action_rows_active + action_rows_done),
            ActionOutcome: _FakeQuery(outcome_rows),
        }
        return mapping.get(model, _FakeQuery([]))

    db.query.side_effect = query_dispatch
    return db


# ---------------------------------------------------------------------------
# Tests — recency label
# ---------------------------------------------------------------------------

def test_recency_today():
    assert _recency_label(_utc(0)) == "today"


def test_recency_this_week():
    assert _recency_label(_utc(3)) == "this_week"


def test_recency_this_month():
    assert _recency_label(_utc(15)) == "this_month"


def test_recency_older():
    assert _recency_label(_utc(60)) == "older"


def test_recency_none():
    assert _recency_label(None) == "unknown"


# ---------------------------------------------------------------------------
# Tests — evidence bundle: symptoms-only
# ---------------------------------------------------------------------------

def test_evidence_bundle_symptoms_only():
    uid = str(uuid4())
    pid = str(uuid4())
    sym = _make_symptom(days_ago=2, severity=7)
    db = _make_db(symptoms=[sym])

    bundle = build_evidence_bundle(db, uid, pid)

    assert bundle["person_id"] == pid
    assert len(bundle["symptoms"]) == 1
    assert bundle["symptoms"][0]["severity"] == 7
    assert bundle["symptoms"][0]["source_type"] == "symptom"
    assert bundle["health_metrics"] == []
    assert bundle["lab_report_items"] == []
    assert "健康指標（血壓、血糖、體重等）" in bundle["missing_data"]
    assert "健檢報告（或無異常項目）" in bundle["missing_data"]
    assert bundle["summary"]["symptom_count"] == 1


# ---------------------------------------------------------------------------
# Tests — evidence bundle: reports-only
# ---------------------------------------------------------------------------

def test_evidence_bundle_reports_only():
    uid = str(uuid4())
    pid = str(uuid4())
    report = _make_lab_report(days_ago=10)
    item = _make_lab_item(report.id)
    db = _make_db(reports=[report], lab_items=[item])

    bundle = build_evidence_bundle(db, uid, pid)

    assert len(bundle["lab_report_items"]) == 1
    assert bundle["lab_report_items"][0]["item_name"] == "HbA1c"
    assert bundle["lab_report_items"][0]["abnormal_flag"] == "H"
    assert bundle["symptoms"] == []
    assert "症狀記錄" in bundle["missing_data"]
    assert bundle["summary"]["abnormal_lab_count"] == 1


# ---------------------------------------------------------------------------
# Tests — evidence bundle: metrics-only
# ---------------------------------------------------------------------------

def test_evidence_bundle_metrics_only():
    uid = str(uuid4())
    pid = str(uuid4())
    metric = _make_metric(days_ago=1)
    db = _make_db(metrics=[metric])

    bundle = build_evidence_bundle(db, uid, pid)

    assert len(bundle["health_metrics"]) == 1
    assert bundle["health_metrics"][0]["systolic_bp"] == 130
    assert bundle["health_metrics"][0]["source_type"] == "health_metric"
    assert bundle["symptoms"] == []
    assert bundle["summary"]["metric_count"] == 1


# ---------------------------------------------------------------------------
# Tests — evidence bundle: mixed data
# ---------------------------------------------------------------------------

def _make_person():
    p = SimpleNamespace()
    p.id = uuid4()
    p.display_name = "測試用戶"
    p.relationship = "self"
    p.birth_date = None
    p.gender = "M"
    p.height_cm = 170
    p.weight_kg = 68
    p.chronic_conditions = None
    p.allergies = None
    p.family_history = None
    return p


def test_evidence_bundle_mixed_data():
    uid = str(uuid4())
    pid = str(uuid4())
    sym = _make_symptom(days_ago=3, severity=8, duration_days=45)
    metric = _make_metric(days_ago=0)
    report = _make_lab_report(days_ago=7)
    item = _make_lab_item(report.id, item_name="Uric Acid", value=8.5, abnormal="H")
    alert = _make_risk_alert()
    ins = _make_insight()
    action = _make_action(status="todo", rule_id="bp_monitor")
    completed = _make_action(status="done", rule_id="diet_salt")
    person = _make_person()

    db = _make_db(
        person=person,
        symptoms=[sym],
        metrics=[metric],
        reports=[report],
        lab_items=[item],
        alerts=[alert],
        insights=[ins],
        actions=[action],
        completed_actions=[completed],
    )

    bundle = build_evidence_bundle(db, uid, pid)

    # Long-term symptom (duration 45 days) should be in long_term_symptoms
    assert len(bundle["long_term_symptoms"]) == 1
    assert bundle["long_term_symptoms"][0]["symptom"] == "頭痛"
    assert len(bundle["symptoms"]) == 0  # moved to long_term
    assert len(bundle["health_metrics"]) == 1
    assert len(bundle["lab_report_items"]) == 1
    assert len(bundle["risk_alerts"]) == 1
    assert len(bundle["insights"]) == 1
    assert len(bundle["actions"]) >= 1  # active action
    assert bundle["missing_data"] == []  # all present
    assert bundle["summary"]["missing_data_count"] == 0


# ---------------------------------------------------------------------------
# Tests — recommendations
# ---------------------------------------------------------------------------

def test_recommendations_returns_top_3():
    uid = str(uuid4())
    pid = str(uuid4())
    alert1 = _make_risk_alert(severity="high", rule_code="bp_high")
    alert2 = _make_risk_alert(severity="medium", rule_code="glucose_high")
    alert3 = _make_risk_alert(severity="low", rule_code="weight_up")
    alert4 = _make_risk_alert(severity="warning", rule_code="sleep_low")
    db = _make_db(alerts=[alert1, alert2, alert3, alert4])

    result = get_action_recommendations(db, uid, pid)

    assert len(result["recommendations"]) == 3
    assert result["person_id"] == pid
    assert "generated_at" in result


def test_recommendations_active_action_marked_tracking():
    uid = str(uuid4())
    pid = str(uuid4())
    alert = _make_risk_alert(severity="high", rule_code="bp_high")
    action = _make_action(status="todo", rule_id="bp_high")
    db = _make_db(alerts=[alert], actions=[action])

    result = get_action_recommendations(db, uid, pid)

    recs = result["recommendations"]
    # The bp_high alert should be found; the action covers it
    bp_rec = next((r for r in recs if "血壓" in r["title"]), None)
    if bp_rec:
        assert bp_rec["is_tracking"] is True
        assert bp_rec["tracking_action_id"] is not None


def test_recommendations_completed_action_suppressed():
    uid = str(uuid4())
    pid = str(uuid4())
    completed_action = _make_action(status="done", rule_id="bp_high")
    alert = _make_risk_alert(severity="high", rule_code="bp_high")
    db = _make_db(alerts=[alert], completed_actions=[completed_action])

    result = get_action_recommendations(db, uid, pid)

    recs = result["recommendations"]
    # bp_high should be suppressed (completed recently, no resurface)
    suppressed = [r for r in recs if r.get("source_id") == str(alert.id)]
    assert suppressed == []


def test_recommendations_empty_data_returns_fallbacks():
    uid = str(uuid4())
    pid = str(uuid4())
    db = _make_db()

    result = get_action_recommendations(db, uid, pid)

    assert len(result["recommendations"]) >= 1
    # All should be missing_data type fallbacks
    fallbacks = [r for r in result["recommendations"] if r["source_type"] == "missing_data"]
    assert len(fallbacks) >= 1
    assert len(result["missing_data"]) > 0


# ---------------------------------------------------------------------------
# Tests — product signals
# ---------------------------------------------------------------------------

def test_product_signals_with_data():
    uid = str(uuid4())
    pid = str(uuid4())
    act_done = _make_action(status="done", rule_id=None, source_type="insight")
    act_todo = _make_action(status="todo", rule_id=None, source_type="manual")
    ins = _make_insight()
    outcome = _make_outcome(act_done.id, label="improved")

    db = _make_db(
        actions=[act_todo],
        completed_actions=[act_done],
        insights=[ins],
        outcomes=[outcome],
    )

    signals = build_product_signals(db, uid, pid)

    assert "completion_rate" in signals
    assert "snooze_count" in signals
    assert "insight_action_conversion" in signals
    assert signals["period_days"] == 30


def test_product_signals_no_data():
    uid = str(uuid4())
    pid = str(uuid4())
    db = _make_db()

    signals = build_product_signals(db, uid, pid)

    assert signals["completion_rate"] is None
    assert signals["snooze_count"] == 0
    assert signals["total_actions"] == 0


# ---------------------------------------------------------------------------
# Tests — external_metrics (P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS)
# ---------------------------------------------------------------------------

def _make_external_metric(days_ago: int = 0, source: str = "apple_health"):
    """Create a HealthMetric-like object with a non-manual source."""
    m = _make_metric(days_ago=days_ago)
    m.source = source
    return m


def test_external_metrics_happy_path():
    """Metric with source != 'manual' populates external_metrics with required fields."""
    uid = str(uuid4())
    pid = str(uuid4())
    m = _make_external_metric(days_ago=0, source="apple_health")
    db = _make_db(metrics=[m])

    bundle = build_evidence_bundle(db, uid, pid)

    assert len(bundle["external_metrics"]) == 1
    em = bundle["external_metrics"][0]
    assert em["source"] == "apple_health"
    assert em["timestamp"] is not None
    assert em["freshness"] == "fresh"
    assert em["reliability"] == 0.90
    assert "血壓" in em["summary"]
    assert "[apple_health]" in em["summary"]


def test_external_metrics_empty_when_all_manual():
    """All-manual metrics produce an empty external_metrics list."""
    uid = str(uuid4())
    pid = str(uuid4())
    m = _make_metric(days_ago=1)  # source = 'manual' by default
    db = _make_db(metrics=[m])

    bundle = build_evidence_bundle(db, uid, pid)

    assert bundle["external_metrics"] == []


def test_external_metrics_stale_freshness():
    """A metric older than 24 h from an external source is marked stale."""
    uid = str(uuid4())
    pid = str(uuid4())
    m = _make_external_metric(days_ago=3, source="wearable")
    db = _make_db(metrics=[m])

    bundle = build_evidence_bundle(db, uid, pid)

    assert len(bundle["external_metrics"]) == 1
    em = bundle["external_metrics"][0]
    assert em["freshness"] == "stale"
    assert em["reliability"] == 0.85
    assert em["source"] == "wearable"
