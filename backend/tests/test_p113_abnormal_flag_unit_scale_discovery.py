"""P113 — Abnormal Flag Unit-Scale Safety Discovery

Characterization tests — these tests document CURRENT behaviour as observed
during P113 discovery.  They do NOT fix any bugs.  They exist to establish
a precise contract baseline before any remediation work begins in a future
lane (A/B/C/D as described in the discovery report).

Discovery answers
-----------------
  A. Where is abnormal_flag derived?   → report_parser.compute_abnormal_flag
                                          (purely numeric, no unit parameter)
  B. Does a cross-unit mismatch produce a wrong flag?
                                       → YES — FALSE POSITIVE ('L') when
                                          mmol/L value compared against mg/dL
                                          rule thresholds via infer_reference_range
  C. Is LabReportItem.normalized_unit consulted before flagging?
                                       → NO — stored but never cross-checked
  D. Does the wrong flag propagate to downstream services?
                                       → YES — detect_lab_abnormalities returns
                                          medium severity from the false-positive;
                                          Daily Assistant / notifications inherit it

Risk classification: LATENT
  The risk activates only when (a) the lab report uses a non-standard unit scale
  AND (b) no explicit reference range is embedded in the report text,
  causing infer_reference_range to fall back to a rule whose thresholds are
  calibrated for a different scale.

Governance
----------
  This file stages NO production code changes.  Parser behaviour, DB schema,
  and the lab-history comparison logic are untouched.
"""
from __future__ import annotations

import inspect

import pytest

from app.services.report_parser import (
    compute_abnormal_flag,
    infer_reference_range,
    parse_lab_items,
)
from app.services.lab_intelligence_service import detect_lab_abnormalities


# ---------------------------------------------------------------------------
# Test A — Same-scale baseline: explicit reference range embedded in report
#   Characterize current CORRECT behaviour (no unit mismatch path).
# ---------------------------------------------------------------------------

class TestA_SameScaleExplicitRange:
    """Glucose in mg/dL with range from report text → no rule-infer path, correct flag."""

    def test_a1_normal_glucose_mg_dl_explicit_range(self):
        """90 mg/dL, explicit range 70-99 → flag='N' (correct, no false positive)."""
        items = parse_lab_items("Glucose 90 mg/dL 70-99")
        assert len(items) == 1
        item = items[0]
        assert item["abnormal_flag"] == "N"
        assert item["unit"] == "mg/dL"
        assert item["normalized_unit"] == "mg/dL"

    def test_a2_high_glucose_mg_dl_explicit_range(self):
        """125 mg/dL, explicit range 70-99 → flag='H' (correct true positive)."""
        items = parse_lab_items("Glucose 125 mg/dL 70-99")
        assert len(items) == 1
        item = items[0]
        assert item["abnormal_flag"] == "H"

    def test_a3_low_glucose_mg_dl_explicit_range(self):
        """60 mg/dL, explicit range 70-99 → flag='L' (correct true positive)."""
        items = parse_lab_items("Glucose 60 mg/dL 70-99")
        assert len(items) == 1
        item = items[0]
        assert item["abnormal_flag"] == "L"


# ---------------------------------------------------------------------------
# Test B — Cross-scale mismatch (rule-inferred path)
#   Characterize FALSE POSITIVE and FALSE NEGATIVE produced by the mismatch.
# ---------------------------------------------------------------------------

class TestB_CrossScaleMismatch:
    """Glucose / LDL in mmol/L without explicit range → rule applied in mg/dL."""

    def test_b1_glucose_5_5_mmol_l_false_positive_suppressed_by_p114(self):
        """5.5 mmol/L is clinically NORMAL Glucose (~99 mg/dL equivalent).

        PRE-P114 BEHAVIOUR (documented in P113):
          compute_abnormal_flag(5.5, 70.0, 99.0) → 'L' (false positive)

        POST-P114 BEHAVIOUR (P114 unit-scale guard active):
          normalized_unit='mmol/L', rule_unit='mg/dL' → mismatch detected
          → _unit_scale_compatible returns False
          → abnormal_flag = None  (suppressed, not a clinical 'normal')
        """
        items = parse_lab_items("Glucose 5.5 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["unit"] == "mmol/L"
        assert item["normalized_unit"] == "mmol/L"
        # P114 guard: false-positive 'L' is now suppressed → None
        assert item["abnormal_flag"] is None, (
            "P114 guard: Glucose 5.5 mmol/L unit-scale mismatch suppresses flag "
            "(abnormal_flag=None means 'not flagged by local rule', not 'clinically normal')"
        )

    def test_b2_infer_reference_range_returns_mg_dl_thresholds_for_mmol_l_unit(self):
        """infer_reference_range accepts 'mmol/L' but returns the mg/dL rule verbatim.

        CURRENT BEHAVIOUR: The unit arg is only used as a display fallback
        (ref_unit = rule.get('unit') or unit).  Thresholds are not scaled.
        """
        low, high, ref_range_str, source = infer_reference_range("Glucose", None, "mmol/L")
        assert low == 70.0
        assert high == 99.0
        assert source == "default_rule"
        # Rule unit (mg/dL) appears in string — NOT the caller's mmol/L
        assert "mg/dL" in ref_range_str, (
            "CHARACTERIZATION: ref_range string uses rule unit 'mg/dL', "
            "not the actual sample unit 'mmol/L'"
        )

    def test_b3_ldl_3_4_mmol_l_false_negative_suppressed_by_p114(self):
        """LDL 3.4 mmol/L ≈ 131 mg/dL (borderline-high) previously got wrong 'N'.

        PRE-P114 BEHAVIOUR (documented in P113):
          compute_abnormal_flag(3.4, 0.0, 130.0) → 'N' (false negative)

        POST-P114 BEHAVIOUR (P114 unit-scale guard active):
          normalized_unit='mmol/L', rule_unit='mg/dL' → mismatch detected
          → abnormal_flag = None  (suppressed — cannot safely apply mg/dL threshold)

        None is safer than 'N': it does NOT assert the value is normal.
        """
        items = parse_lab_items("LDL 3.4 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mmol/L"
        # P114 guard: no longer produces misleading 'N' from mg/dL threshold
        assert item["abnormal_flag"] is None, (
            "P114 guard: LDL 3.4 mmol/L unit-scale mismatch → flag suppressed (None), "
            "not 'N' as though the mg/dL threshold confirmed normal"
        )

    def test_b4_compute_abnormal_flag_signature_has_no_unit_parameter(self):
        """compute_abnormal_flag() takes (value, low, high) — no unit param.

        CHARACTERIZATION: Unit-scale validation is architecturally absent from
        the flag computation function.  This is the root cause of B1–B3.
        """
        sig = inspect.signature(compute_abnormal_flag)
        param_names = list(sig.parameters.keys())
        assert "unit" not in param_names
        assert param_names == ["value", "low", "high"]


# ---------------------------------------------------------------------------
# Test C — normalized_unit stored but never consulted for flag derivation
# ---------------------------------------------------------------------------

class TestC_NormalizedUnitNotConsulted:
    """normalized_unit is present in the parsed item dict but is unused during
    abnormal_flag computation.  No part of the parse pipeline reads it back."""

    def test_c1_normalized_unit_now_consulted_by_p114_guard(self):
        """P114 guard uses normalized_unit to detect and suppress the mismatch.

        PRE-P114: normalized_unit='mmol/L' and abnormal_flag='L' coexisted
          (normalized_unit was stored but never checked).

        POST-P114: normalized_unit='mmol/L' is compared against rule_unit='mg/dL';
          mismatch detected → abnormal_flag suppressed to None.
        """
        items = parse_lab_items("Glucose 5.5 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mmol/L"
        # Guard now active: normalized_unit is consulted and mismatch suppresses flag
        assert item["abnormal_flag"] is None

    def test_c2_same_item_name_same_rule_different_unit_same_wrong_thresholds(self):
        """Regardless of whether unit is 'mmol/L' or 'mg/dL', the same rule is returned.

        CHARACTERIZATION: infer_reference_range does not branch on unit to select
        a scale-appropriate rule — unit is accepted but does not change thresholds.
        """
        low_mg, high_mg, _, _ = infer_reference_range("Glucose", None, "mg/dL")
        low_mmol, high_mmol, _, _ = infer_reference_range("Glucose", None, "mmol/L")
        # Same thresholds regardless of caller unit
        assert low_mg == low_mmol == 70.0
        assert high_mg == high_mmol == 99.0


# ---------------------------------------------------------------------------
# Test D — Downstream propagation: detect_lab_abnormalities amplifies the flag
# ---------------------------------------------------------------------------

class TestD_DownstreamPropagation:
    """False-positive flags from parse time propagate to the Daily Assistant
    via detect_lab_abnormalities → medium severity → surfaced to user."""

    @staticmethod
    def _make_lab_evidence_item(**overrides) -> dict:
        """Minimal evidence-bundle dict matching build_evidence_bundle() format."""
        base: dict = {
            "source_type": "lab_report_item",
            "source_id": "p113-test-id-1",
            "report_id": "p113-report-1",
            "document_id": "p113-doc-1",
            "recency": "this_week",
            "confidence": 0.75,
            "evidence_level": "A",
            "summary": "Glucose 5.5（L）",
            "item_name": "Glucose",
            "item_code": "GLUCOSE",
            "value_num": 5.5,
            "value_text": None,
            "unit": "mmol/L",
            "ref_range": "70.0-99.0 mg/dL",
            "abnormal_flag": "L",
            "report_date": "2024-01-15",
        }
        base.update(overrides)
        return base

    def test_d1_false_positive_L_flag_becomes_medium_severity_in_assistant(self):
        """A false-positive 'L' flag in the evidence bundle → medium severity.

        CURRENT BEHAVIOUR:
          _flag_severity('L') → 'medium'
          detect_lab_abnormalities surfaces Glucose as a medium-severity abnormality
          even though 5.5 mmol/L is clinically normal.

        Impact: Daily Assistant narrative and recommendations are based on this.
        """
        result = detect_lab_abnormalities([self._make_lab_evidence_item()], risk_alerts=[])
        assert len(result) == 1
        detected = result[0]
        assert detected["labItemName"] == "Glucose"
        assert detected["severity"] == "medium", (
            "CHARACTERIZATION: False-positive 'L' → medium severity surfaced "
            "to Daily Assistant / notification engine"
        )

    def test_d2_false_positive_propagates_into_whyDetected_narrative(self):
        """The user-facing whyDetected string includes the false-positive flag text.

        CURRENT BEHAVIOUR: Users see '異常（L）' in the Daily Assistant UI,
        reinforcing the false alarm without any unit-scale caveat.
        """
        result = detect_lab_abnormalities([self._make_lab_evidence_item()], risk_alerts=[])
        assert len(result) == 1
        why = result[0]["whyDetected"]
        assert "L" in why or "異常" in why, (
            "CHARACTERIZATION: whyDetected narrative propagates the false-positive flag text"
        )

    def test_d3_normalized_unit_extra_field_does_not_suppress_severity(self):
        """detect_lab_abnormalities ignores normalized_unit when assigned as extra field.

        CURRENT BEHAVIOUR: Even when an item dict carries normalized_unit='mmol/L'
        (as it would from the DB via LabReportItem.normalized_unit), the function
        determines severity solely from abnormal_flag.  No unit guard exists.
        """
        item = self._make_lab_evidence_item()
        item["normalized_unit"] = "mmol/L"   # extra field — function ignores it
        result = detect_lab_abnormalities([item], risk_alerts=[])
        assert len(result) == 1
        # Severity is still medium — normalized_unit did not reduce it
        assert result[0]["severity"] == "medium"
