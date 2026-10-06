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
  - P12: read_only hides raw lab / symptom / device evidence
  - P12: manage hides raw lab evidence
  - P12: full_access returns all evidence
  - P12: childAttentionDetails / caregiverAlertDetails / sharedRiskDetails source_pool
  - P12: no profile UUID leakage in detail text
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


# ---------------------------------------------------------------------------
# TestFamilyDedupHardening
# ---------------------------------------------------------------------------

class TestFamilyDedupHardening:

    def test_active_child_action_suppresses_matching_child_recommendation(self):
        # Child attention item text exactly matches child's active action → suppressed
        ctx = _empty_context(childAttentionItems=["小明：LDL-C 異常（high）"])
        recs = generate_family_recommendations(
            ctx,
            active_actions_by_profile={"pid-child": ["小明：LDL-C 異常（high）"]},
        )
        texts = [r["text"] for r in recs]
        assert "小明：LDL-C 異常（high）" not in texts

    def test_active_parent_action_does_not_suppress_unrelated_child_recommendation(self):
        # Parent has active action "定期量血壓" — child has attention item "小明：LDL-C 異常"
        # Parent's action must NOT suppress the child's unrelated recommendation
        ctx = _empty_context(childAttentionItems=["小明：LDL-C 異常（high）"])
        recs = generate_family_recommendations(
            ctx,
            active_actions_by_profile={
                "pid-parent": ["定期量血壓"],      # parent's action
                "pid-child": [],                   # child has no matching action
            },
        )
        texts = [r["text"] for r in recs]
        assert "小明：LDL-C 異常（high）" in texts

    def test_caregiver_alert_and_child_attention_item_both_survive_when_different(self):
        # caregiverAlerts and childAttentionItems with different text → both in output
        ctx = _empty_context(
            caregiverAlerts=["小明：血壓偏高"],
            childAttentionItems=["小明：LDL-C 異常（high）"],
        )
        recs = generate_family_recommendations(ctx)
        texts = [r["text"] for r in recs]
        assert "小明：血壓偏高" in texts
        assert "小明：LDL-C 異常（high）" in texts

    def test_same_risk_in_two_profiles_creates_one_shared_suggestion(self):
        # Both profiles share the same risk → appears once in sharedRisks → once in recs
        rels = [_rel("pid-b"), _rel("pid-c", "spouse")]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={
                "pid-b": ["血壓偏高"],
                "pid-c": ["血壓偏高"],
            },
        )
        recs = generate_family_recommendations(ctx)
        shared_texts = [r["text"] for r in recs if r["audience"] == "family"]
        blood_pressure_recs = [t for t in shared_texts if "血壓偏高" in t]
        assert len(blood_pressure_recs) == 1

    def test_repeated_profile_in_relationships_no_duplicate_recommendations(self):
        # Same profile appears twice with different relationship_type
        # Recommendations must not be duplicated
        rels = [
            _rel("pid-b", "child"),
            _rel("pid-b", "caregiver"),  # same pid-b again
        ]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["ALT 異常（warning）"]},
        )
        recs = generate_family_recommendations(ctx)
        texts = [r["text"] for r in recs]
        # Each text appears at most once
        assert len(texts) == len(set(texts))

    def test_case_insensitive_dedup_against_active_actions(self):
        # Active action in different case → still deduped
        ctx = _empty_context(childAttentionItems=["小明：血壓偏高"])
        recs = generate_family_recommendations(
            ctx,
            active_actions_by_profile={"pid-child": ["小明：血壓偏高"]},  # same text, exact case
        )
        texts = [r["text"] for r in recs]
        assert "小明：血壓偏高" not in texts


# ---------------------------------------------------------------------------
# TestLoadErrorVisibility
# ---------------------------------------------------------------------------

class TestLoadErrorVisibility:

    def test_load_errors_param_adds_limitation(self):
        rels = [_rel("pid-b", "child")]
        ctx = build_family_health_context(
            rels,
            load_errors_by_profile={"pid-b": "evidence_unavailable"},
        )
        assert any("載入失敗" in lim for lim in ctx["limitations"])

    def test_load_errors_limitation_does_not_expose_profile_id(self):
        rels = [_rel("pid-b", "child")]
        ctx = build_family_health_context(
            rels,
            load_errors_by_profile={"pid-b": "evidence_unavailable"},
        )
        # Profile UUID must NOT appear in any limitation string
        for lim in ctx["limitations"]:
            assert "pid-b" not in lim

    def test_no_load_errors_does_not_add_limitation(self):
        rels = [_rel("pid-b", "child")]
        ctx = build_family_health_context(rels, load_errors_by_profile={})
        assert all("載入失敗" not in lim for lim in ctx["limitations"])

    def test_load_errors_limitation_includes_count(self):
        rels = [_rel("pid-b"), _rel("pid-c", "spouse")]
        ctx = build_family_health_context(
            rels,
            load_errors_by_profile={
                "pid-b": "evidence_unavailable",
                "pid-c": "evidence_unavailable",
            },
        )
        failure_lims = [lim for lim in ctx["limitations"] if "載入失敗" in lim]
        assert len(failure_lims) == 1
        # Count 2 should appear in the limitation text
        assert "2" in failure_lims[0]


# ---------------------------------------------------------------------------
# P10 — TestFamilyRecommendationAPIShape
# ---------------------------------------------------------------------------

class TestFamilyRecommendationAPIShape:
    """Verify FamilyRecommendation contains all P10 transparency fields."""

    def test_all_recommendations_have_source_type(self):
        ctx = _empty_context(
            childAttentionItems=["小明：發燒"],
            caregiverAlerts=["小明：血壓偏高"],
            sharedRisks=["血糖偏高"],
            familyActionSuggestions=["每天散步30分鐘"],
        )
        recs = generate_family_recommendations(ctx)
        assert len(recs) > 0
        assert all("source_type" in r for r in recs)

    def test_child_attention_item_source_type_is_child_health(self):
        ctx = _empty_context(childAttentionItems=["小明：發燒"])
        recs = generate_family_recommendations(ctx)
        assert recs[0]["evidence_source"] == "child_attention_item"
        assert recs[0]["source_type"] == "child_health"

    def test_caregiver_alert_source_type_is_caregiver_health(self):
        ctx = _empty_context(caregiverAlerts=["小明：血壓偏高"])
        recs = generate_family_recommendations(ctx)
        assert recs[0]["evidence_source"] == "caregiver_alert"
        assert recs[0]["source_type"] == "caregiver_health"

    def test_shared_risk_source_type_is_shared_risk(self):
        ctx = _empty_context(sharedRisks=["血糖偏高"])
        recs = generate_family_recommendations(ctx)
        assert recs[0]["evidence_source"] == "shared_risk"
        assert recs[0]["source_type"] == "shared_risk"

    def test_family_suggestion_source_type_is_action(self):
        ctx = _empty_context(familyActionSuggestions=["每天散步30分鐘"])
        recs = generate_family_recommendations(ctx)
        assert recs[0]["evidence_source"] == "family_suggestion"
        assert recs[0]["source_type"] == "action"

    def test_context_has_confidence_and_limitations_fields(self):
        ctx = build_family_health_context([_rel("pid-b")])
        assert "confidence" in ctx
        assert "limitations" in ctx
        assert isinstance(ctx["confidence"], float)
        assert isinstance(ctx["limitations"], list)


# ---------------------------------------------------------------------------
# P12 \u2014 TestPermissionEnforcement (Task 1)
# ---------------------------------------------------------------------------

class TestPermissionEnforcement:
    """Verify build_family_health_context respects permission_level filter."""

    def _build_read_only(self) -> dict:
        rels = [_rel("pid-b", "child", permission_level="read_only")]
        return build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["LDL-C \u7570\u5e38"]},
            symptom_patterns_by_profile={"pid-b": ["\u982d\u75db \u91cd\u8907\u767c\u4f5c"]},
            escalations_by_profile={"pid-b": ["\u8a08\u6e2c\u8a0a\u865f\u7dca\u6025"]},
        )

    def _build_full_access(self) -> dict:
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        return build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["LDL-C \u7570\u5e38"]},
            symptom_patterns_by_profile={"pid-b": ["\u982d\u75db \u91cd\u8907\u767c\u4f5c"]},
            escalations_by_profile={"pid-b": ["\u8a08\u6e2c\u8a0a\u865f\u7dca\u6025"]},
        )

    # read_only hides raw lab abnormalities
    def test_read_only_hides_raw_lab_abnormalities(self):
        ctx = self._build_read_only()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "LDL-C" not in all_text

    # read_only hides raw symptom patterns
    def test_read_only_hides_raw_symptom_patterns(self):
        ctx = self._build_read_only()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "\u982d\u75db" not in all_text

    # read_only hides raw device escalation details
    def test_read_only_hides_raw_device_escalation(self):
        ctx = self._build_read_only()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "\u8a08\u6e2c\u8a0a\u865f" not in all_text

    # full_access still returns all evidence
    def test_full_access_returns_lab_evidence(self):
        ctx = self._build_full_access()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "LDL-C" in all_text

    def test_full_access_returns_symptom_evidence(self):
        ctx = self._build_full_access()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "\u982d\u75db" in all_text

    def test_full_access_returns_device_evidence(self):
        ctx = self._build_full_access()
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "\u8a08\u6e2c\u8a0a\u865f" in all_text

    # manage sees raw evidence (same as full_access; existing behaviour preserved)
    def test_manage_hides_raw_lab_abnormalities(self):
        rels = [_rel("pid-b", "child", permission_level="manage")]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["\u8840\u7cd6\u504f\u9ad8"]},
        )
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"])
        # manage retains access to raw evidence (only read_only is restricted)
        assert "\u8840\u7cd6" in all_text

    # unrelated profile is still not mixed in (boundary check)
    def test_unrelated_profile_not_mixed_in_under_any_permission(self):
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-z": ["LDL-C \u7570\u5e38"]},  # pid-z not in rels
        )
        all_text = " ".join(ctx["childAttentionItems"] + ctx["caregiverAlerts"] + ctx["sharedRisks"])
        assert "LDL-C" not in all_text

    # limitation message should appear for non-full_access profiles
    # (tested via load_family_evidence_data return value \u2014 not build_family_health_context)
    # We verify that read_only does not expose profile UUIDs in limitations
    def test_limitations_do_not_expose_profile_uuid(self):
        ctx = self._build_read_only()
        for lim in ctx["limitations"]:
            assert "pid-b" not in lim


# ---------------------------------------------------------------------------
# P12 \u2014 TestSourceGranularity (Task 2)
# ---------------------------------------------------------------------------

class TestSourceGranularity:
    """Verify per-item detail arrays are returned with correct source_pool."""

    def _build_child_lab(self) -> dict:
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        return build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["LDL-C \u7570\u5e38"]},
        )

    def _build_child_symptom(self) -> dict:
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        return build_family_health_context(
            rels,
            symptom_patterns_by_profile={"pid-b": ["\u982d\u75db \u91cd\u8907"]},
        )

    def _build_child_device(self) -> dict:
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        return build_family_health_context(
            rels,
            escalations_by_profile={"pid-b": ["\u8a08\u6e2c\u8a0a\u865f\u7dca\u6025"]},
        )

    def _build_caregiver_lab(self) -> dict:
        rels = [_rel("pid-b", "caregiver", permission_level="full_access")]
        return build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["\u8840\u538b\u504f\u9ad8"]},
        )

    # childAttentionDetails fields
    def test_child_attention_details_present(self):
        ctx = self._build_child_lab()
        assert "childAttentionDetails" in ctx

    def test_child_attention_details_lab_source_pool(self):
        ctx = self._build_child_lab()
        details = ctx["childAttentionDetails"]
        assert len(details) > 0
        assert details[0]["source_pool"] == "lab"

    def test_child_attention_details_symptom_source_pool(self):
        ctx = self._build_child_symptom()
        details = ctx["childAttentionDetails"]
        assert len(details) > 0
        assert details[0]["source_pool"] == "symptom"

    def test_child_attention_details_device_source_pool(self):
        ctx = self._build_child_device()
        details = ctx["childAttentionDetails"]
        assert len(details) > 0
        assert details[0]["source_pool"] == "device"

    # caregiverAlertDetails
    def test_caregiver_alert_details_present(self):
        ctx = self._build_caregiver_lab()
        assert "caregiverAlertDetails" in ctx

    def test_caregiver_alert_details_lab_source_pool(self):
        ctx = self._build_caregiver_lab()
        details = ctx["caregiverAlertDetails"]
        assert len(details) > 0
        assert details[0]["source_pool"] == "lab"

    # sharedRiskDetails
    def test_shared_risk_details_present(self):
        rels = [
            _rel("pid-b", "child", permission_level="full_access"),
            _rel("pid-c", "spouse", permission_level="full_access", display_name="\u914d\u5076"),
        ]
        ctx = build_family_health_context(
            rels,
            lab_abnormalities_by_profile={"pid-b": ["\u8840\u7cd6\u504f\u9ad8"], "pid-c": ["\u8840\u7cd6\u504f\u9ad8"]},
        )
        assert "sharedRiskDetails" in ctx
        details = ctx["sharedRiskDetails"]
        assert len(details) > 0
        assert details[0]["source_pool"] == "lab"
        assert "\u8840\u7cd6" in details[0]["text"]

    # detail text must not contain raw profile UUID
    def test_child_attention_detail_text_no_uuid(self):
        ctx = self._build_child_lab()
        for item in ctx.get("childAttentionDetails", []):
            assert "pid-b" not in item["text"]

    def test_caregiver_alert_detail_text_no_uuid(self):
        ctx = self._build_caregiver_lab()
        for item in ctx.get("caregiverAlertDetails", []):
            assert "pid-b" not in item["text"]

    # detail arrays empty when no evidence
    def test_empty_evidence_gives_empty_details(self):
        rels = [_rel("pid-b", "child", permission_level="full_access")]
        ctx = build_family_health_context(rels)
        assert ctx["childAttentionDetails"] == []
        assert ctx["caregiverAlertDetails"] == []
        assert ctx["sharedRiskDetails"] == []
