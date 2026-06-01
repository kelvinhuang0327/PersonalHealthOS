# P124 — First-Run Journey Evidence Integration Review (2026-06-01)

## Final Classification
`P124_FIRST_RUN_EVIDENCE_INTEGRATION_READY`

## Phase 0 Actual Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- P123 commit found: `a5a6785 feat(frontend): P123 add minimal first-run journey`
- P121 commit found: `9c4ff0b feat(backend): P121 propagate suppression reason in evidence bundle`
- P122 commit found: `308bd11 docs(product): P122 first-run journey discovery`
- Dirty/untracked observed were known governance/runtime/environment artifacts only:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`

## P123 Journey vs Evidence/Recommendation Alignment
Review target was whether P123 journey is only route navigation, or really aligns with existing evidence surfaces.

Observed alignment:
1. Dashboard first-run journey card (`first-run-*`) routes to existing four surfaces as designed.
2. Dashboard Daily Assistant top recommendation already has evidence visualization:
   - `data-testid="daily-toprec-evidence-badge"`
   - optional source page link `data-testid="p91-daily-source-page-link"` based on `source_type`.
3. Actions recommendation layer already has evidence visualization + source link:
   - `evidence_summary` block
   - `data-testid="p89-source-page-link"` using `source_type` and `source_id/document_id` mapping.
4. Missing evidence path is safe: no evidence badge rendered when `evidence_summary` is absent, and no crash.

Conclusion: no runtime UI gap requiring TSX changes in this lane; contract-level verification was sufficient.

## lab_report_item / symptom / suppressed not-judged UI Behavior
- `lab_report_item` recommendation:
  - evidence summary is visible.
  - source link targets documents with deep-link when `document_id` exists.
- `symptom` recommendation:
  - evidence summary is visible.
  - source link targets symptoms page.
- suppressed/not-judged evidence (`suppressed_unit_scale_mismatch`):
  - dashboard note appears via `first-run-suppression-not-judged-note`.
  - copy remains cautious and does not claim clinical normality.

## data-testid / Contract Guard Summary
New guard file: `frontend/tests/e2e/p124-first-run-evidence-integration-contract.spec.ts`

Covered contracts:
1. Completed first-run state includes evidence-aware recommendation surface, not links only.
2. `lab_report_item` recommendation evidence links to documents deep-link.
3. `symptom` recommendation evidence links to symptoms route.
4. Missing evidence does not crash and does not force fake evidence UI.
5. Suppressed/not-judged content does not claim normal.
6. Overclaim phrase guard (medical over-promise prohibited terms absent).
7. Documents/Symptoms/Dashboard/Actions links remain healthy without ErrorBoundary.

## Test Results
| Command | Result |
|---|---|
| `cd frontend && npx tsc --noEmit` | PASS |
| `cd frontend && npx playwright test tests/e2e/p124-first-run-evidence-integration-contract.spec.ts --reporter=line` | PASS (7 passed) |
| `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts --reporter=line` | NOT RUN (no runtime TSX change) |
| `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts --reporter=line` | NOT RUN (no runtime TSX change) |
| `cd frontend && npx playwright test tests/e2e/p82-actions-page-contract.spec.ts --reporter=line` | NOT RUN (no runtime TSX change) |
| `cd frontend && npx playwright test tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line` | NOT RUN (no runtime TSX change) |
| `cd frontend && npx next build` | NOT RUN (no runtime TSX change) |

## Known Limitations
1. P124 validates integration behavior via mocked contracts, not backend live data runs.
2. Journey completion still represents minimal orchestration, not a persisted onboarding state machine.
3. This lane does not introduce new cross-surface analytics events for journey-to-evidence conversion.

## Next Lane Suggestion
- Add lightweight telemetry for first-run to evidence-view and evidence-view to action-add transitions, while preserving current no-new-endpoint architecture.
