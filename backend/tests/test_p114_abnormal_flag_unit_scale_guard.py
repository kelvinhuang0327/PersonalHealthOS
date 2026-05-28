"""P114 — Abnormal Flag Unit-Scale Guard

Focused tests for the P114 unit-scale guard implemented in report_parser.py.

The guard (implemented in parse_lab_items):
  When range_source == 'default_rule':
    - Compute _norm_unit = normalize_unit(sample_unit)
    - Compute _rule_unit = _get_rule_unit(item_name, gender)
    - If _unit_scale_compatible(_norm_unit, _rule_unit) is False:
        → abnormal_flag = None  (suppressed — unit-scale mismatch)
  When range_source == 'extracted':
    - Range came from the report text — same document scale — guard bypassed

Test groups
-----------
  A — same unit: existing correct behaviour preserved
  B — mmol/L Glucose: false-positive 'L' now suppressed
  C — mmol/L LDL: false-negative 'N' replaced with neutral None
  D — alias-compatible unit: IU/L treated as U/L (P108 alias chain)
  E — missing / empty unit: no crash, behaviour documented
  F — normalized_unit used (not raw unit) for compatibility decision
"""
from __future__ import annotations

import pytest

from app.services.report_parser import (
    _get_rule_unit,
    _unit_scale_compatible,
    compute_abnormal_flag,
    normalize_unit,
    parse_lab_items,
)


# ---------------------------------------------------------------------------
# Test A — Same unit: guard transparent, existing correct behaviour preserved
# ---------------------------------------------------------------------------

class TestA_SameUnitPreserved:
    """When sample unit == rule unit, guard passes and flags are computed normally."""

    def test_a1_glucose_mg_dl_high(self):
        """Glucose 125 mg/dL, rule unit mg/dL → guard passes → 'H' (correct)."""
        items = parse_lab_items("Glucose 125 mg/dL")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mg/dL"
        # Guard passes: same unit → flag computed from rule {high=99}
        assert item["abnormal_flag"] == "H"

    def test_a2_glucose_mg_dl_low(self):
        """Glucose 60 mg/dL, rule unit mg/dL → guard passes → 'L' (correct)."""
        items = parse_lab_items("Glucose 60 mg/dL")
        assert len(items) == 1
        assert items[0]["abnormal_flag"] == "L"

    def test_a3_glucose_mg_dl_normal(self):
        """Glucose 85 mg/dL, rule unit mg/dL → guard passes → 'N' (correct)."""
        items = parse_lab_items("Glucose 85 mg/dL")
        assert len(items) == 1
        assert items[0]["abnormal_flag"] == "N"

    def test_a4_hdl_mg_dl_low_flag_preserved(self):
        """HDL 35 mg/dL (below 40 rule threshold) → 'L' flag preserved after guard."""
        items = parse_lab_items("HDL 35 mg/dL")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mg/dL"
        assert item["abnormal_flag"] == "L"

    def test_a5_explicit_range_in_text_bypasses_guard(self):
        """Glucose 110 mg/dL with embedded range 70-99: range_source='extracted' → guard bypassed."""
        items = parse_lab_items("Glucose 110 mg/dL 70-99")
        assert len(items) == 1
        item = items[0]
        # Extracted range → guard not applied regardless of unit
        assert item["abnormal_flag"] == "H"


# ---------------------------------------------------------------------------
# Test B — mmol/L Glucose mismatch: false-positive suppressed
# ---------------------------------------------------------------------------

class TestB_GlucoseMmolLSuppressed:
    """Glucose in mmol/L with rule calibrated in mg/dL → guard suppresses flag."""

    def test_b1_glucose_5_5_mmol_l_flag_suppressed(self):
        """5.5 mmol/L (clinically normal Glucose) → unit-scale mismatch → None.

        Pre-P114: compute_abnormal_flag(5.5, 70.0, 99.0) → 'L' (false positive).
        Post-P114: _unit_scale_compatible('mmol/L', 'mg/dL') → False → None.
        """
        items = parse_lab_items("Glucose 5.5 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["unit"] == "mmol/L"
        assert item["normalized_unit"] == "mmol/L"
        # Guard: mismatch detected → flag suppressed (not 'L', not 'N')
        assert item["abnormal_flag"] is None

    def test_b2_glucose_8_mmol_l_flag_suppressed(self):
        """High Glucose in mmol/L also suppressed — no unsafe comparison performed."""
        items = parse_lab_items("Glucose 8.0 mmol/L")
        assert len(items) == 1
        # 8.0 mmol/L ≈ 144 mg/dL (would be 'H') but we cannot safely assert that
        assert items[0]["abnormal_flag"] is None

    def test_b3_unit_scale_compatible_rejects_mmol_vs_mg_dl(self):
        """_unit_scale_compatible('mmol/L', 'mg/dL') → False."""
        result = _unit_scale_compatible("mmol/L", "mg/dL")
        assert result is False

    def test_b4_glucose_rule_unit_is_mg_dl(self):
        """_get_rule_unit('Glucose') returns 'mg/dL' — rule is in mg/dL scale."""
        rule_unit = _get_rule_unit("Glucose")
        assert rule_unit == "mg/dL"


# ---------------------------------------------------------------------------
# Test C — mmol/L LDL mismatch: false-negative replaced with neutral None
# ---------------------------------------------------------------------------

class TestC_LDLMmolLSuppressed:
    """LDL in mmol/L with rule calibrated in mg/dL → guard suppresses comparison."""

    def test_c1_ldl_3_4_mmol_l_flag_suppressed(self):
        """LDL 3.4 mmol/L → unit-scale mismatch → None (not misleading 'N').

        Pre-P114: compute_abnormal_flag(3.4, 0.0, 130.0) → 'N' (false negative
          — borderline-high in mg/dL terms missed entirely).
        Post-P114: mismatch detected → None (safer: does not assert normal).
        """
        items = parse_lab_items("LDL 3.4 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mmol/L"
        # No longer 'N' from wrong scale — suppressed to None
        assert item["abnormal_flag"] is None

    def test_c2_ldl_rule_unit_is_mg_dl(self):
        """_get_rule_unit('LDL') → 'mg/dL'."""
        assert _get_rule_unit("LDL") == "mg/dL"

    def test_c3_total_cholesterol_mmol_l_suppressed(self):
        """Total Cholesterol in mmol/L (rule: mg/dL) → flag suppressed."""
        items = parse_lab_items("Total Cholesterol 5.2 mmol/L")
        assert len(items) == 1
        item = items[0]
        assert item["normalized_unit"] == "mmol/L"
        assert item["abnormal_flag"] is None


# ---------------------------------------------------------------------------
# Test D — Alias-compatible unit: IU/L treated as U/L, flag computed correctly
# ---------------------------------------------------------------------------

class TestD_AliasCompatibleUnit:
    """IU/L is normalized to U/L by normalize_unit() (P108).
    The guard compares normalized forms, so IU/L and U/L are compatible."""

    def test_d1_alt_iu_l_high_flag_computed_not_suppressed(self):
        """ALT 45 IU/L (above 40 U/L rule limit) → normalize IU/L to U/L → compatible.

        normalize_unit('IU/L') = 'U/L' = rule_unit → _unit_scale_compatible → True
        → compute_abnormal_flag(45, 0, 40) → 'H' (correct).
        """
        items = parse_lab_items("ALT 45 IU/L")
        assert len(items) == 1
        item = items[0]
        assert item["unit"] == "IU/L"
        assert item["normalized_unit"] == "U/L"  # P108 normalization
        # Guard: normalized 'U/L' == rule_unit 'U/L' → compatible
        assert item["abnormal_flag"] == "H"

    def test_d2_alt_iu_l_normal_range_no_flag(self):
        """ALT 30 IU/L (within 0–40 range) → 'N' preserved after guard."""
        items = parse_lab_items("ALT 30 IU/L")
        assert len(items) == 1
        assert items[0]["abnormal_flag"] == "N"

    def test_d3_unit_scale_compatible_iu_l_vs_u_l(self):
        """_unit_scale_compatible with pre-normalized 'U/L' vs rule 'U/L' → True."""
        # normalize_unit('IU/L') = 'U/L' → compared against rule_unit 'U/L'
        normalized_iu_l = normalize_unit("IU/L")
        assert normalized_iu_l == "U/L"
        result = _unit_scale_compatible(normalized_iu_l, "U/L")
        assert result is True

    def test_d4_alt_rule_unit_is_u_l(self):
        """_get_rule_unit('ALT') → 'U/L'."""
        assert _get_rule_unit("ALT") == "U/L"


# ---------------------------------------------------------------------------
# Test E — Missing / empty unit: no crash, documented behavior
# ---------------------------------------------------------------------------

class TestE_MissingUnit:
    """When sample unit is absent, guard cannot confirm mismatch → existing behaviour."""

    def test_e1_unit_scale_compatible_none_sample_unit(self):
        """_unit_scale_compatible(None, 'mg/dL') → True (cannot confirm mismatch)."""
        assert _unit_scale_compatible(None, "mg/dL") is True

    def test_e2_unit_scale_compatible_none_rule_unit(self):
        """_unit_scale_compatible('mmol/L', None) → True (rule has no declared unit)."""
        assert _unit_scale_compatible("mmol/L", None) is True

    def test_e3_unit_scale_compatible_both_none(self):
        """_unit_scale_compatible(None, None) → True."""
        assert _unit_scale_compatible(None, None) is True

    def test_e4_no_crash_when_item_has_no_unit(self):
        """parse_lab_items does not crash when sample has no unit."""
        # "Glucose 90" — no unit captured
        items = parse_lab_items("Glucose 90")
        # May or may not match depending on parser — must not crash
        if items:
            item = items[0]
            # normalized_unit is None since no unit
            assert item["normalized_unit"] is None
            # Guard: sample_unit=None → compatible=True → flag computed from rule
            # (existing behaviour preserved for missing unit)
            assert item["abnormal_flag"] in ("L", "N", "H", None)

    def test_e5_unknown_item_no_rule_unit_no_crash(self):
        """Item with no rule entry: _get_rule_unit returns None → no crash."""
        rule_unit = _get_rule_unit("SomeUnknownBiomarker")
        assert rule_unit is None
        # Compatible because rule_unit is None
        assert _unit_scale_compatible("mmol/L", None) is True


# ---------------------------------------------------------------------------
# Test F — normalized_unit (not raw unit) drives the compatibility decision
# ---------------------------------------------------------------------------

class TestF_NormalizedUnitPreferred:
    """The guard uses normalize_unit(raw_unit) for comparison.
    This ensures P108 alias normalization (IU/L → U/L) is respected."""

    def test_f1_raw_iu_l_would_fail_raw_comparison_but_normalized_passes(self):
        """Demonstrate why normalize_unit is applied before guard check.

        Raw 'IU/L' != 'U/L' as strings.
        normalize_unit('IU/L') = 'U/L' == 'U/L' → compatible.
        Guard uses normalized form → IU/L correctly treated as alias.
        """
        raw_unit = "IU/L"
        # Raw comparison would wrongly fail
        assert raw_unit != "U/L"
        # Normalized comparison correctly passes
        normalized = normalize_unit(raw_unit)
        assert normalized == "U/L"
        assert _unit_scale_compatible(normalized, "U/L") is True

    def test_f2_rule_unit_also_normalized_before_comparison(self):
        """_unit_scale_compatible normalizes rule_unit too (via normalize_unit).

        If a rule_unit were stored as 'IU/L' (hypothetical), it would be
        canonicalized to 'U/L' before comparison.
        """
        # simulate: sample normalized to 'U/L', rule stored as 'IU/L' (edge case)
        result = _unit_scale_compatible("U/L", "IU/L")
        assert result is True  # normalize_unit('IU/L') = 'U/L' = 'U/L'

    def test_f3_mmol_l_sample_with_mg_dl_rule_consistently_incompatible(self):
        """mmol/L vs mg/dL is incompatible regardless of order or case."""
        assert _unit_scale_compatible("mmol/L", "mg/dL") is False
        assert _unit_scale_compatible("mg/dL", "mmol/L") is False

    def test_f4_get_rule_unit_hemoglobin_gender_aware(self):
        """_get_rule_unit respects gender sub-rules (Hemoglobin has male/female)."""
        male_unit = _get_rule_unit("Hemoglobin", gender="male")
        female_unit = _get_rule_unit("Hemoglobin", gender="female")
        # Both should return 'g/dL' (same unit, different thresholds)
        assert male_unit == "g/dL"
        assert female_unit == "g/dL"
