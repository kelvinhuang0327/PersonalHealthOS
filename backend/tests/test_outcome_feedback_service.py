"""Tests for compare_expected_vs_actual_outcome() — P1 Outcome Feedback Loop.

Coverage:
  - completed action + ActionOutcome improved → improved
  - completed action + no outcome/metric → insufficient_data (confidence 0.20)
  - completed action + ActionOutcome deteriorated → deteriorated
  - completed action + ActionOutcome no_change → unchanged
  - active action (in_progress / todo) → tracking
  - 7-day window excludes actions completed > 7 days ago
  - 14-day window includes actions completed ≤ 14 days ago
  - 30-day window includes actions completed ≤ 30 days ago
  - all window_days values reflected in response
  - no hallucinated improvement: metric shows worsening → deteriorated
  - derive improved from metrics: BP drops → improved (lower-is-better)
  - derive improved from metrics: sleep rises → improved (higher-is-better)
  - only-before metric → insufficient_data (confidence 0.35)
  - summary counts are accurate across mixed outcomes
  - confidence values: outcome 0.80, metric-both 0.60, no-data 0.20
  - explanation is non-empty for every outcome_status
  - glucose: delta < 0 → improved (lower-is-better)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.entities import ActionOutcome, HealthAction, HealthMetric
from app.services.outcome_feedback_service import compare_expected_vs_actual_outcome


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _make_action(
    status: str = "todo",
    category: str = "bp",
    completed_at: datetime | None = None,
) -> SimpleNamespace:
    a = SimpleNamespace()
    a.id = uuid4()
    a.title = "每日量血壓"
    a.status = status
    a.category = category
    a.completed_at = completed_at
    a.updated_at = _utc(0)
    return a


def _make_outcome(
    action_id: object,
    outcome_label: str = "improved",
    metric_type: str = "systolic_bp",
    before: float = 135.0,
    after: float = 125.0,
    delta: float = -10.0,
) -> SimpleNamespace:
    o = SimpleNamespace()
    o.id = uuid4()
    o.action_id = action_id
    o.metric_type = metric_type
    o.outcome_label = outcome_label
    o.before_value = before
    o.after_value = after
    o.delta = delta
    o.computed_at = _utc(1)
    o.time_window_days = 7
    return o


def _make_metric(
    days_ago: int = 1,
    bp_sys: float = 130.0,
    glucose: float = 95.0,
    weight: float = 70.0,
    sleep: float = 7.0,
    steps: int = 5000,
) -> SimpleNamespace:
    m = SimpleNamespace()
    m.id = uuid4()
    m.recorded_at = _utc(days_ago)
    m.systolic_bp = bp_sys
    m.diastolic_bp = 85.0
    m.heart_rate = 72
    m.blood_glucose = glucose
    m.weight_kg = weight
    m.sleep_hours = sleep
    m.steps = steps
    return m


class _FakeQuery:
    def __init__(self, items: list) -> None:
        self._items = list(items)

    def filter(self, *_a, **_kw) -> "_FakeQuery":
        return self

    def order_by(self, *_a, **_kw) -> "_FakeQuery":
        return self

    def limit(self, n: int) -> "_FakeQuery":
        return _FakeQuery(self._items[:n])

    def all(self) -> list:
        return list(self._items)

    def first(self) -> object:
        return self._items[0] if self._items else None

    def count(self) -> int:
        return len(self._items)


def _make_db(model_map: dict) -> MagicMock:
    db = MagicMock()

    def _dispatch(model: type) -> _FakeQuery:
        return _FakeQuery(model_map.get(model, []))

    db.query.side_effect = _dispatch
    return db


UID = str(uuid4())
PID = str(uuid4())


# ---------------------------------------------------------------------------
# Tests — ActionOutcome-backed results
# ---------------------------------------------------------------------------


def test_completed_action_outcome_improved():
    action = _make_action(status="done", category="bp", completed_at=_utc(3))
    outcome = _make_outcome(
        action.id, outcome_label="improved", metric_type="systolic_bp",
        before=135, after=125, delta=-10,
    )
    db = _make_db({HealthAction: [action], ActionOutcome: [outcome], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    items = result["outcomes"]
    assert len(items) == 1
    assert items[0]["outcome_status"] == "improved"
    assert items[0]["status"] == "completed"
    assert items[0]["evidence_sources"] == ["action_outcome"]
    assert items[0]["confidence"] == 0.80
    assert result["summary"]["improved_count"] == 1


def test_completed_action_outcome_deteriorated():
    action = _make_action(status="done", category="bp", completed_at=_utc(2))
    outcome = _make_outcome(
        action.id, outcome_label="deteriorated", metric_type="systolic_bp",
        before=125, after=140, delta=15,
    )
    db = _make_db({HealthAction: [action], ActionOutcome: [outcome], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["outcome_status"] == "deteriorated"
    assert result["summary"]["deteriorated_count"] == 1


def test_completed_action_outcome_no_change_maps_to_unchanged():
    action = _make_action(status="done", category="bp", completed_at=_utc(2))
    outcome = _make_outcome(
        action.id, outcome_label="no_change", metric_type="systolic_bp",
        before=130, after=130, delta=0,
    )
    db = _make_db({HealthAction: [action], ActionOutcome: [outcome], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["outcome_status"] == "unchanged"
    assert result["summary"]["unchanged_count"] == 1


def test_completed_action_no_data_insufficient():
    """No ActionOutcome and no HealthMetric → insufficient_data, confidence 0.20."""
    action = _make_action(status="done", category="bp", completed_at=_utc(3))
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    item = result["outcomes"][0]
    assert item["outcome_status"] == "insufficient_data"
    assert item["confidence"] == 0.20
    assert item["actual_metric_change"] is None
    assert result["summary"]["insufficient_data_count"] == 1


# ---------------------------------------------------------------------------
# Tests — active action tracking
# ---------------------------------------------------------------------------


def test_active_in_progress_action_is_tracking():
    action = _make_action(status="in_progress", category="sleep")
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    item = result["outcomes"][0]
    assert item["outcome_status"] == "tracking"
    assert item["status"] == "tracking"
    assert item["completed_at"] is None
    assert result["summary"]["tracking_count"] == 1


def test_active_todo_action_is_tracking():
    action = _make_action(status="todo", category="glucose")
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["outcome_status"] == "tracking"


# ---------------------------------------------------------------------------
# Tests — window_days filtering
# ---------------------------------------------------------------------------


def test_7_day_window_excludes_old_action():
    action = _make_action(status="done", category="bp", completed_at=_utc(10))
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    completed = [o for o in result["outcomes"] if o["status"] == "completed"]
    assert len(completed) == 0


def test_14_day_window_includes_10_day_old_action():
    action = _make_action(status="done", category="bp", completed_at=_utc(10))
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=14)

    completed = [o for o in result["outcomes"] if o["status"] == "completed"]
    assert len(completed) == 1


def test_30_day_window_includes_25_day_old_action():
    action = _make_action(status="done", category="bp", completed_at=_utc(25))
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=30)

    completed = [o for o in result["outcomes"] if o["status"] == "completed"]
    assert len(completed) == 1


def test_window_days_reflected_in_response():
    db = _make_db({HealthAction: [], ActionOutcome: [], HealthMetric: []})
    for w in (7, 14, 30):
        result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=w)
        assert result["window_days"] == w


# ---------------------------------------------------------------------------
# Tests — no hallucination
# ---------------------------------------------------------------------------


def test_no_hallucinated_improvement_when_metric_worsens():
    """BP rose after completing action → must be 'deteriorated', never 'improved'."""
    action = _make_action(status="done", category="bp", completed_at=_utc(3))
    metric_before = _make_metric(days_ago=5, bp_sys=120)   # 5 days ago (before)
    metric_after = _make_metric(days_ago=1, bp_sys=135)    # 1 day ago (after)
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [metric_before, metric_after],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    item = result["outcomes"][0]
    assert item["outcome_status"] == "deteriorated"
    assert item["outcome_status"] != "improved"


# ---------------------------------------------------------------------------
# Tests — metric-derived outcomes
# ---------------------------------------------------------------------------


def test_derive_improved_from_bp_metric():
    """BP dropped after action → improved (lower-is-better)."""
    action = _make_action(status="done", category="bp", completed_at=_utc(3))
    metric_before = _make_metric(days_ago=5, bp_sys=135)
    metric_after = _make_metric(days_ago=1, bp_sys=125)
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [metric_before, metric_after],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    item = result["outcomes"][0]
    assert item["outcome_status"] == "improved"
    assert item["confidence"] == 0.60
    assert item["evidence_sources"] == ["health_metric"]
    assert item["actual_metric_change"]["delta"] == pytest.approx(-10.0)


def test_derive_improved_from_glucose_metric():
    """Glucose dropped after action → improved (lower-is-better)."""
    action = _make_action(status="done", category="glucose", completed_at=_utc(3))
    metric_before = _make_metric(days_ago=5, glucose=9.5)
    metric_after = _make_metric(days_ago=1, glucose=8.0)
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [metric_before, metric_after],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["outcome_status"] == "improved"


def test_derive_improved_from_sleep_metric():
    """Sleep increased after action → improved (higher-is-better)."""
    action = _make_action(status="done", category="sleep", completed_at=_utc(3))
    metric_before = _make_metric(days_ago=5, sleep=5.5)
    metric_after = _make_metric(days_ago=1, sleep=7.5)
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [metric_before, metric_after],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["outcome_status"] == "improved"


def test_only_before_metric_insufficient():
    """Only before-completion metrics exist → insufficient_data, confidence 0.35."""
    action = _make_action(status="done", category="bp", completed_at=_utc(1))
    metric_before = _make_metric(days_ago=3, bp_sys=135)   # before completed_at=1
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [metric_before],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    item = result["outcomes"][0]
    assert item["outcome_status"] == "insufficient_data"
    assert item["confidence"] == 0.35


# ---------------------------------------------------------------------------
# Tests — summary counts
# ---------------------------------------------------------------------------


def test_summary_counts_mixed():
    a1 = _make_action(status="done", category="bp", completed_at=_utc(1))
    a2 = _make_action(status="done", category="glucose", completed_at=_utc(2))
    a3 = _make_action(status="in_progress", category="sleep")

    o1 = _make_outcome(a1.id, outcome_label="improved")
    o2 = _make_outcome(a2.id, outcome_label="deteriorated", metric_type="blood_glucose", delta=1.5)

    db = _make_db({
        HealthAction: [a1, a2, a3],
        ActionOutcome: [o1, o2],
        HealthMetric: [],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    s = result["summary"]
    assert s["improved_count"] == 1
    assert s["deteriorated_count"] == 1
    assert s["tracking_count"] == 1
    assert s["total_count"] == 3


def test_summary_empty_when_no_actions():
    db = _make_db({HealthAction: [], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    s = result["summary"]
    assert s["total_count"] == 0
    assert s["improved_count"] == 0


# ---------------------------------------------------------------------------
# Tests — explanations and response structure
# ---------------------------------------------------------------------------


def test_explanation_is_nonempty_for_all_statuses():
    """Every outcome item must carry a non-empty explanation string."""
    a_done = _make_action(status="done", category="bp", completed_at=_utc(2))
    a_active = _make_action(status="in_progress", category="sleep")
    db = _make_db({
        HealthAction: [a_done, a_active],
        ActionOutcome: [],
        HealthMetric: [],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    for item in result["outcomes"]:
        assert isinstance(item["explanation"], str)
        assert len(item["explanation"]) > 0


def test_response_contains_required_keys():
    db = _make_db({HealthAction: [], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=14)

    assert "person_id" in result
    assert "generated_at" in result
    assert "window_days" in result
    assert "outcomes" in result
    assert "summary" in result
    assert result["person_id"] == PID


def test_confidence_action_outcome_is_0_80():
    action = _make_action(status="done", category="bp", completed_at=_utc(1))
    outcome = _make_outcome(action.id, outcome_label="improved")
    db = _make_db({HealthAction: [action], ActionOutcome: [outcome], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["confidence"] == 0.80


def test_confidence_metric_derived_is_0_60():
    action = _make_action(status="done", category="bp", completed_at=_utc(3))
    before = _make_metric(days_ago=5, bp_sys=135)
    after = _make_metric(days_ago=1, bp_sys=125)
    db = _make_db({
        HealthAction: [action],
        ActionOutcome: [],
        HealthMetric: [before, after],
    })
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["confidence"] == 0.60


def test_tracking_action_confidence_is_0():
    action = _make_action(status="todo", category="glucose")
    db = _make_db({HealthAction: [action], ActionOutcome: [], HealthMetric: []})
    result = compare_expected_vs_actual_outcome(db, UID, PID, window_days=7)

    assert result["outcomes"][0]["confidence"] == 0.0
