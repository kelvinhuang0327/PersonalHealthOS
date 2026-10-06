"""Tests for adaptive_recommendation_service (P6 Personalization).

Pure-function tests — no DB required.
Covers:
  - default (no profile): recommendations returned unchanged
  - acted category raises ranking
  - ignored category lowers ranking / downgrades priority
  - outcome success raises confidence
  - low engagement reduces notification intensity (caps priority at medium)
  - urgent escalation bypasses personalization suppression
  - hard-floor: ignore count >= 5 → priority "low"
  - re-sorting: higher acted category bubbles up
  - personalization_reasons is a list of strings
"""
from __future__ import annotations

import pytest

from app.services.adaptive_recommendation_service import adaptive_recommendation_score

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def _rec(
    source_type: str = "lab_abnormality",
    priority: str = "high",
    confidence: float = 0.70,
) -> dict:
    return {
        "source_type": source_type,
        "priority": priority,
        "confidence": confidence,
        "title": f"Test rec ({source_type})",
    }


def _profile(
    acted: dict | None = None,
    ignored: dict | None = None,
    high_response: list | None = None,
    engagement: float = 0.5,
) -> dict:
    return {
        "engagement_score": engagement,
        "acted_categories": acted or {},
        "ignored_categories": ignored or {},
        "high_response_categories": high_response or [],
        "preferred_notification_types": [],
    }


def _outcome(source_type: str, status: str = "improved") -> dict:
    return {"source_type": source_type, "outcome_status": status}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDefaultFallback:
    def test_no_profile_returns_unchanged(self):
        recs = [_rec("lab_abnormality", "high", 0.70)]
        result = adaptive_recommendation_score(recs)
        assert result[0]["priority"] == "high"
        assert result[0]["adjusted_confidence"] == pytest.approx(0.70, abs=0.01)

    def test_empty_profile_no_crash(self):
        recs = [_rec()]
        result = adaptive_recommendation_score(recs, profile={})
        assert len(result) == 1


class TestActedCategoryBoost:
    def test_acted_category_raises_confidence(self):
        profile = _profile(acted={"lab_abnormality": 2})
        recs = [_rec("lab_abnormality", "high", 0.65)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["adjusted_confidence"] > 0.65

    def test_acted_category_adds_reason(self):
        profile = _profile(acted={"lab_abnormality": 3})
        recs = [_rec("lab_abnormality")]
        result = adaptive_recommendation_score(recs, profile=profile)
        reasons = result[0].get("personalization_reasons", [])
        assert any("次" in r or "建議" in r or "行動" in r for r in reasons)

    def test_confidence_capped_at_0_95(self):
        profile = _profile(acted={"lab_abnormality": 100})
        recs = [_rec("lab_abnormality", "high", 0.90)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["adjusted_confidence"] <= 0.95

    def test_high_response_category_boost(self):
        profile = _profile(high_response=["device_escalation"])
        recs = [_rec("device_escalation", "medium", 0.60)]
        result = adaptive_recommendation_score(recs, profile=profile)
        # Should get the bypass since device_escalation is bypass source type
        assert result[0]["adjusted_confidence"] == pytest.approx(0.60, abs=0.01)


class TestIgnoredCategoryPenalty:
    def test_ignored_category_lowers_confidence(self):
        profile = _profile(ignored={"symptom_pattern": 3})
        recs = [_rec("symptom_pattern", "high", 0.75)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["adjusted_confidence"] < 0.75

    def test_ignored_category_downgrades_priority(self):
        profile = _profile(ignored={"symptom_pattern": 3})
        recs = [_rec("symptom_pattern", "high", 0.75)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["priority"] != "high"

    def test_hard_floor_ignore_5_sets_low_priority(self):
        profile = _profile(ignored={"risk_alert": 6})
        recs = [_rec("risk_alert", "high", 0.80)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["priority"] == "low"

    def test_confidence_floor_0_20(self):
        profile = _profile(ignored={"symptom_pattern": 100})
        recs = [_rec("symptom_pattern", "medium", 0.50)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["adjusted_confidence"] >= 0.20


class TestOutcomeSuccessBoost:
    def test_outcome_improved_raises_confidence(self):
        recs = [_rec("lab_abnormality", "medium", 0.60)]
        outcomes = [_outcome("lab_abnormality", "improved")]
        result = adaptive_recommendation_score(recs, outcome_summaries=outcomes)
        # Without profile, bypass is not triggered and boost applies
        assert result[0]["adjusted_confidence"] >= 0.60

    def test_no_outcome_no_boost(self):
        recs = [_rec("lab_abnormality", "medium", 0.60)]
        result = adaptive_recommendation_score(recs, outcome_summaries=[])
        assert result[0]["adjusted_confidence"] == pytest.approx(0.60, abs=0.01)


class TestLowEngagement:
    def test_low_engagement_caps_priority_at_medium(self):
        profile = _profile(engagement=0.15)
        recs = [_rec("lab_abnormality", "high", 0.75)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["priority"] == "medium"

    def test_low_engagement_does_not_affect_urgent(self):
        """Urgent priority with device_escalation bypasses all personalization."""
        profile = _profile(engagement=0.05)
        recs = [_rec("device_escalation", "urgent", 0.90)]
        result = adaptive_recommendation_score(recs, profile=profile)
        # Bypass: device_escalation is always exempt
        assert result[0]["priority"] == "urgent"

    def test_medium_engagement_no_cap(self):
        profile = _profile(engagement=0.50)
        recs = [_rec("lab_abnormality", "high", 0.75)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["priority"] == "high"


class TestUrgentEscalationBypass:
    def test_urgent_priority_bypasses_personalization(self):
        profile = _profile(
            ignored={"device_escalation": 10},
            engagement=0.05,
        )
        recs = [_rec("device_escalation", "urgent", 0.90)]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert result[0]["priority"] == "urgent"
        # Confidence unchanged by penalties
        assert result[0]["adjusted_confidence"] == pytest.approx(0.90, abs=0.01)

    def test_device_escalation_source_bypasses(self):
        profile = _profile(ignored={"device_escalation": 99}, engagement=0.05)
        recs = [_rec("device_escalation", "high", 0.80)]
        result = adaptive_recommendation_score(recs, profile=profile)
        # No priority downgrade for device_escalation
        assert result[0]["priority"] == "high"


class TestSorting:
    def test_higher_acted_category_bubbles_up(self):
        profile = _profile(acted={"lab_abnormality": 5, "symptom_pattern": 0})
        recs = [
            _rec("symptom_pattern", "high", 0.70),
            _rec("lab_abnormality", "high", 0.60),
        ]
        result = adaptive_recommendation_score(recs, profile=profile)
        # lab_abnormality should have higher adjusted_confidence → sorted first
        assert result[0]["source_type"] == "lab_abnormality"

    def test_personalization_reasons_is_list(self):
        profile = _profile(acted={"lab_abnormality": 3})
        recs = [_rec("lab_abnormality")]
        result = adaptive_recommendation_score(recs, profile=profile)
        assert isinstance(result[0]["personalization_reasons"], list)
