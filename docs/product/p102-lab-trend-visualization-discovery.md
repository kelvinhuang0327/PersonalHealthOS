# P102 — Lab Trend Visualization Discovery

**Date:** 2026-05-26
**Classification:** `P102_FRONTEND_ONLY_TREND_FEASIBLE`
**Status:** Discovery complete — feature already partially implemented; P103 is enhancement + contract guard.

---

## 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `38f7696` (P101) |
| Dirty files | governance-only: `CEO-Decision.md`, `CTO-Analysis.md`, `roadmap.md` |
| P101 commit present | YES — `38f7696` |

**Baseline gates (all green before docs work):**

| Gate | Result |
|---|---|
| `report-symptom-recommendation-contract` | 5 passed |
| `documents-evidence-deeplink-contract` | 4 passed |
| `daily-summary-evidence-contract` | 4 passed |
| `daily-assistant-contract` | 5 passed |
| `actions-page-contract` | 4 passed |
| `documents-confirmed-data-contract` | 4 passed |
| `documents-page-contract` | 4 passed |
| `symptoms-page-contract` | 4 passed |
| `runtime-smoke` | 56 passed |

---

## 2. Discovery Result

### 2.1 Current Lab Data Model

```
MedicalDocument
  id, user_id, subject_profile_id
  original_filename, category
  parse_status ('pending' | 'parsed' | 'confirmed')
  confirmed_at (DateTime, nullable)       ← gating field for trend
  confirmed_data (JSON snapshot at confirm time)

LabReport
  id → document_id (FK → MedicalDocument)
  user_id, subject_profile_id
  report_date (Date, nullable)            ← set to date.today() at parse time
  parser_version, raw_text

LabReportItem
  id → report_id (FK → LabReport)
  item_name  (String, normalized via ALIAS_MAP)
  item_code  (String, derived: item_name uppercased/stripped)
  value_num  (Numeric 10,3, nullable)
  value_text (String, nullable)
  unit       (String, nullable)
  ref_range  (String, nullable)
  ref_low / ref_high (Numeric, nullable)
  range_source ('extracted' | 'default_rule' | 'unknown')
  abnormal_flag ('H' | 'L' | 'N' | null)
  parser_confidence (Numeric 0–1)
```

**Normalization:** `report_parser.py` `normalize_item_name()` maps aliases to
canonical keys via `ALIAS_MAP` (e.g. GPT→ALT, GOT→AST, 血糖→Glucose). Items
with the same canonical name across different reports will match in trend queries.

### 2.2 Backend API Map

| Endpoint | What it returns | Cross-document? | Confirmed-only? |
|---|---|---|---|
| `GET /documents/lab-history` | All metrics (grouped, latest N) or single metric history | **YES** | **YES** — filters `confirmed_at IS NOT NULL` |
| `GET /documents/{id}/parsed-items` | Items for one document | No | No |
| `PATCH /documents/{id}/parsed-items/{item_id}` | Corrects value/unit/ref_range in DB | No | No |

`/documents/lab-history` response shape:
```json
{
  "metric": "ALT",
  "report_date": "2026-05-20",
  "document_id": "uuid",
  "document_name": "health_check_2026.pdf",
  "value": 32.0,
  "unit": "U/L",
  "is_abnormal": false,
  "reference_range": "7-40 U/L"
}
```

### 2.3 Frontend Implementation Status

**Already built:**

| Component | Location | Status |
|---|---|---|
| `LabComparisonTable` | `frontend/app/components/platform/lab-comparison-table.tsx` | **Complete** |
| "歷史比較" tab in documents page | `frontend/app/platform/documents/page.tsx` | **Integrated** |
| Compare preview in drawer | `frontend/app/components/platform/parsed-items-drawer.tsx` | **Present** (top-5 metrics, 2 points) |
| `api.getLabHistory()` | `frontend/lib/api.ts:405` | **Complete** |

`LabComparisonTable` features:
- Calls `GET /documents/lab-history?limit=5` on mount
- Groups rows by metric, sorts by `report_date` descending
- Displays: metric name, latest value+unit, previous value+unit, Δ% (↑/↓), reference range
- Expandable rows showing all history points with report_date + document_name
- Filter tabs: 全部 / 異常指標 / 已改善 / 未改善

---

## 3. Is Trend Data Available Today?

**Yes — with one significant accuracy limitation.**

Data flows through: upload → parse → confirm → lab-history query.
Confirmed documents are queryable today. The `LabComparisonTable` renders
immediately if 2+ confirmed documents exist with overlapping metric names.

**Critical gap: `report_date` accuracy**

`report_date` is set to `date.today()` at parse time (see `documents.py` line in `parse_document`). If a user uploads 3 reports on the same day (even if the reports are from 2024, 2025, 2026), all three `LabReport` rows get `report_date = 2026-05-26`. The `LabComparisonTable` sorts by `report_date` descending — when all dates are equal, ordering falls back to `created_at`, which reflects upload order, not health check order.

**Result:** Trend direction (↑/↓%) may be chronologically correct if reports were uploaded in order, but the displayed `report_date` in expandable rows will be wrong (showing upload date, not actual health check date). This is misleading for users comparing multi-year lab history.

---

## 4. Confirmed vs Parsed Value Implications

The `/documents/lab-history` endpoint reads `LabReportItem.value_num` directly from the database. There are two paths by which a value can reach that column:

1. **Parsed raw value** — set by `parse_lab_items()` from OCR text.
2. **User-corrected value** — set by `PATCH /documents/{id}/parsed-items/{item_id}`, which updates `value_num` in place.

`confirmed_data` on the `MedicalDocument` is a JSON snapshot stored at confirm time. It is NOT re-read by `lab-history`. If a user corrects a value before confirming, the correction is already in `LabReportItem.value_num`, so `lab-history` picks up the corrected value. If a user somehow edits after confirming (not exposed in UI today), the snapshot would diverge from the trend data — but this path does not exist in the current UI.

**Practical conclusion:** Confirmed values in the trend table reflect the most recent human-reviewed value. The path is safe for P103 development.

---

## 5. Safety / Trust Framing Audit

Current `LabComparisonTable` language:

| Element | Current text | Risk |
|---|---|---|
| Direction arrows | ↑ / ↓ + percentage | Low — directionally neutral |
| Filter: "已改善" | "improved" | **Medium** — assumes ↓ = better. Wrong for HDL, Hemoglobin, eGFR |
| Filter: "未改善" | "not improved" | **Medium** — same issue |
| No disclaimer | _(absent)_ | Low for raw number display; Medium if user acts on it |
| ParsedItemsDrawer preview | `Glucose ↑12%，ALT ↓8%` | Low — format only, no judgment |

**Recommended P103 fix:** Replace "已改善/未改善" filter labels with "數值下降/數值上升" (value decreased / value increased). Avoid any "better/worse" framing without reference-range anchoring.

Reference-range aware phrasing (future enhancement beyond P103):
- If latest value is within range AND was previously outside → "回到正常範圍"
- If latest value is outside range AND was previously within → "超出參考範圍"
- Otherwise → "數值上升 / 下降"

---

## 6. Recommended Minimal UI Slice

The `LabComparisonTable` already implements the core feature. The minimal P103 slice is:

1. **Add a Playwright contract guard** for the "歷史比較" tab (`lab-trend-comparison-contract`). No Makefile target currently covers this surface.
2. **Fix direction framing** in `LabComparisonTable` — replace "已改善/未改善" with non-judgmental direction labels.
3. **Add `report_date` capture to the confirm flow** — expose a date input in `ParsedItemsDrawer` so users can set the actual health check date before confirming. Write to `LabReport.report_date` via a new PATCH endpoint or extend the confirm payload.

This is the smallest change that makes the existing feature trustworthy enough to promote to users.

**What is NOT needed for P103:**
- New trend chart / visualisation (table is sufficient)
- Backend rewrite of `lab-history` endpoint
- Unit normalization across reports
- AI-generated trend narrative

---

## 7. Recommended P103 Implementation Plan

### Option A (docs-only)
Not applicable. Feature is already implemented.

### Option B: Frontend Enhancement + Contract Guard ← **RECOMMENDED**

**Scope:** Frontend-only + one new Makefile target. No backend schema migration.

1. Fix `LabComparisonTable` direction labels (30 min, frontend only)
2. Add `report_date` date input to `ParsedItemsDrawer` confirm footer  
   - Calls `PUT /documents/{id}/confirm` with `report_date` in payload, OR  
   - Add `PATCH /documents/{id}/report-date` — single-field backend endpoint
3. Write `frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts` (4 tests):
   - T1: "歷史比較" tab visible on documents page
   - T2: `LabComparisonTable` renders with mocked multi-document lab history
   - T3: Δ% column shows ↑/↓ direction
   - T4: No medical overclaim phrases ("改善", "惡化", "恢復正常") without reference-range gating
4. Add `lab-trend-comparison-contract` Makefile target
5. Update guard index (`local-contract-guard-index.md`)

**Backend change scope for report_date:** Extend `PUT /documents/{id}/confirm` to accept optional `report_date` field, write to `LabReport.report_date` where `document_id = doc.id`. No migration required (column already exists, nullable).

### Option C: Full Backend Enhancement
Add a dedicated `/documents/lab-trend` endpoint with:
- `item_name` normalization pass
- explicit `report_date` ordering with null-date sentinel handling
- unit normalization (requires new unit-conversion config)

**Not recommended for P103** — over-engineered relative to value. The existing `lab-history` endpoint is sufficient.

### Option D: Mocked contract only (no feature change)
Add a Playwright guard without fixing the direction labels or report_date. Not recommended — guard would pass while known issues remain unaddressed.

---

## 8. Risks / Unknowns

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| report_date accuracy misleads users | **High** (if multiple uploads same day) | Medium | Add date input in P103 confirm flow |
| "已改善" framing misjudges HDL/Hemoglobin | **Medium** | Medium | Replace with neutral direction labels |
| ALIAS_MAP coverage gaps (unrecognized item names) | **Medium** | Low | Metric still appears, just without normalization; future work |
| Unit mismatch across reports (mg/dL vs mmol/L) | **Low** (single-user, usually same lab) | High if hit | Out of scope P103; add unit check in P104+ |
| User uploads 0–1 confirmed docs | None | None | "歷史比較" tab shows "尚無歷史資料" gracefully |

---

## 9. Validation Table (Post-Discovery)

| Gate | Before docs | After docs | Delta |
|---|---|---|---|
| `report-symptom-recommendation-contract` | 5 passed | 5 passed | — |
| `documents-evidence-deeplink-contract` | 4 passed | 4 passed | — |
| `daily-summary-evidence-contract` | 4 passed | 4 passed | — |
| `daily-assistant-contract` | 5 passed | 5 passed | — |
| `actions-page-contract` | 4 passed | 4 passed | — |
| `documents-confirmed-data-contract` | 4 passed | 4 passed | — |
| `documents-page-contract` | 4 passed | 4 passed | — |
| `symptoms-page-contract` | 4 passed | 4 passed | — |
| `runtime-smoke` | 56 passed | 56 passed | — |

No code changes in P102. All 9 guards remain green.

---

## 10. Next 24h Executable Prompt

```
[P103 — Lab Trend Contract + Direction Framing Fix]

Branch governance: main only. No new branch.

Pre-flight:
  git rev-parse --show-toplevel
  git branch --show-current
  git status --short
  git log --oneline -8

Required pre-flight baseline (all must pass before any code change):
  make report-symptom-recommendation-contract
  make documents-evidence-deeplink-contract
  make daily-summary-evidence-contract
  make daily-assistant-contract
  make actions-page-contract
  make documents-confirmed-data-contract
  make documents-page-contract
  make symptoms-page-contract
  make runtime-smoke

Task:
  1. Fix direction labels in LabComparisonTable:
     File: frontend/app/components/platform/lab-comparison-table.tsx
     - Change FilterKey type 'improved' → 'value_down', 'not_improved' → 'value_up'
     - Change filter button labels: "已改善" → "數值下降", "未改善" → "數值上升"
     - Change tableRows filter logic accordingly (deltaPct < 0 → 'value_down')

  2. Add report_date capture to ParsedItemsDrawer confirm flow:
     File: frontend/app/components/platform/parsed-items-drawer.tsx
     - Add a date input in the footer (above the confirm button)
     - Label: "健檢日期（選填）" — prepopulate empty
     - On confirm, pass report_date (ISO date string or null) in confirmed_data payload

     File: backend/app/api/documents.py
     - In PUT /{document_id}/confirm: accept optional report_date field
     - If provided, find the LabReport with document_id == doc.id and set report_date

     File: backend/app/schemas/documents.py
     - Extend DocumentConfirmRequest: add optional report_date: date | None = None

  3. Write contract spec:
     File: frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts
     - T1: documents page has "歷史比較" tab button visible
     - T2: clicking "歷史比較" renders lab-comparison-table (mock GET /documents/lab-history
           returning 2 rows for ALT: [{value:45, report_date:'2026-03-01'}, {value:38, report_date:'2025-12-01'}])
     - T3: delta column shows ↑ or ↓ direction for the ALT row
     - T4: no prohibited overclaim phrases in the comparison table
           (prohibited: 改善, 惡化, 恢復正常, 超過, 危險 — per existing overclaim guard pattern)

  4. Add Makefile target:
     # P103 Lab trend comparison contract — local/manual only, not CI-required
     # Runs TypeScript check + P103 lab trend smoke (4 tests).
     lab-trend-comparison-contract:
       cd frontend && npx tsc --noEmit
       cd frontend && npx playwright test tests/e2e/p103-lab-trend-comparison-contract.spec.ts --reporter=line

     Add to .PHONY line.

  5. Update guard index:
     File: docs/product/local-contract-guard-index.md
     - Add row to Guard Matrix (§2)
     - Add to documents validation bundle (§3)
     - Add to Quick Reference (§8)

  6. Build and validate:
     cd frontend && npm run build
     make lab-trend-comparison-contract
     make documents-page-contract
     make runtime-smoke

  7. Commit (stage only changed files — no governance files):
     git add frontend/app/components/platform/lab-comparison-table.tsx
     git add frontend/app/components/platform/parsed-items-drawer.tsx
     git add backend/app/api/documents.py
     git add backend/app/schemas/documents.py
     git add frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts
     git add Makefile
     git add docs/product/local-contract-guard-index.md
     git add 00-Plan/roadmap/active_task_report.md
     git commit -m "feat: P103 lab trend comparison contract and direction framing fix"

Final classification: P103_LAB_TREND_CONTRACT_READY or P103_BLOCKED_BY_CONTRACT_REGRESSION
```

---

## 11. CTO Agent 5-Line Summary

1. `/documents/lab-history` endpoint already exists, filters confirmed docs, joins across LabReport+LabReportItem, returns metric/value/unit/date/document_id per row.
2. `LabComparisonTable` component is fully built and integrated in the "歷史比較" tab of the documents page — no new frontend architecture needed.
3. Critical gap: `report_date` is set to `date.today()` at parse time, not extracted from document, so chronological ordering is upload-order not health-check-order.
4. Trust risk: "已改善/未改善" filter labels assume ↓ = better, wrong for HDL/Hemoglobin; must be replaced with neutral direction language before user promotion.
5. P103 = add a Playwright contract guard for the "歷史比較" tab + fix direction framing + add optional report_date capture in confirm flow. Entirely frontend with a minimal backend field write; no migration required.

---

## 12. CEO Agent 5-Line Summary

1. PersonalHealthOS can already compare lab values across multiple uploaded reports — the "歷史比較" tab in the Health Report section is built and works today.
2. The feature needs two trust fixes before active promotion: replace "improved/not improved" labels (which are medically ambiguous) with neutral direction arrows, and let users specify the actual date of each health check report.
3. Once those two fixes are in, users who upload 2+ confirmed health check PDFs will see a table comparing the same metric (e.g. ALT, Glucose, Cholesterol) across all their reports.
4. This directly answers the product question: yes, users can compare the same lab item across 3–5 uploaded reports and see direction changes, connected back to the actual document via deep-link.
5. P103 is a 1–2 day frontend enhancement with a small backend field extension — no new infrastructure, no AI calls, fully testable with existing contract guards.
