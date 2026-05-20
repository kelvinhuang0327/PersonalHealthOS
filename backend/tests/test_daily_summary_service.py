"""Tests for generate_daily_health_summary() — P1 Daily Summary Engine.

Coverage:
  - full-data summary: topRisk from alert, change from outcome, action from rec
  - empty-data summary: fallback strings, low confidence, missingData present
  - topRisk: alert > high-priority rec > long-term symptom > rec > fallback
  - biggestChange: from outcome delta, from metric trend, no data fallback
  - confidence: scales with evidence completeness
  - encouragement: streak ≥ 7, streak ≥ 3, positive outcome, completed count, new user
  - missingData absent when no missing data
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.health_assistant_service import (
    _compute_confidence,
    _derive_biggest_change,
    _derive_encouragement,
    _derive_today_action_and_why,
    _derive_top_risk,
    generate_daily_health_summary,
)


# ---------------------------------------------------------------------------
# Helpers (mirrored from test_health_assistant_service.py)
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


def _make_metric(days_ago=1, weight=70.5, bp_sys=130):
    m = SimpleNamespace()
    m.id = uuid4()
    m.recorded_at = _utc(days_ago)
    m.systolic_bp = bp_sys
    m.diastolic_bp = 85
    m.heart_rate = 72
    m.blood_glucose = 95.0
    m.weight_kg = weight
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


def _make_lab_item(report_id, item_name="HbA1c", value=7.2):
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
    i.abnormal_flag = "H"
    i.parser_confidence = 0.9
    return i


def _make_action(status="todo", rule_id=None, streak_count=0):
    a = SimpleNamespace()
    a.id = uuid4()
    a.title = "每日量血壓"
    a.status = status
    a.priority = "high"
    a.category = "bp"
    a.action_type = "lifestyle"
    a.source_type = "manual"
    a.source_id = None
    a.rule_id = rule_id
    a.confidence = 0.8
    a.evidence_level = "B"
    a.resurface_count = 0
    a.streak_count = streak_count
    a.due_date = None
    a.snoozed_until = None
    a.completed_at = _utc(2) if status == "done" else None
    a.created_at = _utc(5)
    return a


def _make_risk_alert(severity="high", title="血壓偏高"):
    ra = SimpleNamespace()
    ra.id = uuid4()
    ra.severity = severity
    ra.risk_type = "cardiovascular"
    ra.rule_code = "bp_high"
    ra.title = title
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


def _make_outcome(action_id=None, label="improved", metric_type="systolic_bp", delta=-12.0):
    o = SimpleNamespace()
    o.id = uuid4()
    o.action_id = action_id or uuid4()
    o.metric_type = metric_type
    o.before_value = 140.0
    o.after_value = 128.0
    o.delta = delta
    o.delta_pct = -8.5
    o.time_window_days = 7
    o.outcome_label = label
    o.computed_at = _utc(1)
    return o


def _make_person():
    p = SimpleNamespace()
    p.id = uuid4()
    p.display_name = "測試用戶"
    p.relationship = "self"
    p.birth_date = None
    p.gender = "M"
    p.height_cm = 170
    p.weight_kg = 70.5
    p.chronic_conditions = []
    p.allergies = []
    p.family_history = []
    return p


class _FakeQuery:
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

    active = actions or []
    done = completed_actions or []

    def query_dispatch(model):
        mapping = {
            UserProfile: _FakeQuery([user_profile] if user_profile else []),
            PersonProfile: _FakeQuery([person] if person else []),
            SymptomLog: _FakeQuery(symptoms or []),
            HealthMetric: _FakeQuery(metrics or []),
            LabReport: _FakeQuery(reports or []),
            LabReportItem: _FakeQuery(lab_items or []),
            RiskAlert: _FakeQuery(alerts or []),
            HealthInsight: _FakeQuery(insights or []),
            HealthAction: _FakeQuery(active + done),
            ActionOutcome: _FakeQuery(outcomes or []),
        }
        return mapping.get(model, _FakeQuery([]))

    db.query.side_effect = query_dispatch
    return db


# ---------------------------------------------------------------------------
# Tests — generate_daily_health_summary (integration-style, no real DB)
# ---------------------------------------------------------------------------

def test_daily_summary_full_data():
    """Full evidence → topRisk from alert, change from outcome, rec as action."""
    uid = str(uuid4())
    pid = str(uuid4())
    person = _make_person()
    alert = _make_risk_alert(severity="high", title="血壓偏高")
    metric = _make_metric(days_ago=1, bp_sys=130)
    outcome_obj = _make_outcome(label="improved", metric_type="systolic_bp", delta=-12.0)
    action = _make_action(status="done", streak_count=0)
    action.completed_at = _utc(2)
    insight = _make_insight(severity="warning")

    db = _make_db(
        person=person,
        metrics=[metric],
        alerts=[alert],
        insights=[insight],
        completed_actions=[action],
        outcomes=[outcome_obj],
    )

    result = generate_daily_health_summary(db, uid, pid)

    assert result["person_id"] == pid
    assert "generated_at" in result
    assert "血壓偏高" in result["topRisk"]
    assert "高風險" in result["topRisk"] or "high" in result["topRisk"].lower() or "高風險" in result["topRisk"]
    assert "收縮壓" in result["biggestChange"]
    assert isinstance(result["todayAction"], str)
    assert len(result["todayAction"]) > 0
    assert isinstance(result["whyNow"], str)
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence"] > 0.20  # has alert + metric + outcome


def test_daily_summary_empty_data():
    """No evidence → fallback strings, low confidence, missingData present."""
    uid = str(uuid4())
    pid = str(uuid4())
    db = _make_db()

    result = generate_daily_health_summary(db, uid, pid)

    assert isinstance(result["topRisk"], str)
    assert isinstance(result["biggestChange"], str)
    assert "missingData" in result
    assert len(result["missingData"]) > 0
    assert result["confidence"] == 0.20  # minimum when no data


def test_daily_summary_missing_data_absent_when_complete():
    """When all evidence categories are present, missingData is omitted."""
    uid = str(uuid4())
    pid = str(uuid4())
    person = _make_person()
    sym = _make_symptom(days_ago=1, severity=5)
    metric = _make_metric(days_ago=1)
    report = _make_lab_report(days_ago=5)
    item = _make_lab_item(report.id)
    alert = _make_risk_alert()
    insight = _make_insight()
    action = _make_action(status="todo")
    outcome_obj = _make_outcome()

    db = _make_db(
        person=person,
        symptoms=[sym],
        metrics=[metric],
        reports=[report],
        lab_items=[item],
        alerts=[alert],
        insights=[insight],
        actions=[action],
        outcomes=[outcome_obj],
    )

    result = generate_daily_health_summary(db, uid, pid)

    # missingData is absent (no key) or present but empty
    assert result.get("missingData", []) == []


# ---------------------------------------------------------------------------
# Tests — _derive_top_risk
# ---------------------------------------------------------------------------

def test_top_risk_from_alert():
    alert = {"title": "血壓偏高", "severity": "high"}
    result = _derive_top_risk([alert], [], [], [])
    assert "血壓偏高" in result
    assert "高風險" in result


def test_top_risk_critical_label():
    alert = {"title": "心臟警示", "severity": "critical"}
    result = _derive_top_risk([alert], [], [], [])
    assert "嚴重" in result


def test_top_risk_from_high_priority_rec_when_no_alert():
    recs = [{"title": "立即就醫", "priority": "high", "source_type": "risk_alert"}]
    result = _derive_top_risk([], recs, [], [])
    assert "立即就醫" in result


def test_top_risk_from_long_term_symptom():
    sym = {"symptom": "胸悶", "severity": 8, "source_type": "symptom"}
    result = _derive_top_risk([], [], [sym], [])
    assert "胸悶" in result


def test_top_risk_missing_data_fallback():
    missing = ["a", "b", "c"]
    result = _derive_top_risk([], [], [], missing)
    assert "資料不足" in result


def test_top_risk_no_risk_fallback():
    result = _derive_top_risk([], [], [], [])
    assert "未偵測" in result


def test_top_risk_picks_highest_severity_alert():
    alerts = [
        {"title": "輕微警示", "severity": "low"},
        {"title": "嚴重心臟問題", "severity": "critical"},
        {"title": "中度風險", "severity": "medium"},
    ]
    result = _derive_top_risk(alerts, [], [], [])
    assert "嚴重心臟問題" in result


# ---------------------------------------------------------------------------
# Tests — _derive_biggest_change
# ---------------------------------------------------------------------------

def test_biggest_change_from_outcome():
    outcome = {
        "metric_type": "systolic_bp",
        "delta": -12.0,
        "outcome_label": "improved",
        "time_window_days": 7,
    }
    result = _derive_biggest_change([outcome], [])
    assert "收縮壓" in result
    assert "12.0" in result
    assert "改善" in result


def test_biggest_change_positive_bp_outcome():
    """Delta > 0 for BP (lower is better) should show 上升."""
    outcome = {
        "metric_type": "systolic_bp",
        "delta": 10.0,
        "outcome_label": "worsened",
        "time_window_days": 7,
    }
    result = _derive_biggest_change([outcome], [])
    assert "收縮壓" in result
    assert "上升" in result


def test_biggest_change_from_metric_trend():
    m1 = {"systolic_bp": 120, "weight_kg": 70.0, "blood_glucose": None, "sleep_hours": None}
    m2 = {"systolic_bp": 135, "weight_kg": 72.0, "blood_glucose": None, "sleep_hours": None}
    result = _derive_biggest_change([], [m1, m2])
    # BP dropped from 135 → 120 (newest first), delta = -15 → 改善
    assert "收縮壓" in result or "體重" in result


def test_biggest_change_no_data():
    result = _derive_biggest_change([], [])
    assert "近期無明顯數據變化" in result


def test_biggest_change_below_threshold_ignored():
    """BP change of 2mmHg (< 5 threshold) should not be reported."""
    m1 = {"systolic_bp": 130, "weight_kg": None, "blood_glucose": None, "sleep_hours": None}
    m2 = {"systolic_bp": 132, "weight_kg": None, "blood_glucose": None, "sleep_hours": None}
    result = _derive_biggest_change([], [m1, m2])
    assert "近期無明顯數據變化" in result


# ---------------------------------------------------------------------------
# Tests — _compute_confidence
# ---------------------------------------------------------------------------

def test_confidence_minimum_no_data():
    result = _compute_confidence({}, ["個人健康檔案", "症狀記錄", "健康指標（血壓、血糖、體重等）"])
    assert result == 0.20


def test_confidence_all_data():
    summary = {
        "symptom_count": 2,
        "metric_count": 5,
        "abnormal_lab_count": 1,
        "insight_count": 3,
        "active_alert_count": 1,
        "outcome_count": 2,
    }
    result = _compute_confidence(summary, [])
    assert result == 0.95  # 0.15 + 0.20 + 0.20 + 0.15 + 0.15 + 0.10 + 0.05 = 1.00 → capped at 0.95


def test_confidence_partial_data():
    summary = {"symptom_count": 1, "metric_count": 3}
    result = _compute_confidence(summary, ["健康指標（血壓、血糖、體重等）"])
    # 0.15 (symptom) + 0.20 (metric) + 0.05 (profile not missing) = 0.40
    assert result == 0.40


def test_confidence_profile_adds_small_bonus():
    # Use metric_count too so score isn't clamped to 0.20 minimum in both cases
    summary = {"symptom_count": 1, "metric_count": 1}
    without_profile = _compute_confidence(summary, ["個人健康檔案"])  # 0.15 + 0.20 = 0.35
    with_profile = _compute_confidence(summary, [])                  # 0.15 + 0.20 + 0.05 = 0.40
    assert with_profile > without_profile
    assert abs(with_profile - without_profile - 0.05) < 0.001


# ---------------------------------------------------------------------------
# Tests — _derive_encouragement
# ---------------------------------------------------------------------------

def test_encouragement_high_streak():
    actions = [{"streak_count": 10}]
    result = _derive_encouragement(actions, [], [])
    assert result is not None
    assert "10" in result
    assert "連續" in result


def test_encouragement_mid_streak():
    actions = [{"streak_count": 4}]
    result = _derive_encouragement(actions, [], [])
    assert result is not None
    assert "4" in result


def test_encouragement_positive_outcome():
    outcomes = [{"outcome_label": "improved", "metric_type": "systolic_bp"}]
    result = _derive_encouragement([{"streak_count": 0}], [], outcomes)
    assert result is not None
    assert "收縮壓" in result  # _METRIC_LABEL maps systolic_bp → 收縮壓


def test_encouragement_completed_many():
    completed = [
        {"title": f"行動 {i}"} for i in range(6)
    ]
    result = _derive_encouragement([], completed, [])
    assert result is not None
    assert "6" in result


def test_encouragement_completed_one():
    completed = [{"title": "每日量血壓"}]
    result = _derive_encouragement([], completed, [])
    assert result is not None
    assert "每日量血壓" in result


def test_encouragement_new_user():
    result = _derive_encouragement([], [], [])
    assert result is not None
    assert "每天" in result


def test_encouragement_none_when_active_but_no_trigger():
    """Active actions with low streak and no completed actions → None."""
    actions = [{"streak_count": 1}, {"streak_count": 2}]
    result = _derive_encouragement(actions, [], [])
    assert result is None


# ---------------------------------------------------------------------------
# Tests — _derive_today_action_and_why
# ---------------------------------------------------------------------------

def test_today_action_prefers_non_tracking():
    recs = [
        {"title": "追蹤中行動", "why_now": "已追蹤", "is_tracking": True, "source_type": "risk_alert"},
        {"title": "新行動", "why_now": "立即需要", "is_tracking": False, "source_type": "insight"},
    ]
    action, why = _derive_today_action_and_why(recs)
    assert action == "新行動"
    assert why == "立即需要"


def test_today_action_accepts_tracking_if_no_other():
    recs = [
        {"title": "追蹤中行動", "why_now": "已追蹤", "is_tracking": True, "source_type": "risk_alert"},
    ]
    action, why = _derive_today_action_and_why(recs)
    assert action == "追蹤中行動"


def test_today_action_skips_missing_data_type():
    recs = [
        {"title": "記錄健康指標", "why_now": "缺資料", "is_tracking": False, "source_type": "missing_data"},
        {"title": "就醫評估", "why_now": "有症狀", "is_tracking": False, "source_type": "insight"},
    ]
    action, why = _derive_today_action_and_why(recs)
    assert action == "就醫評估"


def test_today_action_fallback_to_missing_data_when_only_option():
    recs = [
        {"title": "記錄健康指標", "why_now": "缺資料", "is_tracking": False, "source_type": "missing_data"},
    ]
    action, why = _derive_today_action_and_why(recs)
    assert action == "記錄健康指標"


def test_today_action_empty_recs():
    action, why = _derive_today_action_and_why([])
    assert action == "記錄今日健康狀況"
    assert len(why) > 0
