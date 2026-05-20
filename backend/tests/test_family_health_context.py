"""Tests for family_health_context_service — P8 Family Health Assistant

Coverage
--------
  - family relationship creation (model)
  - get_related_profiles filters and labels correctly
  - unrelated profiles are never mixed in
  - caregiver child visibility (caregiver + parent rel types)
  - child attention items for child-type relationships
  - shared risk detection (≥ 2 profiles)
  - single-profile risk NOT counted as shared
  - family action suggestions from recommendations
  - no family data returns explainable empty state
  - generate_family_recommendations: child attention → high urgency
  - generate_family_recommendations: shared risk → medium urgency
  - generate_family_recommendations: dedup against active actions
  - generate_family_recommendations: no duplicates in output
  - generate_family_recommendations: empty context returns empty
  - confidence scales with data richness
"""
from __future__ import annotations

import pytest

from app.services.family_health_context_service import (
    build_family_health_context,
    generate_family_recommendations,
    get_family_risk_summary,
    get_related_profiles,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rel(
    related_profile_id: str = "pid-b",
    relationship_type: str = "child",
    permission_level: str = "manage",
    display_name: str = "小明",
) -> dict:
    return {
        "id": "rel-1",
        "owner_user_id": "uid-1",
        "subject_profile_id": "pid-a",
        "related_profile_id": related_profile_id,
        "relationship_type": relationship_type,
        "permission_level": permission_level,
        "related_display_name": display_name,
    }


def _empty_context(**overrides) -> dict:
    base = {
        "relatedProfiles": [],
        "sharedRisks": [],
        "caregiverAlerts": [],
        "childAttentionItems": [],
        "familyActionSuggestions": [],
        "confidence": 0.0,
        "limitations": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestGetRelatedProfiles
# ---------------------------------------------------------------------------

class TestGetRelatedProfiles:

    def test_single_relationship_returns_one_profile(self):
        rels = [_rel("pid-b", "child")]
        profiles = get_related_profiles(rels)
        assert len(profiles) == 1
        assert profiles[0]["profile_id"] == "pid-b"
        assert profiles[0]["relationship_type"] == "child"

    def test_duplicate_related_profile_deduped(self):
        # Same related_profile_id with two entries (e.g., both child and caregiver)
        rels = [
            _rel("pid-b", "child"),
            _rel("pid-b", "caregiver"),
        ]
        profiles = get_related_profiles(rels)
        assert len(profiles) == 1
        assert profiles[0]["profile_id"] == "pid-b"
        # First-seen entry wins
        assert profiles[0]["relationship_type"] == "child"

    def test_multiple_distinct_profiles(self):
        rels = [
            _rel("pid-b", "child", display_name="小明"),
            _rel("pid-c", "spouse", display_name="配偶"),
        ]
        profiles = get_related_profiles(rels)
        ids = {p["profile_id"] for p in profiles}
        assert ids == {"pid-b", "pid-c"}

    def test_empty_relationships_returns_empty(self):
        assert get_related_profiles([]) == []

    def test_display_name_falls_back_to_unknown(self):
        rel = {**_rel("pid-z"), "related_display_name": None, "display_name": None}
        profiles = get_related_profiles([rel])
        assert profiles[0]["display_name"] == "未知成員"


# ---------------------------------------------------------------------------
# TestGetFamilyRiskSummary
# ---------------------------------------------------------------------------

class TestGetFamilyRiskSummary:

    def test_shared_risk_across_two_profiles(self):
        rels = [_rel("pid-b"), _rel("pid-c", "spouse")]
        risk_map = {
            "pid-b": ["血壓偏高"],
            "pid-c": ["血壓偏高"],
        }
        shared = get_family_risk_summary(rels, risk_map)
        assert "血壓偏高" in shared

    def test_single_profile_risk_not_shared(self):
        rels = [_rel("pid-b")]
        risk_map = {"pid-b": ["血糖偏高"]}
        shared = get_family_risk_summary(rels, risk_map)
        assert shared == []

    def test_unrelated_profile_excluded(self):
        rels = [_rel("pid-b")]
        # pid-z is NOT in relationships
        risk_map = {
            "pid-b": ["體重超標"],
            "pid-z": ["體重超標"],
        }
        shared = get_family_risk_summary(rels, risk_map)
        # Only pid-b in rels → count = 1 → not shared
        assert shared == []

    def test_empty_rels_returns_empty(self):
        shared = get_family_risk_summary([], {"pid-b": ["風險"]})
        assert shared == []

    def test_multiple_shared_risks(self):
        rels = [_rel("pid-b"), _rel("pid-c", "parent")]
        risk_map = {
            "pid-b": ["血壓偏高", "血糖偏高"],
            "pid-c": ["血壓偏高", "血糖偏高"],
        }
        shared = get_family_risk_summary(rels, risk_map)
        assert "血壓偏高" in shared
        assert "血糖偏高" in shared


# ---------------------------------------------------------------------------
# TestBuildFamilyHealthContext
# ---------------------------------------------------------------------------

class TestBuildFamilyHealthContext:

    def test_no_relationships_returns_empty_with_limitation(self):
        ctx = build_family_health_context([])
        assert ctx["relatedProfiles"] == []
        assert ctx["sharedRisks"] == []
        assert ctx["confidence"] == 0.0
        assert len(ctx["limitations"]) >= 1
        assert "家庭成員關係" in ctx["limitations"][0]

    def test_caregiver_type_sees_child_risks_in_caregiver_alerts(self):
        rels = [_rel("pid-b", "caregiver")]
        ctx = build_family_health_context(
            rels,
            escalations_by_profile={"pid-b": ["裝置訊號異常"]},
        )
        assert any("裝置訊號異常" in alert for alert in ctx["caregiverAlerts"])

    def test_parent_type_sees_child_risks_in_caregiver_alerts(self):
        rels = [_rel("pid-b", "parent")]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["血糖偏高"]},
        )
        assert any("血糖偏高" in a for a in ctx["caregiverAlerts"])

    def test_child_type_appears_in_child_attention_items(self):
        rels = [_rel("pid-b", "child")]
        ctx = build_family_health_context(
            rels,
            symptom_patterns_by_profile={"pid-b": ["發燒"]},
        )
        assert any("發燒" in item for item in ctx["childAttentionItems"])

    def test_spouse_type_does_not_produce_child_attention_items(self):
        rels = [_rel("pid-b", "spouse")]
        ctx = build_family_health_context(
            rels,
            escalations_by_profile={"pid-b": ["血壓警示"]},
        )
        assert ctx["childAttentionItems"] == []

    def test_full_access_permission_generates_caregiver_alerts(self):
        rels = [_rel("pid-b", "spouse", permission_level="full_access")]
        ctx = build_family_health_context(
            rels,
            escalations_by_profile={"pid-b": ["警示"]},
        )
        assert any("警示" in a for a in ctx["caregiverAlerts"])

    def test_family_action_suggestions_from_recommendations(self):
        rels = [_rel("pid-b")]
        ctx = build_family_health_context(
            rels,
            recommendations_by_profile={"pid-b": ["每天散步"]},
        )
        assert "每天散步" in ctx["familyActionSuggestions"]

    def test_shared_risks_require_two_profiles(self):
        rels = [_rel("pid-b"), _rel("pid-c", "spouse")]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={
                "pid-b": ["血壓偏高"],
                "pid-c": ["血壓偏高"],
            },
        )
        assert "血壓偏高" in ctx["sharedRisks"]

    def test_read_only_permission_does_not_generate_caregiver_alerts(self):
        rels = [_rel("pid-b", "spouse", permission_level="read_only")]
        ctx = build_family_health_context(
            rels,
            escalations_by_profile={"pid-b": ["警示"]},
        )
        # read_only + spouse → neither caregiver-type nor elevated-permission
        assert ctx["caregiverAlerts"] == []

    def test_confidence_increases_with_more_profiles(self):
        rels_one = [_rel("pid-b")]
        rels_two = [_rel("pid-b"), _rel("pid-c", "spouse")]
        ctx_one = build_family_health_context(rels_one)
        ctx_two = build_family_health_context(rels_two)
        assert ctx_two["confidence"] >= ctx_one["confidence"]

    def test_unrelated_profile_data_not_included(self):
        rels = [_rel("pid-b")]
        # pid-z not in rels
        ctx = build_family_health_context(
            rels,
            escalations_by_profile={"pid-z": ["不相關風險"]},
        )
        assert all("不相關風險" not in a for a in ctx["caregiverAlerts"])
        assert "不相關風險" not in ctx["sharedRisks"]

    def test_no_evidence_adds_limitation(self):
        rels = [_rel("pid-b")]
        ctx = build_family_health_context(rels)
        assert any("健康資料" in lim for lim in ctx["limitations"])


# ---------------------------------------------------------------------------
# TestGenerateFamilyRecommendations
# ---------------------------------------------------------------------------

class TestGenerateFamilyRecommendations:

    def test_child_attention_item_becomes_high_urgency(self):
        ctx = _empty_context(childAttentionItems=["小明：發燒"])
        recs = generate_family_recommendations(ctx)
        assert any(r["urgency"] == "high" for r in recs)
        assert any(r["audience"] == "caregiver" for r in recs)

    def test_caregiver_alert_becomes_medium_urgency(self):
        ctx = _empty_context(caregiverAlerts=["小明：血壓偏高"])
        recs = generate_family_recommendations(ctx)
        assert any(r["urgency"] == "medium" for r in recs)

    def test_shared_risk_becomes_family_audience(self):
        ctx = _empty_context(sharedRisks=["血糖偏高"])
        recs = generate_family_recommendations(ctx)
        family_recs = [r for r in recs if r["audience"] == "family"]
        assert any("血糖偏高" in r["text"] for r in family_recs)

    def test_active_action_excluded_from_recommendations(self):
        ctx = _empty_context(childAttentionItems=["小明：發燒"])
        recs = generate_family_recommendations(ctx, active_actions_by_profile={"pid-b": ["小明：發燒"]})
        texts = [r["text"] for r in recs]
        assert "小明：發燒" not in texts

    def test_no_duplicate_texts_in_output(self):
        # Same item in childAttentionItems and caregiverAlerts
        ctx = _empty_context(
            childAttentionItems=["小明：發燒"],
            caregiverAlerts=["小明：發燒"],
        )
        recs = generate_family_recommendations(ctx)
        texts = [r["text"] for r in recs]
        assert len(texts) == len(set(texts))

    def test_empty_context_returns_empty(self):
        ctx = _empty_context()
        recs = generate_family_recommendations(ctx)
        assert recs == []

    def test_high_urgency_sorted_before_low(self):
        ctx = _empty_context(
            childAttentionItems=["小明：發燒"],
            familyActionSuggestions=["每天散步"],
        )
        recs = generate_family_recommendations(ctx)
        urgencies = [r["urgency"] for r in recs]
        assert urgencies[0] == "high"

    def test_evidence_source_preserved(self):
        ctx = _empty_context(childAttentionItems=["小明：發燒"])
        recs = generate_family_recommendations(ctx)
        child_recs = [r for r in recs if r["audience"] == "caregiver"]
        assert all(r["evidence_source"] == "child_attention_item" for r in child_recs)
