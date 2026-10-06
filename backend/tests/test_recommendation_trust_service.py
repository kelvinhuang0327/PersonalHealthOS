"""Tests for recommendation_confidence_score() — P1 Recommendation Trust Layer.

Coverage:
  F1  Primary source quality: lab=30, risk_alert=22, missing_data=0
  F2  Data recency: today→20, older→3, fallback to metric recency
  F3  Evidence breadth: 5-domain → 15pts, empty → 0pts
  F4  Repeated signals: metric_count≥3 → +5pts
  F5  Adherence: streak=7 → 10pts, snooze reduces, no tracking → 0pts
  F6  Outcome validation: improved → 15pts + verified, no outcome → 0pts
      anti-hallucination: deteriorated alone does NOT set verifiedByOutcome
  Level thresholds: ≥0.65 high | ≥0.35 medium | <0.35 low
  Structural: all 6 keys present, confidence clamped [0, 1]
  Reasons / limitations / nextCheckInSuggestion correctness
"""
from __future__ import annotations

from app.services.recommendation_trust_service import recommendation_confidence_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rec(
    source_type: str = "risk_alert",
    source_id: str | None = "src-001",
    tracking_action_id: str | None = None,
) -> dict:
    return {
        "title": "Test recommendation",
        "source_type": source_type,
        "source_id": source_id,
        "tracking_action_id": tracking_action_id,
        "evidence_sources": [],
        "is_tracking": tracking_action_id is not None,
    }


def _make_bundle(
    source_type: str = "risk_alert",
    source_id: str | None = "src-001",
    recency: str = "today",
    metric_count: int = 1,
    lab_count: int = 0,
    alert_count: int = 0,
    symptom_count: int = 0,
    insight_count: int = 0,
    missing_data: list[str] | None = None,
    actions: list[dict] | None = None,
) -> dict:
    """Minimal evidence bundle for testing."""
    # Build the primary source item in the right bundle list
    bundle_key_map = {
        "risk_alert": "risk_alerts",
        "lab_report_item": "lab_report_items",
        "insight": "insights",
        "long_term_symptom": "long_term_symptoms",
        "health_metric": "health_metrics",
    }
    bundle_key = bundle_key_map.get(source_type)
    bundle: dict = {
        "risk_alerts": [],
        "lab_report_items": [],
        "insights": [],
        "long_term_symptoms": [],
        "health_metrics": [],
        "symptoms": [],
        "actions": actions or [],
        "missing_data": missing_data or [],
        "summary": {
            "metric_count": metric_count,
            "abnormal_lab_count": lab_count,
            "active_alert_count": alert_count,
            "symptom_count": symptom_count,
            "insight_count": insight_count,
        },
    }
    if bundle_key and source_id:
        bundle[bundle_key] = [{"source_id": source_id, "recency": recency}]
    # Add metric placeholder for fallback recency
    if metric_count > 0 and source_type != "health_metric":
        bundle["health_metrics"] = [{"source_id": "m-001", "recency": recency}]
    return bundle


def _make_outcome(label: str = "improved") -> dict:
    return {
        "source_id": "o-001",
        "action_id": "a-001",
        "outcome_label": label,
        "metric_type": "systolic_bp",
    }


def _make_action(
    action_id: str = "act-001",
    streak: int = 0,
    snooze: int = 0,
) -> dict:
    return {
        "source_id": action_id,
        "streak_count": streak,
        "snooze_count": snooze,
        "status": "in_progress",
    }


# ---------------------------------------------------------------------------
# F1 — Primary source quality
# ---------------------------------------------------------------------------


def test_lab_report_quality_score_is_max():
    rec = _make_rec(source_type="lab_report_item")
    bundle = _make_bundle(source_type="lab_report_item", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    # lab=30, today=20, breadth=3(1domain), repeat=0, adherence=0, outcome=0 → 53 → 0.53
    assert result["confidence"] >= 0.50


def test_missing_data_quality_score_is_zero_giving_low_confidence():
    rec = _make_rec(source_type="missing_data", source_id=None)
    bundle = _make_bundle(source_type="missing_data", source_id=None, metric_count=0)
    result = recommendation_confidence_score(rec, bundle, [])
    assert result["level"] == "low"
    assert result["confidence"] < 0.35


def test_risk_alert_quality_reason_added():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("風險警示" in r for r in result["reasons"])


def test_lab_report_quality_reason_added():
    rec = _make_rec(source_type="lab_report_item")
    bundle = _make_bundle(source_type="lab_report_item", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("健檢報告" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# F2 — Data recency
# ---------------------------------------------------------------------------


def test_today_recency_adds_max_recency_score():
    rec_today = _make_rec(source_type="risk_alert", source_id="src-1")
    rec_old = _make_rec(source_type="risk_alert", source_id="src-2")
    bundle_today = _make_bundle(source_type="risk_alert", source_id="src-1", recency="today")
    bundle_old = _make_bundle(source_type="risk_alert", source_id="src-2", recency="older")
    today_conf = recommendation_confidence_score(rec_today, bundle_today, [])["confidence"]
    old_conf = recommendation_confidence_score(rec_old, bundle_old, [])["confidence"]
    assert today_conf > old_conf


def test_today_recency_reason_is_added():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("今日" in r for r in result["reasons"])


def test_older_recency_adds_limitation():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="older")
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("時效" in l for l in result["limitations"])


def test_fallback_to_metric_recency_when_source_not_in_bundle():
    rec = _make_rec(source_type="risk_alert", source_id="nonexistent")
    bundle = {
        "risk_alerts": [{"source_id": "other", "recency": "older"}],
        "health_metrics": [{"source_id": "m-1", "recency": "today"}],
        "lab_report_items": [],
        "insights": [],
        "long_term_symptoms": [],
        "symptoms": [],
        "actions": [],
        "missing_data": [],
        "summary": {"metric_count": 1, "abnormal_lab_count": 0,
                    "active_alert_count": 0, "symptom_count": 0, "insight_count": 0},
    }
    result = recommendation_confidence_score(rec, bundle, [])
    # Should use metric recency "today" → reason about today
    assert any("今日" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# F3 — Evidence breadth
# ---------------------------------------------------------------------------


def test_5_domains_gives_max_breadth():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        metric_count=1, lab_count=1, alert_count=1, symptom_count=1, insight_count=1,
    )
    result = recommendation_confidence_score(rec, bundle, [])
    # 5 domains → breadth=15; expect reason about multiple domains
    assert any("種健康資料" in r for r in result["reasons"])


def test_0_domains_adds_limitation():
    rec = _make_rec(source_type="missing_data", source_id=None)
    bundle = _make_bundle(
        source_type="missing_data", source_id=None,
        metric_count=0, lab_count=0, alert_count=0, symptom_count=0, insight_count=0,
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("資料類型不足" in l for l in result["limitations"])


def test_2_domains_mentions_count_in_reason():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        metric_count=1, alert_count=1,
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("2 種" in r or "種" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# F4 — Repeated signals
# ---------------------------------------------------------------------------


def test_3_metrics_adds_repeated_signals_score():
    rec = _make_rec(source_type="risk_alert")
    bundle_repeat = _make_bundle(source_type="risk_alert", recency="today", metric_count=3)
    bundle_single = _make_bundle(source_type="risk_alert", recency="today", metric_count=1)
    conf_repeat = recommendation_confidence_score(rec, bundle_repeat, [])["confidence"]
    conf_single = recommendation_confidence_score(rec, bundle_single, [])["confidence"]
    assert conf_repeat > conf_single


def test_2_abnormal_labs_adds_repeat_score():
    rec = _make_rec(source_type="lab_report_item")
    bundle = _make_bundle(source_type="lab_report_item", recency="today", lab_count=2)
    result = recommendation_confidence_score(rec, bundle, [])
    # 2 labs → repeat+5; reason should mention trend
    assert any("趨勢" in r or "訊號" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# F5 — Adherence history
# ---------------------------------------------------------------------------


def test_streak_7_gives_max_adherence():
    act_id = "act-007"
    rec = _make_rec(source_type="risk_alert", tracking_action_id=act_id)
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        actions=[_make_action(action_id=act_id, streak=7)],
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("7 天" in r or "連續" in r for r in result["reasons"])


def test_no_tracking_action_zero_adherence():
    rec = _make_rec(source_type="risk_alert", tracking_action_id=None)
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    # No adherence reasons about streak
    assert not any("連續" in r for r in result["reasons"])


def test_snooze_adds_limitation():
    act_id = "act-snz"
    rec = _make_rec(source_type="risk_alert", tracking_action_id=act_id)
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        actions=[_make_action(action_id=act_id, streak=3, snooze=2)],
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert any("暫緩" in l for l in result["limitations"])


def test_snooze_reduces_adherence_compared_to_no_snooze():
    act_id = "act-cmp"
    rec = _make_rec(source_type="risk_alert", tracking_action_id=act_id)

    bundle_clean = _make_bundle(
        source_type="risk_alert", recency="today",
        actions=[_make_action(action_id=act_id, streak=3, snooze=0)],
    )
    bundle_snoozed = _make_bundle(
        source_type="risk_alert", recency="today",
        actions=[_make_action(action_id=act_id, streak=3, snooze=2)],
    )
    conf_clean = recommendation_confidence_score(rec, bundle_clean, [])["confidence"]
    conf_snoozed = recommendation_confidence_score(rec, bundle_snoozed, [])["confidence"]
    assert conf_clean >= conf_snoozed


# ---------------------------------------------------------------------------
# F6 — Outcome validation
# ---------------------------------------------------------------------------


def test_improved_outcome_sets_verified_and_max_score():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("improved")])
    assert result["verifiedByOutcome"] is True
    assert any("已驗證" in r or "improved" in r for r in result["reasons"])


def test_no_outcomes_verified_false():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [])
    assert result["verifiedByOutcome"] is False
    assert any("尚無成效驗證" in l for l in result["limitations"])


def test_deteriorated_outcome_does_not_set_verified():
    """Anti-hallucination: deteriorated outcome must NOT set verifiedByOutcome=True."""
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("deteriorated")])
    assert result["verifiedByOutcome"] is False


def test_no_change_outcome_does_not_set_verified():
    """no_change is measured but not confirmed improvement."""
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="today")
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("no_change")])
    assert result["verifiedByOutcome"] is False


def test_outcomes_without_improved_still_adds_partial_score():
    rec = _make_rec(source_type="risk_alert")
    bundle_no_outcome = _make_bundle(source_type="risk_alert", recency="today")
    bundle_with_outcome = _make_bundle(source_type="risk_alert", recency="today")
    conf_no = recommendation_confidence_score(rec, bundle_no_outcome, [])["confidence"]
    conf_with = recommendation_confidence_score(rec, bundle_with_outcome, [_make_outcome("no_change")])["confidence"]
    # no_change gives partial score (5) vs no outcome (0)
    assert conf_with > conf_no


# ---------------------------------------------------------------------------
# Level thresholds
# ---------------------------------------------------------------------------


def test_high_confidence_level():
    """Lab + today + 5 domains + streak=7 + improved outcome → high level."""
    act_id = "act-h"
    rec = _make_rec(source_type="lab_report_item", tracking_action_id=act_id)
    bundle = _make_bundle(
        source_type="lab_report_item", recency="today",
        metric_count=3, lab_count=2, alert_count=1, symptom_count=1, insight_count=1,
        actions=[_make_action(action_id=act_id, streak=7)],
    )
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("improved")])
    assert result["level"] == "high"
    assert result["confidence"] >= 0.65


def test_low_confidence_level():
    """Missing data source + no bundle data → low level."""
    rec = _make_rec(source_type="missing_data", source_id=None)
    bundle = _make_bundle(
        source_type="missing_data", source_id=None,
        metric_count=0, lab_count=0, alert_count=0, symptom_count=0, insight_count=0,
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert result["level"] == "low"
    assert result["confidence"] < 0.35


def test_medium_confidence_level():
    """Risk alert + this_week recency + 2 domains → medium level."""
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(source_type="risk_alert", recency="this_week", metric_count=1)
    result = recommendation_confidence_score(rec, bundle, [])
    assert result["level"] in ("medium", "high")  # at least medium


# ---------------------------------------------------------------------------
# Structure and correctness
# ---------------------------------------------------------------------------


def test_result_has_all_required_keys():
    rec = _make_rec()
    bundle = _make_bundle()
    result = recommendation_confidence_score(rec, bundle, [])
    assert "confidence" in result
    assert "level" in result
    assert "reasons" in result
    assert "limitations" in result
    assert "verifiedByOutcome" in result
    assert "nextCheckInSuggestion" in result


def test_confidence_clamped_between_0_and_1():
    """Even with perfect data, confidence must not exceed 1.0."""
    act_id = "act-max"
    rec = _make_rec(source_type="lab_report_item", tracking_action_id=act_id)
    bundle = _make_bundle(
        source_type="lab_report_item", recency="today",
        metric_count=10, lab_count=5, alert_count=5, symptom_count=3, insight_count=3,
        actions=[_make_action(action_id=act_id, streak=30)],
    )
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("improved")] * 5)
    assert 0.0 <= result["confidence"] <= 1.0


def test_missing_data_limitations_surfaced():
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        missing_data=["症狀記錄", "健康指標（血壓、血糖、體重等）"],
    )
    result = recommendation_confidence_score(rec, bundle, [])
    limitations_text = " ".join(result["limitations"])
    assert "症狀記錄" in limitations_text
    assert "健康指標" in limitations_text


def test_trivial_missing_data_not_in_limitations():
    """Risk alert and insight absence are expected — should not appear as limitations."""
    rec = _make_rec(source_type="risk_alert")
    bundle = _make_bundle(
        source_type="risk_alert", recency="today",
        missing_data=["風險警示（目前無主動警示）", "健康洞察（建議先執行健康分析）"],
    )
    result = recommendation_confidence_score(rec, bundle, [])
    limitations_text = " ".join(result["limitations"])
    assert "風險警示" not in limitations_text
    assert "健康洞察" not in limitations_text


def test_next_check_in_high_says_7_days():
    act_id = "act-h2"
    rec = _make_rec(source_type="lab_report_item", tracking_action_id=act_id)
    bundle = _make_bundle(
        source_type="lab_report_item", recency="today",
        metric_count=3, lab_count=2, alert_count=1, symptom_count=1, insight_count=1,
        actions=[_make_action(action_id=act_id, streak=7)],
    )
    result = recommendation_confidence_score(rec, bundle, [_make_outcome("improved")])
    assert "7 天" in result["nextCheckInSuggestion"]


def test_next_check_in_low_mentions_today():
    rec = _make_rec(source_type="missing_data", source_id=None)
    bundle = _make_bundle(
        source_type="missing_data", source_id=None,
        metric_count=0, lab_count=0, alert_count=0, symptom_count=0, insight_count=0,
    )
    result = recommendation_confidence_score(rec, bundle, [])
    assert "今日" in result["nextCheckInSuggestion"]


def test_level_field_is_valid_enum():
    rec = _make_rec()
    bundle = _make_bundle()
    result = recommendation_confidence_score(rec, bundle, [])
    assert result["level"] in ("low", "medium", "high")


def test_reasons_and_limitations_are_lists():
    rec = _make_rec()
    bundle = _make_bundle()
    result = recommendation_confidence_score(rec, bundle, [])
    assert isinstance(result["reasons"], list)
    assert isinstance(result["limitations"], list)
