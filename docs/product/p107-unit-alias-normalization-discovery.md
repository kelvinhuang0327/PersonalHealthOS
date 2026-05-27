# P107 — Unit Alias Normalization Discovery

**Date:** 2026-05-27
**Branch:** `main`
**Classification:** `P107_UNIT_ALIAS_DISCOVERY_READY`

---

## 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| P106 report commit `6d3de03` | ✅ present |
| Dirty files at start | Governance docs only (`CEO-Decision.md`, `CTO-Analysis.md`, `roadmap.md`) ✅ |
| Baseline contracts (11 guards) | All 11 PASS ✅ |

---

## 2. Discovery Results

### 2.1 Scope of Investigation

Files surveyed:
- `backend/app/config/lab_reference_ranges.json` — canonical reference units
- `backend/app/services/report_parser.py` — unit capture regex + ALIAS_MAP
- `backend/scripts/seed_demo_data.py` — seeded lab data
- `backend/tests/*.py` — all backend test fixtures
- `frontend/tests/e2e/*.spec.ts` — all frontend Playwright mocks
- `docs/product/p105-lab-unit-normalization-discovery.md` — prior findings

---

### 2.2 Observed Unit Strings Table

| Unit String | Source(s) | Metric(s) | Notes |
|---|---|---|---|
| `mg/dL` | config, seed, backend tests, frontend tests | Glucose, Uric Acid, LDL, HDL, Triglycerides, Total Cholesterol | Most common; canonical for lipids/glucose in config |
| `U/L` | config, seed, backend tests, frontend tests | ALT, AST | Canonical for liver enzymes in config |
| `g/dL` | config, seed, frontend tests | Hemoglobin | Canonical for hemoglobin |
| `mmol/L` | backend tests, frontend tests | Glucose (6.8 mmol/L), LDL (`< 3.37 mmol/L`) | International (SI) units; real ~18× scale from mg/dL for glucose |
| `%` | backend tests | (health_assistant_service, daily_summary_service) | Percentage — no trend comparison expected |
| `mg/dL` (in ref_range strings) | backend tests, config | All lipid/glucose metrics | Embedded in ref range text |

**No occurrences found for:**
- `IU/L` — not in any source file, seed, or test
- `μmol/L` / `umol/L` — not in any source file (parser regex supports `μµ` characters but no data uses them)
- `mg/dl` (lowercase L) — not in any source file
- `mmol/l` (lowercase L) — not in any source file
- `g/L` — not in any source file
- `ng/mL`, `pg/mL`, `mU/L`, `nmol/L`, `pmol/L`, `mEq/L` — not in any source file

---

### 2.3 Parser Capability Analysis

`GENERIC_LINE_PATTERN` in `report_parser.py:42`:
```python
r'(-?\d+(?:\.\d+)?)\s*([A-Za-z/%\.μµ]+)?'
```

The regex includes `μµ` in the character class — meaning OCR-captured reports using Unicode mu (`μ`) or micro sign (`µ`) for units like `μmol/L` or `µg/dL` **will be captured**. However, no real uploaded report data with these characters exists in the codebase today.

Unit normalization at parse time: **does not exist.** Raw OCR/extracted string is stored as-is in `LabReportItem.unit`.

---

### 2.4 Current Normalization in P106

`lab-comparison-table.tsx`:
```ts
const normalizeUnit = (u?: string | null) => (u ?? '').trim().toLowerCase()
const unitsMatch = normalizeUnit(latest?.unit) === normalizeUnit(prev?.unit)
```

**What this already handles:**
| Raw pair | After normalizeUnit | Match? |
|---|---|---|
| `mg/dL` vs `mg/dL` | `mg/dl` vs `mg/dl` | ✅ match |
| `mg/dL` vs `MG/DL` | `mg/dl` vs `mg/dl` | ✅ match |
| `mmol/L` vs `MMOL/L` | `mmol/l` vs `mmol/l` | ✅ match |
| `U/L` vs `u/l` | `u/l` vs `u/l` | ✅ match |
| `g/dL` vs `G/DL` | `g/dl` vs `g/dl` | ✅ match |

**What this does NOT handle (alias gaps):**
| Raw pair | After normalizeUnit | Match? | Safe alias? |
|---|---|---|---|
| `IU/L` vs `U/L` | `iu/l` vs `u/l` | ❌ suppressed | ✅ Yes — same quantity, different abbreviation |
| `μmol/L` vs `umol/L` | `μmol/l` vs `umol/l` | ❌ suppressed | ✅ Yes — Unicode variant of same prefix |
| `µmol/L` vs `umol/L` | `µmol/l` vs `umol/l` | ❌ suppressed | ✅ Yes — Unicode micro sign variant |

---

## 3. Safe Alias Candidate Table

These are **format/symbol/abbreviation variants of the same unit** — no scale conversion involved.

| Alias A | Alias B | After lowercase | Reason safe |
|---|---|---|---|
| `IU/L` | `U/L` | `iu/l` vs `u/l` | IU and U are the same quantity for enzymatic assays (WHO historically equated them); no scale factor |
| `μmol/L` | `umol/L` | `μmol/l` vs `umol/l` | Unicode Greek mu (`μ`, U+03BC) vs ASCII `u` as micro prefix — same meaning |
| `µmol/L` | `umol/L` | `µmol/l` vs `umol/l` | Unicode micro sign (`µ`, U+00B5) vs ASCII `u` — same meaning |
| `μg/dL` | `ug/dL` | `μg/dl` vs `ug/dl` | Same micro prefix variant |
| `µg/dL` | `ug/dL` | `µg/dl` vs `ug/dl` | Same micro prefix variant |

**Implementation note:** These can be normalized by a single post-lowercase replacement:
```ts
.replace(/^µ/, 'u')   // micro sign U+00B5 → u
.replace(/^μ/, 'u')   // Greek mu U+03BC → u
.replace(/^iu\//, 'u/') // IU/X → U/X (enzyme assay units)
```

---

## 4. Explicit Non-Alias / Conversion Table

These pairs look similar but involve **real unit conversion (different numeric scale)**.  
They MUST remain suppressed by P106. Do NOT alias-normalize.

| Unit A | Unit B | Relationship | Scale factor (example) | P106 behavior |
|---|---|---|---|---|
| `mg/dL` | `mmol/L` | Conversion | Glucose: ÷18.015; Cholesterol: ÷38.67; Uric Acid: ÷59.48 | ✅ Suppress — keep as-is |
| `g/dL` | `g/L` | Conversion | ×10 | ✅ Suppress — keep as-is |
| `mg/dL` | `mg/L` | Conversion | ×10 | ✅ Suppress — keep as-is |
| `nmol/L` | `pmol/L` | Conversion | ×1000 | ✅ Suppress — keep as-is |
| `mmol/L` | `μmol/L` | Conversion | ×1000 | ✅ Suppress — keep as-is |

---

## 5. Recommended P108 Implementation Plan

### 5.1 Architecture Decision

**Recommended location:** `frontend/lib/lab-unit-normalization.ts` (new file)

Rationale: Keeps unit logic separately testable; `lab-comparison-table.tsx` imports the helper. If other components later need unit normalization, they import from the same lib file without duplicating logic.

**Scope:** P108 updates **comparison logic only**. Raw unit strings displayed in the table remain exactly as returned by the API. No display normalization.

### 5.2 Proposed Implementation

```ts
// frontend/lib/lab-unit-normalization.ts

/**
 * Normalize a lab unit string for comparison purposes only.
 * Does NOT affect display — raw units are always shown as returned by the API.
 *
 * Handles:
 * - Case and whitespace (trim + lowercase) — inherited from P106
 * - Unicode micro prefix variants (μ/µ → u)
 * - IU/X ≡ U/X for enzymatic assay units
 *
 * Does NOT convert between different scales (mg/dL ↔ mmol/L etc.)
 */
export function normalizeUnitForCompare(unit?: string | null): string {
  return (unit ?? '')
    .trim()
    .toLowerCase()
    .replace(/^µ/, 'u')      // Unicode micro sign U+00B5 → u
    .replace(/^μ/, 'u')      // Unicode Greek mu U+03BC → u
    .replace(/^iu\//, 'u/')  // IU/X → U/X (enzyme unit alias)
}
```

### 5.3 Change to `lab-comparison-table.tsx`

Replace the inline `normalizeUnit` with an import:
```ts
import { normalizeUnitForCompare } from '@/lib/lab-unit-normalization'
// ...
const unitsMatch =
  normalizeUnitForCompare(latest?.unit) === normalizeUnitForCompare(prev?.unit)
```

### 5.4 What Remains Unchanged

- Raw unit strings displayed in Latest / Previous columns: **unchanged**
- `單位不同，暫不比較` shown when units still differ after alias normalization: **unchanged**
- Backend, API, parser: **no changes**
- Null unit handling (treated as match): **unchanged**

---

## 6. Recommended P108 Contract Tests

Update `frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts`:

**T6 — IU/L and U/L treated as same unit (alias match)**
```
Mock: ALT latest = 30 U/L, previous = 25 IU/L
Assert:
- delta% IS calculated (no suppression)
- 數值上升 OR delta shown (directional label visible)
- 單位不同，暫不比較 is NOT visible
- raw "U/L" and "IU/L" remain visible in their respective cells
```

**T7 — μmol/L and umol/L treated as same unit (Unicode alias match)**
```
Mock: Bilirubin latest = 18 umol/L, previous = 15 μmol/L
Assert:
- delta% IS calculated
- 單位不同，暫不比較 is NOT visible
- raw units visible as returned
```

**T5 (regression) — mg/dL vs mmol/L still suppressed**
```
Existing T5 must continue to PASS.
Glucose 100 mg/dL vs 5.5 mmol/L → suppressed.
```

---

## 7. Risks and Unknowns

| Risk | Severity | Notes |
|---|---|---|
| `IU/L` is not currently in any fixture, seed, or test | Low | Risk is prospective (future uploads); alias is safe to add |
| Unicode `μ` (U+03BC) vs `µ` (U+00B5) in OCR | Low | Both handled by separate `.replace()` calls |
| IU ≡ U equivalence for all assay types | Medium | Clinically true for most enzyme assays (ALT, AST, ALP, LDH); NOT true for hormones (e.g. IU/L for TSH ≠ mU/L). However: TSH uses `mIU/L` or `µIU/mL`, never bare `IU/L`, so `iu/l` alias to `u/l` is safe for enzyme-only matching |
| New lib file creates surface for future incorrect extension | Low | File should have clear doc comment: alias-only, no conversion |
| Abnormal flag accuracy with mismatched scales | Existing | Out of scope for P108; deferred to P109 |

---

## 8. Validation Table

| Contract | Pre-flight | Post-docs |
|---|---|---|
| `lab-trend-comparison-contract` (T1–T5) | ✅ 5/5 | ✅ 5/5 |
| `lab-trend-report-date-contract` | ✅ PASS | ✅ PASS |
| `documents-confirmed-data-contract` | ✅ PASS | ✅ PASS |
| `documents-page-contract` | ✅ PASS | ✅ PASS |
| `report-symptom-recommendation-contract` | ✅ PASS | ✅ PASS |
| `documents-evidence-deeplink-contract` | ✅ PASS | ✅ PASS |
| `daily-summary-evidence-contract` | ✅ PASS | ✅ PASS |
| `daily-assistant-contract` | ✅ PASS | ✅ PASS |
| `actions-page-contract` | ✅ PASS | ✅ PASS |
| `symptoms-page-contract` | ✅ PASS | ✅ PASS |
| `runtime-smoke` | ✅ 56/56 | ✅ 56/56 |
| `next build` | NOT RUN (docs-only) | NOT RUN (docs-only) |

---

## 9. Files Changed

| File | Action |
|---|---|
| `docs/product/p107-unit-alias-normalization-discovery.md` | Created (this file) |
| `00-Plan/roadmap/active_task_report.md` | Updated — P107 section |

---

## 10. Commit

`docs(product): P107 unit alias normalization discovery`

---

## 11. Known Limitations

- No real uploaded report data with `IU/L`, `μmol/L`, or `umol/L` exists in the system today — alias risk is prospective.
- `%` unit (used in health_assistant_service tests) is not expected to appear in LabComparisonTable trend comparison — no alias action needed.
- TSH units (`mIU/L`, `µIU/mL`) are distinct from bare `IU/L` and are safe from the proposed `iu/l → u/l` alias.
- P108 does not solve the abnormal flag accuracy problem when unit scale differs — that remains a backend concern for P109.

---

## 12. CTO Agent 5-line Summary

1. P107 完成，分類：`P107_UNIT_ALIAS_DISCOVERY_READY`。
2. 全域掃描結果：codebase 現有單位字串為 `mg/dL`、`U/L`、`g/dL`、`mmol/L`、`%`；`IU/L`、`μmol/L`、`umol/L` 在任何 fixture/seed/test 中均不存在，風險屬前瞻性。
3. P106 `trim().toLowerCase()` 已處理所有大小寫變體；剩餘 alias gap 為 `IU/L↔U/L`（after lowercase: `iu/l` vs `u/l`）與 Unicode mu 前綴 `μ/µ` vs `u`。
4. P108 推薦方案：新建 `frontend/lib/lab-unit-normalization.ts`，單一 `normalizeUnitForCompare()` 函數，三行 `.replace()`（micro sign、Greek mu、iu/→u/）；`lab-comparison-table.tsx` import 替換現有 inline helper。
5. `mmol/L` vs `mg/dL` 屬真實量綱轉換（~18×），不得 alias；P106 suppression 必須維持；abnormal flag 精確度問題延後至 P109。

---

## 13. CEO Agent 5-line Summary

1. P107 確認目前系統的單位字串十分統一，主要只有 `mg/dL`、`U/L`、`g/dL`、`mmol/L` 四種，無亂用單位的現象。
2. 唯一的「假性壓制」風險來自 `IU/L` vs `U/L`（兩者臨床等價）與 Unicode 編碼差異（`μmol/L` vs `umol/L`），但這些目前在系統中均未出現。
3. P108 只需新增一個小型工具函數（~5 行），就能消除這些假壓制，讓 ALT/AST 等指標跨報告比較更順暢。
4. `mmol/L` vs `mg/dL`（血糖/血脂常見的不同單位系統）屬真實數值差異，P106 的壓制保護必須維持，不可混淆。
5. 整體評估：P108 可安全實施，風險極低，建議優先推進。
