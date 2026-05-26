# P97 — Documents Evidence Deep Link

## Summary

Evidence badges on the Actions page and Daily Assistant panel now deep-link directly to the Documents page with the relevant document's drawer auto-opened, closing the traceability gap between AI recommendations and their source health reports.

## Problem

Evidence badges for `lab_report_item` and `lab_abnormality` sources previously linked to `/platform/documents` (the list page), but did not identify which document was relevant. Users had to manually search the document list to find the source report, breaking the evidence traceability chain.

## Solution

### Backend — `document_id` propagation

**`health_assistant_service.py`**: Propagated `document_id` (FK to `MedicalDocument`) through four touch points in the evidence pipeline:
- `lab_report_items.append({...})` — source extraction
- `_build_recommendation_from_candidate()` — recommendation building
- `_derive_top_risk()` — top risk and fallback refs
- `_derive_today_action_and_why()` — today action refs (tracking and non-tracking)

**`lab_intelligence_service.py`**: Added `document_id` to `detect_lab_abnormalities()` result items.

### Frontend — type system + routing

**`lib/api.ts`**: Added `document_id?: string | null` to `DailySummaryEvidenceRef`.

**`lib/decision-support.ts`**: Added `document_id?: string | null` to `UnifiedDecisionItem`.

**`lib/evidence-source-meta.ts`**: Added `getEvidenceHref(sourceType, ref)` helper — returns `/platform/documents?document_id=<id>` for `lab_report_item` / `lab_abnormality` sources when `ref.document_id` is present.

**`app/components/platform/daily-assistant-entry.tsx`**: All 3 evidence badge `Link` hrefs updated to use `getEvidenceHref(ref.source_type, ref)`.

**`app/components/platform/decision-recommendation-layer.tsx`**: Source page link href updated to use `getEvidenceHref(item.source_type, item)`.

**`app/platform/actions/page.tsx`**: Added `document_id: r.document_id ?? undefined` to the `assistantRecs.recommendations.map(...)` mapping so `document_id` flows through to `UnifiedDecisionItem`.

**`app/platform/documents/page.tsx`**: 
- Added `Suspense` wrapper + extracted `DocumentsPageInner` (required for `useSearchParams` in Next.js App Router).
- Added `useSearchParams()` to read `?document_id=` query param.
- Added `useEffect([loading, docs, deepLinkDocId])` that auto-opens the `ParsedItemsDrawer` when the matching document is found in the loaded list.

### Tests

**`backend/tests/test_daily_summary_service.py`**: 4 new backend unit tests:
- `test_derive_top_risk_lab_rec_ref_includes_document_id`
- `test_derive_top_risk_lab_rec_ref_document_id_none_when_absent`
- `test_derive_today_action_lab_rec_ref_includes_document_id`
- `test_derive_today_action_lab_rec_ref_document_id_none_graceful`

**`frontend/tests/e2e/p97-documents-evidence-deep-link.spec.ts`**: 4 Playwright E2E tests (fully mocked):
1. Documents page auto-opens drawer when `?document_id=` matches a document
2. Documents page no crash when `?document_id=` matches nothing
3. Actions page evidence link includes `?document_id=` when source has `document_id`
4. Daily Assistant `topRisk` evidence link includes `?document_id=` when ref has `document_id`

**`Makefile`**: New gate `documents-evidence-deeplink-contract`.

## Gate Results

| Gate | Result |
|------|--------|
| `documents-evidence-deeplink-contract` | ✅ 4/4 passed |
| `daily-summary-evidence-contract` | ✅ passed |
| `daily-assistant-contract` | ✅ passed |
| `actions-page-contract` | ✅ passed |
| `documents-confirmed-data-contract` | ✅ passed |
| `documents-page-contract` | ✅ passed |
| `symptoms-page-contract` | ✅ passed |
| `runtime-smoke` | ✅ 56 passed |

## Root Causes Diagnosed During Implementation

1. **`ParsedItemsDrawer` mock bug**: Mock returned `{ items: [] }` object instead of `[]` array — `items.slice()` threw `TypeError` causing the global `app/error.tsx` to render.
2. **Actions page `document_id` mapping gap**: The `assistantRecs.recommendations.map(...)` in `actions/page.tsx` was not forwarding `document_id` from the API response to the `UnifiedDecisionItem`.
3. **Wrong wait selector for documents test**: Used `documents-list-section` (always in DOM during loading) instead of `documents-page` + waiting for `documents-loading` to detach.
