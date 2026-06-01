# P128 — Dogfood-Ready Checklist And Minimal Patch Discovery (2026-06-01)

## Final Classification
`P128_NEEDS_P129_MINIMAL_PATCH`

## Scope
This lane is discovery/checklist only. No frontend/backend runtime implementation, no test creation, no schema/migration/config changes.

## Phase 0 Actual Observations
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- P127 commit present: `f46f5a2`
- P126/P124/P123/P121 states present and consistent with prompt expectations:
  - `bcccbd7` (P126)
  - `0329834` (P124)
  - `a5a6785` (P123)
  - `9c4ff0b` (P121)
- Existing dirty/untracked set matched known governance/runtime environment artifacts from prior lanes:
  - modified: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`
- No pre-flight STOP condition triggered.

## P127 Conclusion Carry-Forward
P127 concluded `P127_DOGFOOD_READY_WITH_LIMITATIONS` and verified targeted quality bundle as all PASS. Therefore this lane focuses on converting that state into a practical dogfood checklist and a tightly scoped next-lane patch proposal.

## Dogfood-Ready Minimum First-Run Path
1. Step 1: `/platform/documents` upload and confirm a health report.
2. Step 2: `/platform/symptoms` add and review symptom input.
3. Step 3: `/platform/dashboard` review first-run checklist and Daily Assistant status.
4. Step 4: `/platform/actions` review recommendation list and evidence source links.

## Observable Acceptance Criteria (Dogfood Session)
| Scenario | Observable behavior required for acceptance |
|---|---|
| Empty state (no report + no symptom) | First-run checklist visible; explicit start CTAs guide to documents/symptoms; no crash/ErrorBoundary |
| Report-only | In-progress checklist state shown; next-step guidance points to symptoms with rationale |
| Symptom-only | In-progress checklist state shown; next-step guidance points to documents with rationale |
| Report + symptom completed | Completed state appears; CTA pair to dashboard/actions visible |
| Evidence badge/source link | Evidence summary badge and source deep-link behavior visible on dashboard/actions where applicable |
| Suppressed/not-judged safety | `suppressed_unit_scale_mismatch` remains not-judged/uncertain wording; no normal/diagnosis overclaim |

## Dogfood Checklist

### A. Pre-test setup
1. Use test environment, not production data.
2. Prepare one test account and deterministic sample report/symptom data.
3. Confirm tester sees current first-run surfaces: documents, symptoms, dashboard, actions.
4. Confirm test plan includes at least one suppressed/not-judged evidence example.

### B. Execution steps
1. Start from empty account and open `/platform/dashboard`.
2. Follow checklist CTA to `/platform/documents`, upload/confirm report, then return.
3. Follow checklist CTA to `/platform/symptoms`, submit symptom entry, then return.
4. Verify dashboard first-run state progression to completed.
5. Open `/platform/actions`, verify recommendation items and evidence source links.
6. If suppressed/not-judged evidence appears, verify wording remains uncertainty-safe.

### C. Expected results
1. First-run path can be completed end-to-end without route dead ends.
2. State transitions are understandable (empty -> in-progress -> completed).
3. Evidence cues are visible and navigable on dashboard/actions.
4. No claim text escalates to diagnosis or certainty.

### D. Overclaim phrases that must not appear
- 「可直接視為正常」
- 「已可診斷」
- 「保證改善」
- 「可取代醫師判斷」
- Any wording that equates not-judged with normal.

### E. Failure reporting protocol
1. Capture route, scenario state, and exact observable mismatch.
2. Attach screenshot/video plus timestamp.
3. Include offending copy string if safety/overclaim issue.
4. Tag issue severity:
   - S0: safety/medical overclaim
   - S1: broken path or crash
   - S2: incorrect state guidance/linking
5. Map each issue to candidate lane:
   - docs/process only -> P129 docs/script
   - bounded UI copy/state issue -> P129 minimal UI patch
   - backend/schema dependency -> blocked classification (new lane required)

## Known Limitations / User-Facing Caveats
1. This product does not replace doctors or clinical diagnosis.
2. Recommendation output is guidance, not guaranteed outcome improvement.
3. not-judged evidence does not mean normal.
4. Unit conversion, historical backfill, and production data migration are out of current phase scope.
5. First-run journey is dashboard-centered (no dedicated onboarding route/state machine).

## Runtime Blocker Assessment
- Runtime blocker found in this discovery lane: **No**.
- Current gaps are execution/observability polish gaps rather than trust-path correctness blockers.

## P129 Next Lane Recommendation (Minimal Patch Scope)
Decision: proceed with a minimal P129 patch lane focused on dogfood execution quality and bounded observability.

### Recommended P129 shape
Option A (preferred if no UI defects in dogfood session):
- docs/script-only lane for dogfood execution protocol, issue intake template, and triage rubric.

Option B (only if dogfood exposes bounded UI friction):
- minimal UI patch limited to first-run checklist clarity/copy/telemetry emit points in existing component.
- no new route/page/component, no backend/schema dependency.

### Proposed P129 task prompt scope (for next round)
1. Keep trust semantics unchanged (P121/P124 safety wording preserved).
2. Add only bounded first-run observability or wording polish where dogfood session reveals friction.
3. Prove no regression against existing first-run and cross-surface evidence contracts.
4. STOP immediately if backend/schema/migration dependency is required.

## Proposed P129 Allowed File Whitelist
### If docs/script-only path
- `docs/product/p129-dogfood-execution-script-and-triage.md`
- `00-Plan/roadmap/active_task_report.md`

### If minimal UI patch path (only when strictly needed)
- `frontend/app/components/platform/daily-assistant-entry.tsx`
- `frontend/tests/e2e/p126-first-run-activation-polish-contract.spec.ts` (extend only)
- `docs/product/p129-dogfood-minimal-ui-patch.md`
- `00-Plan/roadmap/active_task_report.md`

## Proposed P129 Validation Strategy
### Docs/script-only path
- Phase 0 pre-flight only: PASS/FAIL
- Runtime validations: NOT RUN

### Minimal UI patch path
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npx playwright test tests/e2e/p123-first-run-journey-contract.spec.ts tests/e2e/p124-first-run-evidence-integration-contract.spec.ts tests/e2e/p126-first-run-activation-polish-contract.spec.ts --reporter=line`
- `cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts tests/e2e/p82-actions-page-contract.spec.ts tests/e2e/p85-documents-page-contract.spec.ts tests/e2e/p86-symptoms-page-contract.spec.ts tests/e2e/p101-report-symptom-recommendation-integration.spec.ts --reporter=line`
- `cd frontend && npx next build`
- backend targeted tests only if backend is touched

## Validation Status For This P128 Lane
| Validation item | Status |
|---|---|
| Phase 0 canonical repo/branch/git-dir checks | PASS |
| P127/P121-P126 commit/state consistency check | PASS |
| `tsc` | NOT RUN (docs-only lane) |
| Playwright | NOT RUN (docs-only lane) |
| next build | NOT RUN (docs-only lane) |
| backend targeted pytest | NOT RUN (docs-only lane) |

## Handoff
Dogfood handoff is allowed with explicit caveats and checklist protocol above. Proceed to P129 minimal patch as a focused follow-up lane, not as an emergency blocker lane.
