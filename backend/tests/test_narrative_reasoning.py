"""Tests for narrative_intelligence_service — P7.2 Cross-Period Health Reasoning

Coverage
--------
  - improving cross-period trend
  - worsening cross-period trend
  - mixed trend detection
  - sustained improvement detection
  - repeated ignored risk detection
  - carry-over recommendation generation
  - stale narrative downgrade
  - insufficient data limitations
  - recommendation dedup / active-action exclusion
  - no hallucinated reasoning without evidence
  - max carry-over prevents infinite loop
  - carry-over count increments correctly
  - sustained improvement not carried over
  - repeated ignored risk urgency capped at 0.75
  - worsening risk outranks effective action
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.services.narrative_intelligence_service import (
    build_cross_period_health_reasoning,
    generate_carry_over_recommendations,
    rank_narrative_insights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mem(
    period_type: str = "weekly",
    improving: list[str] | None = None,
    worsening: list[str] | None = None,
    repeated_risks: list[str] | None = None,
    effective_actions: list[str] | None = None,
    ignored_items: list[str] | None = None,
    confidence: float = 0.70,
    generated_at: str | None = None,
) -> dict:
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "periodType": period_type,
        "periodStart": "2026-05-01",
        "periodEnd": "2026-05-07",
        "summaryText": "Test",
        "topThemes": [],
        "improvingItems": improving or [],
        "worseningItems": worsening or [],
        "repeatedRisks": repeated_risks or [],
        "effectiveActions": effective_actions or [],
        "ignoredItems": ignored_items or [],
        "confidence": confidence,
        "limitations": [],
        "generatedAt": generated_at,
    }


def _empty_reasoning(**overrides) -> dict:
    base = {
        "overallTrend": "stable",
        "longTermRisks": [],
        "sustainedImprovements": [],
        "unstableAreas": [],
        "repeatedIgnoredRisks": [],
        "effectiveLongTermActions": [],
        "carryOverRecommendations": [],
        "confidence": 0.5,
        "limitations": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestBuildCrossPeriodHealthReasoning
# ---------------------------------------------------------------------------

class TestBuildCrossPeriodHealthReasoning:

    def test_empty_input_returns_stable_with_limitation(self):
        result = build_cross_period_health_reasoning([], [], [])
        assert result["overallTrend"] == "stable"
        assert result["confidence"] == 0.0
        assert len(result["limitations"]) >= 1
        assert "跨期間" in result["limitations"][0]

    def test_improving_trend_two_periods(self):
        m1 = _mem(improving=["血壓已改善"])
        m2 = _mem(improving=["血壓已改善"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert result["overallTrend"] == "improving"
        assert "血壓已改善" in result["sustainedImprovements"]

    def test_worsening_trend_two_periods(self):
        m1 = _mem(worsening=["血糖持續惡化"])
        m2 = _mem(worsening=["血糖持續惡化"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert result["overallTrend"] == "worsening"
        assert "血糖持續惡化" in result["longTermRisks"]

    def test_mixed_trend_detected(self):
        m1 = _mem(improving=["血壓已改善"], worsening=["血糖持續惡化"])
        m2 = _mem(improving=["血壓已改善"], worsening=["血糖持續惡化"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert result["overallTrend"] == "mixed"

    def test_sustained_improvement_requires_two_occurrences(self):
        m1 = _mem(improving=["體重下降"])
        m2 = _mem(improving=["體重下降"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "體重下降" in result["sustainedImprovements"]

    def test_single_occurrence_not_sustained(self):
        m1 = _mem(improving=["體重下降"])
        m2 = _mem(improving=[])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "體重下降" not in result["sustainedImprovements"]

    def test_repeated_ignored_risk_detection(self):
        m1 = _mem(ignored_items=["症狀模式"])
        m2 = _mem(ignored_items=["症狀模式"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "症狀模式" in result["repeatedIgnoredRisks"]

    def test_insufficient_data_adds_limitation(self):
        m1 = _mem()
        result = build_cross_period_health_reasoning([], [m1], [])
        assert any("期間" in lim for lim in result["limitations"])

    def test_long_term_risk_from_repeated_risks_field(self):
        m1 = _mem(repeated_risks=["健檢指標異常"])
        m2 = _mem(repeated_risks=["健檢指標異常"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "健檢指標異常" in result["longTermRisks"]

    def test_carry_over_excludes_sustained_improvements(self):
        # Item appears as both repeated risk AND improving — the improvement wins
        m1 = _mem(repeated_risks=["症狀模式"], improving=["症狀模式"])
        m2 = _mem(repeated_risks=["症狀模式"], improving=["症狀模式"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "症狀模式" not in result["carryOverRecommendations"]

    def test_no_hallucinated_reasoning_without_evidence(self):
        m1 = _mem()
        m2 = _mem()
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert result["longTermRisks"] == []
        assert result["sustainedImprovements"] == []
        assert result["repeatedIgnoredRisks"] == []

    def test_unstable_area_appears_in_both_directions(self):
        m1 = _mem(improving=["血壓"], worsening=["血壓"])
        m2 = _mem(improving=["血壓"])
        result = build_cross_period_health_reasoning([], [m1, m2], [])
        assert "血壓" in result["unstableAreas"]

    def test_cross_period_combines_daily_weekly_monthly(self):
        d1 = _mem("daily", improving=["步數增加"])
        w1 = _mem("weekly", improving=["步數增加"])
        mo1 = _mem("monthly", improving=["步數增加"])
        result = build_cross_period_health_reasoning([d1], [w1], [mo1])
        assert "步數增加" in result["sustainedImprovements"]
        assert result["overallTrend"] == "improving"


# ---------------------------------------------------------------------------
# TestRankNarrativeInsights
# ---------------------------------------------------------------------------

class TestRankNarrativeInsights:

    def test_worsening_risk_ranks_higher_than_effective_action(self):
        reasoning = _empty_reasoning(
            overallTrend="worsening",
            longTermRisks=["血糖持續惡化"],
            effectiveLongTermActions=["每日散步"],
        )
        memories = [_mem(repeated_risks=["血糖持續惡化"], effective_actions=["每日散步"])]
        ranked = rank_narrative_insights(reasoning, memories)
        items = [r["item"] for r in ranked]
        assert items.index("血糖持續惡化") < items.index("每日散步")

    def test_stale_memory_reduces_insight_score(self):
        old_gen = "2025-01-01T00:00:00+00:00"
        reasoning = _empty_reasoning(
            overallTrend="worsening",
            longTermRisks=["舊風險"],
        )
        memories = [_mem(generated_at=old_gen, repeated_risks=["舊風險"])]
        ranked = rank_narrative_insights(reasoning, memories, stale_threshold_days=30)
        # Without staleness: base score = 0.70; staleness penalty should reduce it
        assert ranked[0]["score"] < 0.70

    def test_repeated_ignored_risk_capped_at_0_75(self):
        reasoning = _empty_reasoning(repeatedIgnoredRisks=["已忽略風險"])
        memories = [_mem(ignored_items=["已忽略風險"])] * 10
        ranked = rank_narrative_insights(reasoning, memories)
        ignored = [r for r in ranked if r["category"] == "repeated_ignored_risk"]
        assert all(r["score"] <= 0.75 for r in ignored)

    def test_empty_reasoning_returns_empty_list(self):
        reasoning = _empty_reasoning()
        ranked = rank_narrative_insights(reasoning, [])
        assert ranked == []

    def test_dedup_keeps_highest_score(self):
        # Same item appears in both longTermRisks AND carryOverRecommendations
        reasoning = _empty_reasoning(
            longTermRisks=["血壓異常"],
            carryOverRecommendations=["血壓異常"],
        )
        memories = [_mem(repeated_risks=["血壓異常"])]
        ranked = rank_narrative_insights(reasoning, memories)
        items = [r["item"] for r in ranked]
        # Item should only appear once
        assert items.count("血壓異常") == 1
        # Should be the higher score (long_term_risk base=0.70 vs carry_over base=0.50)
        assert ranked[0]["score"] >= 0.70


# ---------------------------------------------------------------------------
# TestGenerateCarryOverRecommendations
# ---------------------------------------------------------------------------

class TestGenerateCarryOverRecommendations:

    def test_long_term_risk_becomes_carry_over(self):
        reasoning = _empty_reasoning(longTermRisks=["血壓異常"])
        result = generate_carry_over_recommendations(reasoning)
        assert len(result) >= 1
        assert result[0]["text"] == "血壓異常"
        assert result[0]["urgency"] == "high"
        assert result[0]["carry_over_count"] == 1

    def test_active_action_excluded_from_carry_over(self):
        reasoning = _empty_reasoning(longTermRisks=["血壓異常"])
        result = generate_carry_over_recommendations(reasoning, active_action_titles=["血壓異常"])
        assert len(result) == 0

    def test_max_carry_over_prevents_infinite_loop(self):
        reasoning = _empty_reasoning(longTermRisks=["久未改善"])
        prev = [{"text": "久未改善", "carry_over_count": 3}]
        result = generate_carry_over_recommendations(reasoning, previous_carry_overs=prev, max_carry=3)
        assert len(result) == 0

    def test_carry_over_count_increments_from_previous(self):
        reasoning = _empty_reasoning(longTermRisks=["血糖"])
        prev = [{"text": "血糖", "carry_over_count": 1}]
        result = generate_carry_over_recommendations(reasoning, previous_carry_overs=prev)
        assert result[0]["carry_over_count"] == 2

    def test_sustained_improvement_excluded_from_carry_over(self):
        reasoning = _empty_reasoning(
            longTermRisks=["症狀模式"],
            sustainedImprovements=["症狀模式"],
        )
        result = generate_carry_over_recommendations(reasoning)
        texts = [r["text"] for r in result]
        assert "症狀模式" not in texts

    def test_high_urgency_sorted_before_medium(self):
        reasoning = _empty_reasoning(
            longTermRisks=["血壓異常"],
            repeatedIgnoredRisks=["飲食風險"],
        )
        result = generate_carry_over_recommendations(reasoning)
        urgencies = [r["urgency"] for r in result]
        assert urgencies[0] == "high"

    def test_repeated_ignored_risk_has_medium_urgency(self):
        reasoning = _empty_reasoning(repeatedIgnoredRisks=["飲食風險"])
        result = generate_carry_over_recommendations(reasoning)
        assert result[0]["urgency"] == "medium"

    def test_effective_action_not_carried_over(self):
        reasoning = _empty_reasoning(
            longTermRisks=["血糖"],
            effectiveLongTermActions=["血糖"],
        )
        result = generate_carry_over_recommendations(reasoning)
        texts = [r["text"] for r in result]
        assert "血糖" not in texts

    def test_empty_reasoning_returns_empty(self):
        reasoning = _empty_reasoning()
        result = generate_carry_over_recommendations(reasoning)
        assert result == []

    def test_dedup_long_term_and_ignored_risk_same_item(self):
        # Same item in both longTermRisks and repeatedIgnoredRisks — high urgency wins
        reasoning = _empty_reasoning(
            longTermRisks=["血壓異常"],
            repeatedIgnoredRisks=["血壓異常"],
        )
        result = generate_carry_over_recommendations(reasoning)
        items = [r["text"] for r in result]
        assert items.count("血壓異常") == 1
        assert result[0]["urgency"] == "high"
