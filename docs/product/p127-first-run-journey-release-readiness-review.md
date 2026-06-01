# P127 — First-Run Journey Release Readiness Review (2026-06-01)

## Final Classification
`P127_DOGFOOD_READY_WITH_LIMITATIONS`

## Scope
Review release readiness for lanes P121–P126 with no new runtime implementation. Validate trust semantics, first-run journey continuity, evidence integration, activation polish behavior, and targeted guard coverage.

## Phase 0 Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- Required commits present:
  - `9c4ff0b` (P121)
  - `a5a6785` (P123)
  - `0329834` (P124)
  - `7e9c9d3` (P125)
  - `bcccbd7` (P126)
- Pre-existing dirty/untracked artifacts remained unchanged and treated as known governance/runtime environment state:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`

## Closure Map (P121–P126)
| Lane | Goal | Status | Evidence |
|---|---|---|---|
| P121 | Suppression reason propagation in backend evidence bundle | Closed | not-judged path + targeted backend tests (6/6 pass) |
| P123 | Minimal first-run journey implementation | Closed | dashboard checklist states + links + contract suite |
| P124 | Evidence integration review and gap coverage | Closed | cross-surface evidence cues verified by contract suite |
| P125 | Activation polish discovery for P126 | Closed | scoped minimal polish recommendations |
| P126 | Minimal activation runtime polish implementation | Closed | runtime polish + new contract suite + guard runs pass |

## Four-Surface Readiness
| Surface | Readiness | Notes |
|---|---|---|
| Dashboard (`/platform/dashboard`) | Ready | first-run states, progress cues, completed CTA pair, safety wording preserved |
| Actions (`/platform/actions`) | Ready | recommendation and evidence source link path remains healthy |
| Documents (`/platform/documents`) | Ready | journey entry and deep-link patterns remain stable |
| Symptoms (`/platform/symptoms`) | Ready | first-run guidance and symptom entry surface remain stable |

## Safety/Copy Review
- Suppressed unit scale mismatch remains represented as not-judged/uncertain context.
- No new wording implies clinically normal/abnormal certainty for suppressed rows.
- No overclaim or diagnosis-level copy introduced by first-run journey/polish changes.

## Targeted Validation Bundle Results
| Command | Result |
|---|---|
| `cd frontend && npx tsc --noEmit` | PASS |
| `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line` | PASS (21 passed) |
| `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line` | PASS (22 passed) |
| `cd frontend && npx next build` | PASS |
| `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py -v` | PASS (6 passed) |

## Known Limitations
1. First-run journey is still dashboard-centered, not a dedicated onboarding route/state machine.
2. Action-step completion signal remains lightweight and UI-derived.
3. No activation telemetry events exist yet for drop-off instrumentation.
4. Classification therefore remains dogfood-ready, not full production-optimization complete.

## Decision
`P127_DOGFOOD_READY_WITH_LIMITATIONS`

Reasoning:
- P121 trust semantics and P123/P124/P126 first-run contracts are all green under targeted verification.
- Four core surfaces required by the journey are functional and connected.
- Remaining gaps are optimization/observability improvements, not release blockers for controlled dogfood usage.

## Proposed Next Lane (P128 Minimal Patch)
Objective: improve observability and activation confidence without changing backend/schema contracts.

### Proposed P128 whitelist
- `frontend/app/components/platform/daily-assistant-entry.tsx`
- `frontend/tests/e2e/p126-first-run-activation-polish-contract.spec.ts` (or new `p128-*` spec)
- `docs/product/p128-*.md`
- `00-Plan/roadmap/active_task_report.md`

### Proposed P128 minimal scope
1. Add lightweight frontend activation telemetry emit points for first-run transitions (empty -> in-progress -> completed).
2. Keep payload bounded and non-clinical; do not add backend schema/API requirements.
3. Add/extend contract tests to assert telemetry trigger conditions do not alter existing UI/safety behavior.

### Proposed P128 validation strategy
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line`
- `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line`
- `cd frontend && npx next build`
- backend targeted tests only if backend is touched.
