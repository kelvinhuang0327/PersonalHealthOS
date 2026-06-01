# P131 — Manual Dogfood Start Package (2026-06-01)

## Final Classification
`P131_READY_FOR_MANUAL_DOGFOOD`

## Scope
This lane is docs-only. No frontend/backend runtime changes, no new tests, no schema/API/config/CI changes.

## Phase 0 Actual Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- Required baseline commit present: `1bfa2fe` (P130)
- P121-P130 chain consistency confirmed from git log and docs references.
- Existing dirty/untracked artifacts matched known governance/runtime environment state:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`
- No pre-flight STOP condition triggered.

## P130 Dry-Run Carry-Forward
- P130 classification: `P130_READY_FOR_MANUAL_DOGFOOD`
- P130 required validation bundle results:
  - frontend tsc: PASS
  - first-run/evidence/polish Playwright bundle: PASS (21 passed)
  - cross-surface Playwright bundle: PASS (22 passed)
  - frontend next build: PASS
  - backend P121 targeted pytest: PASS (6 passed)
- P130 conclusion remains valid: manual dogfood can begin; UI patch lane should be conditional on repeated friction evidence.

## Manual Dogfood Start Package

### 1) Pre-test readiness

#### 1.1 Environment anchor
- Canonical repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Canonical branch: `main`
- Latest automated dry-run reference: `1bfa2fe`
- Recommended run base: `1bfa2fe` or later commit that preserves P121-P130 outcomes.

#### 1.2 Known-validated baseline
Already validated in P130 and accepted as dry-run baseline:
1. `cd frontend && npx tsc --noEmit`
2. `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line`
3. `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line`
4. `cd frontend && npx next build`
5. `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py -v`

#### 1.3 Tester prerequisites
- Login requirement: **Unknown** (confirm in actual environment; do not assume bypass).
- Service startup command for manual session: **Unknown** (confirm with local runbook before start).
- Seed/demo dataset requirement: **Unknown** (if absent, tester uses deterministic manual input).
- Suggested minimal test data:
  1. one report upload/confirm sample
  2. one symptom input sample
  3. one case where uncertain/not-judged cue is visible if possible

#### 1.4 Recommended screenshot checkpoints
1. Initial dashboard state before any action.
2. Documents page after upload/confirm.
3. Symptoms page after input.
4. Dashboard first-run card in in-progress/completed states.
5. Actions page showing recommendation and evidence source cues.

## Step-by-Step Manual Dogfood Script
1. Step 1: open `/platform/documents`, upload or confirm health report.
2. Step 2: open `/platform/symptoms`, input or review symptom entry.
3. Step 3: open `/platform/dashboard`, verify first-run checklist and Daily Assistant cues.
4. Step 4: open `/platform/actions`, verify recommendation rows and evidence source links.

## Observation Checklist
For each session, record Yes/No + notes:
1. Tester can tell the next step without external explanation.
2. Tester can complete the first-run loop end-to-end.
3. Evidence badge/source link is visible where expected.
4. Tester understands not-judged or `suppressed_unit_scale_mismatch` is not normal.
5. No crash, loading-stuck, or ErrorBoundary fallback appears.
6. No overclaim/medical certainty language appears.

## Result Classification Rules
- PASS:
  - first-run loop is completable,
  - no major misleading behavior,
  - no safety/overclaim issue.
- WARN:
  - loop completes,
  - but copy/CTA wording causes repeated hesitation or friction.
- FAIL:
  - one or more core steps cannot be completed,
  - or evidence/CTA behavior is materially confusing.
- BLOCKER:
  - crash, loading dead-end, data-path contradiction,
  - overclaim risk,
  - not-judged presented as normal,
  - or fix requires DB/API/schema expansion.

## Failure Report Form
Use this form for every non-PASS observation.

```md
### Manual Dogfood Failure Report
- Tester:
- Date/Time:
- Commit:
- Browser/OS:

#### Operation Steps
1.
2.
3.

#### Expected Result
-

#### Actual Result
-

#### Evidence
- Screenshot:
- Console log:
- Network log:
- App/terminal log:

#### Classification
- copy friction / navigation friction / evidence confusion / data issue / crash / overclaim risk / scope expansion needed

#### Manual Dogfood Impact
- Blocks manual dogfood? (Yes/No)
- Affected step: documents / symptoms / dashboard / actions
- Severity: WARN / FAIL / BLOCKER

#### Additional Notes
-
```

## P132 Decision Rules
1. If issue is wording clarity only and no runtime ambiguity -> P132 docs or copy patch.
2. If CTA clarity is weak but data path is correct -> P132 minimal UI patch.
3. If evidence path is wrong or contradictory -> STOP and open backend/evidence scope lane.
4. If crash/build/test instability appears in manual run -> P132 blocker-fix scope (bounded, evidence-backed).
5. If DB/schema/API expansion is required -> STOP; do not execute under minimal UI patch lane.

## Proposed P132 Lane, Allowed File Whitelist, and Validation Strategy

### Case A: docs or copy-only follow-up
- Proposed classification: `P132_DOCS_COPY_PATCH`
- Allowed files:
  - `docs/product/p132-manual-dogfood-findings-docs-copy-patch.md`
  - `00-Plan/roadmap/active_task_report.md`
- Validation strategy:
  - Phase 0 pre-flight only
  - runtime validations marked NOT RUN

### Case B: minimal UI patch follow-up (only for repeated CTA/copy friction)
- Proposed classification: `P132_MINIMAL_UI_PATCH`
- Allowed files:
  - `frontend/app/components/platform/daily-assistant-entry.tsx`
  - `frontend/tests/e2e/p126-first-run-activation-polish-contract.spec.ts` (extend only)
  - `docs/product/p132-minimal-ui-patch.md`
  - `00-Plan/roadmap/active_task_report.md`
- Validation strategy:
  1. `cd frontend && npx tsc --noEmit`
  2. `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line`
  3. `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line`
  4. `cd frontend && npx next build`
  5. backend pytest only if backend files are touched

## Validation Status For This P131 Lane
| Item | Status |
|---|---|
| Phase 0 canonical checks | PASS |
| P130 commit/state consistency checks | PASS |
| tsc | NOT RUN (docs-only lane) |
| Playwright | NOT RUN (docs-only lane) |
| next build | NOT RUN (docs-only lane) |
| backend pytest | NOT RUN (docs-only lane) |

## Go / No-Go Gate For Manual Dogfood Start
- GO when:
  1. Preconditions and screenshot checkpoints are prepared.
  2. Session follows the 4-step script.
  3. No BLOCKER observation appears.
- NO-GO when:
  1. BLOCKER appears (especially overclaim risk, crash, or scope expansion needed).
  2. Evidence path correctness is in doubt and cannot be resolved in docs/copy lane.

Manual dogfood is approved to start under this package, with escalation strictly controlled by the classification and P132 decision rules above.
