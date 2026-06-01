# P123 — Minimal First-Run Journey Implementation (2026-06-01)

## Final Classification
`P123_MINIMAL_FIRST_RUN_JOURNEY_READY`

## Scope
- Lane: frontend minimal activation journey after P122 discovery and P121 trust-path fix.
- Goal: connect existing four surfaces into a minimal first-run flow in current dashboard entry.
- Constraint: no backend/schema expansion, no new route/page, no broad redesign.

## Phase 0 Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- Previous lane commits present:
  - P122: `308bd11`
  - P121: `9c4ff0b`
- Existing dirty/untracked were known governance/runtime artifacts only.

## P122 Contract Landing
P122 defined a minimal contract using existing routes only:
1. Documents (`/platform/documents`)
2. Symptoms (`/platform/symptoms`)
3. Dashboard Daily Assistant (`/platform/dashboard`)
4. Actions (`/platform/actions`)

P123 landed this contract directly inside `daily-assistant-entry.tsx` without adding a new onboarding page.

## Implementation Summary
- Added first-run checklist card with stable test IDs in dashboard assistant entry.
- Added runtime data fetch for journey signals:
  - `api.listDocuments()`
  - `api.listSymptoms()`
- Derived journey states from existing signals:
  - confirmed report
  - symptom log presence
  - assistant surface availability (daily summary or top recommendation)
- Added route links for the four surfaces and next-step hints.

## Steps / States / Routes
| Step | Route | Completion signal |
|---|---|---|
| Report | `/platform/documents` | at least one confirmed document |
| Symptom | `/platform/symptoms` | at least one symptom record |
| Assistant | `/platform/dashboard` | daily summary or top recommendation available |
| Action | `/platform/actions` | user can continue with action tracking |

| Journey state | Rule | UI copy intent |
|---|---|---|
| `empty` | none of key signals ready | orient user to two basic setup steps |
| `in_progress` | partial signals ready | show missing next-step guidance |
| `completed` | report + symptom + assistant ready | encourage move to actions tracking |

## Test IDs / Contract Guard
Added/used stable selectors:
- `first-run-journey-card`
- `first-run-journey-empty`
- `first-run-journey-in-progress`
- `first-run-journey-completed`
- `first-run-link-documents`
- `first-run-link-symptoms`
- `first-run-link-dashboard`
- `first-run-link-actions`
- `first-run-next-step-documents`
- `first-run-next-step-symptoms`
- `first-run-next-step-dashboard`
- `first-run-next-step-actions`
- `first-run-suppression-not-judged-note`

New contract spec:
- `frontend/tests/e2e/p123-first-run-journey-contract.spec.ts`

## P121 Suppression Relation
- P121 introduced not-judged evidence path for `suppressed_unit_scale_mismatch`.
- P123 frontend reflects this safely via a dedicated note when suppressed/not-judged evidence is detected.
- Wording is intentionally non-clinical and avoids normal/abnormal overclaim.

## Test Results
| Command | Result |
|---|---|
| `cd frontend && npx tsc --noEmit` | PASS |
| `cd frontend && npx next build` | PASS |
| `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts --reporter=line` | PASS (7 passed) |
| `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts --reporter=line` | PASS (24 passed) |

## Limitations
1. Journey completion is UI-level minimal orchestration, not a persisted onboarding workflow state machine.
2. Actions step remains route-level continuation guidance; this lane does not redefine action completion semantics.
3. No backend-side journey telemetry or funnel analytics added in this lane.

## Next Lane Suggestion
- Add lightweight journey analytics and drop-off visibility (frontend event instrumentation) while keeping current route contract unchanged.
