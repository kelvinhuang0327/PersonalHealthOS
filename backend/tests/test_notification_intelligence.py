"""Unit tests — P5 Notification Intelligence Service
=====================================================
All tests are pure-function: no DB, no HTTP.
Input dicts mirror the shapes produced by build_evidence_bundle().

Coverage
--------
  build_notification_candidates()
    - urgent device escalation → urgent candidate
    - warning device escalation → high candidate
    - watch device escalation → medium candidate
    - none device escalation → no candidate
    - high lab abnormality → high candidate
    - medium lab abnormality → medium candidate
    - low confidence candidate capped at medium
    - very low confidence below threshold → no candidate
    - worsening symptom high severity → high candidate
    - worsening symptom medium severity → medium candidate
    - unresolved high severity symptom → high candidate
    - risk alert critical → urgent candidate
    - risk alert high → high candidate
    - empty bundle → empty list
    - no evidence → no candidates
    - evidence_sources preserved in candidate
    - cooldown_key present in candidate
    - duplicate cooldown_key: keep highest priority
    - candidates sorted by priority desc
    - symptom_with_lab_risk → medium candidate

  apply_notification_fatigue_guard()
    - no history → all active
    - ignore_count >= 3 → suppressed
    - active action rule_id dedup → suppressed
    - cooldown window not elapsed → suppressed
    - cooldown window elapsed → active
    - snoozed → downgraded priority (still active)
    - suppressed candidates have suppress_reason
    - guard returns both active and suppressed lists
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.notification_intelligence_service import (
    apply_notification_fatigue_guard,
    build_notification_candidates,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _urgent_escalation() -> dict:
    return {
        "escalationLevel": "urgent",
        "reasons": ["心率持續偏高", "連續3天未緩解"],
        "confidence": 0.85,
        "recommendedAction": "建議盡快就醫",
        "requiresFollowUp": True,
    }


def _warning_escalation() -> dict:
    return {
        "escalationLevel": "warning",
        "reasons": ["靜息心率偏高"],
        "confidence": 0.70,
        "recommendedAction": "建議監測",
        "requiresFollowUp": False,
    }


def _watch_escalation() -> dict:
    return {
        "escalationLevel": "watch",
        "reasons": ["步數偏低"],
        "confidence": 0.60,
        "recommendedAction": None,
        "requiresFollowUp": False,
    }


def _high_lab_abn() -> dict:
    return {
        "abnormalityType": "lipid_abnormality",
        "severity": "high",
        "labItemName": "LDL",
        "whyDetected": "LDL 數值偏高",
        "suggestedAction": "建議與醫師討論血脂管理",
        "confidence": 0.75,
        "evidenceSources": [{"type": "lab_report_item", "id": "abc", "summary": "LDL H"}],
        "recurrenceCount": 2,
        "rule_id": "lab_abnormality_ldl",
    }


def _medium_lab_abn() -> dict:
    return {
        "abnormalityType": "glucose_abnormality",
        "severity": "medium",
        "labItemName": "血糖",
        "whyDetected": "血糖偏高",
        "suggestedAction": "建議追蹤血糖",
        "confidence": 0.60,
        "evidenceSources": [],
        "recurrenceCount": 1,
        "rule_id": "lab_abnormality_xue_tang",
    }


def _worsening_symptom_high() -> dict:
    return {
        "patternType": "worsening_symptom",
        "severity": "high",
        "symptomType": "頭痛",
        "label": "症狀持續惡化",
        "whyDetected": "頭痛嚴重度在過去7天持續上升",
        "confidence": 0.70,
        "suggestedAction": "建議密切觀察",
        "evidenceSources": [{"type": "symptom", "id": "s1", "summary": "頭痛"}],
    }


def _worsening_symptom_medium() -> dict:
    return {
        "patternType": "worsening_symptom",
        "severity": "medium",
        "symptomType": "疲勞",
        "label": "症狀持續惡化",
        "whyDetected": "疲勞嚴重度輕微上升",
        "confidence": 0.55,
        "suggestedAction": "建議觀察",
        "evidenceSources": [],
    }


def _unresolved_high_severity() -> dict:
    return {
        "patternType": "unresolved_high_severity_symptom",
        "severity": "high",
        "symptomType": "胸痛",
        "label": "高嚴重度症狀尚未緩解",
        "whyDetected": "胸痛已持續多日未緩解",
        "confidence": 0.80,
        "suggestedAction": "建議儘快諮詢醫師",
        "evidenceSources": [],
    }


def _bundle(**kwargs) -> dict:
    defaults: dict = {
        "device_escalation": {"escalationLevel": "none", "reasons": [], "confidence": 0.5, "recommendedAction": None, "requiresFollowUp": False},
        "lab_abnormalities": [],
        "symptom_patterns": [],
        "risk_alerts": [],
        "actions": [],
    }
    defaults.update(kwargs)
    return defaults


def _history_entry(
    cooldown_key: str,
    *,
    status: str = "sent",
    sent_at: str | None = None,
    snooze_count: int = 0,
    ignore_count: int = 0,
) -> dict:
    return {
        "cooldown_key": cooldown_key,
        "priority": "high",
        "status": status,
        "snooze_count": snooze_count,
        "ignore_count": ignore_count,
        "sent_at": sent_at,
    }


def _ago(hours: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.isoformat()


# ===========================================================================
# build_notification_candidates — source tests
# ===========================================================================

class TestCandidateBuilderSources:
    def test_urgent_device_escalation_produces_urgent(self):
        b = _bundle(device_escalation=_urgent_escalation())
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "urgent"
        assert candidates[0]["source_type"] == "device_escalation"

    def test_warning_device_escalation_produces_high(self):
        b = _bundle(device_escalation=_warning_escalation())
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"

    def test_watch_device_escalation_produces_medium(self):
        b = _bundle(device_escalation=_watch_escalation())
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "medium"

    def test_none_escalation_produces_no_candidate(self):
        b = _bundle()  # default has escalationLevel="none"
        candidates = build_notification_candidates(b)
        assert candidates == []

    def test_high_lab_abnormality_produces_high(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"
        assert candidates[0]["source_type"] == "lab_abnormality"

    def test_medium_lab_abnormality_produces_medium(self):
        b = _bundle(lab_abnormalities=[_medium_lab_abn()])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "medium"

    def test_worsening_symptom_high_produces_high(self):
        b = _bundle(symptom_patterns=[_worsening_symptom_high()])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"
        assert candidates[0]["source_type"] == "symptom_pattern"

    def test_worsening_symptom_medium_produces_medium(self):
        b = _bundle(symptom_patterns=[_worsening_symptom_medium()])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "medium"

    def test_unresolved_high_severity_produces_high(self):
        b = _bundle(symptom_patterns=[_unresolved_high_severity()])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"

    def test_risk_alert_critical_produces_urgent(self):
        alert = {
            "source_id": "ra1",
            "severity": "critical",
            "title": "心率危急警示",
            "message": "心率超過 140 bpm",
            "rule_code": "hr_critical",
            "recommendation": "立即就醫",
        }
        b = _bundle(risk_alerts=[alert])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "urgent"
        assert candidates[0]["source_type"] == "risk_alert"

    def test_risk_alert_high_produces_high(self):
        alert = {
            "source_id": "ra2",
            "severity": "high",
            "title": "血壓偏高",
            "message": "血壓連續偏高",
            "rule_code": "bp_high",
            "recommendation": "建議監測",
        }
        b = _bundle(risk_alerts=[alert])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"

    def test_symptom_with_lab_risk_produces_medium(self):
        pattern = {
            "patternType": "symptom_with_lab_risk",
            "severity": "medium",
            "symptomType": "疲勞",
            "label": "症狀伴隨異常檢驗指標",
            "whyDetected": "疲勞伴隨貧血指標異常",
            "confidence": 0.65,
            "suggestedAction": "建議說明",
            "evidenceSources": [],
        }
        b = _bundle(symptom_patterns=[pattern])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "medium"


# ===========================================================================
# build_notification_candidates — confidence and empty tests
# ===========================================================================

class TestCandidateBuilderConfidenceAndEmpty:
    def test_low_confidence_capped_at_medium(self):
        """confidence=0.30 < threshold: high lab → capped to medium."""
        abn = dict(_high_lab_abn())
        abn["confidence"] = 0.30  # below 0.40 threshold
        b = _bundle(lab_abnormalities=[abn])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "medium"

    def test_very_low_confidence_below_min_threshold_no_candidate(self):
        """confidence < 0.20 → no candidate generated."""
        abn = dict(_high_lab_abn())
        abn["confidence"] = 0.10
        b = _bundle(lab_abnormalities=[abn])
        candidates = build_notification_candidates(b)
        assert candidates == []

    def test_empty_bundle_returns_no_candidates(self):
        b: dict = {}
        candidates = build_notification_candidates(b)
        assert candidates == []

    def test_all_empty_sources_returns_no_candidates(self):
        b = _bundle(
            device_escalation={"escalationLevel": "none"},
            lab_abnormalities=[],
            symptom_patterns=[],
            risk_alerts=[],
        )
        candidates = build_notification_candidates(b)
        assert candidates == []


# ===========================================================================
# build_notification_candidates — structural tests
# ===========================================================================

class TestCandidateBuilderStructure:
    def test_evidence_sources_preserved(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        c = build_notification_candidates(b)[0]
        assert isinstance(c["evidence_sources"], list)
        assert len(c["evidence_sources"]) > 0
        assert "type" in c["evidence_sources"][0]

    def test_cooldown_key_present(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        c = build_notification_candidates(b)[0]
        assert "cooldown_key" in c
        assert isinstance(c["cooldown_key"], str)
        assert len(c["cooldown_key"]) > 0

    def test_candidate_id_is_deterministic(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        c1 = build_notification_candidates(b)[0]
        c2 = build_notification_candidates(b)[0]
        assert c1["candidate_id"] == c2["candidate_id"]

    def test_suppress_reason_none_on_active_candidate(self):
        b = _bundle(device_escalation=_urgent_escalation())
        c = build_notification_candidates(b)[0]
        assert c["suppress_reason"] is None

    def test_sorted_urgent_before_high_before_medium(self):
        b = _bundle(
            device_escalation=_watch_escalation(),  # medium
            lab_abnormalities=[_high_lab_abn()],    # high
        )
        candidates = build_notification_candidates(b)
        priorities = [c["priority"] for c in candidates]
        high_idx = priorities.index("high")
        medium_idx = priorities.index("medium")
        assert high_idx < medium_idx

    def test_duplicate_cooldown_key_keeps_higher_priority(self):
        """Two lab items with same rule_id → only one candidate, highest priority."""
        abn_low = dict(_medium_lab_abn())
        abn_low["rule_id"] = "lab_abnormality_ldl"
        abn_low["severity"] = "low"
        abn_low["labItemName"] = "LDL_low"

        abn_high = dict(_high_lab_abn())
        abn_high["rule_id"] = "lab_abnormality_ldl"
        abn_high["labItemName"] = "LDL_high"

        b = _bundle(lab_abnormalities=[abn_low, abn_high])
        candidates = build_notification_candidates(b)
        assert len(candidates) == 1
        assert candidates[0]["priority"] == "high"


# ===========================================================================
# apply_notification_fatigue_guard
# ===========================================================================

class TestFatigueGuard:
    def test_no_history_all_candidates_active(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn(), _medium_lab_abn()])
        candidates = build_notification_candidates(b)
        result = apply_notification_fatigue_guard(candidates)
        assert len(result["active"]) == 2
        assert result["suppressed"] == []

    def test_ignore_count_gte_3_suppressed(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        key = candidates[0]["cooldown_key"]
        history = [_history_entry(key, ignore_count=3)]
        result = apply_notification_fatigue_guard(candidates, history)
        assert len(result["active"]) == 0
        assert len(result["suppressed"]) == 1
        assert result["suppressed"][0]["suppress_reason"] is not None

    def test_active_action_rule_id_dedup_suppresses(self):
        abn = _high_lab_abn()
        abn["rule_id"] = "lab_abnormality_ldl"
        b = _bundle(lab_abnormalities=[abn])
        candidates = build_notification_candidates(b)
        # cooldown_key contains "lab_abnormality_ldl"
        active_rule_ids = {"lab_abnormality_ldl"}
        result = apply_notification_fatigue_guard(candidates, active_rule_ids=active_rule_ids)
        assert len(result["active"]) == 0
        assert len(result["suppressed"]) == 1
        assert "追蹤" in result["suppressed"][0]["suppress_reason"]

    def test_cooldown_window_not_elapsed_suppresses(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        key = candidates[0]["cooldown_key"]
        # sent 2 hours ago; high cooldown = 24h
        history = [_history_entry(key, sent_at=_ago(2))]
        result = apply_notification_fatigue_guard(candidates, history)
        assert len(result["active"]) == 0
        assert "冷卻" in result["suppressed"][0]["suppress_reason"]

    def test_cooldown_window_elapsed_candidate_active(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        key = candidates[0]["cooldown_key"]
        # sent 30 hours ago; high cooldown = 24h → elapsed
        history = [_history_entry(key, sent_at=_ago(30))]
        result = apply_notification_fatigue_guard(candidates, history)
        assert len(result["active"]) == 1
        assert result["suppressed"] == []

    def test_snoozed_status_downgrades_priority(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        key = candidates[0]["cooldown_key"]
        assert candidates[0]["priority"] == "high"
        history = [_history_entry(key, status="snoozed")]
        result = apply_notification_fatigue_guard(candidates, history)
        # Still active but downgraded
        assert len(result["active"]) == 1
        assert result["active"][0]["priority"] == "medium"

    def test_suppressed_candidates_have_suppress_reason(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        key = candidates[0]["cooldown_key"]
        history = [_history_entry(key, ignore_count=5)]
        result = apply_notification_fatigue_guard(candidates, history)
        for sup in result["suppressed"]:
            assert sup["suppress_reason"] is not None
            assert isinstance(sup["suppress_reason"], str)

    def test_guard_returns_both_keys(self):
        b = _bundle(lab_abnormalities=[_high_lab_abn()])
        candidates = build_notification_candidates(b)
        result = apply_notification_fatigue_guard(candidates)
        assert "active" in result
        assert "suppressed" in result

    def test_urgent_escalation_not_suppressed_by_unrelated_action(self):
        b = _bundle(device_escalation=_urgent_escalation())
        candidates = build_notification_candidates(b)
        # rule_id that does NOT appear in the escalation cooldown_key
        active_rule_ids = {"lab_abnormality_ldl"}
        result = apply_notification_fatigue_guard(candidates, active_rule_ids=active_rule_ids)
        assert len(result["active"]) == 1

    def test_empty_candidates_returns_empty_lists(self):
        result = apply_notification_fatigue_guard([])
        assert result["active"] == []
        assert result["suppressed"] == []
