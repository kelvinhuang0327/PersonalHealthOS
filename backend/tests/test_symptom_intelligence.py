"""Tests for symptom_intelligence_service.py
=============================================
All pure-function tests — no DB, no HTTP.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.symptom_intelligence_service import (
    build_symptom_timeline,
    detect_symptom_patterns,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _sym(
    name: str,
    severity: int,
    days_ago: int = 0,
    source_id: str = "sym-001",
    estimated_duration_days: int | None = None,
) -> dict:
    occ = (_NOW - timedelta(days=days_ago)).isoformat()
    return {
        "source_type": "symptom",
        "source_id": source_id,
        "symptom": name,
        "severity": severity,
        "occurred_at": occ,
        "summary": f"{name}（嚴重度 {severity}/10）",
        "estimated_duration_days": estimated_duration_days,
        "confidence": 0.7,
        "evidence_level": "C",
        "recency": "today" if days_ago == 0 else "this_week",
    }


def _sig(signal_type: str, severity: str = "medium") -> dict:
    return {
        "signal_type": signal_type,
        "severity": severity,
        "metric_type": "heart_rate",
        "current_value": 100.0,
        "baseline_value": 70.0,
        "trend": "rising",
        "why_detected": "test",
        "suggested_action": None,
        "confidence": 0.8,
        "freshness": "fresh",
    }


def _lab(item_name: str, abnormal_flag: str = "H") -> dict:
    return {
        "item_name": item_name,
        "abnormal_flag": abnormal_flag,
        "value_num": 140.0,
        "value_text": None,
        "report_date": _NOW.date().isoformat(),
        "source_id": "lab-001",
        "recency": "today",
        "summary": f"{item_name} 異常",
    }


# ---------------------------------------------------------------------------
# build_symptom_timeline
# ---------------------------------------------------------------------------


class TestBuildSymptomTimeline:
    """Timeline construction tests."""

    def test_empty_inputs_return_empty_list(self):
        result = build_symptom_timeline([], [], [], [], [])
        assert result == []

    def test_single_symptom_single_occurrence(self):
        syms = [_sym("頭痛", severity=5, days_ago=2, source_id="s1")]
        result = build_symptom_timeline(syms, [], [], [], [])
        assert len(result) == 1
        item = result[0]
        assert item["symptomType"] == "頭痛"
        assert item["recurrenceCount"] == 1
        assert item["severityTrend"] == "unknown"  # only 1 point
        assert item["recentSeverity"] == 5
        assert item["relatedDeviceSignals"] == []
        assert item["relatedLabItems"] == []

    def test_multiple_occurrences_same_symptom(self):
        syms = [
            _sym("疲勞", severity=4, days_ago=10, source_id="s1"),
            _sym("疲勞", severity=5, days_ago=5, source_id="s2"),
            _sym("疲勞", severity=6, days_ago=0, source_id="s3"),
        ]
        result = build_symptom_timeline(syms, [], [], [], [])
        assert len(result) == 1
        item = result[0]
        assert item["recurrenceCount"] == 3
        assert item["recentSeverity"] == 6

    def test_worsening_trend(self):
        syms = [
            _sym("頭痛", severity=2, days_ago=10, source_id="s1"),
            _sym("頭痛", severity=5, days_ago=5, source_id="s2"),
            _sym("頭痛", severity=8, days_ago=0, source_id="s3"),
        ]
        result = build_symptom_timeline(syms, [], [], [], [])
        assert result[0]["severityTrend"] == "worsening"

    def test_improving_trend(self):
        syms = [
            _sym("頭痛", severity=8, days_ago=10, source_id="s1"),
            _sym("頭痛", severity=5, days_ago=5, source_id="s2"),
            _sym("頭痛", severity=2, days_ago=0, source_id="s3"),
        ]
        result = build_symptom_timeline(syms, [], [], [], [])
        assert result[0]["severityTrend"] == "improving"

    def test_stable_trend(self):
        syms = [
            _sym("頭痛", severity=5, days_ago=10, source_id="s1"),
            _sym("頭痛", severity=5, days_ago=5, source_id="s2"),
            _sym("頭痛", severity=5, days_ago=0, source_id="s3"),
        ]
        result = build_symptom_timeline(syms, [], [], [], [])
        assert result[0]["severityTrend"] == "stable"

    def test_device_signal_correlation(self):
        """頭痛 should correlate with elevated_resting_heart_rate when present."""
        syms = [_sym("頭痛", severity=6, days_ago=1)]
        sigs = [_sig("elevated_resting_heart_rate", severity="medium")]
        result = build_symptom_timeline(syms, [], [], sigs, [])
        assert "elevated_resting_heart_rate" in result[0]["relatedDeviceSignals"]

    def test_no_hallucination_absent_signal(self):
        """Signal not in input must NOT appear in relatedDeviceSignals."""
        syms = [_sym("頭痛", severity=6, days_ago=1)]
        # no device signals in input
        result = build_symptom_timeline(syms, [], [], [], [])
        assert result[0]["relatedDeviceSignals"] == []

    def test_lab_correlation(self):
        """血壓 symptom should correlate with abnormal 血壓 lab item."""
        syms = [_sym("高血壓", severity=6, days_ago=1)]
        labs = [_lab("血壓", abnormal_flag="H")]
        result = build_symptom_timeline(syms, [], [], [], labs)
        assert len(result[0]["relatedLabItems"]) > 0
        assert "血壓" in result[0]["relatedLabItems"][0]

    def test_normal_lab_not_correlated(self):
        """Normal lab item (no abnormal_flag) must NOT appear in relatedLabItems."""
        syms = [_sym("高血壓", severity=6, days_ago=1)]
        labs = [{"item_name": "血壓", "abnormal_flag": None, "value_num": 120, "value_text": None}]
        result = build_symptom_timeline(syms, [], [], [], labs)
        assert result[0]["relatedLabItems"] == []

    def test_long_term_symptoms_merged(self):
        """long_term_symptoms should be merged with regular symptoms."""
        syms = [_sym("疲勞", severity=4, days_ago=10, source_id="s1")]
        lts = [_sym("疲勞", severity=6, days_ago=0, source_id="s2")]
        result = build_symptom_timeline(syms, lts, [], [], [])
        assert result[0]["recurrenceCount"] == 2

    def test_evidence_sources_populated(self):
        syms = [_sym("頭痛", severity=5, days_ago=2, source_id="s-abc")]
        result = build_symptom_timeline(syms, [], [], [], [])
        evidence = result[0]["evidenceSources"]
        assert len(evidence) == 1
        assert evidence[0]["type"] == "symptom"
        assert evidence[0]["id"] == "s-abc"


# ---------------------------------------------------------------------------
# detect_symptom_patterns
# ---------------------------------------------------------------------------


class TestDetectSymptomPatterns:
    """Pattern detection tests."""

    def test_empty_timeline_returns_empty(self):
        result = detect_symptom_patterns([], [], [], [], [])
        assert result == []

    def test_recurring_symptom_3_occurrences(self):
        syms = [
            _sym("疲勞", severity=5, days_ago=12, source_id="s1"),
            _sym("疲勞", severity=5, days_ago=6, source_id="s2"),
            _sym("疲勞", severity=5, days_ago=0, source_id="s3"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        types = [p["patternType"] for p in patterns]
        assert "recurring_symptom" in types

    def test_no_recurring_pattern_below_threshold(self):
        """recurrenceCount == 2 → no recurring_symptom pattern (threshold ≥ 3)."""
        syms = [
            _sym("疲勞", severity=5, days_ago=5, source_id="s1"),
            _sym("疲勞", severity=5, days_ago=0, source_id="s2"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        types = [p["patternType"] for p in patterns]
        assert "recurring_symptom" not in types

    def test_worsening_symptom_detected(self):
        syms = [
            _sym("頭痛", severity=2, days_ago=10, source_id="s1"),
            _sym("頭痛", severity=5, days_ago=5, source_id="s2"),
            _sym("頭痛", severity=9, days_ago=0, source_id="s3"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        types = [p["patternType"] for p in patterns]
        assert "worsening_symptom" in types

    def test_symptom_with_device_signal_pattern(self):
        syms = [_sym("頭痛", severity=6, days_ago=0)]
        sigs = [_sig("elevated_resting_heart_rate")]
        timeline = build_symptom_timeline(syms, [], [], sigs, [])
        patterns = detect_symptom_patterns(timeline, syms, [], sigs, [])
        types = [p["patternType"] for p in patterns]
        assert "symptom_with_device_signal" in types

    def test_symptom_with_lab_risk_pattern(self):
        syms = [_sym("高血壓", severity=6, days_ago=0)]
        labs = [_lab("血壓", abnormal_flag="H")]
        timeline = build_symptom_timeline(syms, [], [], [], labs)
        patterns = detect_symptom_patterns(timeline, syms, [], [], labs)
        types = [p["patternType"] for p in patterns]
        assert "symptom_with_lab_risk" in types

    def test_unresolved_high_severity(self):
        syms = [
            _sym("胸痛", severity=9, days_ago=2, source_id="s1"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        types = [p["patternType"] for p in patterns]
        assert "unresolved_high_severity_symptom" in types

    def test_no_hallucinated_pattern_for_low_severity(self):
        """Low-severity, single, improving symptom with no device signals/labs.
        Should produce no high-severity pattern."""
        syms = [_sym("輕微頭痛", severity=3, days_ago=0)]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        # No unresolved_high_severity_symptom (sev < 8)
        types = [p["patternType"] for p in patterns]
        assert "unresolved_high_severity_symptom" not in types
        assert "worsening_symptom" not in types
        assert "recurring_symptom" not in types

    def test_pattern_severity_high_when_recent_severity_high(self):
        """worsening + high recentSeverity → pattern severity == 'high'."""
        syms = [
            _sym("頭痛", severity=3, days_ago=10, source_id="s1"),
            _sym("頭痛", severity=7, days_ago=5, source_id="s2"),
            _sym("頭痛", severity=9, days_ago=0, source_id="s3"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        worsening = next(p for p in patterns if p["patternType"] == "worsening_symptom")
        assert worsening["severity"] == "high"

    def test_confidence_capped_at_0_90(self):
        """Confidence must never exceed 0.90."""
        # 10 occurrences → would push 0.60 + 10*0.05 = 1.10 without capping
        syms = [
            _sym("疲勞", severity=5, days_ago=i, source_id=f"s{i}") for i in range(10)
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        for p in patterns:
            assert p["confidence"] <= 0.90

    def test_pattern_why_detected_contains_symptom_name(self):
        syms = [
            _sym("心悸", severity=6, days_ago=5, source_id="s1"),
            _sym("心悸", severity=7, days_ago=2, source_id="s2"),
            _sym("心悸", severity=8, days_ago=0, source_id="s3"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        for p in patterns:
            assert "心悸" in p["whyDetected"]

    def test_sorted_high_before_medium(self):
        """High-severity patterns must appear before medium-severity ones."""
        syms = [
            _sym("胸痛", severity=9, days_ago=0),   # unresolved_high_severity
            _sym("疲勞", severity=4, days_ago=5, source_id="s2"),
            _sym("疲勞", severity=4, days_ago=10, source_id="s3"),
            _sym("疲勞", severity=4, days_ago=15, source_id="s4"),
        ]
        timeline = build_symptom_timeline(syms, [], [], [], [])
        patterns = detect_symptom_patterns(timeline, syms, [], [], [])
        severities = [p["severity"] for p in patterns]
        # All high patterns must come before any medium pattern
        high_indices = [i for i, s in enumerate(severities) if s == "high"]
        medium_indices = [i for i, s in enumerate(severities) if s == "medium"]
        if high_indices and medium_indices:
            assert max(high_indices) < min(medium_indices)
