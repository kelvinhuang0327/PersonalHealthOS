# P114 — Abnormal Flag Unit-Scale Guard

**Status:** Implemented  
**Branch:** main  
**Commits:** see git log  
**Related:** [P113 Discovery Report](p113-abnormal-flag-unit-scale-safety-discovery.md)

---

## 1. Root Cause Recap (from P113)

`compute_abnormal_flag(value, low, high)` carries no unit parameter.  
`infer_reference_range(item_name, gender, unit)` accepts a `unit` argument but uses it only as a display fallback — the returned thresholds are always the raw rule values regardless of whether `unit` matches the rule's declared unit.

**Consequence:**

| Sample | Rule | compute_abnormal_flag | Outcome |
|--------|------|-----------------------|---------|
| Glucose 5.5 mmol/L | low=70, high=99 (mg/dL) | (5.5, 70, 99) → 5.5 < 70 | **False-positive 'L'** |
| LDL 3.4 mmol/L | low=0, high=130 (mg/dL) | (3.4, 0, 130) → 'N' | **False-negative 'N'** |

---

## 2. Implemented Guard

Added to `backend/app/services/report_parser.py`:

### 2.1 `_get_rule_unit(item_name, gender) -> str | None`

Looks up the canonical unit declared in `lab_reference_ranges.json` for the given item.  
Gender-aware: selects the correct sub-rule for items like Hemoglobin.  
Returns `None` when the item has no rule or the rule omits a unit.

### 2.2 `_unit_scale_compatible(sample_normalized_unit, rule_unit) -> bool`

| sample_normalized_unit | rule_unit | Result |
|------------------------|-----------|--------|
| `None` | any | `True` — cannot confirm mismatch; preserve existing behaviour |
| any | `None` | `True` — rule has no declared unit; cannot confirm mismatch |
| `"mmol/L"` | `"mg/dL"` | **`False`** — mismatch confirmed |
| `"U/L"` | `"U/L"` | `True` — same scale |
| `"U/L"` (from `normalize_unit("IU/L")`) | `"U/L"` | `True` — alias compatible |

Canonicalization: both sides passed through `normalize_unit()` so P108 alias chain (IU/L → U/L) is respected.

### 2.3 Guard in `parse_lab_items`

```python
# When range comes from rule file (not extracted from report text):
_can_flag = True
if range_source == 'default_rule':
    _norm_unit = normalize_unit(unit)
    _rule_unit = _get_rule_unit(item_name, gender)
    _can_flag = _unit_scale_compatible(_norm_unit, _rule_unit)

abnormal_flag = (
    compute_abnormal_flag(value_num, ref_low, ref_high)
    if _can_flag and (ref_low is not None or ref_high is not None)
    else None
)
```

Guard fires **only** when `range_source == 'default_rule'`.  
Ranges extracted from the report text (`range_source == 'extracted'`) are assumed to share the same scale as the sample value — guard is bypassed.

---

## 3. Decision Table

| Scenario | range_source | compatible? | abnormal_flag |
|----------|-------------|-------------|---------------|
| Glucose 125 mg/dL (no embedded range) | `default_rule` | True (mg/dL == mg/dL) | computed: 'H' |
| Glucose 5.5 mmol/L (no embedded range) | `default_rule` | **False** (mmol/L ≠ mg/dL) | **None** |
| Glucose 110 mg/dL with embedded 70–99 | `extracted` | bypassed | computed: 'H' |
| ALT 45 IU/L (no embedded range) | `default_rule` | True (U/L == U/L after normalize) | computed: 'H' |
| Unknown item (no rule entry) | `unknown` | N/A | None (ref_low/high are None) |
| Item with no unit captured | `default_rule` | True (sample_unit is None → no evidence of mismatch) | computed from rule |

---

## 4. Why No Unit Conversion

P114 is the **minimum viable guard**: suppress the unsafe flag, never convert.

**Reasons:**
1. Unit conversion requires a trusted, auditable conversion table for every biomarker (Glucose alone has multiple mmol/L↔mg/dL factors in clinical databases).
2. An incorrect conversion factor is more dangerous than a suppressed flag — it produces a *confident but wrong* abnormal_flag rather than an explicit unknown.
3. `abnormal_flag = None` + `normalized_unit = 'mmol/L'` gives the frontend all the information needed to prompt the user to re-enter the value in a compatible unit or seek conversion.

The downstream `detect_lab_abnormalities` service already handles `None` abnormal_flag gracefully.

---

## 5. Before / After

### Glucose 5.5 mmol/L

**Before P114:**
```json
{
  "item_name": "Glucose",
  "value": 5.5,
  "unit": "mmol/L",
  "normalized_unit": "mmol/L",
  "abnormal_flag": "L"    ← false positive
}
```

**After P114:**
```json
{
  "item_name": "Glucose",
  "value": 5.5,
  "unit": "mmol/L",
  "normalized_unit": "mmol/L",
  "abnormal_flag": null   ← guard suppressed (not 'clinically normal')
}
```

### ALT 45 IU/L (alias-compatible — guard transparent)

**Before P114:**
```json
{ "abnormal_flag": "H" }
```

**After P114:**
```json
{ "abnormal_flag": "H" }   ← unchanged (IU/L → U/L via normalize_unit; same scale as rule)
```

---

## 6. Tests

| File | Tests | Notes |
|------|-------|-------|
| `test_p114_abnormal_flag_unit_scale_guard.py` | 25 | New — covers A–F scenarios |
| `test_p113_abnormal_flag_unit_scale_discovery.py` | 12 | Updated — b1, b3, c1 reflect fixed behaviour |
| `test_report_parser_stage2.py` | 21 | Unchanged — explicit-range / normalize_unit tests unaffected |
| `test_lab_history_unit_comparison.py` | 11 | Unchanged |
| `test_p112_normalized_unit_migration_runtime.py` | 4 | Unchanged |

Total backend: **73 passed**.  
E2E runtime-smoke: **56 passed**.

---

## 7. Known Limitations

1. **No conversion:** a sample in mmol/L gets `abnormal_flag=None` even when the clinical value is clearly abnormal. The user / upstream system must supply the value in the same unit as the rule (mg/dL for most metabolic markers).
2. **No schema reason field:** `None` flag does not distinguish "clinically normal" from "unit-scale mismatch". A future `abnormal_flag_reason` field (see P113 discovery, Lane B) would make this explicit.
3. **No historical backfill:** existing persisted records with `abnormal_flag='L'` due to the pre-P114 bug are not corrected. A migration script would be a separate task (P113, Lane D).
4. **Rule file coverage:** guard depends on `unit` being declared in `lab_reference_ranges.json`. All current rules include `unit`; any future rule added without `unit` will skip the guard (safe: `_unit_scale_compatible(x, None) = True`).

---

## 8. Next Lane

- **Lane B (schema):** Add `abnormal_flag_reason: str | None` to parsed item dict — values like `"unit_scale_mismatch"` or `"extracted_range"`. Makes `None` flag interpretable without side-channel knowledge.
- **Lane C (UI):** When `abnormal_flag is None` and `normalized_unit` implies a different scale, surface a UI hint ("Value in mmol/L — reference range in mg/dL; unit conversion required for flagging").
- **Lane D (historical):** One-shot migration to recalculate or nullify `abnormal_flag` for historical records where `normalized_unit != rule_unit`.
