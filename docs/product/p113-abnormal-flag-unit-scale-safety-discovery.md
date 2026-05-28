# P113 — Abnormal Flag Unit-Scale Safety Discovery Report

**Task ID**: P113  
**Type**: Discovery + Contract Characterization (no production fixes)  
**Risk Status**: **LATENT_RISK**  
**Date**: 2025-01-15  
**Branch**: `main` (commits follow)

---

## Executive Summary

P113 investigated whether the existing abnormal flag derivation pipeline
correctly handles lab values reported in non-standard units (e.g., mmol/L for
glucose, which is conventionally reported in mg/dL in Taiwan).

**Finding**: A latent unit-scale mismatch exists. When a lab report omits an
explicit reference range and the system falls back to `infer_reference_range()`,
the hardcoded rule thresholds (in mg/dL) are applied verbatim to the reported
value regardless of its unit. This produces:

- **False positives**: Glucose 5.5 mmol/L → flag='L' (normal value wrongly flagged)
- **False negatives**: LDL 3.4 mmol/L → no flag (borderline-high value missed)

The risk is **latent** (not active) because Taiwanese clinical labs predominantly
use conventional units (mg/dL for glucose/lipids, U/L for enzymes), and most
uploaded reports embed an explicit reference range that bypasses `infer_reference_range`.

---

## 1. Abnormal Flag Derivation Map

```
report_parser.parse_lab_items(raw_text)
│
├─ parse_reference_range(raw_ref)          ← (a) extracted from report text
│    └─ if found → ref_low, ref_high from text (CORRECT scale, no mismatch)
│
└─ infer_reference_range(item_name, gender, unit)    ← (b) rule-fallback path
     └─ loads lab_reference_ranges.json
     └─ rule = ranges[item_name]           ← e.g. Glucose: {low:70, high:99, unit:'mg/dL'}
     └─ low, high = rule['low'], rule['high']  ← NO unit scaling applied
     └─ ref_unit = rule.get('unit') or unit   ← display only, not used for comparison

compute_abnormal_flag(value_num, ref_low, ref_high)
    → signature: (value, low, high)         ← NO 'unit' parameter
    → if value < low  → 'L'
    → if value > high → 'H'
    → else            → 'N'
```

**Root cause**: `compute_abnormal_flag` has no `unit` parameter, and
`infer_reference_range` accepts `unit` only for display — it never scales
thresholds to match the caller's unit.

---

## 2. Storage Map

| Location | Field | Notes |
|---|---|---|
| `LabReportItem.abnormal_flag` | `String(20)`, nullable | Set at parse time; persisted to DB |
| `LabReportItem.normalized_unit` | `String(30)`, nullable | Added by P110; stored but **not consulted** during flag derivation |
| `LabReportItem.ref_low` | `Numeric` | Threshold from rule or extracted range; same scale issue applies |
| `LabReportItem.ref_high` | `Numeric` | Same |
| `LabReportItem.ref_range` | `String(120)` | Display string; may contain mg/dL even when value is mmol/L |

---

## 3. Downstream Consumption Map

All downstream consumers read `abnormal_flag` as stored — none apply a
unit-scale correction before consumption.

| Consumer | Path | Impact of false-positive flag |
|---|---|---|
| `GET /documents/lab-history` | `documents.py:248` | `is_abnormal=True` returned to frontend |
| `GET /documents/` summary | `documents.py:142` | `abnormal_items` count inflated |
| Dashboard summary | `dashboard.py:227` | Abnormal count inflated in report timeline |
| `build_evidence_bundle()` | `health_assistant_service.py:291` | Filters `abnormal_flag.isnot(None)` — false-positive included |
| `detect_lab_abnormalities()` | `lab_intelligence_service.py:187` | `_flag_severity('L') → 'medium'`; item surfaced to Daily Assistant |
| `build_health_analysis()` | `health_analysis_service.py:24` | Included in `abnormal_indicators` list sent to AI |
| `notification_intelligence_service` | line 354 | Lab abnormality push notification candidate |
| `symptom_intelligence_service` | line 159 | Correlated with symptoms if `abnormal_flag` set |
| PATCH re-flag path | `documents.py:304–311` | Re-flags from `ref_low`/`ref_high` — still at parse-time scale |

---

## 4. Unit-Scale Mismatch Risk Evidence

### 4.1 False Positive Path (characterised by test_b1, test_c1)

```
Input:  "Glucose 5.5 mmol/L"  (no explicit ref range)
Actual: 5.5 mmol/L ≈ 99 mg/dL  → clinically normal

System execution:
  infer_reference_range('Glucose', None, 'mmol/L')
    → low=70.0, high=99.0   (mg/dL rule, not scaled)
  compute_abnormal_flag(5.5, 70.0, 99.0)
    → 5.5 < 70.0 → 'L'   ← FALSE POSITIVE

Downstream: medium severity surfaced to Daily Assistant
```

### 4.2 False Negative Path (characterised by test_b3)

```
Input:  "LDL 3.4 mmol/L"  (no explicit ref range)
Actual: 3.4 mmol/L ≈ 131 mg/dL  → borderline-high (above 130 limit)

System execution:
  infer_reference_range('LDL', None, 'mmol/L')
    → low=0.0, high=130.0   (mg/dL rule, not scaled)
  compute_abnormal_flag(3.4, 0.0, 130.0)
    → 3.4 within range → 'N'   ← FALSE NEGATIVE

Downstream: item NOT included in evidence bundle (abnormal_flag='N' filtered out)
```

### 4.3 Re-flag Path (characterised by code review)

When a user edits `value` or `unit` via PATCH `/documents/{id}/items/{item_id}`:
- `item.unit = payload.unit` updates display unit only
- Re-flag uses existing `item.ref_low` / `item.ref_high` from parse time (wrong scale)
- Changing unit from `mmol/L` → `mg/dL` via PATCH still compares against old thresholds

### 4.4 normalized_unit is never consulted (characterised by test_c2, test_d3)

`infer_reference_range("Glucose", None, "mg/dL")` and
`infer_reference_range("Glucose", None, "mmol/L")` return identical thresholds
`(70.0, 99.0, ...)`. The `unit` argument is accepted but ignored for threshold
selection. `LabReportItem.normalized_unit` stored from P110 is never read back
during flag derivation or downstream severity classification.

---

## 5. Risk Classification

**Status: LATENT_RISK**

| Factor | Assessment |
|---|---|
| Probability of activation | Low — Taiwanese labs predominantly use mg/dL; most reports embed reference ranges |
| Impact if activated | Medium — false abnormal flags propagate to Daily Assistant narrative and push notifications |
| Exploitability | Automatic (any report with mmol/L values and no embedded range) |
| Detection | None — no logging or warning when unit mismatch occurs |
| `normalized_unit` field | Available (P110) but not wired into flag computation |

The risk is **latent** today. It becomes **active** under these conditions:
1. Lab report uses non-standard unit (mmol/L, g/L, µmol/L, etc.)
2. Report text does not embed an explicit reference range
3. The item_name is present in `lab_reference_ranges.json`

---

## 6. Recommended Next Lanes (for future P task)

**Lane A — Threshold Scaling** *(preferred)*
Add a unit conversion table; `infer_reference_range` scales thresholds from
rule unit to sample unit before returning. Requires expanding
`lab_reference_ranges.json` with conversion factors.

**Lane B — Unit Guard + Suppress**
When `normalized_unit` ≠ rule unit and no explicit range exists,
set `abnormal_flag = None` (suppress rather than risk false alarm).
Log a `unit_mismatch_suppressed` audit event. Safer but may increase false negatives.

**Lane C — User Warning Display Only**
No flag change; add a `unit_mismatch_warning: bool` field to
`ParsedItemResponse`. Frontend surfaces a caution indicator.
Low risk but does not fix downstream AI input.

**Lane D — Manual Re-review Queue**
On unit mismatch detection at ingest, set `abnormal_flag = None` and
create a `PENDING_UNIT_REVIEW` status row for manual confirmation.
High fidelity but requires UI work.

**Recommendation**: Lane A for items with known conversion factors (Glucose,
LDL, HDL, Triglycerides, Uric Acid where mmol/L ↔ mg/dL factors are fixed);
Lane B as fallback for items without a known conversion.

---

## 7. Non-Goals of P113

- No production code was modified
- No parser behaviour was changed
- No DB migration was added
- No historical data was backfilled
- No unit conversion logic was implemented
- No frontend changes were made
- No Makefile / CI / Alembic changes were made

---

## 8. Characterization Test Coverage

File: `backend/tests/test_p113_abnormal_flag_unit_scale_discovery.py`

| Test | Class | What is characterized |
|---|---|---|
| test_a1 | TestA | Same-scale (mg/dL + explicit range) → correct flag 'N' |
| test_a2 | TestA | Same-scale high value → correct flag 'H' |
| test_a3 | TestA | Same-scale low value → correct flag 'L' |
| test_b1 | TestB | Glucose 5.5 mmol/L → false positive 'L' (current behaviour) |
| test_b2 | TestB | `infer_reference_range` returns mg/dL thresholds for mmol/L caller |
| test_b3 | TestB | LDL 3.4 mmol/L → false negative 'N' (missed borderline-high) |
| test_b4 | TestB | `compute_abnormal_flag` has no `unit` parameter (root cause) |
| test_c1 | TestC | `normalized_unit='mmol/L'` and `abnormal_flag='L'` coexist (not cross-checked) |
| test_c2 | TestC | Same rule thresholds returned regardless of unit arg |
| test_d1 | TestD | False-positive 'L' → medium severity in `detect_lab_abnormalities` |
| test_d2 | TestD | False-positive flag appears in whyDetected narrative text |
| test_d3 | TestD | Extra `normalized_unit` field in evidence dict does not suppress severity |

**All 12 tests: PASS**

---

## 9. Governance Notes

Files deliberately NOT touched by P113 (pre-existing dirty state at session start):
- `00-Plan/roadmap/CEO-Decision.md`
- `00-Plan/roadmap/CTO-Analysis.md`
- `00-Plan/roadmap/roadmap.md`

Files staged for P113 commits:
1. `backend/tests/test_p113_abnormal_flag_unit_scale_discovery.py` (new)
2. `docs/product/p113-abnormal-flag-unit-scale-safety-discovery.md` (this file)
3. `00-Plan/roadmap/active_task_report.md` (P113 section prepended)

---

*P113 Final Classification: `P113_ABNORMAL_FLAG_UNIT_SCALE_DISCOVERY_COMPLETE_LATENT_RISK`*
