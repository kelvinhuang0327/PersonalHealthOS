# Local Contract Guard Index

**Last updated:** P99 (2026-05-26)
**Status:** Authoritative runbook for all local/manual Makefile contract guards.

---

## 1. Purpose

Local contract guards are **not CI-required**. They are fast, targeted guardrails
for specific product surfaces. Each guard runs in seconds and catches regressions
before commit, without needing a running backend or Docker stack.

This document is the single source of truth for:
- Which guard covers which surface
- When each guard should be run
- Which files are in scope for each guard
- How to group guards when a change spans multiple surfaces

**Maintenance rule:** Every new `make` contract target must be added to this index
before the task that introduces it is considered complete.

---

## 2. Guard Matrix

All frontend guards run `npx tsc --noEmit` first, then the Playwright spec.
`next build` is only required when frontend code has changed (see column below).

| Target | Spec file | Tests | Requires `next build`? | What it protects |
|--------|-----------|-------|------------------------|-----------------|
| `daily-assistant-contract` | `p76-daily-assistant-signal-contract.spec.ts` | 5 | **Yes** — if any frontend file changed | Daily Assistant panel render, signal display, error boundary, loading state, overclaim guard |
| `daily-summary-evidence-contract` | `p94-daily-summary-3grid-evidence-refs.spec.ts` | 4 | **Yes** — if any frontend file changed | 3-grid evidence ref badges, per-card `source_type` attribution, `EVIDENCE_SOURCE_META` display |
| `actions-page-contract` | `p82-actions-page-contract.spec.ts` | 4 | **Yes** — if any frontend file changed | `/platform/actions` render, recommendation history, feedback loop, snooze sections, overclaim guard |
| `documents-evidence-deeplink-contract` | `p97-documents-evidence-deep-link.spec.ts` | 4 | **Yes** — if any frontend file changed | `document_id` deep link URL, `ParsedItemsDrawer` auto-open, fallback to base route, Actions + Daily Assistant badge hrefs |
| `documents-confirmed-data-contract` | `p87-documents-confirmed-data-refeed.spec.ts` | 4 | **Yes** — if any frontend file changed | `ParsedItemsDrawer` confirm flow, `Doc` interface confirmed-data display, overclaim guard |
| `documents-page-contract` | `p85-documents-page-contract.spec.ts` | 4 | **Yes** — if any frontend file changed | `/platform/documents` list render, upload/parse flow, `LabReportItem` display, 500 failure safe |
| `symptoms-page-contract` | `p86-symptoms-page-contract.spec.ts` | 4 | **Yes** — if any frontend file changed | `/platform/symptoms` render, quick-symptom chips, heatmap, severity/duration selectors, 500 failure safe |
| `runtime-smoke` | `tests/test_runtime_smoke.py` + security/config/validation/outcome suites | 56+ | **No** (backend pytest only) | All backend pytest suites — API contracts, security audit, config schema, validation rules, outcome feedback |

### When to run each guard

| Target | Run after touching... |
|--------|-----------------------|
| `daily-assistant-contract` | `daily-assistant-entry.tsx`, `decision-recommendation-layer.tsx`, Daily Assistant API response shape, signal priority logic |
| `daily-summary-evidence-contract` | `DailyHealthSummary` evidence refs, 3-grid card layout, `EVIDENCE_SOURCE_META`, `evidence-source-meta.ts`, `api.ts` `DailySummaryEvidenceRef` |
| `actions-page-contract` | `actions/page.tsx`, recommendation history list, snooze/feedback API, `UnifiedDecisionItem` shape |
| `documents-evidence-deeplink-contract` | `evidence-source-meta.ts` `getEvidenceHref()`, `documents/page.tsx` `useSearchParams`, `actions/page.tsx` `document_id` forwarding, evidence badge hrefs, `health_assistant_service.py` top-risk/today-action refs, `lab_intelligence_service.py` abnormality `document_id` |
| `documents-confirmed-data-contract` | `parsed-items-drawer.tsx`, `Doc` interface, confirmed-data re-feed API, `documents-confirmed-data-refeed` service |
| `documents-page-contract` | `documents/page.tsx` (non-deeplink), document list components, upload API, `LabReportItem` display |
| `symptoms-page-contract` | `symptoms/page.tsx`, symptom chip components, heatmap, severity/duration selectors, symptoms API |
| `runtime-smoke` | Any backend service, model, API route, config schema, validation rule, or security audit path |

### Related files per guard

| Target | Key frontend files | Key backend files | Phase |
|--------|--------------------|-------------------|-------|
| `daily-assistant-contract` | `daily-assistant-entry.tsx`, `decision-recommendation-layer.tsx`, `lib/decision-support.ts` | `health_assistant_service.py` | P76–P77 |
| `daily-summary-evidence-contract` | `lib/evidence-source-meta.ts`, `lib/api.ts` (`DailySummaryEvidenceRef`), 3-grid components | `health_assistant_service.py` | P92–P95 |
| `actions-page-contract` | `app/platform/actions/page.tsx`, `lib/decision-support.ts` | `health_assistant_service.py` | P82–P83 |
| `documents-evidence-deeplink-contract` | `lib/evidence-source-meta.ts`, `app/platform/documents/page.tsx`, `app/platform/actions/page.tsx`, `daily-assistant-entry.tsx`, `decision-recommendation-layer.tsx` | `health_assistant_service.py`, `lab_intelligence_service.py` | P97 |
| `documents-confirmed-data-contract` | `components/platform/parsed-items-drawer.tsx`, `lib/api.ts` | document parsing services | P87 |
| `documents-page-contract` | `app/platform/documents/page.tsx`, document list components | document API routes | P85 |
| `symptoms-page-contract` | `app/platform/symptoms/page.tsx`, symptom chip/heatmap components | symptoms API routes | P86 |
| `runtime-smoke` | _(backend only)_ | `tests/test_runtime_smoke.py`, security/config/validation/outcome test suites | P65+ |

---

## 3. Recommended Validation Bundles

Run the minimal set that covers your change surface. Do not run everything every
time — that slows feedback without adding signal.

### Daily Assistant copy / cards / signal display
```bash
make daily-assistant-contract
make daily-summary-evidence-contract
```

### Actions page — recommendation display / evidence links
```bash
make actions-page-contract
```

### Documents — upload, parse, confirm, deeplink (full documents surface)
```bash
make documents-page-contract
make documents-confirmed-data-contract
make documents-evidence-deeplink-contract
```

### Documents — deeplink only (touched `document_id` propagation or `getEvidenceHref`)
```bash
make documents-evidence-deeplink-contract
make runtime-smoke
```

### Symptoms page
```bash
make symptoms-page-contract
```

### Backend safety / runtime only (no frontend changes)
```bash
make runtime-smoke
```

### Broad evidence traceability work (touched evidence refs end-to-end)
```bash
make daily-summary-evidence-contract
make actions-page-contract
make documents-evidence-deeplink-contract
make runtime-smoke
```

### Full local validation (pre-commit after cross-surface change)
```bash
make documents-evidence-deeplink-contract
make daily-summary-evidence-contract
make daily-assistant-contract
make actions-page-contract
make documents-confirmed-data-contract
make documents-page-contract
make symptoms-page-contract
make runtime-smoke
```
Total wall-clock time: ~50–60 seconds.

---

## 4. `next build` Requirement

All Playwright frontend guards (`daily-assistant-contract` through
`symptoms-page-contract`) use `reuseExistingServer: false` in
`playwright.config.ts`. This means Playwright kills and restarts the Next.js
server for each test run via `next start`. The server serves the **last built
artefact** — it does NOT hot-reload source changes.

**Rule:**
- If you changed any frontend `.ts` / `.tsx` / `.css` / config file since the
  last build → run `cd frontend && npm run build` before running any Playwright
  guard.
- If you only changed backend `.py` files or docs → `next build` is not required.
- If you are running docs-only tasks (no code changes) → `next build` is not required.

Build command:
```bash
cd frontend && npm run build
```

---

## 5. Non-Goals

- **This index does not make guards CI-required.** CI adoption is a separate
  decision. See `docs/product/p98-evidence-deeplink-contract-adoption.md` §5 P99-C.
- **This index does not replace full regression.** When component logic changes
  broadly (e.g. shared layout, auth, routing), run the full frontend E2E suite:
  `make frontend-e2e-local`.
- **This index does not authorize staging governance files.** Never stage
  `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, or `roadmap.md`
  as part of a guard run.

---

## 6. Staging Hygiene

- **Never use `git add -A`.**
- Never stage: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md`.
  These are governance files; they are always dirty and are never committed as part of
  a task commit.
- Stage only the files directly changed by the task.
- Verify staged files with `git status --short` before every commit.

---

## 7. Future Maintenance

When adding a new Makefile contract target:

1. Add the target to `.PHONY` in `Makefile`.
2. Add a comment block above the target in `Makefile` describing: phase, what it
   protects, when to run it.
3. Add a row to the **Guard matrix** in this file (§2).
4. Add the target to the relevant **Validation bundle** in §3, or create a new bundle.
5. Update the `active_task_report.md` entry for the task that introduced the guard.

Do not group targets into meta-targets (e.g. `make all-contracts`) until there
are more than 12 individual guards. Grouping hides which surface failed.

---

## 8. Quick Reference

```bash
# Paste into terminal after any frontend evidence/deeplink change:
make documents-evidence-deeplink-contract
make daily-summary-evidence-contract
make actions-page-contract
make runtime-smoke

# Paste after any documents-surface change:
make documents-page-contract
make documents-confirmed-data-contract
make documents-evidence-deeplink-contract

# Paste before any commit that touches 3+ surfaces:
make documents-evidence-deeplink-contract daily-summary-evidence-contract daily-assistant-contract actions-page-contract documents-confirmed-data-contract documents-page-contract symptoms-page-contract runtime-smoke
```
