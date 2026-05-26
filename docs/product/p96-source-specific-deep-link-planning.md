# P96 — Source-Specific Deep Link Planning

**Status**: Discovery complete — ready for P97 implementation  
**Classification**: `P96_SOURCE_DEEP_LINK_PLANNING_READY`  
**Date**: 2025-01 (post-P95)  
**Scope**: Discovery only — zero implementation changes in P96

---

## 1. Context

P94 added optional evidence refs (`topRiskRef`, `biggestChangeRef`, `todayActionRef`) to `DailyHealthSummary`.  
P95 added the `daily-summary-evidence-contract` gate.  
P96 answers: can those refs produce source-specific deep links instead of page-level links?

---

## 2. Source ID Map

For each `source_type` in the system, the table below records what ID is currently available, its stability, and whether a destination page exists.

| source_type | ID in evidence bundle | ID type | Stable? | Destination page |
|---|---|---|---|---|
| `lab_report_item` | `source_id` = `LabReportItem.id` | UUID | ✅ stable per-row | `/platform/documents` (drawer keyed on `MedicalDocument.id`) |
| `lab_abnormality` | `reportId` = `LabReport.id` | UUID | ✅ stable per-report | `/platform/documents` (drawer keyed on `MedicalDocument.id`) |
| `symptom` | `source_id` = `SymptomLog.id` | UUID | ✅ stable per-log | `/platform/symptoms` (flat list, no per-entry UI) |
| `long_term_symptom` | `source_id` = `SymptomLog.id` | UUID | ✅ stable per-log | `/platform/symptoms` (flat list, no per-entry UI) |
| `risk_alert` | `source_id` = `RiskAlert.id` | UUID | ✅ stable | ❌ no `/risk-alerts` page |
| `health_metric` | `source_id` = `None` (P94 trend: multi-record) | — | ⚠️ not available | ❌ no dedicated page |
| `outcome` | `source_id` = `ActionOutcome.id` | UUID | ✅ stable | ❌ no dedicated page |
| `insight` | `source_id` = insight UUID | UUID | ✅ stable | ⚠️ `/platform/insights` (category-only, no per-insight entry) |
| `recommendation` | varies | — | ⚠️ varies | ❌ no dedicated page |

### Critical ID gap: documents page uses `MedicalDocument.id`, not `LabReportItem.id` or `LabReport.id`

The documents page `ParsedItemsDrawer` is opened via `setReviewDoc(doc)` where `doc.id = MedicalDocument.id`.

The current evidence bundle chain for `lab_report_item`:
```
LabReportItem.id  →  LabReportItem.report_id  →  LabReport.id  →  LabReport.document_id  →  MedicalDocument.id
  (source_id)                                    (report_id in bundle)                      (what the drawer needs)
```

**Neither `source_id` (LabReportItem.id) nor the bundled `report_id` (LabReport.id) is directly usable** for opening the drawer — the drawer needs `MedicalDocument.id` (= `LabReport.document_id`).

For `lab_abnormality`, `reportId` in the `lab_intelligence_service` output = `LabReport.id`. Same gap.

**Fix is small**: the `lab_report_items` bundle dict is built in a loop over `recent_reports` (each `report` is a `LabReport`). `LabReport` has a `document_id` column. Adding `"document_id": str(report.document_id) if report.document_id else None` to the bundle dict exposes the bridge in one line. `lab_intelligence_service` already propagates `report_id`/`source_id` from the input bundle, so the same field flows through automatically.

---

## 3. Destination Page Capability Map

### `/platform/documents`

- **`useSearchParams`**: ❌ Not imported — no query param support today.
- **Drawer mechanism**: `ParsedItemsDrawer` controlled by `reviewDoc` React state (`Doc | null`). User clicks a "審閱解析結果" button per document row to set `reviewDoc(d)`.
- **Deep-link feasibility**: ✅ **Feasible** — page needs `useSearchParams` to read `?document_id=<MedicalDocument.id>`, then once `docs` list loads, find matching doc and call `setReviewDoc(matchingDoc)`.
- **Existing pattern**: `/platform/insights` already uses `useSearchParams` for `?category=` — proven Next.js 13 App Router pattern in this codebase.
- **Existing testids**: `documents-page`, `documents-list-section`, `documents-loading`, `documents-confirmed-summary`, `documents-upload-section`.
- **Risk**: If the referenced document is not in the `listDocuments` response (e.g., deleted), the drawer silently does not open — acceptable graceful degradation.

### `/platform/symptoms`

- **`useSearchParams`**: ❌ Not imported — no query param support today.
- **Per-entry UI**: ❌ No drawer, no modal, no expandable accordion per symptom entry. Entries are flat `<div>` cards. No per-entry testid exists.
- **List slice**: `recentLogs = logs.slice(0, 20)` — only the 20 most recent. A referenced symptom older than slot 20 would be invisible.
- **Deep-link feasibility**: ⚠️ **Page-level only recommended.** Scroll+highlight to a specific `SymptomLog.id` is fragile (entry may not be in slice), and there is no per-entry UI to open. Adding a per-entry drawer would be out of P97 scope.
- **Verdict**: Continue using `/platform/symptoms` as page-level link. No `source_id` in the URL.

### `/platform/insights`

- **`useSearchParams`**: ✅ Already imported — reads `?category=`. Proof the pattern works.
- **Deep-link feasibility**: ⚠️ Low priority. Insight entries are not individually addressable in the current UI.

---

## 4. Recommended Deep-Link Model

**Recommendation: Option B (documents) + Option A (symptoms remain page-level)**

### Option A — Page-level only (current state)
- `/platform/documents` for all lab source types — user lands on list, must find manually.
- `/platform/symptoms` for symptom source types — user lands on list.
- Zero new work. Existing P94 badges already do this via `EVIDENCE_SOURCE_META`.
- **Not chosen** because the documents page has a clear auto-open path for the exact document.

### Option B — `?document_id` query param for lab types ← **CHOSEN**
- `lab_report_item`: link = `/platform/documents?document_id=<MedicalDocument.id>`
- `lab_abnormality`: link = `/platform/documents?document_id=<MedicalDocument.id>`
- `symptom` / `long_term_symptom`: remain `/platform/symptoms` (page-level, no per-entry UI)
- `risk_alert` / `health_metric` / `outcome`: remain label-only (no page)
- UX: on page load, documents page reads `document_id`, waits for `docs` list, finds match, calls `setReviewDoc` → drawer opens automatically.

### Option C — Full deep links including `?symptom_id=`
- Rejected: symptoms page has no per-entry UI; adding one is out of P97 scope.

### Option D — Backend provides computed `href` field
- Rejected: adds backend coupling to frontend routing; not necessary.

---

## 5. ID Resolution: What P97 Backend Must Add

### 5a. `lab_report_item` entries in bundle

**File**: `backend/app/services/health_assistant_service.py`  
**Location**: the loop `for report in recent_reports: for item in items:` that builds `lab_report_items.append({...})`  
**Change**: add `"document_id": str(report.document_id) if report.document_id else None`

The `report` object is already a `LabReport` SQLAlchemy row in scope. `LabReport.document_id` is a UUID FK to `MedicalDocument.id`. One field addition.

### 5b. `lab_abnormality` entries

**File**: `backend/app/services/lab_intelligence_service.py`  
**Location**: `detect_lab_abnormalities` → `results.append({...})` (line ~359)  
**Change**: add `"documentId": most_recent.get("document_id")` to the result dict.  
This flows automatically once 5a populates `document_id` in the `lab_report_items` input to `detect_lab_abnormalities`.

### 5c. Ref dict in `_derive_*` helpers (P94)

The `_derive_top_risk` / `_derive_biggest_change` / `_derive_today_action_and_why` helpers build the ref dict: `{"source_type": ..., "source_id": ..., "summary": ...}`. For `lab_report_item` and `lab_abnormality` winners, add `"document_id": src.get("document_id")` so the ref carries it all the way to the API response.

### 5d. `DailySummaryEvidenceRef` TypeScript type

```typescript
// frontend/lib/api.ts
export type DailySummaryEvidenceRef = {
  source_type: string
  source_id?: string
  document_id?: string   // NEW — MedicalDocument.id for lab types
  summary?: string
}
```

---

## 6. P97 Minimal Implementation Plan

> All changes are additive / backward-compatible. No existing fields removed. No existing tests broken.

### Backend (2 files)

| File | Change |
|---|---|
| `health_assistant_service.py` | Add `"document_id"` to `lab_report_items` bundle dict |
| `health_assistant_service.py` | Add `"document_id"` to ref dicts in `_derive_top_risk`, `_derive_biggest_change`, `_derive_today_action_and_why` for `lab_report_item` and `lab_abnormality` paths |
| `lab_intelligence_service.py` | Add `"documentId"` to result dict in `detect_lab_abnormalities` |

### Frontend (4 files)

| File | Change |
|---|---|
| `lib/api.ts` | Add `document_id?: string` to `DailySummaryEvidenceRef` |
| `lib/evidence-source-meta.ts` | Update `href` for `lab_report_item`/`lab_abnormality` to be a function `(ref) => ref.document_id ? \`/platform/documents?document_id=${ref.document_id}\` : '/platform/documents'`, OR add `hrefTemplate` field; decide exact pattern in P97 |
| `app/platform/documents/page.tsx` | Add `useSearchParams`, read `document_id` param, add `useEffect` that calls `setReviewDoc` when docs loaded and param present |
| `app/components/platform/daily-assistant-entry.tsx` | Update badge `Link href` for lab source types to use `document_id` in URL when available |

### Tests (2 new spec files)

| File | Tests |
|---|---|
| `tests/e2e/p97-document-deep-link.spec.ts` | T1: `lab_report_item` ref with `document_id` → badge link includes `?document_id=<id>`; T2: no `document_id` → falls back to `/platform/documents`; T3: documents page loads with `?document_id=<id>` → drawer auto-opens |
| `tests/e2e/p97-symptom-page-level-only.spec.ts` | T4: `symptom` ref → link is `/platform/symptoms` (no symptom_id in URL) |

### Makefile gate

```make
# P97 document deep-link contract guard
document-deep-link-contract:
	cd frontend && npx tsc --noEmit
	cd frontend && npx playwright test tests/e2e/p97-document-deep-link.spec.ts tests/e2e/p97-symptom-page-level-only.spec.ts --reporter=line
```

### Backend unit tests

Add tests to `tests/test_daily_summary_service.py`:
- `test_derive_top_risk_lab_report_item_ref_includes_document_id`
- `test_derive_biggest_change_lab_report_item_ref_includes_document_id`

---

## 7. UX/Safety Analysis

### Missing source graceful degradation

When a link is clicked and the document is not found in `listDocuments()`:
- Documents page renders the full list; drawer simply does not open.
- No error state shown (acceptable — user can browse the list manually).
- No empty state confusion: the page always loads its normal content.

### Auto-open vs scroll/highlight

For the documents page:
- **Auto-open drawer**: preferred — `ParsedItemsDrawer` is already the primary interaction model. Opening it immediately is the expected behavior after clicking an evidence ref badge.
- Timing: add a `useEffect(() => { if (!loading && searchDoc && docs.length) { const match = docs.find(d => d.id === searchDoc); if (match) setReviewDoc(match); } }, [loading, docs, searchDoc])`.

For symptoms page:
- No auto-open possible (no per-entry UI). Page-level link is the final answer for P97.
- Optional future: add a collapsible per-symptom detail card in a later P-task.

### Edge cases

| Case | Handling |
|---|---|
| `document_id` is null (no associated MedicalDocument) | Fall back to `/platform/documents` (page-level) |
| Referenced document deleted | Drawer silently does not open; user sees full list |
| Referenced document not in user's accessible list | Same — list loads without match, drawer stays closed |
| Multiple refs in same card | Each badge independently links using its own `document_id` |
| `lab_report.document_id` is NULL in DB | Possible for reports created without a parent document; fall back accepted |

---

## 8. Risks and Unknowns

| Risk | Severity | Mitigation |
|---|---|---|
| `LabReport.document_id` is NULL for some historical records | Medium | Fall back to page-level link when `document_id` absent |
| `lab_abnormality` `documentId` chain — needs lab_intelligence_service to propagate field | Low | Clear 1-line fix; field originates in the same bundle |
| `evidence-source-meta.ts` `href` is currently a string; making it a function or template changes the call sites | Medium | Alternative: add `hrefWithId` template alongside existing `href`; both stay optional |
| Documents page `useSearchParams` requires `Suspense` wrapper in Next.js 13 App Router | Medium | Follow same pattern as `/platform/insights` page which already does this correctly |
| Playwright mock for P97 tests must provide `document_id` in the mocked `DailyHealthSummary` | Low | Standard mock extension; existing P94 spec is the template |

---

## 9. Validation Table

| Goal | Criterion | Met in P97? |
|---|---|---|
| `lab_report_item` badge → opens correct document drawer | `?document_id` in URL triggers auto-open | ✅ planned |
| `lab_abnormality` badge → opens correct document drawer | Same via `documentId` field | ✅ planned |
| `symptom` badge → page-level only | `/platform/symptoms` no id param | ✅ (already correct) |
| `risk_alert` badge → label-only (no link) | No href in meta | ✅ (already correct) |
| `document_id` missing → graceful degradation | Falls back to `/platform/documents` | ✅ planned |
| TypeScript strict passes | `tsc --noEmit` clean | ✅ planned |
| New Playwright gate added | `document-deep-link-contract` | ✅ planned |
| No regression on P94 gate | `daily-summary-evidence-contract` still passes | ✅ additive only |

---

## 10. CTO 10-Line Summary

P96 investigation confirms a clear, minimal path to source-specific deep links for documents.  
The core gap: evidence refs carry `LabReportItem.id` / `LabReport.id`, but the documents drawer needs `MedicalDocument.id`.  
Fix: add `document_id = LabReport.document_id` to the `lab_report_items` bundle dict (one line, backend); propagate through `lab_intelligence_service` (one line); expose in `DailySummaryEvidenceRef` TypeScript type.  
Documents page needs `useSearchParams` (proven pattern: `/platform/insights` already does it) + a `useEffect` to auto-open the drawer when param is present.  
Symptoms page: no per-entry UI exists — page-level link is the correct and final answer for P97 scope.  
`risk_alert`, `health_metric`, `outcome`: no destination pages — label-only badges remain; no change.  
P97 scope: 2 backend files, 4 frontend files, 2 new Playwright spec files, 1 Makefile gate.  
All changes are additive; all existing P94/P95 gates unaffected.  
Graceful degradation covers `document_id = NULL` and deleted documents — no error state needed.  
Classification: `P96_SOURCE_DEEP_LINK_PLANNING_READY` — P97 can start immediately from this doc.

---

## 11. Next 24h Executable Prompt (P97 kickoff)

```
Task: P97 — implement source-specific document deep links from Daily Assistant 3-grid evidence ref badges.

Input: docs/product/p96-source-specific-deep-link-planning.md (this file)

Steps:
1. Pre-flight: git status — expect clean except 4 governance files.
2. Baseline gates: make daily-summary-evidence-contract daily-assistant-contract runtime-smoke
3. Backend:
   a. health_assistant_service.py — add "document_id": str(report.document_id) if report.document_id else None to lab_report_items bundle
   b. health_assistant_service.py — add "document_id": src.get("document_id") to lab_report_item and lab_abnormality ref dicts in _derive_top_risk, _derive_biggest_change, _derive_today_action_and_why
   c. lab_intelligence_service.py — add "documentId": most_recent.get("document_id") to results.append({...})
4. Frontend:
   a. lib/api.ts — add document_id?: string to DailySummaryEvidenceRef
   b. lib/evidence-source-meta.ts — add hrefWithId field or update href construction for lab types
   c. app/platform/documents/page.tsx — add useSearchParams, auto-open drawer
   d. app/components/platform/daily-assistant-entry.tsx — update badge Link href to include document_id when present
5. Tests:
   a. backend/tests/test_daily_summary_service.py — add 2 ref_includes_document_id tests
   b. frontend/tests/e2e/p97-document-deep-link.spec.ts — 3 tests (link url, fallback, auto-open)
   c. frontend/tests/e2e/p97-symptom-page-level-only.spec.ts — 1 test
6. Makefile: add document-deep-link-contract target
7. Gate run: make daily-summary-evidence-contract document-deep-link-contract documents-page-contract runtime-smoke
8. Commit: git add <files excluding governance>
   git commit -m "feat(deeplink): P97 document deep-link from Daily Assistant evidence badges"
```
