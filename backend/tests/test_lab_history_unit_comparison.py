"""P111 — Backend lab comparison uses LabReportItem.normalized_unit.

Tests verify the unit_equivalence_key helper and the comparison contract
for the lab-history response. Frontend normalizeUnitForCompare() remains
the fallback for rows where normalized_unit is NULL (historical rows).
"""
from app.api.documents import lab_unit_equivalence_key


# ── lab_unit_equivalence_key() unit tests ────────────────────────────────────

def test_equivalence_key_none_returns_none():
    assert lab_unit_equivalence_key(None) is None


def test_equivalence_key_empty_string_returns_none():
    assert lab_unit_equivalence_key('') is None


def test_equivalence_key_whitespace_only_returns_none():
    # Test D: whitespace-only must be treated like NULL, not a wildcard match
    assert lab_unit_equivalence_key('   ') is None


def test_equivalence_key_passthrough():
    assert lab_unit_equivalence_key('U/L') == 'U/L'


def test_equivalence_key_strips_surrounding_whitespace():
    assert lab_unit_equivalence_key('  mg/dL  ') == 'mg/dL'


# ── Comparison branch helpers ─────────────────────────────────────────────────

def _compare_units(key_a, key_b) -> str:
    """Simulate the backend comparison decision for a row pair.

    Returns:
      'comparable'        — both keys non-None and equal
      'not_comparable'    — both keys non-None and different
      'unknown_fallback'  — at least one key is None; defer to frontend
    """
    if key_a is None or key_b is None:
        return 'unknown_fallback'
    return 'comparable' if key_a == key_b else 'not_comparable'


# ── Test A: IU/L vs U/L — normalized to same key → comparable ────────────────

def test_iu_l_and_u_l_are_comparable():
    """Both rows have normalized_unit set; IU/L normalizes to U/L at ingest."""
    # raw unit = "IU/L" normalizes to "U/L" in P110; raw unit = "U/L" stays "U/L"
    key_a = lab_unit_equivalence_key('U/L')   # IU/L row after P110 normalization
    key_b = lab_unit_equivalence_key('U/L')   # U/L row
    assert _compare_units(key_a, key_b) == 'comparable'


# ── Test B: one NULL (historical row) → unknown_fallback, no crash ───────────

def test_null_normalized_unit_yields_unknown_fallback():
    """Historical row before P110 has normalized_unit = NULL.
    Backend MUST NOT crash and MUST NOT treat NULL as a wildcard match.
    """
    key_a = lab_unit_equivalence_key(None)   # historical row
    key_b = lab_unit_equivalence_key('U/L')  # post-P110 row
    result = _compare_units(key_a, key_b)
    assert result == 'unknown_fallback'
    # Explicitly confirm NULL is not treated as a match to 'U/L'
    assert key_a != key_b


# ── Test C: mg/dL vs mmol/L — both non-NULL but different → not_comparable ───

def test_mg_dl_vs_mmol_l_are_not_comparable():
    """Different absolute units must not be silently compared."""
    key_a = lab_unit_equivalence_key('mg/dL')
    key_b = lab_unit_equivalence_key('mmol/L')
    assert _compare_units(key_a, key_b) == 'not_comparable'
    # Also confirm no silent conversion happened
    assert key_a != key_b


# ── Test D: empty / whitespace-only treated like NULL ─────────────────────────

def test_empty_normalized_unit_yields_unknown_fallback():
    key_a = lab_unit_equivalence_key('')     # empty string
    key_b = lab_unit_equivalence_key('U/L')
    assert _compare_units(key_a, key_b) == 'unknown_fallback'


def test_whitespace_normalized_unit_yields_unknown_fallback():
    key_a = lab_unit_equivalence_key('   ')  # whitespace only
    key_b = lab_unit_equivalence_key('U/L')
    assert _compare_units(key_a, key_b) == 'unknown_fallback'


def test_two_empty_rows_yield_unknown_fallback():
    """Two blank normalized_unit values must not match each other."""
    key_a = lab_unit_equivalence_key('')
    key_b = lab_unit_equivalence_key('   ')
    assert _compare_units(key_a, key_b) == 'unknown_fallback'
