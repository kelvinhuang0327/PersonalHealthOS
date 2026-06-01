# P129 — Dogfood Execution Kit (2026-06-01)

## Final Classification
`P129_DOGFOOD_EXECUTION_KIT_READY`

## Scope
This lane is docs/script-only. No frontend/backend runtime changes, no test additions, no DB/schema/config changes.

## Phase 0 Actual Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- Required baseline commit present: `912418d` (P128)
- P127/P126/P123/P121 state chain present and consistent with prompt expectations.
- Existing dirty/untracked set matched prior known governance/runtime environment artifacts:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`
- No pre-flight STOP condition triggered.

## Carry-Forward From P128
- P128 classification: `P128_NEEDS_P129_MINIMAL_PATCH`
- P128 recommendation: execute docs/script-only dogfood lane first; only escalate to minimal UI patch when dogfood evidence shows concrete UI friction.

## Dogfood Execution Kit

### 1) Pre-test setup

#### 1.1 Environment anchor
- Canonical repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Canonical branch: `main`
- Expected baseline sequence visible in `git log`: P121 -> P123 -> P124 -> P126 -> P127 -> P128
- Recommended starting commit for this manual run: `912418d` or later on `main` that preserves P121-P128 outcomes.

#### 1.2 Prerequisites
- Login required: **Unknown** (confirm at run time; do not assume bypass)
- Service startup command: **Unknown** (confirm project-local startup runbook before test)
- Seed/demo data requirement: **Unknown** (if unavailable, tester must use deterministic manual input)
- Browser requirement: Use one stable desktop browser and record version.

#### 1.3 Pre-run evidence capture
Before step execution, tester records:
1. Current commit hash (`git rev-parse --short HEAD`)
2. Browser + OS version
3. Start timestamp
4. Whether account is empty/report-only/symptom-only/completed initial state
5. Screenshot of `/platform/dashboard` initial state

### 2) Dogfood Path (Minimal First-Run Loop)
1. Step 1: Go to `/platform/documents` and upload/confirm health report.
2. Step 2: Go to `/platform/symptoms` and add/review symptom entry.
3. Step 3: Go to `/platform/dashboard` and verify first-run checklist + Daily Assistant state.
4. Step 4: Go to `/platform/actions` and verify recommendations + evidence source links.

## Step-by-Step Test Script

### Step 1 — Documents
- Action:
  1. Open `/platform/documents`
  2. Upload or confirm one report
- Expected observable:
  1. Documents page renders without crash
  2. Confirmed report becomes visible in the documents flow
- Success condition:
  - Report can be used as first-run input for downstream checklist progression

### Step 2 — Symptoms
- Action:
  1. Open `/platform/symptoms`
  2. Add one symptom record
- Expected observable:
  1. Symptoms page renders without crash
  2. Symptom input persists enough to influence checklist state
- Success condition:
  - Symptom input is available for dashboard journey progression

### Step 3 — Dashboard first-run checklist
- Action:
  1. Open `/platform/dashboard`
  2. Inspect first-run checklist and Daily Assistant entry
- Expected observable:
  1. Checklist state transitions are understandable (empty/in-progress/completed)
  2. CTA links route to existing surfaces (documents/symptoms/dashboard/actions)
- Success condition:
  - Tester can identify next step from UI without guessing

### Step 4 — Actions and evidence source
- Action:
  1. Open `/platform/actions`
  2. Inspect recommendation rows and evidence cues
- Expected observable:
  1. Evidence summary/source link cues are visible where available
  2. Navigation path remains in-platform and non-broken
- Success condition:
  - Tester can inspect recommendation context and source linkage

## Observable Acceptance Criteria
| Scenario | Required observable behavior |
|---|---|
| Empty state | First-run checklist visible; clear CTA guidance to documents/symptoms |
| Report-only state | In-progress state with symptoms-oriented next-step guidance |
| Symptom-only state | In-progress state with documents-oriented next-step guidance |
| Completed state | Completion cues and CTA pair to dashboard/actions visible |
| Evidence badge/source link | Evidence cue/link appears where recommendation contains evidence context |
| not-judged safety | `suppressed_unit_scale_mismatch` remains uncertain/not-judged context, not normal |

## Known Limitations / User-Facing Caveats
1. This system does not replace doctors.
2. This system does not perform clinical diagnosis.
3. This system does not guarantee improvement outcomes.
4. not-judged does not mean normal.
5. Unit conversion, historical backfill, and production data migration are out of this phase.
6. First-run is dashboard-centered and not a dedicated onboarding route/state machine.

## Failure Report Template
Use the template below for every failed/manual-defect observation:

```md
### Dogfood Failure Report
- Session ID:
- Tester:
- Timestamp:
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
- Screenshot(s):
- Console log:
- Network trace:
- App/terminal log:

#### Impact
- Blocks first-run completion? (Yes/No)
- Affected state: empty/report-only/symptom-only/completed

#### Suggested Classification
- copy friction / navigation friction / evidence confusion / data issue / crash / overclaim risk

#### Severity
- S0 / S1 / S2

#### Notes
- 
```

## P130 Decision Rules
1. If issue is only wording/document clarity -> docs update lane (no runtime patch).
2. If CTA/copy clarity is poor but data flow remains correct -> minimal UI patch candidate.
3. If evidence path is incorrect or missing where expected -> STOP and open backend/evidence scope lane.
4. If fix requires DB/schema/API expansion -> STOP; prohibited in minimal UI patch lane.

## Proposed P130 Lane
Decision: conditional follow-up lane; execute only when dogfood findings justify runtime changes.

### Proposed P130 allowed file whitelist
#### Case A: docs-only follow-up
- `docs/product/p130-dogfood-findings-and-docs-adjustments.md`
- `00-Plan/roadmap/active_task_report.md`

#### Case B: minimal UI patch follow-up (strictly bounded)
- `frontend/app/components/platform/daily-assistant-entry.tsx`
- `frontend/tests/e2e/p126-first-run-activation-polish-contract.spec.ts` (extend existing only)
- `docs/product/p130-minimal-ui-patch.md`
- `00-Plan/roadmap/active_task_report.md`

### Proposed P130 validation strategy
#### Case A: docs-only
- Phase 0 pre-flight: PASS/FAIL
- tsc / Playwright / next build / backend pytest: NOT RUN

#### Case B: minimal UI patch
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line`
- `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line`
- `cd frontend && npx next build`
- backend pytest only if backend files are touched

## Validation Status For This P129 Lane
| Item | Status |
|---|---|
| Phase 0 canonical repo/branch/git-dir checks | PASS |
| P128/P121-P127 chain consistency checks | PASS |
| tsc | NOT RUN (docs-only lane) |
| Playwright | NOT RUN (docs-only lane) |
| next build | NOT RUN (docs-only lane) |
| backend pytest | NOT RUN (docs-only lane) |

## Handoff
This execution kit is ready for manual dogfood sessions. Use the failure template and decision rules to determine whether next action is docs-only refinement or a bounded P130 minimal UI patch.
