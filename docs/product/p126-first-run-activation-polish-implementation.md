# P126 — First-Run Activation Polish Implementation (2026-06-01)

## Final Classification
`P126_FIRST_RUN_ACTIVATION_POLISH_READY`

## Phase 0 Actual Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- P125 commit found: `7e9c9d3 docs(product): P125 first-run activation polish discovery`
- P124 commit found: `0329834 test(frontend): P124 verify first-run evidence integration`
- P123 commit found: `a5a6785 feat(frontend): P123 add minimal first-run journey`
- Pre-existing dirty/untracked observed and treated as known governance/runtime/environment artifacts:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`
- No pre-flight STOP condition triggered.

## How P125 Discovery Landed
P125 recommended minimal polish focused on Dashboard first-run checklist clarity, not backend/schema expansion.

Implemented in this lane:
1. Added explicit step status text (not just checkmarks).
2. Added missing-step “為什麼需要” short copy in in-progress states.
3. Added clear empty-state CTA shortcuts.
4. Added completed-state CTA shortcuts to Dashboard and Actions.
5. Kept P121/P124 safety wording for not-judged evidence unchanged in clinical meaning.

## Before / After (First-Run Polish)

### Before
- Checklist showed links with limited status semantics.
- In-progress copy gave next step but weaker rationale.
- Completed state had suggestion copy but no explicit completion CTA pair.

### After
- Each step now exposes explicit status text (`已完成` / `尚未開始` / `建議下一步` / `已開始追蹤`).
- In-progress now includes progress cue (`已完成 X/3`) and per-step rationale copy.
- Empty state has explicit CTA links for immediate start.
- Completed state has explicit CTA links for “查看今日建議” and “查看行動清單”.

## Activation State Table
| State | Trigger | Polish behavior |
|---|---|---|
| `empty` | no confirmed report + no symptom + no assistant surface | explicit start CTAs for documents/symptoms |
| `report-only` | confirmed report but no symptom | next step points to symptoms + why-needed copy |
| `symptom-only` | symptom exists but no confirmed report | next step points to documents + why-needed copy |
| `completed` | confirmed report + symptom + assistant surface | explicit CTA to dashboard and actions; actions step status visible |

## CTA Route Table
| CTA/TestID | Route |
|---|---|
| `first-run-empty-cta-documents` | `/platform/documents` |
| `first-run-empty-cta-symptoms` | `/platform/symptoms` |
| `first-run-link-documents` | `/platform/documents` |
| `first-run-link-symptoms` | `/platform/symptoms` |
| `first-run-link-dashboard` | `/platform/dashboard` |
| `first-run-link-actions` | `/platform/actions` |
| `first-run-completed-cta-dashboard` | `/platform/dashboard` |
| `first-run-completed-cta-actions` | `/platform/actions` |

## data-testid / Contract Guard Summary
Runtime file updated:
- `frontend/app/components/platform/daily-assistant-entry.tsx`

New contract test file:
- `frontend/tests/e2e/p126-first-run-activation-polish-contract.spec.ts`

P126 contract coverage:
1. Empty state explicit CTA + no ErrorBoundary.
2. Report-only next-step symptom guidance.
3. Symptom-only next-step documents guidance.
4. Completed state CTA visibility.
5. CTA routes remain existing routes.
6. Suppressed/not-judged wording not described as normal.
7. Overclaim prohibited phrases absent.

## P121/P124 Not-Judged Evidence Safety Note
- `suppressed_unit_scale_mismatch` remains represented as not-judged/uncertain context.
- No copy added that implies clinical normality.
- No copy added that escalates to diagnosis/medical certainty.

## Test Results
| Command | Result |
|---|---|
| `cd frontend && npx tsc --noEmit` | PASS |
| `cd frontend && npx next build` | PASS |
| `cd frontend && npx playwright test tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line` | PASS (7 passed) |
| `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts --reporter=line` | PASS (7 passed) |
| `cd frontend && npx playwright test tests/e2e/p124-first-run-evidence-integration-contract.spec.ts --reporter=line` | PASS (7 passed) |
| `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts --reporter=line` | PASS (5 passed) |
| `cd frontend && npx playwright test tests/e2e/p82-actions-page-contract.spec.ts --reporter=line` | PASS (4 passed) |
| `cd frontend && npx playwright test tests/e2e/p85-documents-page-contract.spec.ts --reporter=line` | NOT RUN (documents UI unchanged) |
| `cd frontend && npx playwright test tests/e2e/p86-symptoms-page-contract.spec.ts --reporter=line` | NOT RUN (symptoms UI unchanged) |

## Known Limitations
1. This remains a minimal UI polish lane; no persisted onboarding state machine was introduced.
2. Action-step “completion” still uses lightweight tracking signal and guidance copy, not a separate formal milestone model.
3. No backend telemetry pipeline or new analytics schema was added.

## Next Lane Suggestion
- Optional P127: add lightweight activation telemetry events (frontend-only event wiring) to measure drop-off from first-run checklist to action tracking, while preserving current backend/API contracts.
