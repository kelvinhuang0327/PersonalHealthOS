"""Tests for narrative_memory_service — P7 Narrative Memory + Long-Term Context.

Coverage:
  - build daily / weekly / monthly memory
  - insufficient data → limitations populated
  - repeated risk detection (≥ 2 occurrences)
  - improving item detection (from outcome outcome_label='improved')
  - worsening item detection (from outcome outcome_label='worsened')
  - ignored item detection (from notification history ignore_count > 0)
  - effective action detection (from acted status OR completed action)
  - confidence scaling
  - persist_narrative_memory saves to DB
  - load_narrative_memory returns stored data
  - compare_narrative_periods diffs two periods correctly
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import NarrativeMemory
from app.services.narrative_memory_service import (
    build_narrative_memory,
    compare_narrative_periods,
    load_narrative_memory,
    persist_narrative_memory,
)

# ---------------------------------------------------------------------------
# Shared in-memory DB
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_ENGINE)
Base.metadata.create_all(bind=_ENGINE)

_UID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_PID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _h(
    source_type: str = "lab_abnormality",
    status: str = "generated",
    ignore_count: int = 0,
    sent_at: str | None = None,
) -> dict[str, Any]:
    return {
        "cooldown_key": f"key_{source_type}",
        "source_type": source_type,
        "status": status,
        "priority": "high",
        "ignore_count": ignore_count,
        "snooze_count": 0,
        "sent_at": sent_at or datetime.now(timezone.utc).isoformat(),
        "acted_at": None,
        "clicked_at": None,
        "snoozed_until": None,
    }


def _outcome(metric_type: str, outcome_label: str) -> SimpleNamespace:
    o = SimpleNamespace()
    o.outcome_label = outcome_label
    o.metric_type = metric_type
    o.action = None
    return o


def _action(title: str, status: str = "completed") -> SimpleNamespace:
    a = SimpleNamespace()
    a.title = title
    a.status = status
    a.completed_at = datetime.now(timezone.utc)
    return a


def _alert(source_type: str = "risk_alert") -> SimpleNamespace:
    a = SimpleNamespace()
    a.source_type = source_type
    a.created_at = datetime.now(timezone.utc)
    return a


# ---------------------------------------------------------------------------
# Test — build_narrative_memory
# ---------------------------------------------------------------------------

class TestBuildNarrativeMemory:
    def test_daily_memory_period_type(self):
        result = build_narrative_memory("daily", [], [], [], [])
        assert result["periodType"] == "daily"

    def test_weekly_memory_period_type(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert result["periodType"] == "weekly"

    def test_monthly_memory_period_type(self):
        result = build_narrative_memory("monthly", [], [], [], [])
        assert result["periodType"] == "monthly"

    def test_all_keys_present(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        expected = {
            "periodType", "periodStart", "periodEnd", "summaryText",
            "topThemes", "improvingItems", "worseningItems",
            "repeatedRisks", "effectiveActions", "ignoredItems",
            "confidence", "limitations",
        }
        assert expected <= set(result.keys())

    def test_period_dates_are_iso_strings(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        date.fromisoformat(result["periodStart"])  # must not raise
        date.fromisoformat(result["periodEnd"])

    def test_weekly_period_start_is_7_days_before_end(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        p_start = date.fromisoformat(result["periodStart"])
        p_end = date.fromisoformat(result["periodEnd"])
        assert (p_end - p_start).days == 6  # 7-day window

    def test_monthly_period_is_30_days(self):
        result = build_narrative_memory("monthly", [], [], [], [])
        p_start = date.fromisoformat(result["periodStart"])
        p_end = date.fromisoformat(result["periodEnd"])
        assert (p_end - p_start).days == 29  # 30-day window


class TestInsufficientDataLimitations:
    def test_empty_inputs_populates_limitations(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert len(result["limitations"]) > 0

    def test_no_notifications_mentions_themes_limitation(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        text = " ".join(result["limitations"])
        # Should mention that there's not enough data
        assert "沒有足夠" in text or "尚無" in text or "不足" in text

    def test_no_outcomes_mentions_outcome_limitation(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        text = " ".join(result["limitations"])
        assert "行動成效" in text or "改善" in text

    def test_confidence_low_on_empty_data(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert result["confidence"] < 0.4

    def test_sufficient_data_reduces_limitations(self):
        history = [_h("lab_abnormality") for _ in range(5)]
        alerts = [_alert("lab_abnormality") for _ in range(3)]
        outcomes = [_outcome("systolic_bp", "improved")]
        actions = [_action("每日量血壓")]
        result = build_narrative_memory("weekly", history, alerts, actions, outcomes)
        # Should have fewer limitations than empty case
        empty_result = build_narrative_memory("weekly", [], [], [], [])
        assert len(result["limitations"]) <= len(empty_result["limitations"])


class TestRepeatedRisks:
    def test_no_repeated_risks_on_single_occurrence(self):
        history = [_h("lab_abnormality")]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" not in result["repeatedRisks"]

    def test_repeated_risk_detected_on_two_notifications(self):
        history = [_h("lab_abnormality"), _h("lab_abnormality")]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" in result["repeatedRisks"]

    def test_repeated_risk_from_notifications_and_alerts(self):
        history = [_h("lab_abnormality")]
        alerts = [_alert("lab_abnormality")]
        result = build_narrative_memory("weekly", history, alerts, [], [])
        assert "健檢指標異常" in result["repeatedRisks"]

    def test_multiple_risk_types_all_counted(self):
        history = [
            _h("lab_abnormality"), _h("lab_abnormality"),
            _h("device_escalation"), _h("device_escalation"),
        ]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" in result["repeatedRisks"]
        assert "裝置訊號異常" in result["repeatedRisks"]


class TestImprovingItems:
    def test_no_improving_items_on_empty_outcomes(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert result["improvingItems"] == []

    def test_improving_item_from_improved_outcome(self):
        outcomes = [_outcome("systolic_bp", "improved")]
        result = build_narrative_memory("weekly", [], [], [], outcomes)
        assert any("systolic_bp" in item for item in result["improvingItems"])

    def test_no_improving_item_from_no_change_outcome(self):
        outcomes = [_outcome("systolic_bp", "no_change")]
        result = build_narrative_memory("weekly", [], [], [], outcomes)
        assert result["improvingItems"] == []

    def test_multiple_improving_items(self):
        outcomes = [
            _outcome("systolic_bp", "improved"),
            _outcome("weight_kg", "improved"),
        ]
        result = build_narrative_memory("weekly", [], [], [], outcomes)
        assert len(result["improvingItems"]) == 2


class TestWorseningItems:
    def test_worsening_item_from_worsened_outcome(self):
        outcomes = [_outcome("blood_glucose", "worsened")]
        result = build_narrative_memory("weekly", [], [], [], outcomes)
        assert any("blood_glucose" in item for item in result["worseningItems"])

    def test_no_worsening_on_improved_outcome(self):
        outcomes = [_outcome("systolic_bp", "improved")]
        result = build_narrative_memory("weekly", [], [], [], outcomes)
        assert result["worseningItems"] == []


class TestIgnoredItems:
    def test_no_ignored_items_on_zero_ignore_count(self):
        history = [_h("lab_abnormality", ignore_count=0)]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert result["ignoredItems"] == []

    def test_ignored_item_detected_from_ignore_count(self):
        history = [_h("lab_abnormality", ignore_count=2)]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" in result["ignoredItems"]

    def test_multiple_ignored_source_types(self):
        history = [
            _h("lab_abnormality", ignore_count=1),
            _h("device_escalation", ignore_count=3),
        ]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" in result["ignoredItems"]
        assert "裝置訊號異常" in result["ignoredItems"]


class TestEffectiveActions:
    def test_no_effective_actions_on_empty(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert result["effectiveActions"] == []

    def test_effective_action_from_acted_notification(self):
        history = [_h("recommendation", status="acted")]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健康建議" in result["effectiveActions"]

    def test_effective_action_from_completed_action(self):
        actions = [_action("每日量血壓", status="completed")]
        result = build_narrative_memory("weekly", [], [], actions, [])
        assert "每日量血壓" in result["effectiveActions"]

    def test_no_effective_action_from_todo_action(self):
        actions = [_action("每日量血壓", status="todo")]
        result = build_narrative_memory("weekly", [], [], actions, [])
        assert "每日量血壓" not in result["effectiveActions"]


class TestTopThemes:
    def test_top_themes_from_notifications(self):
        history = [_h("lab_abnormality") for _ in range(3)]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert "健檢指標異常" in result["topThemes"]

    def test_top_themes_max_3(self):
        history = [
            _h("lab_abnormality"), _h("lab_abnormality"),
            _h("device_escalation"), _h("device_escalation"),
            _h("symptom_pattern"), _h("symptom_pattern"),
            _h("risk_alert"), _h("risk_alert"),
        ]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert len(result["topThemes"]) <= 3

    def test_top_themes_ordered_by_frequency(self):
        history = (
            [_h("lab_abnormality")] * 5
            + [_h("device_escalation")] * 2
        )
        result = build_narrative_memory("weekly", history, [], [], [])
        assert result["topThemes"][0] == "健檢指標異常"


class TestConfidenceScaling:
    def test_confidence_zero_on_empty(self):
        result = build_narrative_memory("weekly", [], [], [], [])
        assert result["confidence"] == 0.0

    def test_confidence_increases_with_notifications(self):
        history = [_h() for _ in range(10)]
        result = build_narrative_memory("weekly", history, [], [], [])
        assert result["confidence"] > 0.0

    def test_confidence_increases_with_outcomes(self):
        outcomes = [_outcome("systolic_bp", "improved")]
        result_with = build_narrative_memory("weekly", [], [], [], outcomes)
        result_without = build_narrative_memory("weekly", [], [], [], [])
        assert result_with["confidence"] > result_without["confidence"]

    def test_confidence_capped_at_1(self):
        history = [_h() for _ in range(50)]
        alerts = [_alert() for _ in range(10)]
        outcomes = [_outcome(f"metric_{i}", "improved") for i in range(5)]
        result = build_narrative_memory("weekly", history, alerts, [], outcomes)
        assert result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Test — persist and load
# ---------------------------------------------------------------------------

class TestPersistAndLoad:
    def setup_method(self):
        self.db = _Session()

    def teardown_method(self):
        self.db.close()

    def test_persist_creates_row(self):
        memory = build_narrative_memory("weekly", [_h()], [], [], [])
        row = persist_narrative_memory(self.db, _UID, _PID, memory)
        assert row.id is not None
        assert row.period_type == "weekly"

    def test_persist_upserts_same_period(self):
        # Generate memory for today's week
        memory1 = build_narrative_memory("weekly", [_h()], [], [], [])
        row1 = persist_narrative_memory(self.db, _UID, _PID, memory1)
        row1_id = row1.id

        # Persist again for the same period — should update, not create new
        memory2 = build_narrative_memory("weekly", [_h(), _h()], [], [], [])
        # Force same period_start to trigger upsert
        memory2["periodStart"] = memory1["periodStart"]
        row2 = persist_narrative_memory(self.db, _UID, _PID, memory2)
        assert row2.id == row1_id

    def test_load_returns_stored_memory(self):
        memory = build_narrative_memory("daily", [_h()], [], [], [])
        persist_narrative_memory(self.db, _UID, _PID, memory)
        loaded = load_narrative_memory(self.db, _UID, _PID, period_type="daily")
        assert len(loaded) >= 1
        assert loaded[0]["periodType"] == "daily"

    def test_load_empty_returns_empty_list(self):
        import uuid
        uid2 = str(uuid.uuid4())
        pid2 = str(uuid.uuid4())
        result = load_narrative_memory(self.db, uid2, pid2, period_type="monthly")
        assert result == []

    def test_load_returns_newest_first(self):
        """Two different daily periods should be returned newest-first."""
        from app.services.narrative_memory_service import _period_window
        import uuid
        uid3 = str(uuid.uuid4())
        pid3 = str(uuid.uuid4())

        # Persist an older daily
        mem_old = build_narrative_memory("daily", [_h()], [], [], [])
        mem_old["periodStart"] = (date.today() - timedelta(days=2)).isoformat()
        mem_old["periodEnd"] = (date.today() - timedelta(days=2)).isoformat()
        persist_narrative_memory(self.db, uid3, pid3, mem_old)

        # Persist a newer daily (today)
        mem_new = build_narrative_memory("daily", [_h(), _h()], [], [], [])
        persist_narrative_memory(self.db, uid3, pid3, mem_new)

        loaded = load_narrative_memory(self.db, uid3, pid3, period_type="daily")
        assert len(loaded) >= 2
        # Newest first
        assert loaded[0]["periodStart"] >= loaded[1]["periodStart"]

    def test_persist_stores_top_themes(self):
        history = [_h("lab_abnormality"), _h("lab_abnormality")]
        memory = build_narrative_memory("weekly", history, [], [], [])
        row = persist_narrative_memory(self.db, _UID, _PID, memory)
        assert "健檢指標異常" in row.top_themes_json

    def test_persist_stores_limitations(self):
        memory = build_narrative_memory("weekly", [], [], [], [])
        row = persist_narrative_memory(self.db, _UID, _PID, memory)
        assert isinstance(row.limitations_json, list)
        assert len(row.limitations_json) > 0


# ---------------------------------------------------------------------------
# Test — compare_narrative_periods
# ---------------------------------------------------------------------------

class TestCompareNarrativePeriods:
    def _make(self, themes=None, risks=None, improving=None, effective=None, confidence=0.5):
        return {
            "topThemes": themes or [],
            "repeatedRisks": risks or [],
            "improvingItems": improving or [],
            "effectiveActions": effective or [],
            "confidence": confidence,
        }

    def test_new_theme_detected(self):
        curr = self._make(themes=["健檢指標異常", "裝置訊號異常"])
        prev = self._make(themes=["健檢指標異常"])
        cmp = compare_narrative_periods(curr, prev)
        assert "裝置訊號異常" in cmp["newThemes"]

    def test_resolved_theme_detected(self):
        curr = self._make(themes=["健檢指標異常"])
        prev = self._make(themes=["健檢指標異常", "裝置訊號異常"])
        cmp = compare_narrative_periods(curr, prev)
        assert "裝置訊號異常" in cmp["resolvedThemes"]

    def test_persisting_theme_detected(self):
        curr = self._make(themes=["健檢指標異常"])
        prev = self._make(themes=["健檢指標異常"])
        cmp = compare_narrative_periods(curr, prev)
        assert "健檢指標異常" in cmp["persistingThemes"]

    def test_new_risk_detected(self):
        curr = self._make(risks=["健檢指標異常"])
        prev = self._make(risks=[])
        cmp = compare_narrative_periods(curr, prev)
        assert "健檢指標異常" in cmp["newRisks"]

    def test_resolved_risk_detected(self):
        curr = self._make(risks=[])
        prev = self._make(risks=["裝置訊號異常"])
        cmp = compare_narrative_periods(curr, prev)
        assert "裝置訊號異常" in cmp["resolvedRisks"]

    def test_confidence_delta(self):
        curr = self._make(confidence=0.8)
        prev = self._make(confidence=0.5)
        cmp = compare_narrative_periods(curr, prev)
        assert abs(cmp["confidenceDelta"] - 0.3) < 0.001

    def test_improving_compared_to_previous(self):
        curr = self._make(improving=["systolic_bp 已改善", "weight_kg 已改善"])
        prev = self._make(improving=["systolic_bp 已改善"])
        cmp = compare_narrative_periods(curr, prev)
        assert cmp["improvingComparedToPrevious"] is True

    def test_new_effective_actions(self):
        curr = self._make(effective=["每日量血壓", "增加步數"])
        prev = self._make(effective=["每日量血壓"])
        cmp = compare_narrative_periods(curr, prev)
        assert "增加步數" in cmp["newEffectiveActions"]

    def test_empty_periods_no_crash(self):
        curr = self._make()
        prev = self._make()
        cmp = compare_narrative_periods(curr, prev)
        assert cmp["newThemes"] == []
        assert cmp["resolvedThemes"] == []
