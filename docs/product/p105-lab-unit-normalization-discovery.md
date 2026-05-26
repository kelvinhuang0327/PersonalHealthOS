# P105 — Lab Item Unit Normalization Discovery

**Date:** 2026-05-26
**Branch:** `main`
**Classification:** `P105_UNIT_MISMATCH_RISK_CONFIRMED`

---

## 1. Pre-flight Result

| Check | Result |
|---|---|
| Branch | `main` ✅ |
| P104 baseline commit `c3dba86` | ✅ present |
| Dirty files at start | Only governance docs ✅ |
| Baseline contracts (11 guards) | All 11 PASS ✅ |

---

## 2. Current Unit Storage and Trend Calculation Map

### 2.1 Data Model

**`LabReportItem.unit`** — `Column(String(30))`
(`backend/app/models/entities.py:168`)

- Stores the **raw unit string as parsed** from the lab report PDF/OCR.
- **Not normalized to a canonical form at parse time.**
- Examples of what may appear: `mg/dL`, `MG/DL`, `mmol/L`, `U/L`, `IU/L`, `g/dL`, `g/L`.

**Item name normalization:**  
`normalize_item_name()` (`backend/app/services/report_parser.py:84`) applies `ALIAS_MAP` to canonicalize item names:
- `Glu` / `血糖` → `Glucose`
- `GPT` → `ALT`
- `GOT` → `AST`
- `三酸甘油脂` → `Triglycerides`
- `膽固醇` → `Total Cholesterol`

**Unit normalization: does not exist.** Only item names are normalized.

### 2.2 Reference Range Config

`backend/app/config/lab_reference_ranges.json` assumes the following canonical units:

| Metric | Canonical Unit in Config |
|---|---|
| Glucose | mg/dL |
| ALT / AST | U/L |
| Uric Acid | mg/dL |
| Total Cholesterol | mg/dL |
| LDL / HDL / Triglycerides | mg/dL |
| Hemoglobin | g/dL (gender-split) |

The config declares canonical units but **does not enforce them on stored rows.** Abnormal flagging uses the raw `ref_low`/`ref_high` columns, which are set from parsed reference ranges or inferred from config. If the incoming unit is `mmol/L` but the config threshold is `mg/dL`, the abnormal flag will be wrong.

### 2.3 Lab History Grouping (Backend)

`GET /documents/lab-history` (`backend/app/api/documents.py:339`)

- Groups by **`item.item_name`** (already canonicalized by ALIAS_MAP at parse time).
- Returns each row with its own `unit` field as-stored.
- **No unit comparison or mismatch detection is performed.**
- Returns up to `limit` (default 5) rows per metric, sorted by `report_date DESC`.

### 2.4 Delta% Calculation (Frontend)

`frontend/app/components/platform/lab-comparison-table.tsx:52`

```ts
const deltaPct = hasNumbers && prevNum !== 0
  ? ((latestNum - prevNum) / prevNum) * 100
  : null
```

- **Delta% is computed purely from numeric values, with zero unit check.**
- `latest?.unit` and `prev?.unit` are displayed in separate columns (line 107–108), providing a partial visual cue for the user — but no warning, no suppression.
- The `數值下降` / `數值上升` filter buttons (line 57–59) are driven by `improved`, which is derived from `deltaPct`, meaning **unit-mismatched rows are included in trend filters**.
- No existing fallback, no existing warning string, no unit guard anywhere.

---

## 3. Where Unit Mismatch Risk Exists

| Location | Risk Level | Description |
|---|---|---|
| `lab-comparison-table.tsx:52` | **CRITICAL** | `deltaPct` computed without unit check |
| `lab-comparison-table.tsx:57-59` | **HIGH** | Filter buttons include mismatch-driven `improved` |
| `backend/api/documents.py:380` | MEDIUM | `unit` returned raw; no mismatch annotation |
| Abnormal flag computation | MEDIUM | If parsed unit ≠ config unit, `ref_low/high` may be wrong scale |
| Daily Assistant evidence | LOW | Uses lab items with `is_abnormal` flag; mismatch taints flag |

### High-Risk Scenarios

**Glucose: mg/dL ↔ mmol/L**
- Conversion factor: 1 mmol/L = 18.016 mg/dL
- If report A shows `5.5 mmol/L` and report B shows `100 mg/dL` (same patient, different lab):
  - Same canonical name `Glucose` → grouped together
  - `deltaPct = (100 − 5.5) / 5.5 × 100 = +1718%` ← **completely wrong**

**Lipids (Total Cholesterol, LDL, HDL, Triglycerides): mg/dL ↔ mmol/L**
- Conversion factor: 1 mmol/L ≈ 38.67 mg/dL (cholesterol)
- Same grouping risk as glucose.

**ALT / AST: U/L vs IU/L**
- U/L and IU/L are numerically equivalent. Risk: near zero in practice.
- μkat/L conversion exists (1 U/L = 0.01667 μkat/L) but rarely seen in Taiwanese lab reports.

**Hemoglobin: g/dL vs g/L**
- Factor 10x. Rare but possible if foreign report uses g/L.

---

## 4. Conversion Feasibility Table

| Metric | From | To | Factor | Feasibility | Notes |
|---|---|---|---|---|---|
| Glucose | mg/dL | mmol/L | ÷ 18.016 | ✅ Safe whitelist | Well-established, reversible |
| Total Cholesterol | mg/dL | mmol/L | ÷ 38.67 | ✅ Safe whitelist | Standard clinical conversion |
| LDL | mg/dL | mmol/L | ÷ 38.67 | ✅ Safe whitelist | Same factor as cholesterol |
| HDL | mg/dL | mmol/L | ÷ 38.67 | ✅ Safe whitelist | Same factor as cholesterol |
| Triglycerides | mg/dL | mmol/L | ÷ 88.57 | ✅ Safe whitelist | Different factor — must not reuse cholesterol factor |
| ALT / AST | U/L | IU/L | × 1 | ✅ Treat as equal | Numerically identical |
| Hemoglobin | g/dL | g/L | × 10 | ✅ Safe whitelist | Simple factor |
| Uric Acid | mg/dL | μmol/L | × 59.48 | ⚠️ Possible | Less common in practice |
| All others | any | any | — | ❌ Do not convert | No reliable clinical factor |

**No conversion helpers exist anywhere in the codebase.** Any Option B work would start from zero.

---

## 5. Recommended P106 Minimal Implementation

### Recommendation: **Option A — Suppress delta% when units differ (frontend-only)**

**Rationale:**
- Zero backend risk. Zero schema migration.
- Minimal surface area: 3–4 lines changed in one component.
- Safe fallback: user sees raw values side-by-side and can compare manually.
- Prevents false delta% from misleading the user or the Daily Assistant evidence layer.

**Concrete change required in `lab-comparison-table.tsx`:**

```ts
// Line ~51, replace current deltaPct block:
const unitMatch = !latest?.unit || !prev?.unit || latest.unit.trim().toLowerCase() === prev.unit.trim().toLowerCase()
const hasNumbers = Number.isFinite(latestNum) && Number.isFinite(prevNum)
const deltaPct = hasNumbers && prevNum !== 0 && unitMatch ? ((latestNum - prevNum) / prevNum) * 100 : null
const unitMismatch = hasNumbers && !unitMatch
```

**Delta column display** (replace line ~110):
```ts
{unitMismatch
  ? <span className="text-slate-400 text-xs">單位不同，暫不比較</span>
  : deltaPct === null
    ? '—'
    : `${deltaPct > 0 ? '↑' : '↓'} ${Math.abs(deltaPct).toFixed(1)}%`}
```

**Filter behavior:** `improved === null` when `unitMismatch` → those rows are excluded from `value_down` / `value_up` filters automatically (no additional change needed).

**Raw values still displayed** in latest/prev columns with unit shown — user retains full information.

**Contract test required:** Add T5 to `p103-lab-trend-comparison-contract.spec.ts` — mock two rows with same metric but different units, assert delta cell shows `單位不同` and does not show `↑`/`↓`.

### Options Not Recommended for P106

| Option | Why Deferred |
|---|---|
| **B: Whitelist conversion** | Requires unit string normalization first (case, whitespace, aliases). Not trivially safe without a normalization layer. Suitable for P107. |
| **C: Backend normalization at confirm** | Schema migration, existing-row backfill, parser refactor. High blast radius. P108+. |
| **D: Warning without suppression** | Shows a potentially wrong number alongside a warning — worse UX than suppression. |
| **E: Do nothing** | Confirmed risk; glucose mg/dL ↔ mmol/L is a real-world scenario for Taiwanese users using both domestic and foreign labs. |

---

## 6. Risks and Unknowns

| Risk | Severity | Notes |
|---|---|---|
| Unit string case variation (`mg/dL` vs `MG/DL`) | MEDIUM | Suppression with `.toLowerCase()` handles this |
| Unit string with whitespace (`mg /dL`) | LOW | `.trim()` handles single-side space; internal spaces need additional normalization in P107 |
| Null unit on one side | LOW | Current spec: if either unit is null, treat as match to avoid false suppression on well-normalized legacy data |
| Abnormal flag computed with wrong-scale reference range | MEDIUM | Not fixed by P106; backend-side normalization (Option C) required |
| Daily Assistant uses `is_abnormal` derived from wrong-scale comparison | LOW | Deferred to P108 — out of scope for unit-mismatch delta fix |
| User confusion when delta suddenly disappears | LOW | Mitigated by showing `單位不同，暫不比較` as explanatory copy |

---

## 7. Validation Table

| Contract | Pre-flight | Post-docs |
|---|---|---|
| `lab-trend-report-date-contract` | ✅ PASS | ✅ PASS |
| `lab-trend-comparison-contract` | ✅ PASS | ✅ PASS |
| `documents-confirmed-data-contract` | ✅ PASS | ✅ PASS |
| `documents-page-contract` | ✅ PASS | ✅ PASS |
| `report-symptom-recommendation-contract` | ✅ PASS | ✅ PASS |
| `documents-evidence-deeplink-contract` | ✅ PASS | ✅ PASS |
| `daily-summary-evidence-contract` | ✅ PASS | ✅ PASS |
| `daily-assistant-contract` | ✅ PASS | ✅ PASS |
| `actions-page-contract` | ✅ PASS | ✅ PASS |
| `symptoms-page-contract` | ✅ PASS | ✅ PASS |
| `runtime-smoke` | ✅ 56/56 PASS | ✅ 56/56 PASS |

P105 is docs-only; no `next build` required.

---

## 8. Next 24h Executable Prompt

```
[每次交接開頭] — Governance Header

## Required Output
- next 24h 可以直接複製貼上的prompt
- CTO agent 5 行內摘要
- CEO agent 5 行內摘要

# Branch Governance (MANDATORY)
Do NOT create a new branch. Stay on main.

# Task: P106 — Lab Item Unit Mismatch Delta Suppression

## Goal
Implement the Option A recommendation from P105 discovery.
Suppress delta% in the lab comparison table when latest.unit ≠ prev.unit.
Show 「單位不同，暫不比較」 copy in place of delta%.

## Context
P105 confirmed: delta% is computed in frontend (lab-comparison-table.tsx:52) with no unit check.
Glucose mg/dL vs mmol/L produces ~1700% false delta. ALT U/L vs IU/L is safe (equal values).
Recommended fix: frontend-only, suppress deltaPct when unit strings differ (case-insensitive trim).

## Scope
- Modify: `frontend/app/components/platform/lab-comparison-table.tsx`
  - Add `unitMatch` check before computing `deltaPct` (line ~51)
  - Add `unitMismatch` flag
  - Render `單位不同，暫不比較` in delta column when `unitMismatch === true`
- Add contract test T5 to: `tests/e2e/p103-lab-trend-comparison-contract.spec.ts`
  - Mock two rows for same metric with different units (e.g. unit: 'mg/dL' and unit: 'mmol/L')
  - Assert delta cell text contains '單位不同' and does NOT contain '↑' or '↓'
- Update: `00-Plan/roadmap/active_task_report.md`

## Required Pre-flight
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -8

Then run ALL baseline contracts:
make lab-trend-report-date-contract
make lab-trend-comparison-contract
make documents-confirmed-data-contract
make documents-page-contract
make report-symptom-recommendation-contract
make documents-evidence-deeplink-contract
make daily-summary-evidence-contract
make daily-assistant-contract
make actions-page-contract
make symptoms-page-contract
make runtime-smoke

## Validation After Implementation
Re-run all 11 contracts above.
All must pass including updated lab-trend-comparison-contract with T5.

## Commit
Stage only:
- `frontend/app/components/platform/lab-comparison-table.tsx`
- `tests/e2e/p103-lab-trend-comparison-contract.spec.ts`
- `00-Plan/roadmap/active_task_report.md`

Commit message: `fix(frontend): P106 suppress delta when lab units differ`

## Final Classification
Use one of:
- P106_UNIT_MISMATCH_SUPPRESSION_READY
- P106_BLOCKED_BY_PRE_FLIGHT
- P106_BLOCKED_BY_CONTRACT_REGRESSION
```

---

## 9. CTO Agent Summary (5 lines)

1. `LabReportItem.unit` stores raw parsed unit strings — no normalization at write time.
2. `lab-comparison-table.tsx:52` computes `deltaPct` from numeric values only, with zero unit guard — glucose `mg/dL` vs `mmol/L` produces ~1700% false delta.
3. Item names are canonicalized by `ALIAS_MAP`; units are not — grouping works but cross-unit comparison is blind.
4. No conversion helpers exist; Option A (frontend-only suppression with `單位不同，暫不比較` copy) is the safe P106 path.
5. P106 change is 3–4 lines in one component + one new contract test T5; no backend or schema changes required.

---

## 10. CEO Agent Summary (5 lines)

1. A bug was confirmed: the app can show wildly wrong trend percentages (e.g. +1700%) when a user's lab reports use different units for the same metric.
2. This affects key health metrics — blood glucose, cholesterol, triglycerides — common in users who mix domestic and foreign lab reports.
3. The fix is minimal and safe: hide the percentage when units don't match and show a plain message instead ("units differ, comparison not available").
4. Raw values are still shown side-by-side so the user keeps full visibility without seeing misleading math.
5. P106 can ship as a one-day frontend-only change; longer-term unit conversion (P107) and backend normalization (P108) are separate lanes.
