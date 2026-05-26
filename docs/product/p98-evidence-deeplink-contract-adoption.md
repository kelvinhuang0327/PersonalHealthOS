# P98 — Evidence Deep Link Contract: Adoption & Pitfall Guide

**Status:** Adopted (P97 shipped)
**Gate:** `make documents-evidence-deeplink-contract`
**Spec file:** `frontend/tests/e2e/p97-documents-evidence-deep-link.spec.ts`

---

## 1. What This Contract Protects

P97 wired a full source-specific deep-link path from AI evidence badges to the
Documents page drawer. This contract guards four observable behaviors:

| # | Behavior | Protected by test |
|---|----------|------------------|
| 1 | Lab evidence refs carry `document_id` from backend | `runtime-smoke` (4 backend unit tests) |
| 2 | Actions page `p89-source-page-link` → `/platform/documents?document_id=<id>` | test 3 in spec |
| 3 | Daily Assistant `p94-top-risk-ref-link` → `/platform/documents?document_id=<id>` | test 4 in spec |
| 4 | `/platform/documents?document_id=<id>` auto-opens matching `ParsedItemsDrawer` | test 1 in spec |
| 5 | Unknown `document_id` → page renders, no crash, no drawer | test 2 in spec |

The contract does **not** cover symptom deep links, risk-alert deep links, or
metric/outcome deep links. Those are out of scope for P97–P98.

---

## 2. When to Run `make documents-evidence-deeplink-contract`

Run this gate any time you touch:

| Touch point | Why it matters |
|-------------|---------------|
| `frontend/lib/evidence-source-meta.ts` | `getEvidenceHref()` builds the deep-link URL |
| `frontend/app/platform/documents/page.tsx` | Suspense + `useSearchParams` + auto-open `useEffect` |
| `frontend/app/platform/actions/page.tsx` | `assistantRecs.recommendations.map(...)` must forward `document_id` |
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Badge `Link` hrefs use `getEvidenceHref()` |
| `frontend/app/components/platform/decision-recommendation-layer.tsx` | `p89-source-page-link` href uses `getEvidenceHref()` |
| `frontend/lib/decision-support.ts` | `UnifiedDecisionItem.document_id` field |
| `frontend/lib/api.ts` | `DailySummaryEvidenceRef.document_id` field |
| `backend/app/services/health_assistant_service.py` | `document_id` in `topRiskRef` / `todayActionRef` |
| `backend/app/services/lab_intelligence_service.py` | `document_id` in `detect_lab_abnormalities()` results |

Run it alongside whichever other gates cover the area you changed. It takes
under 10 seconds.

---

## 3. Explicit Non-Goals

These are **not** in scope for P97–P98 and must not be added without a new task:

- **No symptoms deep links.** The symptoms page has no per-entry drawer; a
  deep-link anchor would have nowhere to land.
- **No risk_alert deep links.** Risk alerts do not yet carry `document_id`
  refs; adoption is premature.
- **No metric/outcome deep links.** Outcome feedback and metric trend cards
  reference timeseries data, not document-level provenance.
- **No CI wiring.** The gate runs locally via `make`. CI integration is a
  separate decision requiring pipeline cost/ownership alignment.

---

## 4. Known Pitfalls

These were discovered during P97 implementation and must be kept in institutional memory.

### 4.1 Parsed-items mock must return an array, not an object

**Wrong:**
```typescript
route.fulfill({ json: { items: [] } })
```

**Correct:**
```typescript
route.fulfill({ json: [] })
```

`ParsedItemsDrawer` calls `items.slice(0, 5)` inside a `useEffect`. If `items`
is an object (not an array), `.slice` is `undefined` and calling it throws a
`TypeError`. This error propagates to the global `app/error.tsx` boundary,
replacing the entire page with "Something went wrong". The Playwright test then
fails with "element(s) not found" on `[role="dialog"]` — which looks like a
routing/timing issue but is actually a silent crash.

### 4.2 `documents-list-section` is visible during loading; use the right wait sequence

**Wrong:**
```typescript
await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10000 })
// then expect dialog — races with still-loading state
```

**Correct:**
```typescript
await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10000 })
await page.waitForSelector('[data-testid="documents-loading"]', { state: 'detached', timeout: 8000 })
// now loading is confirmed done; deepLink useEffect has had its chance to run
await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 })
```

`documents-list-section` is always rendered (with a loading skeleton inside it)
even when the API call is in flight. Waiting for it gives a false sense of
readiness. `documents-page` is the outer wrapper; `documents-loading` only
exists while `loading === true`. Waiting for its detachment confirms the
`listDocuments()` response has been processed and the deepLink `useEffect` has
had its first run with fully populated state.

Note: if the mock responds before React's first paint, `documents-loading` may
never appear in the DOM at all. `waitForSelector(..., { state: 'detached' })`
succeeds immediately when the element is absent — this is correct behavior, not
a false pass.

### 4.3 `document_id` must remain optional; fallback must be preserved

`getEvidenceHref()` must always fall back to `meta.href` (the plain `/platform/documents`
route) when `ref?.document_id` is absent or null:

```typescript
// evidence-source-meta.ts
export function getEvidenceHref(
  sourceType: string,
  ref?: { document_id?: string | null },
): string | undefined {
  const meta = EVIDENCE_SOURCE_META[sourceType]
  if (!meta?.href) return undefined
  if (
    (sourceType === 'lab_report_item' || sourceType === 'lab_abnormality') &&
    ref?.document_id
  ) {
    return `/platform/documents?document_id=${ref.document_id}`
  }
  return meta.href  // ← fallback always present
}
```

Never throw or return `undefined` when `document_id` is missing. Older evidence
refs from before P97 do not carry `document_id`, and the page must still render.

### 4.4 `actions/page.tsx` recommendation mapping must forward `document_id`

The `assistantRecs.recommendations.map(...)` block explicitly constructs each
`UnifiedDecisionItem`. Fields omitted from the spread are silently dropped.
**Always include `document_id`:**

```typescript
return assistantRecs.recommendations.map((r: any, i: number) => ({
  // ... other fields ...
  evidence_summary: r.evidence_summary ?? undefined,
  data_insufficiency_reason: r.data_insufficiency_reason ?? undefined,
  document_id: r.document_id ?? undefined,   // ← must not be omitted
}))
```

If `document_id` is omitted here, `getEvidenceHref()` receives a ref without
the field and silently falls back to the plain `/platform/documents` route.
The test for this is P97 test 3 (`p89-source-page-link` href contains
`document_id=`).

### 4.5 `source_id` must remain unchanged and backward-compatible

`document_id` is an **additional** field alongside `source_id`. It does not
replace `source_id`. All existing logic that uses `source_id` for deduplication,
feedback, or outcome tracking must continue to use `source_id` unchanged. Never
merge or alias the two fields.

---

## 5. Future Lanes

These are the only expansion paths that make sense to evaluate next.

### P99-A — Symptoms deep-link feasibility
**Prerequisite:** The symptoms page must gain a per-entry drawer or detail panel
that can be anchored via a query param. Currently symptoms are displayed as a
heatmap + flat list with no stable per-entry anchor. A `?symptom_id=` deep link
would have nowhere to open. Evaluate only after a drawer UI is designed.

### P99-B — Evidence source map extension
**Prerequisite:** Source IDs (e.g. symptom UUIDs, metric record IDs) must be
stable, navigation-safe values that the frontend can receive via the evidence
API. Currently many sources have synthetic IDs generated at analysis time.
Evaluate only after backend source ID stabilization.

### P99-C — CI adoption of local guards
**Prerequisite:** Measure actual wall-clock cost of the full guard suite in a CI
environment. Local guards take ~30–60s total. CI cold-start cost and parallelism
strategy must be confirmed before wiring. Evaluate after at least 30 days of
stable local runs with zero false positives.

---

## 6. Guard Execution Sequence (Reference)

Full local validation sequence for any evidence/deep-link change:

```bash
make documents-evidence-deeplink-contract   # P97 deep link: 4 tests, ~5s
make daily-summary-evidence-contract        # evidence ref shape: ~5s
make daily-assistant-contract               # daily assistant panel: ~5s
make actions-page-contract                  # actions page links: ~5s
make documents-confirmed-data-contract      # doc confirmed data: ~5s
make documents-page-contract                # documents page UI: ~5s
make symptoms-page-contract                 # symptoms page: ~5s
make runtime-smoke                          # backend 56 tests: ~2s
```

Total: under 60 seconds. All gates must pass before commit.

---

## 7. File Map

| File | Role |
|------|------|
| `frontend/lib/evidence-source-meta.ts` | `getEvidenceHref()` — URL builder |
| `frontend/lib/decision-support.ts` | `UnifiedDecisionItem.document_id` type field |
| `frontend/lib/api.ts` | `DailySummaryEvidenceRef.document_id` type field |
| `frontend/app/platform/documents/page.tsx` | Suspense + `useSearchParams` + auto-open `useEffect` |
| `frontend/app/platform/actions/page.tsx` | `document_id` forwarding in rec mapping |
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Badge `Link` hrefs |
| `frontend/app/components/platform/decision-recommendation-layer.tsx` | `p89-source-page-link` href |
| `frontend/app/components/platform/parsed-items-drawer.tsx` | Drawer UI (no testid; use `[role="dialog"]`) |
| `backend/app/services/health_assistant_service.py` | `document_id` in evidence ref dicts |
| `backend/app/services/lab_intelligence_service.py` | `document_id` in abnormality results |
| `frontend/tests/e2e/p97-documents-evidence-deep-link.spec.ts` | Contract spec (4 tests) |
| `Makefile` | `documents-evidence-deeplink-contract` target |
