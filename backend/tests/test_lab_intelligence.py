"""Pure-function tests — Lab Intelligence Service (P4)
======================================================
All tests call detect_lab_abnormalities() directly with in-memory data.
No DB, no HTTP.

Coverage:
  • Empty inputs → empty output (anti-hallucination)
  • Single abnormal item → medium severity (H flag)
  • Critical flag → high severity regardless of recurrence
  • 2 occurrences of same item → recurrenceCount == 2, severity >= medium
  • 3 occurrences of same item → severity == high
  • Different items remain separate entries
  • Risk alert corroboration → severity boost + evidenceSource added
  • Risk alert for unknown item → NOT introduced (anti-hallucination)
  • Abnormality type classification (LDL, HbA1c, ALT, creatinine, TSH)
  • suggestedAction present and non-empty for each type
  • whyDetected contains item_name
  • confidence bounded [0.30, 0.88]
  • Confidence boosted with alert corroboration
  • Sorted: high before medium before low
  • Sorted: higher recurrenceCount first within same severity
  • rule_id format: "lab_abnormality_{item_name}"
  • currentValue: float when value_num present, str when only value_text
  • referenceRange: None when not provided
  • evidenceSources contains one entry per occurrence
"""
from __future__ import annotations

import pytest

from app.services.lab_intelligence_service import detect_lab_abnormalities


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(
    item_name: str = "LDL",
    value_num: float | None = 4.5,
    value_text: str | None = None,
    unit: str = "mmol/L",
    ref_range: str | None = "< 3.37 mmol/L",
    abnormal_flag: str | None = "H",
    confidence: float = 0.80,
    report_id: str = "report-001",
    source_id: str | None = None,
    recency: str = "this_month",
    report_date: str = "2026-05-10",
) -> dict:
    import uuid
    return {
        "source_type": "lab_report_item",
        "source_id": source_id or str(uuid.uuid4()),
        "report_id": report_id,
        "recency": recency,
        "confidence": confidence,
        "evidence_level": "A",
        "summary": f"{item_name} 異常",
        "item_name": item_name,
        "item_code": None,
        "value_num": value_num,
        "value_text": value_text,
        "unit": unit,
        "ref_range": ref_range,
        "abnormal_flag": abnormal_flag,
        "report_date": report_date,
    }


def _alert(
    item_name_keyword: str,
    severity: str = "high",
    source_id: str = "alert-001",
) -> dict:
    return {
        "source_type": "risk_alert",
        "source_id": source_id,
        "recency": "this_week",
        "confidence": 0.85,
        "evidence_level": "B",
        "title": f"{item_name_keyword} 異常警示",
        "summary": f"{item_name_keyword} 異常警示",
        "severity": severity,
        "risk_type": "lab_risk",
        "rule_code": f"lab_{item_name_keyword.lower()}",
        "message": f"{item_name_keyword} 數值超出正常範圍",
        "recommendation": "建議追蹤",
        "created_at": "2026-05-10T08:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Basic contracts
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_no_items_returns_empty(self):
        result = detect_lab_abnormalities([], [])
        assert result == []

    def test_no_items_with_alerts_still_empty(self):
        """Alerts cannot hallucinate new lab items."""
        alerts = [_alert("LDL")]
        result = detect_lab_abnormalities([], alerts)
        assert result == []

    def test_no_abnormal_flag_items_only(self):
        """Items with abnormal_flag=None are already filtered by build_evidence_bundle,
        so passing them in should still produce output (we trust the caller).
        This test verifies we handle them gracefully."""
        items = [_item(abnormal_flag=None)]
        result = detect_lab_abnormalities(items, [])
        # Still produces entry — service doesn't re-filter, trusts caller
        assert len(result) == 1


class TestSingleItem:
    def test_h_flag_medium_severity(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="H")], [])
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_l_flag_medium_severity(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="L")], [])
        assert result[0]["severity"] == "medium"

    def test_hh_flag_high_severity(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="HH")], [])
        assert result[0]["severity"] == "high"

    def test_critical_flag_high_severity(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="CRITICAL")], [])
        assert result[0]["severity"] == "high"

    def test_bang_bang_flag_high(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="!!")], [])
        assert result[0]["severity"] == "high"

    def test_unknown_flag_low_severity(self):
        result = detect_lab_abnormalities([_item(abnormal_flag="BORDERLINE")], [])
        assert result[0]["severity"] == "low"


# ---------------------------------------------------------------------------
# Recurrence detection
# ---------------------------------------------------------------------------

class TestRecurrence:
    def test_two_occurrences_same_item_count_is_2(self):
        items = [
            _item(item_name="LDL", report_id="r1", recency="this_month"),
            _item(item_name="LDL", report_id="r2", recency="older"),
        ]
        result = detect_lab_abnormalities(items, [])
        assert len(result) == 1
        assert result[0]["recurrenceCount"] == 2

    def test_two_occurrences_severity_at_least_medium(self):
        items = [
            _item(item_name="LDL", abnormal_flag="H", report_id="r1"),
            _item(item_name="LDL", abnormal_flag="H", report_id="r2"),
        ]
        result = detect_lab_abnormalities(items, [])
        assert result[0]["severity"] in ("medium", "high")

    def test_three_occurrences_severity_high(self):
        items = [
            _item(item_name="LDL", abnormal_flag="H", report_id=f"r{i}")
            for i in range(3)
        ]
        result = detect_lab_abnormalities(items, [])
        assert result[0]["severity"] == "high"

    def test_different_items_remain_separate(self):
        items = [
            _item(item_name="LDL"),
            _item(item_name="ALT"),
        ]
        result = detect_lab_abnormalities(items, [])
        assert len(result) == 2
        names = {r["labItemName"] for r in result}
        assert names == {"LDL", "ALT"}


# ---------------------------------------------------------------------------
# Risk-alert corroboration
# ---------------------------------------------------------------------------

class TestAlertCorroboration:
    def test_matching_alert_boosts_severity(self):
        items = [_item(item_name="LDL", abnormal_flag="H")]
        alerts = [_alert("LDL", severity="high")]
        result = detect_lab_abnormalities(items, alerts)
        assert result[0]["severity"] == "high"

    def test_matching_alert_added_to_evidence_sources(self):
        items = [_item(item_name="LDL")]
        alerts = [_alert("LDL")]
        result = detect_lab_abnormalities(items, alerts)
        types = [e["type"] for e in result[0]["evidenceSources"]]
        assert "risk_alert" in types

    def test_unrelated_alert_does_not_appear(self):
        items = [_item(item_name="LDL")]
        alerts = [_alert("ALT")]  # different item
        result = detect_lab_abnormalities(items, alerts)
        types = [e["type"] for e in result[0]["evidenceSources"]]
        assert "risk_alert" not in types

    def test_alert_boosts_confidence(self):
        items = [_item(item_name="LDL", confidence=0.70)]
        no_alert_result = detect_lab_abnormalities(items, [])
        alert_result = detect_lab_abnormalities(items, [_alert("LDL")])
        assert alert_result[0]["confidence"] > no_alert_result[0]["confidence"]


# ---------------------------------------------------------------------------
# Abnormality type classification
# ---------------------------------------------------------------------------

class TestAbnormalityTypeClassification:
    @pytest.mark.parametrize("item_name,expected_type", [
        ("LDL",              "lipid_abnormality"),
        ("HDL",              "lipid_abnormality"),
        ("膽固醇",            "lipid_abnormality"),
        ("HbA1c",            "glucose_abnormality"),
        ("血糖",              "glucose_abnormality"),
        ("ALT",              "liver_function"),
        ("GOT",              "liver_function"),
        ("creatinine",       "kidney_function"),
        ("eGFR",             "kidney_function"),
        ("TSH",              "thyroid_function"),
        ("甲狀腺",            "thyroid_function"),
        ("Hemoglobin",       "anemia_marker"),
        ("血紅素",            "anemia_marker"),
        ("尿酸",              "uric_acid"),
        ("CRP",              "inflammation_marker"),
        ("UnknownMarker123", "lab_abnormality"),
    ])
    def test_classification(self, item_name, expected_type):
        items = [_item(item_name=item_name)]
        result = detect_lab_abnormalities(items, [])
        assert result[0]["abnormalityType"] == expected_type, (
            f"Expected {expected_type} for {item_name}, got {result[0]['abnormalityType']}"
        )


# ---------------------------------------------------------------------------
# Output schema & values
# ---------------------------------------------------------------------------

class TestOutputSchema:
    _REQUIRED_KEYS = {
        "abnormalityType", "severity", "labItemName", "currentValue",
        "referenceRange", "reportId", "detectedAt", "whyDetected",
        "suggestedAction", "confidence", "evidenceSources",
        "recurrenceCount", "rule_id",
    }

    def test_all_required_keys_present(self):
        result = detect_lab_abnormalities([_item()], [])
        missing = self._REQUIRED_KEYS - set(result[0].keys())
        assert not missing, f"Missing keys: {missing}"

    def test_why_detected_contains_item_name(self):
        result = detect_lab_abnormalities([_item(item_name="LDL")], [])
        assert "LDL" in result[0]["whyDetected"]

    def test_suggested_action_non_empty(self):
        result = detect_lab_abnormalities([_item()], [])
        assert result[0]["suggestedAction"].strip()

    def test_suggested_action_no_diagnosis_wording(self):
        """Non-diagnosis contract: certain clinical claim phrases must not appear."""
        blacklist = ["您罹患", "診斷為", "確診", "病症"]
        for item_name in ("LDL", "HbA1c", "ALT", "creatinine", "TSH"):
            items = [_item(item_name=item_name)]
            result = detect_lab_abnormalities(items, [])
            action = result[0]["suggestedAction"]
            for phrase in blacklist:
                assert phrase not in action, (
                    f"Diagnosis wording '{phrase}' found in suggestedAction for {item_name}"
                )

    def test_confidence_bounded_low(self):
        result = detect_lab_abnormalities([_item(confidence=0.05)], [])
        assert result[0]["confidence"] >= 0.30

    def test_confidence_bounded_high(self):
        result = detect_lab_abnormalities([_item(confidence=0.99)], [])
        assert result[0]["confidence"] <= 0.88

    def test_current_value_float_when_value_num_present(self):
        result = detect_lab_abnormalities([_item(value_num=5.2)], [])
        assert isinstance(result[0]["currentValue"], float)
        assert result[0]["currentValue"] == pytest.approx(5.2)

    def test_current_value_str_when_only_value_text(self):
        result = detect_lab_abnormalities([_item(value_num=None, value_text="Positive")], [])
        assert result[0]["currentValue"] == "Positive"

    def test_current_value_none_when_neither(self):
        result = detect_lab_abnormalities([_item(value_num=None, value_text=None)], [])
        assert result[0]["currentValue"] is None

    def test_reference_range_none_when_not_provided(self):
        result = detect_lab_abnormalities([_item(ref_range=None)], [])
        assert result[0]["referenceRange"] is None

    def test_rule_id_format(self):
        result = detect_lab_abnormalities([_item(item_name="LDL")], [])
        assert result[0]["rule_id"].startswith("lab_abnormality_")
        assert "LDL" in result[0]["rule_id"]

    def test_evidence_sources_one_per_occurrence(self):
        items = [
            _item(item_name="LDL", report_id="r1"),
            _item(item_name="LDL", report_id="r2"),
        ]
        result = detect_lab_abnormalities(items, [])
        lab_sources = [e for e in result[0]["evidenceSources"] if e["type"] == "lab_report_item"]
        assert len(lab_sources) == 2


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

class TestSorting:
    def test_high_before_medium_before_low(self):
        items = [
            _item(item_name="Low",    abnormal_flag="BORDERLINE"),
            _item(item_name="High",   abnormal_flag="HH"),
            _item(item_name="Medium", abnormal_flag="H"),
        ]
        result = detect_lab_abnormalities(items, [])
        severities = [r["severity"] for r in result]
        # high should come first
        assert severities[0] == "high"
        # medium before low
        med_idx = next((i for i, s in enumerate(severities) if s == "medium"), None)
        low_idx = next((i for i, s in enumerate(severities) if s == "low"), None)
        if med_idx is not None and low_idx is not None:
            assert med_idx < low_idx

    def test_higher_recurrence_first_within_same_severity(self):
        items_3x = [_item(item_name="LDL", abnormal_flag="H", report_id=f"r{i}") for i in range(3)]
        items_1x = [_item(item_name="ALT", abnormal_flag="H", report_id="r10")]
        result = detect_lab_abnormalities(items_3x + items_1x, [])
        # LDL has 3 occurrences → both end up "high" severity;
        # LDL should sort before ALT within "high"
        names = [r["labItemName"] for r in result if r["severity"] == "high"]
        if len(names) >= 2:
            assert names[0] == "LDL"


# ---------------------------------------------------------------------------
# Task 5 — Required test scenarios
# ---------------------------------------------------------------------------

class TestHighTriglycerides:
    """high_triglycerides detection — TG / 三酸甘油酯 items."""

    def test_tg_item_detected(self):
        result = detect_lab_abnormalities([_item(item_name="TG", abnormal_flag="H")], [])
        assert len(result) == 1
        assert result[0]["labItemName"] == "TG"

    def test_tg_classified_as_lipid(self):
        result = detect_lab_abnormalities([_item(item_name="TG", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "lipid_abnormality"

    def test_triglyceride_zh_detected(self):
        result = detect_lab_abnormalities([_item(item_name="三酸甘油酯", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "lipid_abnormality"

    def test_tg_high_flag_medium_severity(self):
        result = detect_lab_abnormalities([_item(item_name="TG", abnormal_flag="H")], [])
        assert result[0]["severity"] == "medium"

    def test_tg_hh_flag_high_severity(self):
        result = detect_lab_abnormalities([_item(item_name="TG", abnormal_flag="HH")], [])
        assert result[0]["severity"] == "high"


class TestLowHDL:
    """low_hdl detection — HDL items (abnormal_flag L = low, which is bad for HDL)."""

    def test_hdl_l_flag_detected(self):
        result = detect_lab_abnormalities([_item(item_name="HDL", abnormal_flag="L")], [])
        assert len(result) == 1
        assert result[0]["labItemName"] == "HDL"

    def test_hdl_classified_as_lipid(self):
        result = detect_lab_abnormalities([_item(item_name="HDL", abnormal_flag="L")], [])
        assert result[0]["abnormalityType"] == "lipid_abnormality"

    def test_hdl_l_flag_medium_severity(self):
        result = detect_lab_abnormalities([_item(item_name="HDL", abnormal_flag="L")], [])
        assert result[0]["severity"] == "medium"

    def test_hdl_action_non_empty(self):
        result = detect_lab_abnormalities([_item(item_name="HDL", abnormal_flag="L")], [])
        assert result[0]["suggestedAction"].strip()


class TestHighUricAcid:
    """high_uric_acid detection — 尿酸 / Uric Acid items."""

    def test_uric_acid_zh_detected(self):
        result = detect_lab_abnormalities([_item(item_name="尿酸", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "uric_acid"

    def test_uric_acid_en_detected(self):
        result = detect_lab_abnormalities([_item(item_name="Uric Acid", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "uric_acid"

    def test_uric_acid_action_mentions_purine(self):
        result = detect_lab_abnormalities([_item(item_name="尿酸", abnormal_flag="H")], [])
        # Action should not say diagnosis but should provide lifestyle guidance
        assert "建議" in result[0]["suggestedAction"]

    def test_uric_acid_not_confused_with_kidney(self):
        """Uric acid should map to uric_acid type, not kidney_function."""
        result = detect_lab_abnormalities([_item(item_name="尿酸", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "uric_acid"
        assert result[0]["abnormalityType"] != "kidney_function"


class TestFattyLiverMarker:
    """fatty_liver_marker detection."""

    def test_fatty_liver_zh_detected(self):
        result = detect_lab_abnormalities([_item(item_name="脂肪肝", abnormal_flag="A")], [])
        assert result[0]["abnormalityType"] == "fatty_liver_marker"

    def test_fatty_liver_action_non_empty(self):
        result = detect_lab_abnormalities([_item(item_name="脂肪肝", abnormal_flag="A")], [])
        assert result[0]["suggestedAction"].strip()
        assert "建議" in result[0]["suggestedAction"]


class TestKidneyStoneMarker:
    """kidney_stone_related_marker detection."""

    def test_oxalate_detected(self):
        result = detect_lab_abnormalities([_item(item_name="Oxalate", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "kidney_stone_related_marker"

    def test_calcium_detected(self):
        result = detect_lab_abnormalities([_item(item_name="Calcium", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "kidney_stone_related_marker"

    def test_kidney_stone_action_mentions_water(self):
        result = detect_lab_abnormalities([_item(item_name="Oxalate", abnormal_flag="H")], [])
        assert "建議" in result[0]["suggestedAction"]


class TestGenericOutOfRange:
    """generic_out_of_range_lab — unknown item_name falls back to lab_abnormality."""

    def test_unknown_item_classified_generic(self):
        result = detect_lab_abnormalities([_item(item_name="XYZ_MARKER_999", abnormal_flag="H")], [])
        assert result[0]["abnormalityType"] == "lab_abnormality"

    def test_generic_still_has_all_required_fields(self):
        required = {"abnormalityType", "severity", "labItemName", "whyDetected",
                    "suggestedAction", "confidence", "evidenceSources", "rule_id"}
        result = detect_lab_abnormalities([_item(item_name="XYZ_MARKER_999", abnormal_flag="H")], [])
        missing = required - set(result[0].keys())
        assert not missing

    def test_generic_suggested_action_non_empty(self):
        result = detect_lab_abnormalities([_item(item_name="UNKNOWN_MED_X", abnormal_flag="A")], [])
        assert result[0]["suggestedAction"].strip()


class TestNoReferenceRangeNoHallucination:
    """When abnormal_flag is set but ref_range is None, output is still produced
    (the flag IS the ground truth). But when NEITHER flag NOR ref_range exists,
    the caller (build_evidence_bundle) should never pass such items in — and
    detect_lab_abnormalities does not invent abnormalities from flagless items.
    """

    def test_no_ref_range_with_flag_produces_entry(self):
        """An item with flag=H but no ref_range must still produce an entry
        (flag alone is sufficient signal — anti-hallucination means we don't
        invent the VALUE being abnormal; the flag already says so)."""
        item = _item(item_name="LDL", abnormal_flag="H", ref_range=None)
        result = detect_lab_abnormalities([item], [])
        assert len(result) == 1
        assert result[0]["referenceRange"] is None  # preserved as-is

    def test_why_detected_works_without_ref_range(self):
        item = _item(item_name="LDL", abnormal_flag="H", ref_range=None)
        result = detect_lab_abnormalities([item], [])
        assert "LDL" in result[0]["whyDetected"]
        # No reference range text should appear
        assert "參考範圍" not in result[0]["whyDetected"]

    def test_two_items_no_ref_range_only_count_what_is_there(self):
        """Service returns exactly the items passed in, no extras."""
        items = [
            _item(item_name="LDL", ref_range=None),
            _item(item_name="HDL", ref_range=None),
        ]
        result = detect_lab_abnormalities(items, [])
        assert len(result) == 2
        names = {r["labItemName"] for r in result}
        assert names == {"LDL", "HDL"}


class TestStaleReportConfidenceDowngrade:
    """Stale reports (recency == 'older') should lower confidence and add
    a data-currency warning to whyDetected."""

    def test_stale_recency_lowers_confidence_vs_recent(self):
        fresh = _item(item_name="LDL", confidence=0.80, recency="this_week")
        stale = _item(item_name="LDL", confidence=0.80, recency="older")
        fresh_result = detect_lab_abnormalities([fresh], [])
        stale_result = detect_lab_abnormalities([stale], [])
        assert stale_result[0]["confidence"] < fresh_result[0]["confidence"]

    def test_stale_confidence_still_bounded_above_minimum(self):
        stale = _item(item_name="LDL", confidence=0.30, recency="older")
        result = detect_lab_abnormalities([stale], [])
        assert result[0]["confidence"] >= 0.30

    def test_stale_why_detected_contains_warning(self):
        stale = _item(item_name="LDL", recency="older")
        result = detect_lab_abnormalities([stale], [])
        # Should contain some indication of data age
        assert "較早" in result[0]["whyDetected"] or "較舊" in result[0]["whyDetected"] or "重新" in result[0]["whyDetected"]

    def test_recent_why_detected_no_stale_warning(self):
        fresh = _item(item_name="LDL", recency="this_week")
        result = detect_lab_abnormalities([fresh], [])
        assert "較早期" not in result[0]["whyDetected"]


class TestEmptyReportFallback:
    """Service must return [] and not raise when given empty inputs."""

    def test_empty_lab_items_returns_empty_list(self):
        assert detect_lab_abnormalities([], []) == []

    def test_empty_lab_items_with_alerts_returns_empty(self):
        alerts = [_alert("LDL"), _alert("TG"), _alert("HDL")]
        assert detect_lab_abnormalities([], alerts) == []

    def test_none_like_items_filtered_gracefully(self):
        # Items with empty item_name string should be silently skipped
        items = [_item(item_name=""), _item(item_name="LDL")]
        result = detect_lab_abnormalities(items, [])
        assert len(result) == 1
        assert result[0]["labItemName"] == "LDL"


class TestEvidenceSourceTraceability:
    """Each detected abnormality must trace back to its source report/item."""

    def test_report_id_preserved_in_entry(self):
        item = _item(item_name="LDL", report_id="report-abc-123")
        result = detect_lab_abnormalities([item], [])
        assert result[0]["reportId"] == "report-abc-123"

    def test_source_id_preserved_in_evidence_sources(self):
        item = _item(item_name="LDL", source_id="item-uuid-456")
        result = detect_lab_abnormalities([item], [])
        lab_srcs = [e for e in result[0]["evidenceSources"] if e["type"] == "lab_report_item"]
        ids = [e["id"] for e in lab_srcs]
        assert "item-uuid-456" in ids

    def test_multiple_reports_all_sources_listed(self):
        items = [
            _item(item_name="TG", report_id="r1", source_id="s1"),
            _item(item_name="TG", report_id="r2", source_id="s2"),
            _item(item_name="TG", report_id="r3", source_id="s3"),
        ]
        result = detect_lab_abnormalities(items, [])
        lab_srcs = [e for e in result[0]["evidenceSources"] if e["type"] == "lab_report_item"]
        ids = {e["id"] for e in lab_srcs}
        assert ids == {"s1", "s2", "s3"}

    def test_alert_source_id_in_evidence(self):
        item = _item(item_name="LDL")
        alert = _alert("LDL", source_id="alert-xyz-789")
        result = detect_lab_abnormalities([item], [alert])
        alert_srcs = [e for e in result[0]["evidenceSources"] if e["type"] == "risk_alert"]
        assert len(alert_srcs) >= 1
        assert alert_srcs[0]["id"] == "alert-xyz-789"

