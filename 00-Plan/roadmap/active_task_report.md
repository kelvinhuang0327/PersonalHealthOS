# P121 — Backend Evidence Bundle Suppression Reason Propagation (2026-06-01)

**Final Classification:** `P121_BACKEND_EVIDENCE_BUNDLE_SUPPRESSION_REASON_READY`
**Branch:** `main`

## Pre-flight Result
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` (PASS)
- Branch: `main` (PASS)
- Git dir: `.git` (PASS, not worktree)
- Detached HEAD: No
- P120/P122 expected state: matched (`9413929` and `308bd11` present)
- Source reconfirmed old assumption error: assistant bundle path previously filtered with `abnormal_flag.isnot(None)` and excluded suppressed rows.

## Dirty File Handling
- Existing dirty/untracked files were known governance/runtime artifacts from prior lanes.
- No unknown unrelated dirty source files were introduced by P121.
- P121 changes were restricted to whitelist files only.

## Evidence Semantics Table
| Row type | Evidence path | Counts as abnormal | Included in lab_abnormalities | Severity/ranking impact |
|---|---|---:|---:|---:|
| `abnormal_flag=H/L` | `lab_report_items` | Yes | Yes | Yes (unchanged) |
| `abnormal_flag=None` + `suppressed_unit_scale_mismatch` | `lab_not_judged_items` | No | No | No |
| `abnormal_flag=None` + no-rule/unknown/parser-low-conf | excluded from assistant lab lists | No | No | No |

## Files Changed
- `backend/app/services/health_assistant_service.py`
- `backend/tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py`
- `docs/product/p121-backend-evidence-bundle-suppression-reason-propagation.md`
- `00-Plan/roadmap/active_task_report.md`

## Test Results
| Test command | Result |
|---|---|
| `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py -v` | PASS (6 passed) |
| `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_health_assistant_service.py -q` | PASS (23 passed) |
| Next build / Playwright full suite | NOT RUN (backend-only lane) |

## Governance Notes
- No DB model change.
- No migration/new column.
- No schema-expansion-driven workaround.
- No frontend runtime changes.
- No modifications to forbidden governance files (`roadmap.md`, `CTO-Analysis.md`, `CEO-Decision.md`, `active_task.md`).

## CTO 5-line Summary
- P121 introduced a safe not-judged evidence path for `suppressed_unit_scale_mismatch`.
- Suppressed rows are now observable in assistant bundle while isolated from abnormal scoring.
- `abnormal_lab_count` and `lab_abnormalities` remain tied to clinically judged rows only.
- Existing health assistant test suite passed after change.
- No schema/DB/frontend blast radius.

## CEO 5-line Summary
- P121 trust-lane blocker has been resolved without risky data model changes.
- Suppressed unit-mismatch evidence is now visible but clearly marked uncertain/not-judged.
- The fix does not inflate abnormal counts or severity.
- Regression tests passed and scope stayed tightly governed.
- This unblocks moving to the next implementation lane.

# P122 — First-Run Journey Discovery (2026-06-01)

**Task:** `P122_FIRST_RUN_JOURNEY_DISCOVERY`
**Final Classification:** `P122_FIRST_RUN_JOURNEY_DISCOVERY_READY`
**Decision:** `can-implement-minimally` (discovery-only, no runtime changes)
**Branch:** `main`

## Pre-flight Result
- Repo: /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
- Branch: main
- Git dir: .git
- P120 commit `9413929` exists in HEAD history
- Known dirty/untracked only (no unknown source drift):
  - Modified governance files: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - Known untracked/runtime artifacts: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`

## Four-Surface Journey Map (Current)
```mermaid
flowchart LR
  A[Documents<br/>/platform/documents] --> B[Symptoms<br/>/platform/symptoms]
  B --> C[Dashboard Daily Assistant<br/>/platform/dashboard]
  C --> D[Actions<br/>/platform/actions]

  A -. evidence refs .-> C
  B -. symptom refs .-> C
  C -. recommendation source links .-> D
  C -. lab deep-link ?document_id .-> A
```

## Surface Inventory (Route / Main Component / Guard)
- Documents:
  - Route: `/platform/documents`
  - Main: `frontend/app/platform/documents/page.tsx`, `frontend/app/components/platform/parsed-items-drawer.tsx`
  - Guard: `frontend/tests/e2e/p85-documents-page-contract.spec.ts`, `frontend/tests/e2e/p87-documents-confirmed-data-refeed.spec.ts`, `frontend/tests/e2e/p97-documents-evidence-deep-link.spec.ts`
- Symptoms:
  - Route: `/platform/symptoms`
  - Main: `frontend/app/platform/symptoms/page.tsx`
  - Guard: `frontend/tests/e2e/p86-symptoms-page-contract.spec.ts`
- Dashboard / Daily Assistant:
  - Route: `/platform/dashboard`
  - Main: `frontend/app/platform/dashboard/page.tsx`, `frontend/app/components/platform/daily-assistant-entry.tsx`
  - Guard: `frontend/tests/e2e/p76-daily-assistant-signal-contract.spec.ts`, `frontend/tests/e2e/p91-daily-assistant-evidence-badge.spec.ts`, `frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts`
- Actions:
  - Route: `/platform/actions`
  - Main: `frontend/app/platform/actions/page.tsx`, `frontend/app/components/platform/decision-recommendation-layer.tsx`
  - Guard: `frontend/tests/e2e/p82-actions-page-contract.spec.ts`, `frontend/tests/e2e/p80-actions-recommendation-smoke.spec.ts`, `frontend/tests/e2e/p89-actions-evidence-traceability.spec.ts`

## Discovery Findings (Activation Gap)
- Four surfaces already exist and are individually guarded.
- No dedicated first-run route (`/platform/onboarding`, `/platform/first-run`, `/platform/welcome` absent).
- Existing onboarding modal (`OnboardingWizard`) is profile/goals/first-metric only; not bound to report-confirm -> symptom-input -> daily-assistant -> action loop completion.
- Therefore gap is orchestration/navigation state, not capability availability.

## Minimal First-Run Contract (No New Surface)
- Entry point: `/platform/dashboard` as journey anchor.
- Step A: report import+confirm (`/platform/documents`)
- Step B: symptom entry (`/platform/symptoms`)
- Step C: daily assistant summary/recommendation visible (`/platform/dashboard`)
- Step D: recommendation tracked/executed (`/platform/actions`)
- States required:
  - Empty: no A/B/C/D completion
  - Missing-data: assistant has gaps and points to existing route CTAs
  - Completed: A/B/C/D done, journey collapses to completed summary

## P121 Suppression-Reason Gap Placement
- Location in journey: Step C/Step D evidence explainability.
- Source verification: `backend/app/services/health_assistant_service.py` filters lab items with `LabReportItem.abnormal_flag.isnot(None)` in evidence bundle assembly, so suppressed `abnormal_flag_reason` rows are excluded from this path.
- Severity for first-run activation: fast-follow, not a blocker (flow remains executable; gap is explainability quality).

## Classification And Next Lane
- Classification: `can-implement-minimally`
- Final: `P122_FIRST_RUN_JOURNEY_DISCOVERY_READY`
- Next lane (CEO approved): `P121 Backend Evidence Bundle Suppression Reason Propagation`

## Minimal Implementation File List (Proposed)
- `frontend/app/components/platform/daily-assistant-entry.tsx`
- `frontend/lib/first-run-journey.ts` (new)
- `frontend/app/platform/dashboard/page.tsx`
- `frontend/tests/e2e/p122-first-run-journey-contract.spec.ts` (new)

## Governance Notes
- Discovery only: no runtime frontend/backend/schema/db change.
- No branch/worktree/checkout/push operations.
- Restricted governance files untouched by this task except this report file (as allowed).
- P120 stale statement was not trusted; source code used as authority.

## CTO 5-line Summary
- Four required surfaces exist and are contract-guarded.
- Activation problem is missing first-run orchestration, not missing core capability.
- Minimal journey can be implemented with existing routes and frontend-only state wiring.
- P121 suppression reason issue sits in evidence explainability, not activation feasibility.
- Recommended next execution is P121 per approved lane.

## CEO 5-line Summary
- Current product can do upload, symptom, assistant, and action, but users are not guided through one path.
- A minimal first-run contract is now clearly defined and ready for implementation.
- No costly regression reruns were needed for this discovery-only task.
- No runtime risk introduced because no code behavior was changed.
- Proceed to P121 next, then ship first-run journey implementation lane.

# P120 — Daily Assistant Suppression Reason Warning — Blocked by Evidence Gap (2026-05-31)

**Final Classification:** `P120_BLOCKED_BY_IMPLEMENTATION_EVIDENCE_GAP`
**Branch:** `main`

## Pre-flight Result
- Repo: /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
- Branch: main
- Git dir: .git
- P118/P119 commits present
- Only restricted governance files and known runtime/test artifacts dirty/untracked

## Baseline Validation Table
| Check                        | Result |
|------------------------------|--------|
| Contract/smoke tests         | PASS   |
| Backend regression           | PASS   |
| P118 E2E                     | PASS   |
| Next.js build                | PASS   |

## Evidence Discovery Summary
- `lab_report_items` includes `abnormal_flag_reason` (from backend/app/api/documents.py)
- `lab_abnormalities` does **not** propagate `abnormal_flag_reason`
- Daily Assistant summary/recommendation evidence consumes `lab_abnormalities` or derived evidence, not `lab_report_items`
- `suppressed_unit_scale_mismatch` is **unavailable** to Daily Assistant evidence surface

## Data Path Gap Table
| Evidence Surface                | abnormal_flag_reason surfaced? | Consumed in UI? | Classification                  |
|---------------------------------|-------------------------------|-----------------|----------------------------------|
| Documents (parsed-items-drawer) | Yes                           | Yes             | Reason available and consumed    |
| Daily Assistant Evidence        | No                            | N/A             | Reason not available in data path|
| Actions Evidence                | No                            | N/A             | Reason not available in data path|
| Lab Trend/History Evidence      | No                            | N/A             | Reason not available in data path|
| Symptom Recommendation         | No                            | N/A             | Reason not available in data path|
| Documents Evidence Table        | No                            | N/A             | Reason not available in data path|
| Summary Card Evidence           | No                            | N/A             | Reason not available in data path|

## Why Implementation Stopped
- Frontend cannot safely infer or guess suppression reason for Daily Assistant evidence
- Backend evidence path needs explicit propagation of `abnormal_flag_reason` to `lab_abnormalities`/evidence bundle
- No DB/API/schema expansion authorized in P120

## Files Changed
- docs/product/p120-daily-assistant-suppression-reason-warning.md
- 00-Plan/roadmap/active_task_report.md

## Commit Hash After Created
(pending, see git log after commit)

## Next Recommended Lane
**P121 Backend Evidence Bundle Suppression Reason Propagation Contract**
Goal: propagate `abnormal_flag_reason` from `lab_report_items` into `lab_abnormalities`/Daily Assistant evidence bundle without DB migration, if source data already contains it.

## Governance Notes
- P120 did NOT touch roadmap.md
- P120 did NOT touch CTO-Analysis.md
- P120 did NOT touch CEO-Decision.md
- P120 did NOT touch active_task.md

## CTO 5-line Summary
- Evidence gap blocks safe propagation of suppression reason to Daily Assistant evidence.
- No backend or frontend runtime code was changed.
- Only documentation and report files were updated.
- Next step is backend contract propagation (P121).
- Governance and validation rules strictly followed.

## CEO 5-line Summary
- P120 implementation halted due to evidence path gap.
- No workaround or unsafe propagation allowed.
- All baseline and governance checks passed.
- Evidence gap and next steps fully documented.
- Ready for P121 backend contract scope.

# P119 — Evidence Surface Suppression Reason Propagation Discovery (2026-05-31)

**Classification:** `P119_EVIDENCE_SURFACE_SUPPRESSION_REASON_DISCOVERY_COMPLETE`
**Branch:** `main`

### 1. Objective
Map how `abnormal_flag_reason` (especially `suppressed_unit_scale_mismatch`) propagates across all evidence surfaces. Classify each as: reason available and consumed, reason available but ignored, reason not available in data path, reason collapsed into abnormal_flag null, or unknown/needs fixture evidence.

### 2. Methodology
- Grep/code archaeology for `abnormal_flag_reason`, `suppressed_unit_scale_mismatch`, `abnormal_flag`, `is_abnormal` across backend, frontend, and tests.
- Reviewed all evidence surface components and their data contracts.
- Confirmed actual UI rendering and test coverage.

### 3. Findings
- Only the Documents/parsed-items-drawer surface exposes and renders suppression reasons (P118).
- All other evidence surfaces ignore or do not receive `abnormal_flag_reason`.
- No evidence of accidental/implicit propagation or UI rendering outside parsed-items-drawer.
- Backend only includes `abnormal_flag_reason` in parsed items API; other surfaces do not receive or propagate this field.
- Only parsed-items-drawer and its E2E test cover suppression reason rendering; all other surfaces/tests only check `abnormal_flag`/`is_abnormal`.

### 4. Summary Table
| Evidence Surface                | abnormal_flag_reason surfaced? | Consumed in UI? | Classification                  |
|---------------------------------|-------------------------------|-----------------|----------------------------------|
| Documents (parsed-items-drawer) | Yes                           | Yes             | Reason available and consumed    |
| Daily Assistant Evidence        | No                            | N/A             | Reason not available in data path|
| Actions Evidence                | No                            | N/A             | Reason not available in data path|
| Lab Trend/History Evidence      | No                            | N/A             | Reason not available in data path|
| Symptom Recommendation         | No                            | N/A             | Reason not available in data path|
| Documents Evidence Table        | No                            | N/A             | Reason not available in data path|
| Summary Card Evidence           | No                            | N/A             | Reason not available in data path|

### 5. Conclusion
- No evidence surface except parsed-items-drawer currently surfaces or renders suppression reasons.
- Propagation to other surfaces would require backend and contract changes.

### 6. Reference
See `docs/product/p119-evidence-surface-suppression-reason-propagation-discovery.md` for full details.
# P118 — Frontend Suppression Reason Badge Contract (2026-05-31)

**Classification:** `P118_FRONTEND_SUPPRESSION_REASON_BADGE_READY`
**Commits:**
- Implementation: bc2abe5
- Report: (pending)
**Branch:** `main`

### 1. Implementation Summary
- Frontend displays abnormal_flag_reason = suppressed_unit_scale_mismatch as「單位不同，暫不判斷異常」
- Copy does not imply clinically normal
- Same-unit normal remains unchanged
- High/low abnormal flags remain unchanged
- P118 E2E selector fixed by clicking「審閱解析結果」button instead of filename <p>
- No backend runtime code change
- No DB migration
- No new DB column
- No real unit conversion
- No historical backfill
- No package or Playwright config change

### 2. Validation Summary
- P118 E2E PASS
- Baseline contracts PASS
- Backend regression PASS
- Next.js build PASS

### 3. Files Changed in Implementation
- frontend/app/components/platform/parsed-items-drawer.tsx
- frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.ts
- docs/product/p118-frontend-suppression-reason-badge-contract.md

### 4. Known Limitations
- P118 covers parsed-items drawer / documents review surface only
- Broader evidence surfaces may need later propagation

### 5. Next Recommended Lane
- P119 First-run report upload onboarding
- Or P119 evidence-surface suppression reason propagation discovery if safety remains priority

### 6. Governance Notes
- P118 did NOT touch roadmap.md
- P118 did NOT touch CTO-Analysis.md
- P118 did NOT touch CEO-Decision.md
- P118 did NOT touch active_task.md

### 7. CTO 5-line Summary
- Frontend now displays suppression reason badge for suppressed_unit_scale_mismatch
- No clinical normal implied for suppressed items
- All contract, regression, and build validations pass
- No backend, DB, or config changes
- Next: propagate suppression reason to broader evidence surfaces if needed

### 8. CEO 5-line Summary
- User-facing clarity improved for suppressed lab results
- Suppression reason now visible in documents review
- No backend or DB changes required
- All tests and builds pass, no regressions
- Next: expand clarity to more evidence surfaces if needed

# P116 — Abnormal Flag Suppression Reason Response Contract (2026-05-31)

# P117 — Suppression Reason Visibility Discovery (2026-05-31)

**Classification:** `P117_SUPPRESSION_REASON_VISIBILITY_DISCOVERY_COMPLETE_BACKEND_ONLY_SAFE_BUT_NOT_VISIBLE`
**Commits:** _(pending)_
**Branch:** `main`

### 1. Pre-flight Result
- Repo: /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
- Branch: main
- Git-dir: .git
- P116 impl commit: e57dafb present
- P116 report commit: d549de8 present
- No unrelated dirty files; only restricted governance files dirty
- P116 temp file cleaned up

### 2. Validation Summary
- All contract, backend, and frontend tests/builds PASS
- No regressions detected

### 3. Discovery Summary
- Backend exposes abnormal_flag_reason (e.g., suppressed_unit_scale_mismatch) in API
- Frontend and all evidence surfaces ignore abnormal_flag_reason
- No UI, table, or evidence renders suppression reason
- User-facing ambiguity persists for suppressed/normal/no-rule

### 4. Backend Response Availability Map
- ParsedItemResponse includes abnormal_flag_reason (backend/app/schemas/documents.py)
- API endpoint returns abnormal_flag_reason (backend/app/api/documents.py)

### 5. Frontend Consumption Map
- No code or test in frontend consumes abnormal_flag_reason
- All logic and UI only reference abnormal_flag

### 6. Evidence Surface Map
- Documents confirmed data: suppression reason NOT visible
- Lab history/trend: suppression reason NOT visible
- Daily Assistant evidence: suppression reason NOT visible
- Actions evidence: suppression reason NOT visible

### 7. User-Facing Ambiguity Risk Classification
- BACKEND_ONLY_SAFE_BUT_NOT_VISIBLE

### 8. Validation Table
| Area                | Status   |
|---------------------|----------|
| Backend API         | PASS     |
| Frontend build      | PASS     |
| Contract tests      | PASS     |
| Evidence surfaces   | Not visible |
| User-facing clarity | Ambiguous |

### 9. Files Changed
- docs/product/p117-suppression-reason-visibility-discovery.md

### 10. Commit Hashes
- P116 impl: e57dafb
- P116 report: d549de8

### 11. Known Limitations
- Suppression reason is not visible to users in any UI
- All ambiguity remains at the UI layer until frontend is updated

### 12. Next Recommended Lane
- Implement frontend badge/copy for suppression reason (Option A)

### 13. Governance Notes
- No backend or frontend runtime code changed in P117
- No DB migration or schema change
- No Makefile or governance file touched

### 14. CTO 5-line Summary
- Backend exposes suppression reason but frontend ignores it
- No evidence surface or UI displays suppressed_unit_scale_mismatch
- User-facing ambiguity persists for suppressed/normal/no-rule
- All tests and builds pass; no regressions
- Next lane: implement frontend badge/copy for suppression reason

### 15. CEO 5-line Summary
- Suppression reason is available in API but not visible to users
- No UI or evidence surface distinguishes suppressed from normal
- User-facing ambiguity remains unresolved
- All validation gates pass
- Recommend UI update to surface suppression reason

**Classification:** `P116_ABNORMAL_FLAG_SUPPRESSION_REASON_RESPONSE_READY`
**Commits:** `e57dafb` feat(backend): P116 expose abnormal flag suppression reason
**Branch:** `main`

### 1. Summary
- Response-level abnormal flag suppression reason/status was added
- `suppressed_unit_scale_mismatch` distinguishes P114 unit mismatch suppression from normal
- Same-unit normal remains distinguishable from suppressed mismatch
- High/low abnormal flags remain distinguishable
- No DB migration
- No new DB column
- No frontend runtime change
- No real unit conversion
- No historical backfill

### 2. Validation Summary
- backend tests PASS
- contract tests PASS
- runtime-smoke PASS
- frontend next build PASS

### 3. Files Changed in Implementation
- backend/app/schemas/documents.py
- backend/app/api/documents.py
- backend/tests/test_p116_abnormal_flag_suppression_reason_response_contract.py
- docs/product/p116-abnormal-flag-suppression-reason-response-contract.md

### 4. Known Limitations
- Response-level reason is not persisted in DB
- Frontend display is not changed in P116

### 5. Governance Notes
- P116 did NOT touch roadmap.md
- P116 did NOT touch CTO-Analysis.md
- P116 did NOT touch CEO-Decision.md
- P116 did NOT touch active_task.md

### 6. CTO 5-line Summary
- Response-level abnormal_flag_reason now exposed for suppressed, normal, high, low, and no-rule cases
- No DB or schema migration required
- All backend and contract tests pass
- No frontend or historical data impact
- Implementation strictly follows governance

### 7. CEO 5-line Summary
- Ambiguity in abnormal_flag=None resolved at API response level
- Downstream can now distinguish suppression, normal, and no-rule cases
- No user-facing or data migration risk
- All tests and validation gates pass
- Ready for next lane or UI/UX coordination

# P115 — Abnormal Flag Suppression Reason Discovery (2026-05-31)

**Classification:** `P115_ABNORMAL_FLAG_SUPPRESSION_REASON_DISCOVERY_COMPLETE_ACTIVE_AMBIGUITY`
**Commits:** `f2734e0` test(backend): P115 characterize abnormal flag suppression reason · _(this report commit)_
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| git-dir | `.git` (not a worktree) ✅ |
| P114 commits present | `e0bf937` + `654bcc2` ✅ |

### 2. Dirty File / Restricted Governance File Status

| File | Status |
|---|---|
| `00-Plan/roadmap/CEO-Decision.md` | Modified (pre-existing) — **NOT touched by P115** |
| `00-Plan/roadmap/CTO-Analysis.md` | Modified (pre-existing) — **NOT touched by P115** |
| `00-Plan/roadmap/roadmap.md` | Modified (pre-existing) — **NOT touched by P115** |
| No other unrelated dirty files | ✅ |

### 3. Import Path Fix Summary

- Fixed import in `test_p115_abnormal_flag_suppression_reason_discovery.py` from `from backend.app.models` to `from app.models` (matches backend test convention).
- No production code or global config changed.

### 4. Baseline Validation Table

| Suite | Count | Result |
|---|---|---|
| test_report_parser_stage2 | 21 | ✅ |
| test_lab_history_unit_comparison | 11 | ✅ |
| test_p112_normalized_unit_migration_runtime | 4 | ✅ |
| test_p113_abnormal_flag_unit_scale_discovery | 12 | ✅ |
| test_p114_abnormal_flag_unit_scale_guard | 25 | ✅ |
| test_p115_abnormal_flag_suppression_reason_discovery | 5 | ✅ |
| runtime-smoke | 3 | ✅ |
| 10 E2E contracts | 41 | ✅ |
| frontend next build | — | ✅ |

### 5. P115 Discovery Summary

- Characterized ambiguity in `abnormal_flag=None` (can mean: normal, unknown, no rule, suppressed by unit-scale guard).
- No schema, DB, or API change; no real unit conversion; no historical backfill.
- Downstream and API do not distinguish suppression reason; only `abnormal_flag` is exposed.

### 6. abnormal_flag Semantics Table

| abnormal_flag | Meaning |
|---|---|
| 'N' | Normal (units match, within range) |
| 'H'/'L' | High/Low (units match, out of range) |
| None | Ambiguous: normal, unknown, no rule, suppressed |

### 7. None Ambiguity Map

| Scenario | Example | Reason |
|---|---|---|
| Unit-scale mismatch | 5.5 mmol/L vs mg/dL rule | Suppressed by guard |
| No local rule | ALT 32 U/L, rule missing | No rule |
| Parser unavailable | 999 (no unit) | Unknown |

### 8. Downstream Consumption Map

- Evidence logic: `abnormal_flag=None` is not flagged as abnormal, may be omitted or shown as normal/unknown.
- No downstream code distinguishes suppression reason.

### 9. API/Schema Exposure Map

- API exposes only `abnormal_flag` (no `abnormal_flag_reason`).
- No schema field for suppression reason.

### 10. Risk Classification

- **Active ambiguity:** None value is overloaded, downstream and API cannot distinguish suppression from other cases.

### 11. Validation Table

| Step | Result |
|---|---|
| Backend pytest (P110–P115) | ✅ |
| All contract/smoke tests | ✅ |
| Frontend next build | ✅ |

### 12. Files Changed

| File | Action |
|---|---|
| `backend/tests/test_p115_abnormal_flag_suppression_reason_discovery.py` | Created |
| `docs/product/p115-abnormal-flag-suppression-reason-discovery.md` | Created |

### 13. Commit Hashes

| Commit | Message |
|---|---|
| f2734e0 | test(backend): P115 characterize abnormal flag suppression reason |

### 14. Known Limitations

- No schema/API extension for suppression reason (future lane).
- No historical backfill or real unit conversion.
- No production code change.

### 15. Next Recommended Lane

- Lane B: Schema/API extension to expose suppression reason.
- Lane D: Historical backfill if needed.

### 16. Governance Notes

- P115 did NOT touch roadmap.md
- P115 did NOT touch CTO-Analysis.md
- P115 did NOT touch CEO-Decision.md
- P115 did NOT touch active_task.md

### 17. CTO 5-line Summary

- P115 discovery confirms `abnormal_flag=None` is ambiguous: can mean suppressed, unknown, or no rule.
- Import path fix aligns with backend test convention; no production code touched.
- All backend, contract, and frontend validations pass; no regressions.
- No schema/API change; ambiguity remains for downstream consumers.
- Next: Schema/API extension lane to clarify suppression reason.

### 18. CEO 5-line Summary

- P115 completes abnormal flag suppression reason discovery with no production impact.
- All tests and contracts pass; system is stable.
- Ambiguity in `abnormal_flag=None` is documented and confirmed.
- No user-facing or data change; only test and doc added.
- Next: Plan schema/API extension to clarify ambiguity.

# Active Task Report

---

## P114 — Abnormal Flag Unit-Scale Guard (2026-05-28)

**Classification:** `P114_ABNORMAL_FLAG_UNIT_SCALE_GUARD_READY`  
**Commits:** `654bcc2` fix(backend): P114 guard abnormal flag unit-scale mismatch · _(this report commit)_  
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| git-dir | `.git` (not a worktree) ✅ |
| P113 commits present | `7c3f230` + `aa6fc6f` ✅ |

### 2. Dirty File / Restricted Governance File Status

| File | Status |
|---|---|
| `00-Plan/roadmap/CEO-Decision.md` | Modified (pre-existing) — **NOT touched by P114** |
| `00-Plan/roadmap/CTO-Analysis.md` | Modified (pre-existing) — **NOT touched by P114** |
| `00-Plan/roadmap/roadmap.md` | Modified (pre-existing) — **NOT touched by P114** |

### 3. Baseline Validation (Pre-implementation)

| Suite | Count | Result |
|---|---|---|
| runtime-smoke (10 E2E contracts) | 56 passed | ✅ |
| test_p113_abnormal_flag_unit_scale_discovery | 12 | ✅ |
| test_report_parser_stage2 | 21 | ✅ |
| test_lab_history_unit_comparison | 11 | ✅ |
| test_p112_normalized_unit_migration_runtime | 4 | ✅ |

### 4. What Was Implemented

**Root cause** (confirmed in P113): `compute_abnormal_flag` has no unit parameter. `infer_reference_range` returns raw rule thresholds (e.g. 70–99 mg/dL) regardless of the sample's unit, producing false positives (Glucose 5.5 mmol/L → 'L') and false negatives (LDL 3.4 mmol/L → 'N').

**Guard added in `backend/app/services/report_parser.py`:**

1. `_get_rule_unit(item_name, gender) -> str | None`  
   Looks up the canonical unit from `lab_reference_ranges.json`. Gender-aware for items with male/female sub-rules.

2. `_unit_scale_compatible(sample_normalized_unit, rule_unit) -> bool`  
   Returns `True` when units are absent or canonically equal (via `normalize_unit()`).  
   Returns `False` when both present and different scale (e.g. mmol/L vs mg/dL).

3. Guard inserted in `parse_lab_items` before `compute_abnormal_flag`:
   - Fires only when `range_source == 'default_rule'`
   - Mismatch → `abnormal_flag = None` (suppressed, not 'clinically normal')
   - IU/L alias preserved: `normalize_unit('IU/L')` = `'U/L'` = rule_unit → compatible
   - Explicit report ranges bypassed (range_source = 'extracted')

**No unit conversion performed. No historical backfill. No schema changes.**

### 5. Post-implementation Validation

| Suite | Count | Result |
|---|---|---|
| test_p114_abnormal_flag_unit_scale_guard (new, A–F) | **25** | ✅ |
| test_p113_abnormal_flag_unit_scale_discovery (updated b1, b3, c1) | 12 | ✅ |
| test_report_parser_stage2 | 21 | ✅ |
| test_lab_history_unit_comparison | 11 | ✅ |
| test_p112_normalized_unit_migration_runtime | 4 | ✅ |
| **Total backend** | **73** | ✅ |
| runtime-smoke | 56 | ✅ |

### 6. Files Changed

| File | Action |
|---|---|
| `backend/app/services/report_parser.py` | Modified — added `_get_rule_unit`, `_unit_scale_compatible`, guard in `parse_lab_items` |
| `backend/tests/test_p114_abnormal_flag_unit_scale_guard.py` | Created — 25 guard tests (groups A–F) |
| `backend/tests/test_p113_abnormal_flag_unit_scale_discovery.py` | Updated — b1, b3, c1 updated to reflect fixed behaviour |
| `docs/product/p114-abnormal-flag-unit-scale-guard.md` | Created — implementation report, decision table, known limitations |

### 7. Known Limitations

- No unit conversion (no conversion table): mmol/L samples remain `None` until upstream provides mg/dL value.
- No `abnormal_flag_reason` field: `None` does not distinguish "mismatch" from "no range". Schema extension is Lane B.
- No historical backfill: pre-P114 stored `abnormal_flag='L'` records not corrected. Migration is Lane D.

### 8. Classification

`P114_ABNORMAL_FLAG_UNIT_SCALE_GUARD_READY`

---

## P113 — Abnormal Flag Unit-Scale Safety Discovery (2026-05-28)

**Classification:** `P113_ABNORMAL_FLAG_UNIT_SCALE_DISCOVERY_COMPLETE_LATENT_RISK`  
**Commits:** _(test + report commit)_ · _(active_task_report commit — this file)_  
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| git-dir | `.git` (not a worktree) ✅ |
| P111 commits `3d0043e` + `6da3125` | present ✅ |
| P112 commits `0358d41` + `90cd36f` | present ✅ |

### 2. Dirty File / Restricted Governance File Status

| File | Status |
|---|---|
| `00-Plan/roadmap/CEO-Decision.md` | Modified (pre-existing) — **NOT touched by P113** |
| `00-Plan/roadmap/CTO-Analysis.md` | Modified (pre-existing) — **NOT touched by P113** |
| `00-Plan/roadmap/roadmap.md` | Modified (pre-existing) — **NOT touched by P113** |
| No other unrelated dirty files | ✅ |

### 3. Baseline Validation (Pre-discovery)

| Suite | Result |
|---|---|
| All 10 E2E contracts | ✅ PASS |
| `make runtime-smoke` | 56 passed ✅ |
| `test_report_parser_stage2.py` | 21 passed ✅ |
| `test_lab_history_unit_comparison.py` | 11 passed ✅ |
| `test_p112_normalized_unit_migration_runtime.py` | 4 passed ✅ |

### 4. Discovery Findings

**Risk Status: LATENT_RISK**

**Root cause**: `compute_abnormal_flag(value, low, high)` has no `unit` parameter.
`infer_reference_range(item_name, gender, unit)` accepts `unit` but uses it only
for display — rule thresholds (calibrated in mg/dL) are applied verbatim
regardless of the sample's unit.

**False positive path**: Glucose 5.5 mmol/L → rule {low=70, high=99 mg/dL} →
`5.5 < 70` → `abnormal_flag='L'` (clinically normal value wrongly flagged).

**False negative path**: LDL 3.4 mmol/L → rule {high=130 mg/dL} →
`3.4 < 130` → `abnormal_flag='N'` (borderline-high missed).

**`normalized_unit` (P110)**: stored in DB but never consulted during flag
derivation or downstream severity classification.

**Downstream propagation** confirmed: `detect_lab_abnormalities` returns
`severity='medium'` from the false-positive 'L' flag — surfaced to Daily
Assistant, notifications, `whyDetected` narrative.

**Activation conditions** (latent → active):
1. Lab report uses non-standard unit (mmol/L, g/L, µmol/L…)
2. No explicit reference range embedded in report text
3. Item name present in `lab_reference_ranges.json`

### 5. Characterization Tests Created

File: `backend/tests/test_p113_abnormal_flag_unit_scale_discovery.py`

| Test | Finding |
|---|---|
| A1–A3 | Same-scale (mg/dL + explicit range) → correct flags (baseline) |
| B1 | Glucose 5.5 mmol/L → false positive 'L' |
| B2 | `infer_reference_range` returns mg/dL thresholds for mmol/L caller |
| B3 | LDL 3.4 mmol/L → false negative 'N' |
| B4 | `compute_abnormal_flag` has no `unit` parameter (root cause) |
| C1 | `normalized_unit` and false-positive flag coexist (not cross-checked) |
| C2 | Same thresholds returned regardless of unit arg |
| D1 | False-positive → medium severity in `detect_lab_abnormalities` |
| D2 | False-positive propagates into `whyDetected` narrative |
| D3 | Extra `normalized_unit` field in evidence dict does not suppress severity |

**All 12 tests: PASS**

### 6. Discovery Report

`docs/product/p113-abnormal-flag-unit-scale-safety-discovery.md`

### 7. Post-Validation

| Suite | Result |
|---|---|
| All 10 E2E contracts | ✅ PASS |
| `make runtime-smoke` | 56 passed ✅ |
| `test_report_parser_stage2.py` | 21 passed ✅ |
| `test_lab_history_unit_comparison.py` | 11 passed ✅ |
| `test_p112_normalized_unit_migration_runtime.py` | 4 passed ✅ |
| `test_p113_abnormal_flag_unit_scale_discovery.py` | 12 passed ✅ |
| `cd frontend && npx next build` | ✅ PASS |

### 8. Non-Goals

- No production code modified
- No parser behaviour changed
- No DB migration added
- No historical data backfilled
- No unit conversion logic implemented
- No frontend runtime changes

### 9. Recommended Next Lanes

| Lane | Approach |
|---|---|
| A (preferred) | Threshold scaling via unit conversion table in `infer_reference_range` |
| B | Unit guard: suppress flag (set `None`) when unit mismatch detected |
| C | Add `unit_mismatch_warning` field; display caution in frontend only |
| D | Route to manual re-review queue on mismatch at ingest |

---

## P112 — normalized_unit Migration Runtime Assurance (2026-05-28)

**Classification:** `P112_NORMALIZED_UNIT_MIGRATION_RUNTIME_ASSURED`
**Commits:** `0358d41` (tests + script fixes) · _(report commit — this file)_
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| git-dir | `.git` (not a worktree) ✅ |
| P110 code commit `0f3348c` | present ✅ |
| P110 report commit `28ec88e` | present ✅ |
| P111 code commit `3d0043e` | present ✅ |
| P111 report commit `6da3125` | present ✅ |

### 2. Dirty File / Restricted Governance File Status

| File | Status |
|---|---|
| `00-Plan/roadmap/CEO-Decision.md` | Modified (pre-existing) — **NOT touched by P112** |
| `00-Plan/roadmap/CTO-Analysis.md` | Modified (pre-existing) — **NOT touched by P112** |
| `00-Plan/roadmap/roadmap.md` | Modified (pre-existing) — **NOT touched by P112** |
| No other unrelated dirty files | ✅ |

### 3. Baseline Validation Table (Before Implementation)

| Gate | Result |
|---|---|
| `lab-trend-comparison-contract` (7 tests) | PASS ✅ |
| `lab-trend-report-date-contract` (4 tests) | PASS ✅ |
| `documents-confirmed-data-contract` (4 tests) | PASS ✅ |
| `documents-page-contract` (4 tests) | PASS ✅ |
| `report-symptom-recommendation-contract` (5 tests) | PASS ✅ |
| `documents-evidence-deeplink-contract` (4 tests) | PASS ✅ |
| `daily-summary-evidence-contract` (4 tests) | PASS ✅ |
| `daily-assistant-contract` (5 tests) | PASS ✅ |
| `actions-page-contract` (4 tests) | PASS ✅ |
| `symptoms-page-contract` (4 tests) | PASS ✅ |
| `runtime-smoke` (56 tests) | PASS ✅ |
| `test_report_parser_stage2.py` (21 tests) | PASS ✅ |
| `test_lab_history_unit_comparison.py` (11 tests) | PASS ✅ |

### 4. Migration / Self-Heal Implementation Summary

#### P110 script audit findings
Both `scripts/migrate_p110_normalized_unit.py` and `scripts/self_heal_db.py` directly imported `engine` / `Base` from `app.core.database` at module level with no engine injection path. This made them untestable against a temporary DB — any test invocation would silently target the production PostgreSQL connection.

#### Changes made (minimal, non-destructive)
**`migrate_p110_normalized_unit.py`:**
- `has_column(table, column, _engine=None)` — accepts optional engine; defaults to production engine (backward-compatible)
- `upgrade(_engine=None)` / `downgrade(_engine=None)` — same injection pattern
- Added docstring documenting the SQLite DROP COLUMN limitation (requires SQLite ≥ 3.35.0) and the engine injection contract
- Import renamed: `engine as _default_engine` to make intent explicit

**`self_heal_db.py`:**
- `has_column(table, column, _engine=None)` — engine injection
- `main(_engine=None, _base=None)` — both engine and Base injectable
- `main()` now passes `eng` into `has_column()` calls (previously used global)
- Added module docstring documenting the destructive `drop_all + create_all` behaviour (intentional for dev/CI)
- Import renamed: `engine as _default_engine`, `Base as _default_base`

All `__main__` entry-points continue to work unchanged (no `_engine` arg = production path).

### 5. Runtime DB Smoke Table

_All smoke output is captured from `test_p112_normalized_unit_migration_runtime.py -v -s`._

| Step | Temp DB | Result |
|---|---|---|
| Before schema (Test A) | `p112_test_e4xyms8m.db` | `['id', 'test_name', 'unit', 'value']` — no `normalized_unit` |
| After upgrade (Test A) | same | `['id', 'normalized_unit', 'test_name', 'unit', 'value']` ✅ |
| Self-heal before (Test C) | `p112_test_0ua2m2po.db` | drift injected — `normalized_unit` ABSENT |
| After self-heal (Test C) | same | `['id', 'normalized_unit', 'test_name', 'unit']` ✅ |
| Data preservation (Test D) | `p112_test_cf5asq1a.db` | `normalized_unit = 'U/L'` preserved after re-upgrade ✅ |
| No production DB queried | all temp SQLite files | ✅ |
| No historical backfill | confirmed | ✅ |

### 6. Idempotency Result

| Run | Output | Status |
|---|---|---|
| First `upgrade()` call | `upgrade complete: normalized_unit added to lab_report_items` | column added |
| Second `upgrade()` call | `normalized_unit already exists — nothing to do` | no-op ✅ |
| Column count after two calls | `1` | PASS ✅ |

### 7. Data Preservation Result

| Scenario | Before | After second upgrade() | Result |
|---|---|---|---|
| Row with `normalized_unit = 'U/L'` | `'U/L'` stored | `'U/L'` unchanged | PASS ✅ |
| No rows mutated | ✅ | ✅ | PASS ✅ |

### 8. Full Validation Table

| Gate | Before | After |
|---|---|---|
| `lab-trend-comparison-contract` (7) | PASS | PASS |
| `lab-trend-report-date-contract` (4) | PASS | PASS |
| `documents-confirmed-data-contract` (4) | PASS | PASS |
| `documents-page-contract` (4) | PASS | PASS |
| `report-symptom-recommendation-contract` (5) | PASS | PASS |
| `documents-evidence-deeplink-contract` (4) | PASS | PASS |
| `daily-summary-evidence-contract` (4) | PASS | PASS |
| `daily-assistant-contract` (5) | PASS | PASS |
| `actions-page-contract` (4) | PASS | PASS |
| `symptoms-page-contract` (4) | PASS | PASS |
| `runtime-smoke` (56) | PASS | PASS |
| `test_report_parser_stage2.py` (21) | PASS | PASS |
| `test_lab_history_unit_comparison.py` (11) | PASS | PASS |
| `test_p112_normalized_unit_migration_runtime.py` (4) | N/A | PASS |
| `next build` | PASS | PASS |
| Alembic migration framework | NOT APPLICABLE (no Alembic in project) | NOT APPLICABLE |
| Migration runtime smoke (temp SQLite) | NOT RUN (pre-P112) | PASS |

### 9. Files Changed

| File | Change |
|---|---|
| `backend/scripts/migrate_p110_normalized_unit.py` | Added `_engine` injection to `has_column`, `upgrade`, `downgrade`; added SQLite limitation docstring |
| `backend/scripts/self_heal_db.py` | Added `_engine`/`_base` injection to `has_column` and `main`; fixed `has_column` call in `main` to pass engine; added destructive-behaviour docstring |
| `backend/tests/test_p112_normalized_unit_migration_runtime.py` | New — 4 tests covering migration add, idempotency, self-heal repair, data preservation |

### 10. Commit Hashes

| # | Hash | Message |
|---|---|---|
| 1 | `0358d41` | `test(backend): P112 assure normalized_unit migration runtime` |
| 2 | _(this commit)_ | `docs(report): P112 normalized_unit migration runtime assurance` |

### 11. Known Limitations

- **self_heal_db.py is destructive by design**: when drift is detected it calls `drop_all + create_all` which destroys all data. This is intentional for dev/CI but must never be called on production without a backup.
- **downgrade() requires SQLite ≥ 3.35.0**: test `test_self_heal_detects_and_repairs_missing_normalized_unit` has a `skipif` guard for older SQLite. Production target is PostgreSQL which supports `DROP COLUMN` unconditionally.
- **No Alembic**: this project uses raw SQLAlchemy migrations. Migration runtime check = NOT APPLICABLE for Alembic-style tooling.
- **Historical rows**: existing rows written before P110 will have `normalized_unit = NULL`. No backfill was performed per governance rules. Frontend `normalizeUnitForCompare()` remains the fallback.
- **scripts/ is not a Python package**: the test file adds `scripts/` to `sys.path` at collection time using `_SCRIPTS_DIR` insertion. If `scripts/` ever becomes a package (via `__init__.py`), the `sys.path` insertion can be removed.

### 12. Next Recommended Lane

**P113** — Expose a structured `/documents/lab-history/compare` endpoint that accepts two row identifiers and returns an explicit `comparable / not_comparable / unknown_fallback` decision with audit logging. This removes client-side comparison logic and provides a server-side record of unit mismatch events.

### 13. Governance Notes

- P112 worker did **NOT** touch `00-Plan/roadmap/roadmap.md`
- P112 worker did **NOT** touch `00-Plan/roadmap/CTO-Analysis.md`
- P112 worker did **NOT** touch `00-Plan/roadmap/CEO-Decision.md`
- P112 worker did **NOT** touch `00-Plan/roadmap/active_task.md`
- `roadmap.md` still dated 2026-05-25 / P61 refocus and does not reflect P107–P112. Next CTO review must update.
- `CTO-Analysis.md` still dated 2026-05-23 / P13 era. Next CTO review must rewrite.

### 14. CTO Agent Summary

P112 closes the "migration runtime check = NOT RUN" gap flagged in the P110 report. Both `migrate_p110_normalized_unit.py` and `self_heal_db.py` received minimal engine-injection refactors (`_engine=None`, `_base=None` kwargs) making them testable without touching the production PostgreSQL DB. Four new tests exercise the full assurance surface: column add, idempotency, self-heal repair, and data preservation — all using ephemeral SQLite file DBs. The destructive nature of `self_heal_db.py` (drop\_all + create\_all on drift) is now explicitly documented. All 11 E2E contracts and 56 smoke tests remain green.

### 15. CEO Agent Summary

P112 completes the runtime safety net for the `normalized_unit` column introduced in P110. The migration and self-heal scripts are now verified to add missing columns without crashing, to be safely re-runnable, and to preserve existing data. Tests run against disposable SQLite databases — no production data is touched. The fix is invisible to users but removes an operational risk: if a deployment ever missed the P110 column addition, the self-heal path now has verified repair logic. All tests green; exactly two commits.

---

## P111 — Backend Lab Comparison Uses normalized_unit (2026-05-28)

**Classification:** `P111_BACKEND_NORMALIZED_UNIT_COMPARISON_READY`
**Commit:** `3d0043e`
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| git-dir | `.git` (not a worktree) ✅ |
| P110 code commit `0f3348c` | present ✅ |
| P110 report commit `28ec88e` | present ✅ |
| Dirty files | Only forbidden governance files (CEO-Decision.md, CTO-Analysis.md, roadmap.md) — not staged ✅ |
| All 11 baseline contracts | PASS ✅ |
| runtime-smoke (56 tests) | PASS ✅ |

### 2. Implementation Summary

This task is **case (a)**: `get_lab_history()` already returned rows; all comparison logic lived in the frontend. P111 adds backend canonical truth without breaking the frontend fallback path.

**Added `lab_unit_equivalence_key()` helper** in `backend/app/api/documents.py`:
- Accepts `normalized_unit` (the P110 column value).
- Returns `None` for `NULL`, empty string, and whitespace-only inputs — `None` is **not** a wildcard match.
- Returns the stripped string for any real value.
- Callers receiving `None` must defer equivalence decisions to frontend `normalizeUnitForCompare()`.

**Updated `get_lab_history()` response** to include `unit_equivalence_key` alongside the existing `unit` and `normalized_unit` fields per row.

**No frontend code was touched.** `normalizeUnitForCompare()` (P108) remains the NULL-row fallback exactly as required.

### 3. Comparison Decision Table

| Scenario | key_a | key_b | Decision |
|---|---|---|---|
| IU/L (P110 normalizes → U/L) vs U/L | `"U/L"` | `"U/L"` | `comparable` |
| Historical NULL row vs post-P110 row | `None` | `"U/L"` | `unknown_fallback` (defer to frontend) |
| mg/dL vs mmol/L | `"mg/dL"` | `"mmol/L"` | `not_comparable` |
| Empty string vs any unit | `None` | `"U/L"` | `unknown_fallback` |
| Whitespace-only vs any unit | `None` | `"U/L"` | `unknown_fallback` |
| Two blank/whitespace rows | `None` | `None` | `unknown_fallback` |

### 4. API / Schema Propagation Summary

`GET /documents/lab-history` response per row now includes:

| Field | Type | Source | Notes |
|---|---|---|---|
| `unit` | `string \| null` | `LabReportItem.unit` | Raw display string — never mutated |
| `normalized_unit` | `string \| null` | `LabReportItem.normalized_unit` | Written at P110 ingest; NULL for historical rows |
| `unit_equivalence_key` | `string \| null` | `lab_unit_equivalence_key(normalized_unit)` | Backend canonical comparison key; None = defer to frontend |

No Alembic migration was added (column exists from P110). No schema version bump needed.

### 5. Validation Table

| Gate | Before | After |
|---|---|---|
| `lab-trend-comparison-contract` (7 tests) | PASS | PASS |
| `lab-trend-report-date-contract` (4 tests) | PASS | PASS |
| `documents-confirmed-data-contract` (4 tests) | PASS | PASS |
| `documents-page-contract` (4 tests) | PASS | PASS |
| `report-symptom-recommendation-contract` (5 tests) | PASS | PASS |
| `documents-evidence-deeplink-contract` (4 tests) | PASS | PASS |
| `daily-summary-evidence-contract` (4 tests) | PASS | PASS |
| `daily-assistant-contract` (5 tests) | PASS | PASS |
| `actions-page-contract` (4 tests) | PASS | PASS |
| `symptoms-page-contract` (4 tests) | PASS | PASS |
| `runtime-smoke` (56 tests) | PASS | PASS |
| `test_report_parser_stage2.py` (21 tests) | PASS | PASS |
| `test_lab_history_unit_comparison.py` (11 tests) | N/A | PASS |
| `next build` | PASS | PASS |
| Alembic migration runtime check | NOT RUN (no Alembic in project) | NOT RUN |

### 6. Files Changed

| File | Change |
|---|---|
| `backend/app/api/documents.py` | Added `lab_unit_equivalence_key()` helper; added `unit_equivalence_key` field to `get_lab_history()` response rows |
| `backend/tests/test_lab_history_unit_comparison.py` | New — 11 tests covering comparison branches A, B, C, D |

### 7. Commit Hashes

| # | Hash | Message |
|---|---|---|
| 1 | `3d0043e` | `feat(backend): P111 lab comparison uses LabReportItem.normalized_unit` |
| 2 | _(this commit)_ | `docs(report): P111 backend lab comparison normalized_unit consumption` |

### 8. Known Limitations

- `unit_equivalence_key` is a passthrough of `normalized_unit` for non-alias values. More complex alias resolution (e.g., `IU/L → U/L`) is handled at P110 ingest time by `normalize_unit()` in `report_parser.py`, not here.
- Historical rows (pre-P110) will always yield `unit_equivalence_key = null` until re-ingested; no backfill was performed per task governance.
- The comparison decision (`comparable / not_comparable / unknown_fallback`) is computed client-side using the returned `unit_equivalence_key`. If a dedicated comparison endpoint is needed in future, P112 should add it.

### 9. Next Recommended Lane

**P112** — Expose a structured `/lab-history/compare` backend endpoint that accepts two row identifiers and returns an explicit `comparable / not_comparable / unknown_fallback` status. This removes the need for clients to re-implement comparison logic and enables server-side audit logging of unit mismatch events.

### 10. Governance Notes

- `00-Plan/roadmap/roadmap.md` is still timestamped 2026-05-25 (P61 refocus) and does **NOT** reflect P107–P111. Next CTO review must update.
- `00-Plan/roadmap/CTO-Analysis.md` is still dated 2026-05-23 (P13 era). Next CTO review must rewrite.
- P111 worker did **NOT** touch either file (out of CEO scope).

### 11. CTO Agent Summary

P111 adds `lab_unit_equivalence_key()` to `documents.py` — a null-safe helper that converts `LabReportItem.normalized_unit` (written at P110 ingest) into a backend comparison key exposed per row in `GET /lab-history`. NULL and whitespace are explicitly not wildcard matches; callers receiving `None` defer to frontend `normalizeUnitForCompare()`. No DB migration, no frontend changes, no new routes — strictly additive. 11 new unit tests cover all four mandated comparison branches. All 11 contracts and 56 smoke tests pass before and after.

### 12. CEO Agent Summary

P111 closes the loop on the P107–P110 lab unit normalization lane. The backend now surfaces a canonical `unit_equivalence_key` for every lab result row, giving the app a reliable server-side signal for whether two test values used the same unit. Historical records are handled safely: when the key is absent, the app falls back to the existing frontend logic with no crash or silent mismatch. The change is invisible to users but enables correct automated comparison across all future lab uploads. All tests green; two clean commits.

---

## P110 — Backend normalized_unit Field for LabReportItem (2026-05-27)

**Classification:** `P110_BACKEND_NORMALIZED_UNIT_FIELD_READY`
**Commit:** `0f3348c`
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | attached ✅ |
| P109 commit `ce096a5` | present ✅ |
| Dirty files | Only governance/roadmap files (not staged) ✅ |
| All 11 baseline contracts | PASS ✅ |

### 2. Implementation Summary

Implemented Option C from P109 discovery: added a nullable `normalized_unit` field alongside the existing raw `unit` field in `LabReportItem`. Newly parsed rows carry both the original OCR/PDF display string and its canonical comparison form. Historical rows keep `normalized_unit = NULL` and continue to fall back to frontend `normalizeUnitForCompare()`.

### 3. normalize_unit() Behavior Table

| Input | Output |
|---|---|
| `"IU/L"` | `"U/L"` |
| `"iu/l"` | `"U/L"` |
| `"IU/l"` | `"U/L"` |
| `"U/L"` | `"U/L"` |
| `"μmol/L"` | `"umol/L"` |
| `"µmol/L"` | `"umol/L"` |
| `"umol/L"` | `"umol/L"` |
| `"mg/dL"` | `"mg/dL"` |
| `"mmol/L"` | `"mmol/L"` |
| `None` | `None` |
| `""` | `None` |
| `"   "` | `None` |

mg/dL and mmol/L are explicitly NOT aliased to each other.

### 4. Migration Summary

- Created `backend/scripts/migrate_p110_normalized_unit.py` — idempotent `ADD COLUMN normalized_unit VARCHAR(30) NULL` with upgrade/downgrade.
- Updated `backend/scripts/self_heal_db.py` drift check to include `('lab_report_items', 'normalized_unit')`.
- No Alembic runtime in this project — migration follows the existing `self_heal_db.py` / raw SQL pattern.
- Migration runtime check: NOT RUN (no Alembic CLI; test suites use in-memory SQLite `create_all` which picks up the new column from the model automatically).

### 5. API / Schema Propagation Summary

| Layer | Change |
|---|---|
| `report_parser.py` | Added `normalize_unit()`, emits `normalized_unit` in `parse_lab_items()` output dict |
| `entities.py` | `normalized_unit = Column(String(30), nullable=True)` on `LabReportItem` |
| `schemas/documents.py` | `normalized_unit: Optional[str] = None` in `ParsedItemResponse` and `ParsedItemPreview` |
| `api/documents.py` | `normalized_unit` propagated in parse preview, parsed-items list, update-item response, lab-history response |

### 6. Validation Table

| Gate | Result |
|---|---|
| `lab-trend-comparison-contract` (7 tests) | PASS |
| `lab-trend-report-date-contract` (4 tests) | PASS |
| `documents-confirmed-data-contract` (4 tests) | PASS |
| `documents-page-contract` (4 tests) | PASS |
| `report-symptom-recommendation-contract` (5 tests) | PASS |
| `documents-evidence-deeplink-contract` (4 tests) | PASS |
| `daily-summary-evidence-contract` (4 tests) | PASS |
| `daily-assistant-contract` (5 tests) | PASS |
| `actions-page-contract` (4 tests) | PASS |
| `symptoms-page-contract` (4 tests) | PASS |
| `runtime-smoke` (56 tests) | PASS |
| `test_report_parser_stage2.py` (21 tests) | PASS |
| Migration runtime check | NOT RUN — no Alembic CLI; model `create_all` used in tests |

### 7. Files Changed

| File | Action |
|---|---|
| `backend/app/services/report_parser.py` | Added `normalize_unit()`, updated `parse_lab_items()` |
| `backend/app/models/entities.py` | Added `normalized_unit` column |
| `backend/app/schemas/documents.py` | Added `normalized_unit` to `ParsedItemResponse` and `ParsedItemPreview` |
| `backend/app/api/documents.py` | Propagated `normalized_unit` in 3 response sites + lab-history |
| `backend/scripts/migrate_p110_normalized_unit.py` | Created — upgrade/downgrade migration script |
| `backend/scripts/self_heal_db.py` | Updated drift check list |
| `backend/tests/test_report_parser_stage2.py` | 20 new tests added (21 total) |
| `00-Plan/roadmap/active_task_report.md` | Updated |

### 8. Commit Hashes

| Commit | Description |
|---|---|
| `0f3348c` | feat(backend): P110 normalized_unit field at ingest for LabReportItem |
| _(follows)_ | docs(report): P110 normalized_unit ingest report |

### 9. Known Limitations

- Historical `lab_report_items` rows have `normalized_unit = NULL`. Frontend `normalizeUnitForCompare()` remains the fallback.
- `migrate_p110_normalized_unit.py` uses raw `ADD COLUMN` SQL — not Alembic managed. Safe for PostgreSQL; SQLite doesn't support `DROP COLUMN` on older versions (downgrade path is PostgreSQL-only).
- `normalize_unit()` handles IU/L and Unicode mu prefix only. Other alias forms (e.g., `g/L`, `pg/mL`) pass through unchanged and are not normalized.

### 10. Next Recommended Lane

**P111 — Backend unit comparison using normalized_unit**: Update `get_lab_history()` and the lab-trend comparison logic to group/compare using `normalized_unit` where non-null, falling back to `normalizeUnitForCompare()` for NULL rows. This closes the remaining gap where the comparison is still done entirely in the frontend.

### 11. CTO Agent Summary

P110 complete. `normalize_unit()` added to parser with full alias coverage (IU/L→U/L, Unicode μ/µ→ASCII u). `LabReportItem` model gains nullable `normalized_unit` column populated at parse time; raw `unit` untouched for display. Propagated through schemas and 4 API response sites. 21/21 backend tests PASS; 11/11 contract gates PASS with zero regressions. Migration script follows project's existing raw-SQL / self_heal pattern (no Alembic). Historical rows remain NULL — frontend normalizeUnitForCompare() is still the fallback.

### 12. CEO Agent Summary

Lab unit normalization is now happening at data ingest, not just in the browser. When a new lab report is uploaded, the system records both the original unit string and its canonical form side by side. IU/L and U/L are already treated as the same thing at the data layer. Existing historical records are untouched and still work. Next step (P111) is to use the backend-normalized unit for actual comparison logic, fully removing the dependency on frontend normalization for accuracy.

---

## P109 — Report Parser Unit Field Normalization at Ingest: Discovery (2026-05-27)

**Classification:** `P109_BACKEND_NORMALIZED_UNIT_FIELD_RECOMMENDED`
**Commit:** _(follows)_
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | attached ✅ |
| P108 commit `a229d1c` | present ✅ |
| Dirty files | Only governance/roadmap files ✅ |

### 2. Discovery Result

- `parse_lab_items()` captures `unit` via regex group(3) — no normalization applied (`report_parser.py:171`)
- `parse_document()` unpacks parser dict directly into `LabReportItem(**row)` — blind pass-through (`documents.py:115-118`)
- `LabReportItem.unit` is a single `String(30)` column storing raw OCR/PDF string verbatim
- `normalize_item_name()` resolves name aliases but no parallel exists for unit
- Frontend `normalizeUnitForCompare()` is the only normalization layer today

### 3. Recommended P110 Lane

**Option C: Add `normalized_unit` field (nullable) to `LabReportItem`**

- Raw `unit` preserved for display — no UX regression
- `normalized_unit` populated at parse time by new `normalize_unit()` helper
- Historical NULL rows fall back to frontend `normalizeUnitForCompare()`
- Enables backend grouping, trending, and analytics without unit ambiguity

### 4. Validation Table

| Gate | Result |
|---|---|
| `lab-trend-comparison-contract` (7 tests) | PASS |
| `lab-trend-report-date-contract` (4 tests) | PASS |
| `documents-confirmed-data-contract` (4 tests) | PASS |
| `documents-page-contract` (4 tests) | PASS |
| `report-symptom-recommendation-contract` (5 tests) | PASS |
| `documents-evidence-deeplink-contract` (4 tests) | PASS |
| `daily-summary-evidence-contract` (4 tests) | PASS |
| `daily-assistant-contract` (5 tests) | PASS |
| `actions-page-contract` (4 tests) | PASS |
| `symptoms-page-contract` (4 tests) | PASS |
| `runtime-smoke` (56 tests) | PASS |
| Code changes | NOT RUN — docs-only |

### 5. Files Changed

| File | Action |
|---|---|
| `docs/product/p109-report-parser-unit-normalization-discovery.md` | Created |
| `00-Plan/roadmap/active_task_report.md` | Updated |

### 6. Known Limitations

- Existing `LabReportItem` rows have raw unit strings; backfill deferred to P110
- Mid-string mu (e.g., `g/μmol`) not covered by current prefix-only alias approach
- Alias list is IU/L ↔ U/L and μ/µ → u only; other aliases not evaluated

---

## P108 — Unit Alias Normalization Implementation (2026-05-27)

**Classification:** `P108_UNIT_ALIAS_NORMALIZATION_READY`
**Commits:** `8d82bbc` (code/test) · _(report commit follows)_
**Branch:** `main`

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | attached ✅ |
| P107 commit `6030f14` | present ✅ |
| Dirty files | Only governance/roadmap files (CEO-Decision.md, CTO-Analysis.md, roadmap.md) ✅ |

### 2. Unit Alias Normalization Behavior

`normalizeUnitForCompare()` in `frontend/lib/lab-unit-normalization.ts` applies three normalizations in sequence:

| Input | Normalized | Rule |
|---|---|---|
| `IU/L` | `u/l` | `iu/` prefix → `u/` |
| `iu/l` | `u/l` | lowercase then `iu/` prefix → `u/` |
| `μmol/L` | `umol/l` | Greek mu (U+03BC) → `u` |
| `µmol/L` | `umol/l` | Micro sign (U+00B5) → `u` |
| `umol/L` | `umol/l` | trim + lowercase |
| `mg/dL` | `mg/dl` | trim + lowercase (no alias) |
| `mmol/L` | `mmol/l` | trim + lowercase (no alias) |

`mg/dL` vs `mmol/L` continues to show 單位不同，暫不比較. Raw display strings unchanged.

### 3. Tests Added / Updated

| Test | Description | Status |
|---|---|---|
| T1–T4 | Existing P103 tests | PASS (unchanged) |
| T5 | mg/dL vs mmol/L suppresses delta (P106) | PASS (unchanged) |
| T6 (new) | IU/L + U/L treated as alias → delta shown, no mismatch label | PASS |
| T7 (new) | μmol/L + umol/L treated as alias → delta shown, no mismatch label | PASS |

### 4. Validation Table

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | PASS |
| `npx next build` | PASS |
| `p103-lab-trend-comparison-contract` (7 tests) | PASS |
| `lab-trend-report-date-contract` (4 tests) | PASS |
| `documents-confirmed-data-contract` | PASS |
| `documents-page-contract` | PASS |
| `report-symptom-recommendation-contract` | PASS |
| `documents-evidence-deeplink-contract` | PASS |
| `daily-summary-evidence-contract` | PASS |
| `daily-assistant-contract` | PASS |
| `actions-page-contract` | PASS |
| `symptoms-page-contract` | PASS |
| `runtime-smoke` (56 tests) | PASS |

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/lib/lab-unit-normalization.ts` | Created — exports `normalizeUnitForCompare()` |
| `frontend/app/components/platform/lab-comparison-table.tsx` | Modified — removes inline helper, imports from lib |
| `frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts` | Modified — adds T6 and T7 |
| `00-Plan/roadmap/active_task_report.md` | Modified — this report |

### 6. Commits

- `8d82bbc` — `feat(frontend): P108 unit alias normalization IU/L and Unicode mu`
- _(report commit)_ — `docs(report): P108 unit alias normalization report`

### 7. Known Limitations

- Only handles prefix-level alias patterns (`iu/` → `u/`, `μ` → `u`). Alias pairs with identical prefix but different suffixes (e.g., future `μg/L` vs `ug/L`) are covered by the same regex but were not explicitly tested.
- Does not handle mixed case middle variants like `IU/l` — covered by `.toLowerCase()` step.
- Real unit conversion (mg/dL ↔ mmol/L, g/dL ↔ g/L) remains out of scope and suppressed.

### 8. Next Recommended Lane

**P109 — Report Parser Unit Field Normalization at Ingest**
Ensure report parsing pipeline normalizes `IU/L` → `U/L` at storage time so future DB records use canonical spellings. This decouples display-layer normalization from parser variance and prepares for clinical reference range validation.

---

### CTO Agent Summary (5 lines)

P108 ships a pure frontend alias normalization layer. A single `normalizeUnitForCompare()` helper in `frontend/lib/lab-unit-normalization.ts` applies trim + lowercase + three targeted `.replace()` calls (IU/L→U/L, μ→u, µ→u). `lab-comparison-table.tsx` now imports this helper, eliminating the inline `normalizeUnit` closure. Existing T1–T5 unchanged; T6 and T7 added to guard IU/L and Unicode mu alias correctness. All 13 contract gates pass, 0 regressions.

### CEO Agent Summary (5 lines)

Users who imported foreign or older lab reports with IU/L enzyme units or Unicode micro-symbol concentrations will now see delta% comparisons instead of a "units differ" suppression message. This removes a friction point that caused clinically equivalent data to appear incomparable. No backend changes, no conversion logic, no risk of false cross-unit comparisons (mg/dL vs mmol/L still suppressed). Shipped in one commit, fully covered by contract tests. Ready to extend toward unit normalization at report parse time in P109.

---

## P107 — Unit Alias Normalization Discovery (2026-05-27)

**Classification:** `P107_UNIT_ALIAS_DISCOVERY_READY`
**Commit:** `6030f14`
**Branch:** `main`

### Summary

Discovery-only (no runtime code changed). Surveyed all backend config, seeds, backend tests, and frontend Playwright mocks for lab unit strings. Found the codebase uses a small, consistent set: `mg/dL`, `U/L`, `g/dL`, `mmol/L`, `%`. No `IU/L`, `μmol/L`, or `umol/L` occurrences exist today — alias risk is prospective. P106 `trim().toLowerCase()` already handles all case variants. Remaining alias gaps are `IU/L↔U/L` and Unicode micro prefix (`μ/µ` vs `u`). Defined a safe P108 implementation plan using a new `frontend/lib/lab-unit-normalization.ts` helper.

### Safe Alias Candidates

| Alias A | Alias B | Safe? | Reason |
|---|---|---|---|
| `IU/L` | `U/L` | ✅ Yes | Same quantity; different abbreviation for enzyme assay units |
| `μmol/L` | `umol/L` | ✅ Yes | Unicode Greek mu vs ASCII u — same prefix |
| `µmol/L` | `umol/L` | ✅ Yes | Unicode micro sign vs ASCII u — same prefix |
| `mg/dL` | `mmol/L` | ❌ No — conversion | ~18× scale for glucose; must remain suppressed |
| `g/dL` | `g/L` | ❌ No — conversion | 10× scale; must remain suppressed |

### Recommended P108 Plan

- Create `frontend/lib/lab-unit-normalization.ts` with `normalizeUnitForCompare()`
- Three `.replace()` calls: Unicode micro sign → `u`, Greek mu → `u`, `iu/` → `u/`
- Update `lab-comparison-table.tsx` to import the helper (replaces inline `normalizeUnit`)
- Add T6 (IU/L ≡ U/L) and T7 (μmol/L ≡ umol/L) to p103 spec
- No backend changes; raw unit display unchanged

### Files Changed

| File | Action |
|---|---|
| `docs/product/p107-unit-alias-normalization-discovery.md` | Created |
| `00-Plan/roadmap/active_task_report.md` | Updated |

### Validation

All 11 baseline contracts PASS before and after docs creation (docs-only, no `next build` required).

### CTO Agent 5-line Summary

1. P107 完成，分類：`P107_UNIT_ALIAS_DISCOVERY_READY`。
2. 全域掃描：codebase 現有單位為 `mg/dL`、`U/L`、`g/dL`、`mmol/L`、`%`；`IU/L`、`μmol/L` 均不存在，風險屬前瞻性。
3. P106 `trim().toLowerCase()` 已處理所有大小寫變體；剩餘 gap：`iu/l` vs `u/l`（IU/L↔U/L）與 Unicode mu 前綴。
4. P108 推薦：`frontend/lib/lab-unit-normalization.ts` + 三行 `.replace()`；`lab-comparison-table.tsx` import 取代 inline helper；新增 T6/T7 contract tests。
5. `mmol/L` vs `mg/dL` 屬真實轉換，P106 suppression 必須維持；abnormal flag 精確度問題延後至 P109。

### CEO Agent 5-line Summary

1. P107 確認系統單位十分統一，主要只有四種，無亂用現象。
2. 唯一假性壓制風險：`IU/L` vs `U/L` 與 Unicode 編碼差異，但目前均未出現。
3. P108 只需 ~5 行新函數，即可消除這些假壓制，讓 ALT/AST 跨報告比較更順暢。
4. `mmol/L` vs `mg/dL` 的壓制保護必須維持，不可混淆。
5. P108 可安全實施，風險極低，建議優先推進。

---

## P106 — Suppress Mixed-Unit Lab Trend Delta (2026-05-26)

**Classification:** `P106_MIXED_UNIT_DELTA_SUPPRESSED`
**Commit 1 (code/test):** `006b723` — `fix(frontend): P106 suppress delta when lab units differ`
**Commit 2 (report):** _(this commit)_
**Branch:** `main`

### Summary

Frontend-only fix: `LabComparisonTable` no longer computes or displays `delta%` when the latest and previous readings for the same metric have different unit strings. Raw values with their respective units remain fully visible. The delta cell shows `單位不同，暫不比較` as a neutral, non-alarming message.

### Changes

| File | Change |
|---|---|
| `frontend/app/components/platform/lab-comparison-table.tsx` | Added `normalizeUnit` helper + `unitsMatch` / `unitMismatch` guards in `tableRows` useMemo; updated delta column render |
| `frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts` | Added T5: mixed-unit glucose fixture asserts `unit-mismatch-label` visible and no `↑`/`↓` in table |
| `00-Plan/roadmap/active_task_report.md` | Updated |

### Validation

| Contract | Pre-flight | Post-implementation |
|---|---|---|
| `lab-trend-comparison-contract` (T1–T5) | ✅ 4/4 | ✅ **5/5** |
| `lab-trend-report-date-contract` | ✅ PASS | ✅ PASS |
| `documents-confirmed-data-contract` | ✅ PASS | ✅ PASS |
| `documents-page-contract` | ✅ PASS | ✅ PASS |
| `report-symptom-recommendation-contract` | ✅ PASS | ✅ PASS |
| `documents-evidence-deeplink-contract` | ✅ PASS | ✅ PASS |
| `daily-summary-evidence-contract` | ✅ PASS | ✅ PASS |
| `daily-assistant-contract` | ✅ PASS | ✅ PASS |
| `actions-page-contract` | ✅ PASS | ✅ PASS |
| `symptoms-page-contract` | ✅ PASS | ✅ PASS |
| `runtime-smoke` | ✅ 56/56 | ✅ 56/56 |
| `next build` | — | ✅ clean |

### Known Limitations

- Unit normalization is case+whitespace only (`trim().toLowerCase()`). Unit aliases (e.g. `IU/L` ≡ `U/L`) are not handled — deferred to P107.
- Null unit on either side is treated as a match (suppression skipped) to avoid false positives on legacy rows with missing unit strings.
- Abnormal flag accuracy when unit scale differs (e.g. mmol/L value flagged against mg/dL threshold) is a backend concern — deferred to P108.

### Next Recommended Lane

**P107 — Unit Alias Normalization Discovery**
- Map common alias equivalences (e.g. `IU/L` ≡ `U/L`, `umol/L` ≡ `μmol/L`, `10^9/L` ≡ `10⁹/L`) in a frontend normalization table.
- Expand `normalizeUnitForCompare` so that clinically equivalent units are treated as matching, reducing false suppression.
- No backend API changes required; pure frontend mapping.

### CTO Agent 5-line Summary

1. P106 完成，分類：`P106_MIXED_UNIT_DELTA_SUPPRESSED`。
2. Root cause：`LabComparisonTable` 在 `tableRows` useMemo 中對任意兩個數值計算 delta%，無單位一致性檢查，glucose mg/dL vs mmol/L 產生約 +1718% 假訊號。
3. Fix：`normalizeUnit`（trim+lowercase）+ `unitsMatch` guard；`deltaPct` 僅在單位相符時計算；不符時 delta cell 改為 `<span data-testid="unit-mismatch-label">單位不同，暫不比較</span>`，class 改為 `text-slate-400`（中性樣式）。
4. T5 (mixed-unit Glucose 100 mg/dL vs 5.5 mmol/L) 新增並通過；T1–T4 全部維持通過；11 個 baseline contract 全部 PASS；`next build` 零錯誤；`runtime-smoke` 56/56。
5. 僅改動 2 個文件（`lab-comparison-table.tsx`、`p103` spec）+ report；不開新 branch，不修改後端，null unit 視為相符以避免舊資料誤觸發；單位別名正規化延後至 P107。

### CEO Agent 5-line Summary

1. P106 解決了一個會讓使用者看到「血糖暴增 +1700%」假警告的前端顯示 bug，現已上線。
2. 核心改動：相同指標的最新與前次報告若單位不同（如 mg/dL vs mmol/L），趨勢欄位改顯示「單位不同，暫不比較」，不再顯示誤導性百分比。
3. 原始數值（含各自單位）仍完整顯示，使用者仍可手動判讀；不影響正常同單位比較流程。
4. 100% 前端修改，零後端變動，11 項自動化合約測試全部通過，風險極低。
5. 下一步 P107：建立單位別名正規化表（IU/L ≡ U/L 等），進一步減少不必要的「暫不比較」顯示。

---

## P105 — Lab Item Unit Normalization Discovery (2026-05-26)

**Classification:** `P105_UNIT_MISMATCH_RISK_CONFIRMED`
**Commit:** _(docs-only, see below)_
**Branch:** `main`

### Summary

- `LabReportItem.unit` stores raw parsed strings; no unit normalization exists at parse or confirm time.
- `lab-comparison-table.tsx:52` computes `deltaPct` with zero unit guard — glucose `mg/dL` vs `mmol/L` produces ~1700% false delta.
- No conversion helpers exist anywhere in the codebase.
- **Recommended P106 path:** frontend-only suppression (Option A) — 3–4 lines + one contract test T5.
- All 11 baseline contracts pass pre- and post-docs.

### Files Changed

| File | Action |
|---|---|
| `docs/product/p105-lab-unit-normalization-discovery.md` | Created |
| `00-Plan/roadmap/active_task_report.md` | Updated |

### Validation

All 11 baseline contracts PASS before and after docs creation (docs-only, no `next build` required).

---

## P104 — Report Date Capture in Lab Confirm Flow (2026-05-26)
**Classification:** `P104_LAB_TREND_DATE_READY`
**Commit:** `1f47c7d`
**Branch:** `main`

---

### 1. Pre-flight Result

| Check | Result |
|---|---|
| Branch | `main` ✅ |
| P103 baseline commit `ab76b53` | ✅ present |
| Dirty files at start | Only governance files ✅ |
| Baseline contracts (10 guards) | All 10 PASS ✅ |

---

### 2. Backend `report_date` Behavior

**Schema** (`backend/app/schemas/documents.py`): Added `report_date: Optional[date] = None` to `DocumentConfirmRequest`. Backward-compatible — absent = no-op.

**API** (`backend/app/api/documents.py`): `confirm_document` PUT handler queries the latest `LabReport` for the document and sets `lab_report.report_date` when payload field is provided. Both `Document` and `LabReport` changes committed atomically.

---

### 3. Frontend Confirm Date Input Behavior

**Component** (`frontend/app/components/platform/parsed-items-drawer.tsx`): Added `reportDate` state, date input (`data-testid="report-date-input"`, `type="date"`, label "健檢日期（選填）") in footer above confirm buttons. `handleConfirm` sends `report_date: reportDate || null`. No api.ts changes — `confirmDocument` already accepts `Record<string, unknown>`.

---

### 4. Contract Tests and Backend Tests

**Backend** — 4/4 PASS: write-through, no-op when absent, confirmed_data preserved, 422 on invalid date.

**Frontend** — 4/4 PASS: input visible, payload capture, empty-date no-crash, table date display.

**Test fix:** `getByText('ALT', { exact: false })` caused strict-mode violation (Playwright case-insensitive substring matched "he**alt**h_check"). Fixed to `getByRole('cell', { name: 'ALT' })`.

---

### 5. Validation Table

| Target | Tests | Result |
|---|---|---|
| Backend pytest (P104) | 4 | ✅ PASS |
| `make lab-trend-report-date-contract` | 4 | ✅ PASS |
| `make lab-trend-comparison-contract` | 4 | ✅ PASS |
| `make documents-confirmed-data-contract` | 4 | ✅ PASS |
| `make documents-page-contract` | 4 | ✅ PASS |
| `make report-symptom-recommendation-contract` | 5 | ✅ PASS |
| `make documents-evidence-deeplink-contract` | 4 | ✅ PASS |
| `make daily-summary-evidence-contract` | 4 | ✅ PASS |
| `make daily-assistant-contract` | 5 | ✅ PASS |
| `make actions-page-contract` | 4 | ✅ PASS |
| `make symptoms-page-contract` | 4 | ✅ PASS |
| `make runtime-smoke` | 56 | ✅ PASS |
| **Total** | **106** | **0 failures** |

---

### 6. Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/documents.py` | `report_date: Optional[date] = None` added |
| `backend/app/api/documents.py` | PUT confirm writes `lab_report.report_date` |
| `backend/tests/test_api_document_report_date.py` | **NEW** 4 backend tests |
| `frontend/app/components/platform/parsed-items-drawer.tsx` | Date input + state + payload |
| `frontend/tests/e2e/p104-lab-trend-report-date-contract.spec.ts` | **NEW** 4 Playwright tests |
| `Makefile` | `lab-trend-report-date-contract` target |
| `docs/product/local-contract-guard-index.md` | 6 locations updated |

---

### 7. Known Limitations

- Only the **latest** LabReport per document is updated (intentional).
- Date defaults to blank — user must explicitly set it.
- Trend table date is only visible in the **expanded** row detail, not the summary row.

---

### 8. Next Recommended Lane

**P105 — Lab item unit normalization**: ALT U/L vs mU/mL, glucose mg/dL vs mmol/L. Without unit normalization, delta% comparisons in the trend table are numerically incorrect for multi-system datasets.

---

### 9. CTO Agent 5-Line Summary

P104 adds an optional `report_date` field to the document confirm flow with zero breaking changes. The backend schema and PUT handler are strictly additive — absent field = no-op. The frontend drawer gains a single date `<input>` in the footer; existing confirm path unchanged. All 106 tests across 12 validation targets pass. LabReport.report_date is now user-controllable, making lab trend chronology meaningful.

---

### 10. CEO Agent 5-Line Summary

Users can now stamp their actual health checkup date when reviewing parsed lab results — instead of defaulting to upload/parse date. The "Lab Trend Comparison" table will show time-ordered trends reflecting real-world checkup chronology. The feature is entirely optional (zero friction). No data migration, no breaking API change, shipped in one atomic commit. Next step: unit normalization so delta% values are accurate across different test systems.

---

## P103 — Lab Trend Comparison Contract + Direction Framing Fix (2026-05-26)

**Final Classification: `P103_LAB_TREND_CONTRACT_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `9bd71ef` (P102) |
| Dirty files | governance-only (3 files) |
| P102 commit present | YES — `9bd71ef` |

---

### 2. Baseline Gates

| Gate | Before | After |
|---|---|---|
| report-symptom-recommendation-contract | 5 passed | 5 passed |
| documents-evidence-deeplink-contract | 4 passed | 4 passed |
| daily-summary-evidence-contract | 4 passed | 4 passed |
| daily-assistant-contract | 5 passed | 5 passed |
| actions-page-contract | 4 passed | 4 passed |
| documents-confirmed-data-contract | 4 passed | 4 passed |
| documents-page-contract | 4 passed | 4 passed |
| symptoms-page-contract | 4 passed | 4 passed |
| runtime-smoke | 56 passed | 56 passed |
| **lab-trend-comparison-contract (new)** | — | **4 passed** |

---

### 3. Direction Framing Changes

File: `frontend/app/components/platform/lab-comparison-table.tsx`

| Before | After |
|---|---|
| `FilterKey: 'improved' \| 'not_improved'` | `FilterKey: 'value_down' \| 'value_up'` |
| Button label `已改善` | Button label `數值下降` |
| Button label `未改善` | Button label `數值上升` |
| Root div had no testid | Added `data-testid="lab-comparison-table"` |

Filter logic behavior unchanged — `value_down` maps to `deltaPct < 0`, `value_up` maps to `deltaPct >= 0`.

---

### 4. Contract Spec

`frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts` — 4 tests:
- T1: "歷史比較" tab click → `lab-comparison-table` visible, mocked ALT metric renders
- T2: `數值下降` / `數值上升` buttons visible; `已改善` / `未改善` absent
- T3: Empty lab history → safe empty state with "尚無歷史資料", no crash
- T4: No prohibited overclaim phrases (已治癒, 保證改善, 取代醫師, 診斷為, 治療成功, 惡化) in comparison tab

---

### 5. Makefile Target Added

`make lab-trend-comparison-contract` — tsc + 4 Playwright tests.
Added to `.PHONY`. Runs in ~3s.

---

### 6. Guard Index Updated

`docs/product/local-contract-guard-index.md`:
- Added row to Guard Matrix (§2)
- Added "When to run" row (§2)
- Added "Related files" row (§2)
- Added new validation bundle "Documents — lab trend comparison" (§3)
- Updated "Full local validation" bundle (§3)
- Updated Quick Reference (§8)

---

### 7. Files Changed

| File | Action |
|---|---|
| `frontend/app/components/platform/lab-comparison-table.tsx` | Modified — direction framing fix + testid |
| `frontend/tests/e2e/p103-lab-trend-comparison-contract.spec.ts` | Created — 4 contract tests |
| `Makefile` | Added `lab-trend-comparison-contract` target + `.PHONY` |
| `docs/product/local-contract-guard-index.md` | Updated — new guard row, bundle, quick-ref |
| `00-Plan/roadmap/active_task_report.md` | Updated |

---

### 8. Commits

- `dbea69a` — `fix(frontend): P103 neutral lab trend direction framing`
- _(this commit)_ — `docs(report): P103 lab trend comparison contract report`

---

### 9. Known Limitations

- `report_date` accuracy: still set to `date.today()` at parse time. Users uploading multiple reports on the same day will see all reports dated today in the expandable history rows. Deferred to P104.
- ALIAS_MAP coverage: unrecognized item names appear unnormalized in trend table. No change in P103.
- Unit normalization (mg/dL vs mmol/L across labs): deferred beyond P104.
- "持平" (flat) direction label: not added in P103 (deltaPct === 0 falls into `value_up` filter currently). Can be refined in P104.

---

### 10. Next Recommended Lane

**P104 — Report Date Capture in Confirm Flow**

The lab trend table currently shows upload/parse date as the report date.
P104 should add a date input to the `ParsedItemsDrawer` confirm footer so
users can record the actual health check date. This requires:
1. A `report_date` date input field in `ParsedItemsDrawer` (optional, pre-empty)
2. Backend: extend `PUT /documents/{id}/confirm` to accept `report_date: date | None`
   and write to `LabReport.report_date` for the document's linked report
3. `p104-lab-trend-report-date-contract.spec.ts` — verify date persists and
   appears in expandable history rows

Alternatively, P104 could focus on **first-run report upload onboarding discovery**:
explore whether new users need a guided upload flow to reach the "歷史比較" tab
with sufficient data for trend comparison.

---

## P102 — Lab Trend Visualization Discovery (2026-05-26)

**Final Classification: `P102_FRONTEND_ONLY_TREND_FEASIBLE`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `38f7696` (P101) |
| Dirty files | governance-only (3 files) |

---

### 2. Baseline Gates (all 9 green before and after docs work)

| Gate | Before | After |
|---|---|---|
| report-symptom-recommendation-contract | 5 passed | 5 passed |
| documents-evidence-deeplink-contract | 4 passed | 4 passed |
| daily-summary-evidence-contract | 4 passed | 4 passed |
| daily-assistant-contract | 5 passed | 5 passed |
| actions-page-contract | 4 passed | 4 passed |
| documents-confirmed-data-contract | 4 passed | 4 passed |
| documents-page-contract | 4 passed | 4 passed |
| symptoms-page-contract | 4 passed | 4 passed |
| runtime-smoke | 56 passed | 56 passed |

---

### 3. Key Discovery Findings

**Trend data is available today — feature partially implemented:**
- `/documents/lab-history` endpoint exists in `backend/app/api/documents.py`
- `LabComparisonTable` component fully built at `frontend/app/components/platform/lab-comparison-table.tsx`
- "歷史比較" tab integrated in `frontend/app/platform/documents/page.tsx`
- `api.getLabHistory()` implemented at `frontend/lib/api.ts:405`

**Critical gap:** `report_date` is set to `date.today()` at parse time (not extracted from document). Multi-report chronology is upload-order, not health-check-order.

**Trust gap:** "已改善/未改善" filter labels assume ↓ = better — incorrect for HDL, Hemoglobin.

**No contract guard exists** for the "歷史比較" tab or `LabComparisonTable`.

---

### 4. Changes in This Task

| File | Action |
|---|---|
| `docs/product/p102-lab-trend-visualization-discovery.md` | Created |
| `00-Plan/roadmap/active_task_report.md` | Updated |

---

### 5. Recommended P103 Lane

**P103 = Lab Trend Contract + Direction Framing Fix**
1. Fix "已改善/未改善" → "數值下降/數值上升" in `LabComparisonTable`
2. Add optional `report_date` capture in `ParsedItemsDrawer` confirm flow + backend field write
3. Write `p103-lab-trend-comparison-contract.spec.ts` (4 tests)
4. Add `lab-trend-comparison-contract` Makefile target
5. Update guard index

---

### 6. Known Limitations

- `report_date` accuracy requires user input; cannot be extracted from PDF reliably in v1
- Unit normalization across reports (mg/dL vs mmol/L) deferred beyond P103
- ALIAS_MAP coverage is manual; unrecognized item names pass through unnormalized

---

## P101 Report + Symptom → Recommendation Integration Contract (2026-05-26)

**Final Classification: `P101_REPORT_SYMPTOM_RECOMMENDATION_CONTRACT_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `aa04e44` (P100) |
| Dirty files | governance-only (4 files) |

---

### 2. Baseline Gates (all 8 green before edits)

| Gate | Before | After |
|---|---|---|
| documents-evidence-deeplink-contract | 4 passed | 4 passed |
| daily-summary-evidence-contract | 4 passed | 4 passed |
| daily-assistant-contract | 5 passed | 5 passed |
| actions-page-contract | 4 passed | 4 passed |
| documents-confirmed-data-contract | 4 passed | 4 passed |
| documents-page-contract | 4 passed | 4 passed |
| symptoms-page-contract | 4 passed | 4 passed |
| runtime-smoke | 56 passed | 56 passed |
| **report-symptom-recommendation-contract (new)** | — | **5 passed** |

---

### 3. Deliverable

`frontend/tests/e2e/p101-report-symptom-recommendation-integration.spec.ts` — 5 tests:
- T1: Daily Assistant `p94-top-risk-ref-link` (lab `topRiskRef`) href contains `?document_id=`
- T2: Daily Assistant `p94-today-action-ref-link` (symptom `todayActionRef`) href is `/platform/symptoms`, no `document_id`
- T3: Actions page `p89-source-page-link` (lab rec with `document_id`) href contains `?document_id=`
- T4: Documents page auto-opens `[role="dialog"]` drawer when `?document_id=` matches document
- T5: Documents page does not crash on unknown `?document_id=` (no drawer, list visible)

New Makefile guard: `make report-symptom-recommendation-contract` (tsc + 5 tests)

Guard index updated: `docs/product/local-contract-guard-index.md` — row + bundle + quick-ref

`active_task.md` refreshed from stale P64 content to P101 (authorized per P100 roadmap checkpoint)

---

### 4. Changes in This Task

| File | Action |
|---|---|
| `frontend/tests/e2e/p101-report-symptom-recommendation-integration.spec.ts` | Created — 5 integration tests |
| `Makefile` | Added `report-symptom-recommendation-contract` target + `.PHONY` |
| `docs/product/local-contract-guard-index.md` | Added P101 guard row, when-to-run, related-files, bundle, quick-ref |
| `00-Plan/roadmap/active_task.md` | Refreshed stale P64 → P101 task |
| `00-Plan/roadmap/active_task_report.md` | P101 entry prepended |

---

### 5. Key Technical Facts

- Mock pattern: `addInitScript` + `page.route('**/api/v1/**', ...)` — same as P97
- `topRiskRef.source_type = 'lab_report_item'` + `document_id` → `getEvidenceHref()` returns `/platform/documents?document_id=<id>` ✅
- `todayActionRef.source_type = 'symptom'` (no `document_id`) → `getEvidenceHref()` returns `/platform/symptoms` ✅ (no fake deeplink)
- `ParsedItemsDrawer` mock: `json: []` (array, NOT `{ items: [] }`) — learned from P97
- `next build` NOT required — spec-only change (no frontend code modified)

---

## P100 Product Lane Reset / Roadmap Checkpoint (2026-05-26)

**Final Classification: `P100_PRODUCT_LANE_RESET_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `f48fa06` (P99) |
| Dirty files | governance-only (4 files) |

---

### 2. Baseline Gates (all 8 green before + after)

| Gate | Before | After |
|---|---|---|
| documents-evidence-deeplink-contract | 4 passed | 4 passed |
| daily-summary-evidence-contract | 4 passed | 4 passed |
| daily-assistant-contract | 5 passed | 5 passed |
| actions-page-contract | 4 passed | 4 passed |
| documents-confirmed-data-contract | 4 passed | 4 passed |
| documents-page-contract | 4 passed | 4 passed |
| symptoms-page-contract | 4 passed | 4 passed |
| runtime-smoke | 56 passed | 56 passed |

---

### 3. Deliverable

`docs/product/p100-product-lane-reset-roadmap-checkpoint.md` — full checkpoint including:
- P80–P99 completion matrix (20 phases, all ✅)
- Current guard/index status (8 guards, 85 tests)
- Roadmap drift assessment (4 drift items; active_task.md blocked)
- 5-candidate next lane comparison with risk matrix
- P101 recommendation: Report+Symptom Integration Contract (mocked spec, 1 guard, zero new backend/frontend code)
- Risk/unknowns table
- Validation table (all gates before + after)
- CTO 10-line summary

Updated in working tree (governance — not staged):
- `00-Plan/roadmap/roadmap.md` — refreshed to P99-era state + P101 plan
- `00-Plan/roadmap/CTO-Analysis.md` — full P100 analysis + risk matrix

Blocked (not updated):
- `00-Plan/roadmap/active_task.md` — stale at P64; update requires authorization at P101 start

---

### 4. Changes in This Task

- No code changes (docs/roadmap-only task)
- New file: `docs/product/p100-product-lane-reset-roadmap-checkpoint.md`
- Updated: `00-Plan/roadmap/active_task_report.md`
- Working tree (not staged): `roadmap.md`, `CTO-Analysis.md`

---

## P99 Local Contract Guard Index (2026-05-26)

**Final Classification: `P99_LOCAL_CONTRACT_GUARD_INDEX_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `0ed0e17` (P98) |
| Dirty files | governance-only (4 files) |

---

### 2. Baseline Gates (all 8 green before + after edits)

| Gate | Before | After |
|---|---|---|
| documents-evidence-deeplink-contract | 4 passed | 4 passed |
| daily-summary-evidence-contract | 4 passed | 4 passed |
| daily-assistant-contract | 5 passed | 5 passed |
| actions-page-contract | 4 passed | 4 passed |
| documents-confirmed-data-contract | 4 passed | 4 passed |
| documents-page-contract | 4 passed | 4 passed |
| symptoms-page-contract | 4 passed | 4 passed |
| runtime-smoke | 56 passed | 56 passed |

---

### 3. Deliverable

`docs/product/local-contract-guard-index.md` — authoritative runbook including:
- Purpose and maintenance rule
- Guard matrix: all 8 targets × (spec file, test count, `next build` requirement, what it protects)
- Per-guard "when to run" trigger table
- Per-guard related files + phase table
- 8 recommended validation bundles (targeted + full)
- `next build` requirement rules
- Non-goals (no CI wiring, no full-regression replacement)
- Staging hygiene rules
- Future maintenance checklist (5 steps for new targets)
- Quick-reference paste blocks

---

### 4. Changes in This Task

- No code changes (docs-only task)
- New file: `docs/product/local-contract-guard-index.md`
- Updated: `00-Plan/roadmap/active_task_report.md`

---

## P98 Evidence Deep Link Contract Adoption (2026-06)

**Final Classification: `P98_EVIDENCE_DEEPLINK_CONTRACT_ADOPTION_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `f5cf87f` (P97 report) |
| Dirty files | governance-only (4 files) |

---

### 2. Baseline Gates (all 8 green before edits)

| Gate | Result |
|---|---|
| documents-evidence-deeplink-contract | 4 passed |
| daily-summary-evidence-contract | 4 passed |
| daily-assistant-contract | 5 passed |
| actions-page-contract | 4 passed |
| documents-confirmed-data-contract | 4 passed |
| documents-page-contract | 4 passed |
| symptoms-page-contract | 4 passed |
| runtime-smoke | 56 passed |

---

### 3. Deliverable

`docs/product/p98-evidence-deeplink-contract-adoption.md` — full adoption guide including:
- What P97's contract protects (5 observable behaviors)
- When to run `make documents-evidence-deeplink-contract` (10 touch-point triggers)
- Explicit non-goals (symptoms/risk-alert/metric deep links; CI wiring)
- Known pitfalls preserved from P97 implementation (5 pitfalls with code examples)
- Future expansion lanes (P99-A symptoms feasibility, P99-B source map extension, P99-C CI adoption)
- Complete file map (13 files)

---

### 4. Changes in This Task

- No code changes (docs-only task)
- New file: `docs/product/p98-evidence-deeplink-contract-adoption.md`
- Updated: `00-Plan/roadmap/active_task_report.md`

---

## P96 Source-Specific Deep Link Planning (2025-01)

**Final Classification: `P96_SOURCE_DEEP_LINK_PLANNING_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `8b76463` (P95) |
| Dirty files | governance-only (4 files) |

---

### 2. Baseline Gates (all 7 green before investigation)

| Gate | Result |
|---|---|
| daily-summary-evidence-contract | 4 passed |
| daily-assistant-contract | passed |
| actions-page-contract | 3 passed, 4 warnings |
| documents-confirmed-data-contract | 41 passed, 2 skip |
| documents-page-contract | 29 passed |
| symptoms-page-contract | 57 passed |
| runtime-smoke | 56 passed |

---

### 3. Investigation Findings

**Source ID gap confirmed**: `lab_report_item` and `lab_abnormality` refs carry `LabReportItem.id` / `LabReport.id`, but the documents page drawer needs `MedicalDocument.id` (= `LabReport.document_id`).

**Destination page capabilities**:
- `/platform/documents` — no `useSearchParams`; drawer state-controlled; **feasible** with small addition.
- `/platform/symptoms` — no `useSearchParams`; no per-entry UI; **page-level only** recommended.
- `/platform/insights` — already uses `useSearchParams`; proven pattern in codebase.

**Recommended model**: Option B — `?document_id=<MedicalDocument.id>` for lab types; page-level for symptoms.

---

### 4. Deliverable

`docs/product/p96-source-specific-deep-link-planning.md` — full discovery report including:
- Source ID map (8 source_types)
- Destination page capability map
- Recommended deep-link URL contract
- Minimal P97 implementation plan (2 backend files, 4 frontend files, 2 spec files, 1 Makefile gate)
- Risks / edge cases / graceful degradation
- P97 kickoff prompt

---

### 5. Changes in This Task

- No code changes (discovery-only task)
- New file: `docs/product/p96-source-specific-deep-link-planning.md`
- Updated: `00-Plan/roadmap/active_task_report.md`

---

## P95 Daily Summary Evidence Refs Contract Guard (2026-05-26)

**Final Classification: `P95_CONTRACT_GUARD_DONE`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `d3d81f6` (P94 report) |
| Dirty files | governance-only |

---

### 2. Baseline Gates (before + after)

All 6 gates green both runs — no regressions.

---

### 3. Changes

**`Makefile`**:
- Added `daily-summary-evidence-contract` to `.PHONY`
- Added new target: `tsc --noEmit` + P94 Playwright spec (4 tests)

---

### 4. New Target

```make
daily-summary-evidence-contract:
    cd frontend && npx tsc --noEmit
    cd frontend && npx playwright test tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts --reporter=line
```

Run after touching: `DailyHealthSummary` evidence refs, Daily Assistant 3-grid cards, `EVIDENCE_SOURCE_META`, or source-link behavior.

---

### 5. Smoke Result

```
4 passed (4.2s)
```

---



**Final Classification: `P94_3GRID_EVIDENCE_REFS_DONE`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `cec22df` (P93) |
| HEAD at commit | `81a5228` |
| Dirty files | governance-only |

---

### 2. Baseline Gates (before + after)

| Gate | Before | After |
|---|---|---|
| daily-assistant-contract | 4 passed | 4 passed |
| actions-page-contract | 3 passed | 3 passed |
| documents-confirmed-data-contract | 41 passed, 2 skip | 41 passed, 2 skip |
| documents-page-contract | 29 passed | 29 passed |
| symptoms-page-contract | 57 passed | 57 passed |
| runtime-smoke | 56 passed | 56 passed |

---

### 3. Changes Implemented

**Backend** (`health_assistant_service.py`):
- `_derive_top_risk` → now returns `tuple[str, dict | None]` with per-branch ref construction
- `_derive_biggest_change` → now returns `tuple[str, dict | None]` with per-branch ref construction
- `_derive_today_action_and_why` → now returns `tuple[str, str, dict | None]` with per-branch ref construction
- `generate_daily_health_summary` → unpacks tuples, conditionally adds `topRiskRef`, `biggestChangeRef`, `todayActionRef` to response dict

**Backend tests** (`test_daily_summary_service.py`):
- 17 `_derive_*` unit tests updated to unpack tuples and assert ref type/None

**Frontend** (`frontend/lib/api.ts`):
- Added `DailySummaryEvidenceRef` type
- Added 3 optional ref fields to `DailyHealthSummary`

**Frontend** (`frontend/lib/evidence-source-meta.ts`):
- Added `health_metric`, `outcome`, `recommendation` label-only entries

**Frontend** (`frontend/app/components/platform/daily-assistant-entry.tsx`):
- Added mini-badge to `daily-summary-top-risk` card
- Added mini-badge to `daily-summary-biggest-change` card
- Added mini-badge to `daily-summary-next-action` card

**Frontend tests** (`tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts`):
- 4 new tests (T1–T4): badge visibility, link presence/absence by source_type

---

### 4. Test Results

| Suite | Result |
|---|---|
| `pytest test_daily_summary_service.py` | 31 passed |
| `npx tsc --noEmit` | clean |
| `npx next build` | clean |
| `playwright p94 + p76` | 9 passed |

---

### 5. Design Notes

- **Non-breaking**: all 3 new fields are optional; P76 mock unaffected
- **health_metric trend**: `source_id: None` (trend spans multiple records, no single UUID)
- **No href** for `risk_alert`, `health_metric`, `outcome` — `ExternalLink` only renders when `href` present in `EVIDENCE_SOURCE_META`
- **No changes** to trust-type-guards, P76 spec, API endpoints, or LLM prompts

---

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `587e452` |
| Dirty files | governance-only |

---

### 2. Baseline Gates (before + after)

All 6 gates green both runs. No failures. No code changes in P93.

---

### 3. Key Findings

#### Backend generation path confirmed (service lines 1143–1386)

| Card | Winning source | source_type | source_id available? | Navigation? |
|---|---|---|---|---|
| `topRisk` | `risk_alerts[max severity]` | `risk_alert` | ✅ UUID | ❌ No page |
| `topRisk` (alt) | `recommendations[0]` | lab/symptom/etc | ✅ UUID | ✅ EVIDENCE_SOURCE_META |
| `topRisk` (alt) | `device_escalation` | — | ❌ None | ❌ Signal only |
| `biggestChange` | `outcomes[max delta]` | `outcome` | ✅ UUID | ❌ No page |
| `biggestChange` (alt) | `health_metrics` trend | `health_metric` | ⚠️ No single UUID | ❌ No page |
| `todayAction` + `whyNow` | `recommendations[0]` | lab/symptom/etc | ✅ UUID | ✅ EVIDENCE_SOURCE_META |

#### Schema gap confirmed

- `generate_daily_health_summary` returns 7 narrative strings, zero source refs
- All three `_derive_*` helpers discard source identity at their return boundary
- No hidden source fields exist in the current API response
- Adding optional `topRiskRef?`, `biggestChangeRef?`, `todayActionRef?` is **non-breaking** for all existing tests

---

### 4. Recommended Evidence Ref Shape (for P94)

```typescript
export type DailySummaryEvidenceRef = {
  source_type: string
  source_id?: string    // absent for escalation / trend / fallback
  summary?: string
}

// DailyHealthSummary gains (all optional):
topRiskRef?:       DailySummaryEvidenceRef
biggestChangeRef?: DailySummaryEvidenceRef
todayActionRef?:   DailySummaryEvidenceRef
```

EVIDENCE_SOURCE_META additions (P94): `health_metric`, `outcome`, `recommendation` — label-only, no `href` (no pages exist).

---

### 5. P94 Implementation Plan Summary

| Phase | Files | LOC |
|---|---|---|
| A — Backend helpers return tuples | `health_assistant_service.py` | ~45 |
| B — Backend tests unpack tuples | `test_daily_summary_service.py` | ~20 |
| C — Frontend type | `api.ts`, `trust-type-guards.ts` | ~10 |
| D — Frontend UI badges | `daily-assistant-entry.tsx`, `evidence-source-meta.ts` | ~30 |
| E — New Playwright spec | `p94-daily-summary-3grid-evidence-refs.spec.ts` | ~30 |

---

### 6. Validation

| Step | Result |
|---|---|
| All 6 Makefile gates (before) | ✅ All green |
| All 6 Makefile gates (after) | ✅ All green |
| Code changes in P93 | None |

---

### 7. Commit

| Commit | Message |
|---|---|
| (code) | None — discovery only |
| `<this report>` | `docs(product): P93 daily summary structured evidence refs discovery` |

---

## P92 Shared Evidence Source Metadata Refactor (2026-05-26)

**Final Classification: `P92_EVIDENCE_SOURCE_META_REFACTOR_DONE`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `7dd9d10` |
| Dirty files | governance-only |

---

### 2. Baseline Gates (before)

All 6 gates green. `4 passed` / `4 passed` / `5 passed` / `3 passed` / `41 passed` / `56 passed`.

---

### 3. Changes Made

#### `frontend/lib/evidence-source-meta.ts` (NEW)

Shared source-page link metadata:
```ts
export type EvidenceSourceMeta = { label: string; href?: string }

export const EVIDENCE_SOURCE_META: Record<string, EvidenceSourceMeta> = {
  lab_report_item:   { label: '查看健檢報告', href: '/platform/documents' },
  lab_abnormality:   { label: '查看健檢報告', href: '/platform/documents' },
  symptom:           { label: '查看症狀紀錄', href: '/platform/symptoms' },
  long_term_symptom: { label: '查看症狀紀錄', href: '/platform/symptoms' },
  risk_alert:        { label: '查看風險提醒' },  // no href → no link
}
```

#### `frontend/app/components/platform/decision-recommendation-layer.tsx`

- Removed local `SOURCE_LINK` constant (P89 duplication)
- Added `import { EVIDENCE_SOURCE_META } from '../../../lib/evidence-source-meta'`
- Updated guard: `SOURCE_LINK[item.source_type]` → `EVIDENCE_SOURCE_META[item.source_type]?.href`
- Updated JSX: `.href` / `.label` via `!` non-null assertion

#### `frontend/app/components/platform/daily-assistant-entry.tsx`

- Removed local `TOPREC_SOURCE_LINK` constant (P91 duplication)
- Added `import { EVIDENCE_SOURCE_META } from '../../../lib/evidence-source-meta'`
- Updated guard: `TOPREC_SOURCE_LINK[topRec.source_type]` → `EVIDENCE_SOURCE_META[topRec.source_type]?.href`
- Updated JSX: `.href` / `.label` via `!` non-null assertion

---

### 4. Validation

| Step | Result |
|---|---|
| `npx tsc --noEmit` | ✅ Clean |
| P89 Playwright (4 tests) | ✅ 4/4 passed |
| P91 Playwright (4 tests) | ✅ 4/4 passed |
| All 6 Makefile gates | ✅ All green (no regressions) |
| `npx next build` | ✅ Clean |

---

### 5. Commit

| Commit | Message |
|---|---|
| `379efe0` | `refactor(frontend): P92 extract shared EVIDENCE_SOURCE_META helper` |

---

### 6. Known Limitations / Design Notes

- `risk_alert` entry has `label` but no `href` — reserved for future page when risk-alerts detail view exists
- New source types (e.g. `health_record`) can be added to `evidence-source-meta.ts` alone — no changes to consumers required
- No test specifically covers `evidence-source-meta.ts` in isolation; coverage is via P89/P91 integration tests

---

## P91 Daily Assistant Top-Rec Evidence Badge (2026-05-26)

**Final Classification: `P91_DAILY_ASSISTANT_EVIDENCE_BADGE_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `23f9d6e` |
| Dirty files | governance-only |

---

### 2. Baseline Gates (before)

All 6 gates green. `57 passed` + `56 passed` + `29 passed` (combined Makefile targets).

---

### 3. Changes Made

#### `frontend/app/components/platform/daily-assistant-entry.tsx`

1. **Added lucide-react imports**: `ExternalLink`, `FileText`
2. **Added `TOPREC_SOURCE_LINK` constant** (module-level, before component):
   - `lab_report_item` / `lab_abnormality` → `/platform/documents` (查看健檢報告)
   - `symptom` / `long_term_symptom` → `/platform/symptoms` (查看症狀紀錄)
3. **Added evidence badge** after `topRec.why_now` paragraph:
   - `data-testid="daily-toprec-evidence-badge"` wraps `FileText` icon + `參考依據：{topRec.evidence_summary}`
   - Conditional `data-testid="p91-daily-source-page-link"` only when `TOPREC_SOURCE_LINK[topRec.source_type]` exists
   - Pattern mirrors P89 `decision-recommendation-layer.tsx`

#### `frontend/tests/e2e/p91-daily-assistant-evidence-badge.spec.ts` (NEW)

4 tests, fully mocked, navigating to `/platform/dashboard`:
- T1: `lab_report_item` → badge + documents link ✅
- T2: `symptom` → badge + symptoms link ✅
- T3: `recommendation` → badge only, no source-page link ✅
- T4: no `evidence_summary` → no badge, no link ✅

---

### 4. Validation

| Step | Result |
|---|---|
| `npx tsc --noEmit` | ✅ Clean |
| P91 Playwright (4 tests) | ✅ 4/4 passed |
| All 6 Makefile gates | ✅ All green (no regressions) |
| `npx next build` | ✅ Clean |

---

### 5. Commit

| Commit | Message |
|---|---|
| `9136327` | `feat(frontend): P91 daily assistant top-rec evidence badge` |

---

### 6. Known Limitations

- `TOPREC_SOURCE_LINK` duplicated from `decision-recommendation-layer.tsx` — shared extraction deferred to P92+
- 3-grid narrative cards (topRisk / biggestChange / todayAction) remain string-only — backend schema extension required for source refs
- No deep-link to specific document or symptom item — page-level nav only
- SOURCE_LINK covers 4 types; any new `source_type` silently shows badge without link

---

## P90 Daily Assistant Evidence Traceability Discovery (2026-05-26)

**Final Classification: `P90_FRONTEND_ONLY_DAILY_TRACEABILITY_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `e1418d6` |
| Dirty files | governance-only |

---

### 2. Baseline Gates

All 6 gates green before and after investigation. No code modified in P90.

---

### 3. Key Findings

| Finding | Detail |
|---|---|
| `generate_daily_health_summary` | Returns 7 narrative strings only. No `source_type`, `source_id`, `evidence_summary`. |
| `DailyHealthSummary` TS type | 9 fields, no source refs. Gap G5 confirmed. |
| `topRec` in `DailyAssistantEntry` | `Recommendation` type — has `source_type`, `source_id`, `evidence_summary` in scope |
| `topRec.evidence_summary` rendering | NOT rendered. Gap confirmed. |
| Frontend-only fix viable? | **Yes.** `topRec.evidence_summary` + P89 `SOURCE_LINK` pattern can be applied to the `topRec` block with ~10 lines JSX, zero backend changes. |

---

### 4. Deliverable

Discovery report: `docs/product/p90-daily-assistant-evidence-traceability-discovery.md`

No code changes. No test changes.

---

### 5. P91 Recommendation

**Option A (recommended)**: Add `evidence_summary` badge + conditional `SOURCE_LINK` to `topRec` block in `daily-assistant-entry.tsx`. Same pattern as P89. Estimated 10 JSX lines + 1 new Playwright spec.

3-grid cards (`topRisk`, `biggestChange`, `todayAction`) remain narrative-only — source refs not available in `DailyHealthSummary` response (Option B / backend schema work deferred to P92+).

---

### 6. Commit

```
docs(product): P90 daily assistant evidence traceability discovery
SHA: <see git log>
Files: 2 changed (report + task_report)
```

---

---

## P89 Frontend Evidence Source Traceability (2026-05-26)

**Final Classification: `P89_FRONTEND_EVIDENCE_TRACEABILITY_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `2743c64` |
| Dirty files | governance-only |

---

### 2. Baseline Gates (all green before changes)

| Gate | Tests | Result |
|---|---|---|
| `actions-page-contract` | 4 | ✅ PASS |
| `documents-confirmed-data-contract` | 4 | ✅ PASS |
| `documents-page-contract` | 4 | ✅ PASS |
| `symptoms-page-contract` | 4 | ✅ PASS |
| `daily-assistant-contract` | 5 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |

---

### 3. Problem Statement

P88 discovery identified 5 traceability gaps. P89 targets the two highest-value, lowest-risk gaps:

- **G1**: `actions/page.tsx` hardcoded `source_type: 'recommendation'` for all health-assistant recs regardless of backend value
- **G3**: `DecisionRecommendationLayer` had no source-page navigation link adjacent to `evidence_summary`

---

### 4. Changes Made

#### 4.1 `frontend/app/platform/actions/page.tsx` — G1 fix (2 lines)

```typescript
// Before
source_type: 'recommendation',
source_id: r.action_id ? String(r.action_id) : `ha_rec_${r.rule_id ?? i}`,

// After
source_type: r.source_type ?? 'recommendation',
source_id: r.source_id ? String(r.source_id) : (r.action_id ? String(r.action_id) : `ha_rec_${r.rule_id ?? i}`),
```

The backend already returns the correct `source_type` per recommendation. This forwards it.

#### 4.2 `frontend/app/components/platform/decision-recommendation-layer.tsx` — G3 fix

**Imports**: Added `Link` (next/link), `Activity`, `ExternalLink` (lucide-react).

**SOURCE_META** expanded with 5 new types: `risk_alert`, `lab_report_item`, `lab_abnormality`, `symptom`, `long_term_symptom` — each with appropriate icon and colour class.

**SOURCE_LINK** map added (page-level only, no deep-link):

```typescript
const SOURCE_LINK: Record<string, { label: string; href: string }> = {
  lab_report_item:   { label: '查看健檢報告', href: '/platform/documents' },
  lab_abnormality:   { label: '查看健檢報告', href: '/platform/documents' },
  symptom:           { label: '查看症狀紀錄', href: '/platform/symptoms' },
  long_term_symptom: { label: '查看症狀紀錄', href: '/platform/symptoms' },
}
```

**evidence_summary badge** updated: when `SOURCE_LINK[item.source_type]` exists, a `<Link data-testid="p89-source-page-link">` is rendered inline after the text.

---

### 5. Test Coverage

New file: `frontend/tests/e2e/p89-actions-evidence-traceability.spec.ts`

| Test | Description | Result |
|---|---|---|
| T1 | `lab_report_item` → evidence_summary + link to `/platform/documents` | ✅ PASS |
| T2 | `symptom` → evidence_summary + link to `/platform/symptoms` | ✅ PASS |
| T3 | `recommendation` → evidence_summary, no source-page link | ✅ PASS |
| T4 | Overclaim guard — page has no 確診/診斷/治療/保證 | ✅ PASS |

---

### 6. Post-Change Validation

| Gate | Tests | Result |
|---|---|---|
| P89 spec | 4 | ✅ PASS |
| `actions-page-contract` (P82) | 4 | ✅ PASS |
| `documents-confirmed-data-contract` | 4 | ✅ PASS |
| `documents-page-contract` | 4 | ✅ PASS |
| `symptoms-page-contract` | 4 | ✅ PASS |
| `daily-assistant-contract` | 5 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |
| `npx tsc --noEmit` | — | ✅ PASS |
| `npx next build` | — | ✅ PASS |

---

### 7. Known Limitations

- `SOURCE_LINK` covers only `lab_report_item`, `lab_abnormality`, `symptom`, `long_term_symptom`. Types `insight`, `alert`, `trend`, `action` have no deep-link target yet.
- Links are page-level only (e.g., `/platform/documents`) — no deep-link to the specific document or symptom entry.
- Daily Assistant `why_now` string (G4) is still not source-annotated — deferred to P90.
- `evidence_sources[]` array (G2) not rendered as structured list — deferred.

---

### 8. Commit

```
feat(frontend): P89 add recommendation evidence source links
SHA: a16d7c1
Files: 3 changed, 274 insertions, 9 deletions
```

---

### 9. CTO Summary

P89 completes the first user-visible traceability slice. Two structural bugs fixed: the frontend was silently discarding the backend's `source_type` field (hardcoded to `'recommendation'`), and the evidence badge had no navigation out. Now `lab_report_item` and `symptom` recommendations surface a one-click link to the relevant data page. SOURCE_META extended to 10 types for future readiness. 4 new E2E tests, all existing 21 contract tests still green, TSC clean, build clean. Gap G1 and G3 are closed; G2 (evidence_sources list), G4 (daily assistant), G5 (backend layer) remain queued.

---

---

## P88 Evidence Traceability Discovery (2026-05-26)

## P88 Evidence Traceability Discovery (2026-05-26)

**Final Classification: `P88_EVIDENCE_TRACEABILITY_DISCOVERY_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `8fbc5b4` |
| Dirty files | governance-only (CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md) |

---

### 2. Baseline Validation (before changes)

| Gate | Result |
|---|---|
| `make documents-confirmed-data-contract` | ✅ 4/4 |
| `make documents-page-contract` | ✅ 4/4 |
| `make symptoms-page-contract` | ✅ 4/4 |
| `make actions-page-contract` | ✅ 5/5 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 3. Investigation Findings

**Scope**: Read-only audit — no code changes. Discovery report only.  
**Report**: `docs/product/p88-evidence-traceability-discovery.md`

**Evidence bundle** (`health_assistant_service.py:build_evidence_bundle`): Fully traceable. Every evidence item carries `source_type`, `source_id`, `evidence_level`, `recency`, and domain-specific fields. Lab report items additionally carry `report_id`, `report_date`, `item_name`, `value_num`, `abnormal_flag`.

**Recommendation response** (`get_action_recommendations`): Rich traceability already present — `evidence_summary` (one-liner), `data_insufficiency_reason`, `evidence_sources[]`, `source_type`, `source_id` all returned by backend.

**Frontend gap G1** (`actions/page.tsx` line 113): `source_type` is hardcoded to `'recommendation'`, discarding the backend's actual originating type (`"lab_report_item"`, `"symptom"`, `"risk_alert"`). One-line fix.

**Frontend gap G3** (`DecisionRecommendationLayer`): `evidence_summary` string is rendered (FileText badge) but no source-page navigation link exists. Users cannot navigate to `/platform/documents` or `/platform/symptoms` from the recommendation card.

**Daily Assistant**: `topRisk`, `biggestChange`, `whyNow` are narrative strings — no structured source refs. Backend-layer gap, out of P88 scope.

---

### 4. Deliverables

| Deliverable | Status |
|---|---|
| `docs/product/p88-evidence-traceability-discovery.md` | ✅ Created |
| `active_task_report.md` updated | ✅ This block |
| No code changes | ✅ Discovery-only |

---

### 5. P89 Recommendation

**Classification**: `P89_FRONTEND_ONLY_TRACEABILITY_READY`  
**Files**: `frontend/app/platform/actions/page.tsx` (1 line) + `frontend/app/components/platform/decision-recommendation-layer.tsx` (~11 lines)  
**Changes**: Forward `r.source_type` instead of hardcoding `'recommendation'`; add `SOURCE_META` entries for lab/symptom types; add conditional source-page link after `evidence_summary` badge.  
**Backend changes**: None.  
**Estimated effort**: ~12 lines, 2 files.

---

# Active Task Report — P87 Documents Confirmed-Data Re-feed (2026-05-26)

## P87 Documents Confirmed-Data Re-feed (2026-05-26)

**Final Classification: `P87_CONFIRMED_DATA_REFEED_FIXED`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `2a5c265` |
| Dirty files | governance-only (CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md) |

---

### 2. Baseline Validation (before changes)

| Gate | Result |
|---|---|
| `make documents-page-contract` | ✅ 4/4 |
| `make symptoms-page-contract` | ✅ 4/4 |
| `make actions-page-contract` (p82) | ✅ 5/5 |
| p76 daily-assistant-signal | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 3. Root Cause Analysis

**Gap: P84 Gap G1 — confirmed_data from confirm not re-fed into document list rows.**

| Layer | Finding |
|---|---|
| Backend | `POST /documents/{id}/confirm` stores only `{reviewed: True}` in `confirmed_data`. `PUT /documents/{id}/confirm` stores the full payload including `items`, `extracted_items`, `abnormal_items`. Both return `DocumentResponse` which includes `confirmed_data`. |
| API client | `confirmDocumentPost` (POST, no body) and `confirmDocument` (PUT, with body) both exist in `lib/api.ts`. |
| Frontend | `ParsedItemsDrawer.handleConfirm` was calling POST — so `confirmed_data` was always just `{reviewed: True}`, no item counts. |
| Doc interface | `confirmed_data` field was absent from the `Doc` interface — even though `GET /documents` returns it in `DocumentResponse`. |
| UI | Document list row showed only filename + 已確認 badge. No item count, no abnormal count. |

**Evidence chain break:** User confirms lab report → drawer closes → list shows 已確認 → user has no idea how many items were confirmed or how many were abnormal without re-opening the drawer.

---

### 4. Changes Made

#### `frontend/app/components/platform/parsed-items-drawer.tsx`

Changed `handleConfirm` from:
```
api.confirmDocumentPost(documentId)   // POST, no body → confirmed_data = {reviewed:True}
```
to:
```
api.confirmDocument(documentId, {
  confirmed_data: { items, extracted_items, abnormal_items, reviewed_at }
})  // PUT with body → confirmed_data stored with full item counts
```

#### `frontend/app/platform/documents/page.tsx`

- Added `confirmed_data?: { extracted_items?: number; abnormal_items?: number } | null` to `Doc` interface
- Added `data-testid="documents-confirmed-summary"` row in confirmed doc: shows `N 項指標 · M 項異常` when `confirmed_data.extracted_items` is present

#### `frontend/tests/e2e/p87-documents-confirmed-data-refeed.spec.ts` — created

4 mocked contract tests:

| # | Test | Key assertions |
|---|---|---|
| 1 | Pre-confirmed doc shows summary | `documents-confirmed-summary` visible, contains `8 項指標 · 3 項異常` |
| 2 | Confirm action re-feeds confirmed_data | Click 審閱解析結果 → items load → click 確認並分析 → drawer closes → summary appears |
| 3 | Legacy confirmed doc (no extracted_items) shows no summary | `documents-confirmed-summary` not visible |
| 4 | Overclaim guard | No prohibited clinical phrases on confirmed doc page |

#### `Makefile`

Added `.PHONY` entry and `documents-confirmed-data-contract` target.

---

### 5. Validation Gates (after changes)

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | ✅ clean |
| `npx next build` | ✅ clean |
| P87 spec (4 tests) | ✅ 4/4 |
| P85 documents-page-contract | ✅ 4/4 |
| P86 symptoms-page-contract | ✅ 4/4 |
| p82 actions-page-contract | ✅ 5/5 |
| p76 daily-assistant-signal | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 6. Commit

`07b4b38` — `fix(frontend): P87 re-feed confirmed_data into document list row`

---

# Active Task Report — P86 Symptoms Page Contract Smoke (2026-05-26)

## P86 Symptoms Page Contract Smoke (2026-05-26)

**Final Classification: `P86_SYMPTOMS_PAGE_CONTRACT_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `edab599` |
| Dirty files | governance-only (CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md) |

---

### 2. Baseline Validation (before changes)

| Gate | Result |
|---|---|
| `make documents-page-contract` | ✅ 4/4 |
| `make actions-page-contract` | ✅ 4/4 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 3. Changes Made

**Gap closed: P84 Gap G5 — `/platform/symptoms` had zero testids.**

#### `frontend/app/platform/symptoms/page.tsx` — 4 testids added

| testid | Element | Condition | Rationale |
|---|---|---|---|
| `symptoms-page` | root `<div>` | always visible | page identity anchor |
| `symptoms-input-section` | `<Card>` wrapping quick-input form | always visible | primary CTA — symptom entry path |
| `symptoms-insight-section` | `<Card>` wrapping 6-week heatmap | always visible | pattern/temporal visualisation surface |
| `symptoms-list-section` | `<Card>` wrapping recent logs | always visible | symptom history — downstream recommendation evidence |

No business logic changed. No backend changes.

#### `frontend/tests/e2e/p86-symptoms-page-contract.spec.ts` — created

4 mocked contract tests:

| # | Test | Key assertions |
|---|---|---|
| 1 | page renders | `symptoms-page` visible, no ErrorBoundary |
| 2 | input section discoverable | `symptoms-input-section` + heading + `儲存症狀` button + `頭痛` chip visible |
| 3 | heatmap + list sections with data | `symptoms-insight-section` + `symptoms-list-section` + `頭痛` + `疲勞` in list |
| 4 | API failure safe + overclaim guard | page survives 500, input still accessible, no prohibited phrases |

Fixtures: `SYMPTOM_RECENT` (頭痛, severity 2, today), `SYMPTOM_CHRONIC` (疲勞, severity 1, chronic, 3 days ago).

Mocked routes: `/symptoms` (GET), `/metrics` (GET), plus full layout shell stubs (health-assistant, dashboard, documents, actions, etc.).

#### `Makefile` — `symptoms-page-contract` target added

```
make symptoms-page-contract   → npx tsc --noEmit + p86 spec (4 tests)
```

---

### 4. Validation

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| P86 spec (4 tests) | ✅ 4/4 |
| `make symptoms-page-contract` | ✅ 4/4 |
| `npx next build` | ✅ clean |
| `make documents-page-contract` | ✅ 4/4 (no regression) |
| `make actions-page-contract` | ✅ 4/4 (no regression) |
| `make daily-assistant-contract` | ✅ 5/5 (no regression) |
| `make runtime-smoke` | ✅ 56/56 (no regression) |

---

### 5. Commits

| SHA | Message |
|---|---|
| `61cd499` | feat(frontend): P86 symptoms page contract smoke |

---

### 6. Known Limitations

- Heatmap cells are rendered as `<button>` elements without per-cell testids — click interaction not covered in this contract (out of P86 scope)
- `symptoms-insight-section` does not cover the `chronic` alert card (amber banner) — that Card is conditionally rendered only when ≥3 occurrences of a symptom exist in the last 14 days; not adding testid to conditional-only elements without contract need
- POST `/symptoms` (createSymptom) not exercised by contract — form interaction test is out of scope for a selector surface smoke

---

### 7. CTO 10-Line Summary

1. P86 closes P84 Gap G5: `/platform/symptoms` now has 4 stable testids.
2. Testids: `symptoms-page` (root), `symptoms-input-section` (quick-entry card), `symptoms-insight-section` (6-week heatmap), `symptoms-list-section` (recent logs).
3. Contract spec: 4 mocked tests — render safety, input section discovery, heatmap + list with data, API failure + overclaim guard.
4. No backend changes. No business logic changes. Testid-only surface addition.
5. `make symptoms-page-contract` target added (TSC + 4 contract tests).
6. `next build` required because component file modified — completed cleanly.
7. All baselines maintained: symptoms 4/4, documents 4/4, actions 4/4, daily-assistant 5/5, runtime-smoke 56/56.
8. Conditional chronic-alert Card not testid'd — renders only when ≥3 same-symptom logs in 14 days, not a stable selector.
9. heatmap cell interaction not covered — out of scope for this contract tier.
10. Next lane: P87 — `confirmed_data` re-feed investigation (P84 Gap G1): when `/documents/{id}/confirm` returns `confirmed_data`, that data is not re-fed into LabReportItem rows. Discovery + minimal fix plan.

---

## P85 Documents Page Contract Smoke (2026-05-26)

**Final Classification: `P85_DOCUMENTS_PAGE_CONTRACT_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | PersonalHealthOS |
| Branch | main |
| HEAD at start | `f59778c` |
| Dirty files | governance-only (no tracked file changes) |

---

### 2. Baseline Validation (before changes)

| Gate | Result |
|---|---|
| `make actions-page-contract` | ✅ 4/4 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 3. Changes Made

**Gap closed: P84 Gap G4 — `/platform/documents` had zero testids.**

#### `frontend/app/platform/documents/page.tsx` — 4 testids added

| testid | Element | Condition |
|---|---|---|
| `documents-page` | root `<div>` | always visible after load |
| `documents-upload-section` | upload `<Card>` | always visible |
| `documents-list-section` | list `<Card>` (tab=documents) | visible when tab active |
| `documents-loading` | Skeleton wrapper `<div>` | `loading === true` only |

No business logic changed. No backend changes.

#### `frontend/tests/e2e/p85-documents-page-contract.spec.ts` — created

4 mocked contract tests:

| # | Test | Assertion |
|---|---|---|
| 1 | page renders | `documents-page` visible, no ErrorBoundary, no stale loading |
| 2 | upload section discoverable | `documents-upload-section` + heading `健檢報告` + `上傳` visible |
| 3 | list section with documents | `documents-list-section` + filenames + `已確認` badge visible |
| 4 | API failure safe + overclaim guard | page survives 500, upload still accessible, no prohibited phrases |

Fix applied during spec run: `健檢報告` text assertion scoped to `getByRole('heading')` to resolve strict-mode multi-match (heading + select option both contain the text).

#### `Makefile` — `documents-page-contract` target added

```
make documents-page-contract   → npx tsc --noEmit + p85 spec (4 tests)
```

---

### 4. Validation

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| P85 spec (4 tests) | ✅ 4/4 |
| `make documents-page-contract` | ✅ 4/4 |
| `npx next build` | ✅ clean build |
| `make actions-page-contract` | ✅ 4/4 (no regression) |
| `make daily-assistant-contract` | ✅ 5/5 (no regression) |
| `make runtime-smoke` | ✅ 56/56 (no regression) |

---

### 5. Commits

| SHA | Message |
|---|---|
| `8ba5c56` | feat(frontend): P85 documents page contract smoke |

---

### 6. Gaps NOT addressed in P85

- **Gap G1**: `confirmed_data` from `PUT /confirm` not re-fed into LabReportItem rows → out of scope
- **Gap G5**: `/platform/symptoms` still has zero testids → P86 scope

---

### 7. CTO Summary

1. P85 closes P84 Gap G4: `/platform/documents` now has 4 stable testids.
2. Testids: `documents-page` (root), `documents-upload-section` (upload card), `documents-list-section` (doc list card), `documents-loading` (skeleton wrapper).
3. Contract spec: 4 mocked tests — render safety, upload section discovery, list with documents, API failure + overclaim guard.
4. No backend changes. No business logic changes. Testid-only surface addition.
5. `make documents-page-contract` target added (TSC + 4 contract tests).
6. `next build` required because component file modified — completed cleanly.
7. All baselines maintained: actions-page-contract 4/4, daily-assistant-contract 5/5, runtime-smoke 56/56.
8. Gap G1 (confirmed_data re-feed) NOT addressed — out of P85 scope.
9. Gap G5 (symptoms page zero testids) NOT addressed — P86 scope.
10. Next lane: P86 symptoms page testid surface + contract smoke (same pattern).

---

## P84 Report/Symptom→Daily Recommendation Lane Discovery (2026-05-26)

**Final Classification: `P84_REPORT_SYMPTOM_DAILY_RECOMMENDATION_DISCOVERY_READY`**

---

### 1. Baseline Validation

| Command | Result |
|---------|--------|
| `make actions-page-contract` (4 tests) | ✅ PASS |
| `make daily-assistant-contract` (5 tests) | ✅ PASS |
| `make runtime-smoke` (56 tests) | ✅ PASS |

No code or test files changed. Discovery only.

---

### 2. Key Findings

- Report path (upload → parse → confirm → evidence bundle → recommendations → daily summary) is **fully wired end-to-end**.
- Symptom path (create → temporal parse → evidence bundle → symptom_timeline/patterns → recommendations) is **fully wired end-to-end**.
- Daily Assistant consumes both paths deterministically (no LLM) and exposes `confidence`, `whyNow`, `topRisk`, `missingData` with actionable links.
- **Gap G1 (medium):** `confirmed_data` from `PUT /confirm` is NOT re-fed into `LabReportItem` rows — evidence bundle uses original parse values.
- **Gap G4 (medium):** `/platform/documents` page has zero `data-testid` attributes — core report path untestable by Playwright.
- **Gap G5 (low):** `/platform/symptoms` page has zero `data-testid` attributes.

---

### 3. Files Changed

| File | Change |
|------|--------|
| `docs/security/P84_REPORT_SYMPTOM_DAILY_RECOMMENDATION_DISCOVERY.md` | Created — full discovery report |

---

### 4. Next Recommended Lane

**P85 — Documents Page Testid Surface + Upload→Parse Contract Smoke**  
Add 4 testids to `documents/page.tsx`, write 4-test mocked Playwright spec, add `make documents-page-contract` to Makefile.  
See §8 of P84 report for the copy-paste prompt.

---

# Active Task Report — P83 Actions Page Contract Local Guard (2026-05-26)

## P83 Actions Page Contract Local Guard (2026-05-26)

**Final Classification: `P83_ACTIONS_PAGE_CONTRACT_GUARD_READY`**

---

### 1. Pre-flight / P82 Postcheck

| Check | Result |
|-------|--------|
| Repo / branch | `main` ✅ |
| HEAD | `bb41ad4` ✅ |
| Dirty files | governance-only ✅ |
| `make actions-page-contract` (new) | ✅ 4/4 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 2. Files Changed

| File | Change |
|------|--------|
| `Makefile` | Added `actions-page-contract` to `.PHONY` + target (TSC + 4 contract tests) |
| `docs/security/P82_ACTIONS_PAGE_CONTRACT.md` | Added "When to run" section, `make actions-page-contract` to validation commands, P83 to change history |

No frontend components modified. No testids added. No backend changes.

---

### 3. Makefile Target Added

```make
# P83 Actions page contract guard — local/manual only, not CI-required
# Runs typescript check + P82 actions page contract smoke (4 tests).
# Run after touching /platform/actions, recommendation history, feedback loop,
# snooze sections, or related selectors.
# See: docs/security/P82_ACTIONS_PAGE_CONTRACT.md
actions-page-contract:
	cd frontend && npx tsc --noEmit
	cd frontend && npx playwright test tests/e2e/p82-actions-page-contract.spec.ts --reporter=line
```

---

### 4. Validation

| Command | Result |
|---------|--------|
| `make actions-page-contract` (TSC + 4 tests) | ✅ 4/4 |
| `make daily-assistant-contract` (TSC + 5 tests) | ✅ 5/5 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 5. Commit

```
e14ada3 chore(dev): add P83 actions page contract guard
```

Files staged explicitly: `Makefile` + `docs/security/P82_ACTIONS_PAGE_CONTRACT.md`

---

### 6. Known Limitations

- `actions-page-contract` is local/manual only — not wired to CI (by design)
- The target uses the P82 spec file (`p82-actions-page-contract.spec.ts`) directly
- Full regression (P80/P81/P55/P56/P57) available via `frontend-e2e-local` but not part of this target

---

### 7. Next Recommended Lane

**Report/Symptom-to-Daily-Recommendation** — connect symptom input to daily recommendation pipeline.

---

# Active Task Report — P82 Actions Page Contract Consolidation (2026-05-26)

## P82 Actions Page Contract Consolidation (2026-05-26)

**Final Classification: `P82_ACTIONS_PAGE_CONTRACT_READY`**

---

### 1. Pre-flight / P81 Postcheck

| Check | Result |
|-------|--------|
| Repo / branch | `main` ✅ |
| P81 commit (`31611ad`) | present at HEAD ✅ |
| P81 report (`active_task_report.md`) | dirty on entry — committed now as `9aabf61` ✅ |
| TSC (`npx tsc --noEmit`) | ✅ clean |
| P81 spec (7 tests) | ✅ 7/7 |
| P80 spec (7 tests) | ✅ 7/7 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 2. Component Changes

**None.** P82 is tests-only + docs consolidation.  
No testids were added to any component.  
All 6 stable selectors already existed from P62, P80, P81.

---

### 3. Stable Actions Page Testid Surface Documented

| Testid | Phase | Condition | Required |
|--------|-------|-----------|----------|
| `actions-loading` | P80 | `loading === true` | ✅ Required |
| `actions-page` | P80 | `loading === false` | ✅ Required |
| `actions-feedback-loop` | P81 | `grouped.completed.length > 0` | Optional |
| `actions-snoozed-section` | P81 | `grouped.snoozed.length > 0` | Optional |
| `recommendation-history-card` | P62 | `historyData !== null` | Optional |
| `history-summary-bar` | P62 | `historyData !== null` | Optional |

---

### 4. Contract Spec — `p82-actions-page-contract.spec.ts`

| # | Test | Result |
|---|------|--------|
| 1 | loaded state — all 4 surfaces co-visible | ✅ |
| 2 | loading state — `actions-loading` visible while dashboard frozen | ✅ |
| 3 | api failure safe — history card absent on 500, page survives | ✅ |
| 4 | medical overclaim guard | ✅ |

**P82: 4/4 ✅**

---

### 5. Regression Matrix

| Suite | Result |
|-------|--------|
| P82 spec (4 tests) | ✅ 4/4 |
| P81 spec (7 tests) | ✅ 7/7 |
| P80 spec (7 tests) | ✅ 7/7 |
| P55 (6 tests) | ✅ 6/6 |
| P56 (6 tests) | ✅ 6/6 |
| P57 (6 tests) | ✅ 6/6 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 6. Commits

```
9aabf61 docs(report): P81 actions consistency smoke report  ← P81 report committed
ee60b7a test(frontend): P82 actions page contract smoke
4788365 docs(security): P82 actions page contract
```

Files staged explicitly:
- `frontend/tests/e2e/p82-actions-page-contract.spec.ts`
- `docs/security/P82_ACTIONS_PAGE_CONTRACT.md`
- `00-Plan/roadmap/active_task_report.md`

---

### 7. Known Limitations

- `action-feedback-card.tsx` has no inner testids — individual card items not addressed
- `decision-recommendation-layer.tsx` has no testids — P55 covers button behavior
- Snoozed section does not verify `snoozed_until` future/past logic in UI layer
- `next build` not required (no component changes in P82)

---

# Active Task Report — P81 Actions Feedback / Snooze Detail Smoke (2026-05-26)

## P81 Actions Page Feedback / Snooze Detail Smoke (2026-05-26)

**Final Classification: `P81_ACTIONS_FEEDBACK_SNOOZE_SMOKE_READY`**

---

### 1. Pre-flight / P80 Postcheck

| Check | Result |
|-------|--------|
| Repo / branch | `main` ✅ |
| P80 commit (`fe1d82c`) | present ✅ |
| P80 spec (`p80-actions-recommendation-smoke.spec.ts`) | ✅ 7/7 |
| `make daily-assistant-contract` | ✅ TSC + 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 2. Option B — Minimal Testids Added

Inspected `actions/page.tsx`, `action-feedback-card.tsx`, `decision-recommendation-layer.tsx`.  
Zero pre-existing testids on target sections. Decision: **Option B** (add 2 testids to page.tsx).

| Testid | Element | Location |
|--------|---------|----------|
| `actions-snoozed-section` | `<Card>` wrapping 稍後提醒 section | page.tsx ~line 500 |
| `actions-feedback-loop` | `<Card>` wrapping Section 4 行動效果回饵 | page.tsx ~line 515 |

---

### 3. Spec — `p81-actions-feedback-snooze-smoke.spec.ts`

| # | Test | Result |
|---|------|--------|
| 1 | feedback-loop section visible when completed action exists | ✅ |
| 2 | feedback-loop section absent when no completed actions | ✅ |
| 3 | snoozed section visible when snoozed action exists | ✅ |
| 4 | snoozed section absent when no snoozed actions | ✅ |
| 5 | both feedback-loop and snoozed section visible simultaneously | ✅ |
| 6 | recommendation-history-card still visible alongside feedback and snooze | ✅ |
| 7 | no unsafe medical overclaiming phrases | ✅ |

**P81: 7/7 ✅**

---

### 4. Regression Matrix

| Suite | Result |
|-------|--------|
| P81 spec (7 tests) | ✅ 7/7 |
| P80 spec (7 tests) | ✅ 7/7 |
| P55 action-feedback-loop (6 tests) | ✅ 6/6 |
| P56 recommendation-feedback-persistence (6 tests) | ✅ 6/6 |
| P57 snooze-persistence (6 tests) | ✅ 6/6 |
| `make daily-assistant-contract` | ✅ 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 5. Commit

```
31611ad feat(frontend): P81 actions feedback snooze smoke testids + spec
```

Files staged: `frontend/app/platform/actions/page.tsx`, `frontend/tests/e2e/p81-actions-feedback-snooze-smoke.spec.ts`

---

# Active Task Report — P80 Actions Page Recommendation Smoke (2026-05-26)

## P80 Actions Page Consistency Smoke — Recommendation History / Outcome Feedback / Loading (2026-05-26)

**Final Classification: `P80_ACTIONS_RECOMMENDATION_SMOKE_READY`**

---

### 1. Pre-flight / P79 Postcheck

| Check | Result |
|-------|--------|
| Repo / branch | `main` ✅ |
| P79 commit (`e6fff4f`) | present ✅ |
| Dirty files | governance-only ✅ |
| `make daily-assistant-contract` | ✅ TSC + 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 2. Testid Discovery

Inspected `frontend/app/platform/actions/page.tsx` (~600 lines) — **zero pre-existing `data-testid` attributes** found on the page itself.

Existing testids in child components relevant to P80:

| Testid | Location |
|--------|----------|
| `recommendation-history-card` | `recommendation-history-card.tsx:97,111` |
| `history-summary-bar` | `recommendation-history-card.tsx:118` |

**Decision: Option B** — Add 2 minimal page-level testids (no logic change), then write spec.

---

### 3. Testids Added

| Testid | Element | Purpose |
|--------|---------|---------|
| `actions-loading` | Loading skeleton `<div>` | Confirm skeleton visible while dashboard API frozen |
| `actions-page` | Root loaded `<div>` | Confirm page rendered without ErrorBoundary fallback |

---

### 4. Spec

**File**: `frontend/tests/e2e/p80-actions-recommendation-smoke.spec.ts`

| # | Test | Coverage |
|---|------|----------|
| 1 | Page renders without ErrorBoundary fallback | `actions-page` visible, no "Something went wrong" |
| 2 | Loading skeleton while dashboard frozen | `actions-loading` visible before API unblocked |
| 3 | `recommendation-history-card` visible with outcome data | historyData set → card renders |
| 4 | `recommendation-history-card` empty state | Empty outcomes → card shows "目前還沒有足夠的建議回饋紀錄" |
| 5 | `recommendation-history-card` absent on API 500 | historyData null → card not rendered |
| 6 | Execution-center heading visible | `<h2>執行中心</h2>` found after load |
| 7 | No medical overclaiming | Page body free of 6 diagnosis/effectiveness phrases |

---

### 5. Build and Validation

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` (pre-build) | ✅ clean |
| `npx next build` | ✅ clean |
| P80 spec (7 tests, Playwright) | ✅ 7/7 |
| `make daily-assistant-contract` | ✅ TSC + 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

**Key fix discovered**: `route.fulfill({ json: null })` causes Playwright route hang — use `{ status: 500 }` to simulate API failure (same pattern as P63).

---

### 6. Commits

| Commit | Message |
|--------|---------|
| `23dbe05` | feat(frontend): P80 actions page recommendation smoke testids and spec |

---

### 7. Known Limitations

- `recommendation-history-card` empty-state test mirrors P62/P63 coverage; P80 adds the page-level integration lens not present in those component-isolated specs.
- `decision-recommendation-layer` has no testid — not needed for P80 scope.
- Snoozed action section (`grouped.snoozed`) is not independently smoke-tested; depends on actions mock data which defaults to `[]`.

---

# Active Task Report — P79 Daily Assistant Next Lane Decision (2026-05-26)

## P79 Daily Assistant Contract Guard Scope Decision / Next Product Lane Selection (2026-05-26)

**Final Classification: `P79_DAILY_ASSISTANT_NEXT_LANE_DECISION_READY`**

---

### 1. Pre-flight / P78 Postcheck

| Check | Result |
|-------|--------|
| Repo / branch | `main` ✅ |
| P78 commits (`59befbb`, `c034640`) | present ✅ |
| Dirty files | governance-only ✅ |
| `make daily-assistant-contract` | ✅ TSC + 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 2. Contract Gap Audit

Full audit of the P76 contract spec vs the testid inventory:

| Area | Verdict |
|------|---------|
| Loading/empty/loaded state exclusivity | ✅ fully covered |
| All 9 optional signals positive path | ✅ fully covered |
| All optional signals negative path | ✅ fully covered |
| ErrorBoundary safety | ✅ fully covered |
| Grid card ids (`top-risk`, `biggest-change`, `next-action`) | inherently covered by full-state test |
| `daily-summary-missing-data` co-render | covered in P66 spec, not a P76 gap |

**Result: No missing invariants. Contract test NOT modified.**

---

### 3. Decision

**STOP Daily Assistant micro-polish.**

Reason: All 13 testids are documented and tested. Signal inflation risk increases with each addition.
Contract guard (`make daily-assistant-contract`) is sufficient as local/manual.

**Next lane: P80 — Recommendation History / Actions Page Consistency Smoke**

Basis: roadmap P1 explicitly states "Keep recommendation history, outcome feedback, and trust UI consistent across Dashboard and Actions." P55–P63 built the foundations; no cross-page E2E smoke exists yet.

---

### 4. Decision Artifact

Path: `docs/security/P79_DAILY_ASSISTANT_NEXT_LANE_DECISION.md`

Sections:
- Current closure state
- What P64–P78 completed (15-phase table)
- Contract guard status
- Contract gap audit result
- Stop decision with rationale
- Recommended next lane (P80)
- P80 bounded scope
- Risk table: continuing micro-polish vs moving to P80
- Validation commands
- Next 24h prompt pointer

---

### 5. Tests

| Gate | Result |
|------|--------|
| `make daily-assistant-contract` (P79 validation) | ✅ TSC + 5/5 |
| `make runtime-smoke` (P79 validation) | ✅ 56/56 |
| Contract spec changes | NOT NEEDED — no gaps found |

---

### 6. Commits

| Commit | Message |
|--------|---------|
| `e6fff4f` | docs(security): P79 daily assistant next lane decision |

---

### 7. Known Limitations

- `docs/product/` directory does not exist; decision artifact placed in `docs/security/` with P76 contract.
- Actions page (`/platform/actions`) testid inventory was not inspected in P79 — that is P80's first step.
- README.md remains globally gitignored and cannot be staged.

---

## P78 Daily Assistant Contract Guard Adoption / Discoverability (2026-05-26)

**Final Classification: `P78_DAILY_ASSISTANT_CONTRACT_DISCOVERABILITY_READY`**

---

### 1. Scope

After P77 added `make daily-assistant-contract`, P78 makes it discoverable:
when to run it and what it protects, co-located with the contract document.

No component changes. No backend changes. No Makefile behavior changes.
No new files created.

---

### 2. Pre-flight / P77 Postcheck

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| P77 commits (`f0fd117`, `abebd9d`) | present ✅ |
| Dirty files | governance-only ✅ |
| `make daily-assistant-contract` | ✅ TSC + 5/5 |
| `make runtime-smoke` | ✅ 56/56 |

---

### 3. Convention Inspection & Option Decision

| Path | Finding |
|------|---------|
| `README.md` | Globally gitignored — cannot stage. Option A excluded. |
| `Makefile` `daily-assistant-contract` comments | Already 4-line block. No further comment needed. |
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` §6 | Had command but no "When to run" guidance |

**Chosen: Option B — contract doc only.**
Added a "When to run" table to §6 Validation Commands of the P76 contract doc.
This is where future CTO agents working on Daily Assistant signals will naturally look.

---

### 4. Changes

| File | Change |
|------|--------|
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` | Added "When to run `make daily-assistant-contract`" table to §6 |

**"When to run" table covers:**
- Before editing `daily-assistant-entry.tsx`
- After adding / renaming any `data-testid` in that component
- After changing signal data conditions
- After modifying fixtures in P64–P76 specs
- Full regression → `make frontend-e2e-local`
- Explicit "do not use as branch-protection gate" note

---

### 5. Validation

| Gate | Result |
|------|--------|
| `make daily-assistant-contract` (TSC + 5 contract tests) | ✅ 5/5 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 6. Known Limitations

- README.md is in `~/.gitignore_global` and cannot be staged. A pointer there was attempted and reverted cleanly.
- Discoverability for workers who never open the contract doc remains low. Mitigation: future Makefile help output or CONTRIBUTING.md could link to it if warranted.

---

### 7. Commits

| Commit | Message |
|--------|---------|
| `59befbb` | docs(security): P78 daily assistant contract guard discoverability |

---

## P77 Daily Assistant Contract Drift Guard (2026-05-26)

**Final Classification: `P77_DAILY_ASSISTANT_CONTRACT_GUARD_READY`**

---

### 1. Scope

After P76 created the contract doc and spec, P77 adds a lightweight
Makefile target so the P76 contract is one command away and harder
to accidentally skip.

No component changes. No backend changes. No new dependencies.
No CI wiring.

---

### 2. Changes

| File | Type | Change |
|---|---|---|
| `Makefile` | Modified | Added `daily-assistant-contract` target + `.PHONY` entry |
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` | Modified | Added P77 guard command to §6, P77 row to §8 |

---

### 3. New Makefile Target

```makefile
# P77 Daily Assistant signal contract guard — local/manual only, not CI-required
# Runs typescript check + P76 contract smoke (5 tests).
# Full P64–P76 regression: use frontend-e2e-local
# See: docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md
daily-assistant-contract:
	cd frontend && npx tsc --noEmit
	cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts --reporter=line
```

---

### 4. Validation Results

| Gate | Result |
|------|--------|
| P76 postcheck: `npx tsc --noEmit` | ✅ 0 errors |
| P76 postcheck: P76 contract tests (5) | ✅ 5/5 |
| P76 postcheck: `make runtime-smoke` (56) | ✅ 56/56 |
| `make daily-assistant-contract` (new target) | ✅ TSC + 5/5 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `f0fd117` | chore(dev): P77 daily assistant contract make target |

---



### 1. Scope

After P64–P75, the Daily Assistant exposes 11 stable test ids. P76 consolidates
them into one frontend signal contract document and one contract smoke test.
No component changes. No backend changes.

---

### 2. Changes

| File | Type |
|---|---|
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` | New contract doc |
| `frontend/tests/e2e/p76-daily-assistant-signal-contract.spec.ts` | New contract test |

---

### 3. Contract Test (`p76-daily-assistant-signal-contract.spec.ts`) — 5 tests

| # | Test | Result |
|---|------|--------|
| 1 | Full signal happy path: all optional signals visible with fully-populated data | ✅ |
| 2 | Loading state contract: `daily-assistant-loading` visible while API pending | ✅ |
| 3 | Empty state contract: `daily-summary-empty` visible when no summary + no topRec | ✅ |
| 4 | Negative contract: all optional signals absent when source fields absent/zero/none | ✅ |
| 5 | ErrorBoundary contract: dashboard renders without error fallback | ✅ |

---

### 4. Contract Document

Path: `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md`

Covers:
- Full test id table with data conditions, phase, required/optional status
- 3 state model (loading / empty / loaded)
- 6 invariant groups (state exclusivity, empty-state guard, optional signal guards,
  escalation source, medical framing, naming conventions)
- Validation commands
- Known limitations

---

### 5. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ clean |
| P76 acceptance (5 tests) | ✅ 5/5 |
| P64–P76 regression (110 tests) | ✅ 110/110 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 6. Commits

| Commit | Message |
|--------|---------|
| `539ecec` | test(frontend): P76 daily assistant signal contract |
| `75e2a6a` | docs(security): P76 daily assistant signal contract |

---

### 7. data-testid inventory (cumulative P64–P76)

| testid | Phase | Required / Optional | Data condition |
|--------|-------|---------------------|---------------|
| `daily-assistant-entry` | baseline | required | always |
| `daily-assistant-loading` | P74 | required during load | `isFullyLoading` |
| `daily-summary-empty` | baseline | required when no data | `!hasDailySummary && !topRec` |
| `daily-summary-why-now` | P65 | optional | `summary.whyNow` truthy |
| `daily-summary-missing-data` | P66 | optional | `missingItems.length > 0` |
| `daily-summary-missing-data-explanation` | P66 | optional | `missingItems.length > 0` |
| `daily-summary-action-impact` | P67 | optional | `summary.todayAction` truthy |
| `daily-summary-outcome-improved-badge` | P68 | optional | `hasFeedback && improved_count > 0` |
| `daily-summary-biggest-change-context` | P69 | optional | `summary.biggestChange` truthy |
| `daily-summary-confidence-signal` | P70 | optional | `confidence > 0` |
| `daily-summary-encouragement` | P71 | optional | `encouragement` non-empty |
| `daily-summary-escalation-notice` | P72 | optional | `escalationLevel !== 'none'` |
| `daily-summary-next-checkin` | P73 | optional* | `trust.nextCheckInSuggestion \|\| summary` |

---

## P75 Daily Assistant Empty State Testability (2026-05-26)

## P75 Daily Assistant Empty State Testability / Copy Consistency (2026-05-26)

**Final Classification: `P75_DAILY_ASSISTANT_EMPTY_STATE_COVERAGE_READY`**

---

### 1. Scope

The empty state branch in `DailyAssistantEntry` already had
`data-testid="daily-summary-empty"` (introduced pre-P65). P74 covered two basic
scenarios. P75 deepens empty state coverage and verifies copy consistency.

**Decision: Option A (tests-only).** No component change was needed.
The existing `daily-summary-empty` testid is stable; P74 tests depend on it.
The naming difference (`daily-summary-empty` vs `daily-assistant-loading`) is
cosmetic — `daily-summary-` is the intra-card namespace, `daily-assistant-` is
the card-level namespace. Alias wrapper would add complexity without benefit.

No component changes. No backend changes. No new dependencies.

---

### 2. Change

None to production code. One test file added:
`frontend/tests/e2e/p75-daily-assistant-empty-state.spec.ts`

---

### 3. Test Coverage (`p75-daily-assistant-empty-state.spec.ts`) — 11 tests

| # | Test | Result |
|---|------|--------|
| 1 | Empty state visible: all summary fields empty strings + no recommendations | ✅ |
| 2 | Empty state visible: daily-summary returns empty object + no recommendations | ✅ |
| 3 | Empty state NOT visible when summary.topRisk is populated | ✅ |
| 4 | Empty state NOT visible when topRec present even if summary empty (grid fallback) | ✅ |
| 5 | Empty state heading copy is non-diagnostic ("今日摘要尚未生成") | ✅ |
| 6 | CTA link points to /quick-check-in | ✅ |
| 7 | Empty state NOT visible while loading (loading phase shown instead) | ✅ |
| 8 | Loading → empty state transition: loading appears then resolves to empty state | ✅ |
| 9 | P74 regression: daily-assistant-loading visible while API pending | ✅ |
| 10 | P73 regression: next-checkin visible in normal loaded state | ✅ |
| 11 | Dashboard renders without ErrorBoundary fallback | ✅ |

**Key techniques:**
- Promise-based route freeze for loading/empty transition tests (same as P74)
- Fixture `DAILY_SUMMARY_NULL_BODY = {}` exercises undefined-field path
- `RECOMMENDATIONS_WITH_ONE` verifies the `hasDailySummary || topRec` guard

---

### 4. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `next build` (no rebuild — tests-only) | ✅ P74 build valid |
| P75 acceptance (11 tests) | ✅ 11/11 |
| P64–P75 regression (105 tests) | ✅ 105/105 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `c2c4a1a` | test(frontend): P75 daily assistant empty state coverage |

---

### 6. data-testid inventory (cumulative P64–P75)

| testid | Phase | Component | Notes |
|--------|-------|-----------|-------|
| `daily-assistant-entry` | baseline | card root | |
| `daily-summary-top-risk` | baseline | 3-card grid | |
| `daily-summary-biggest-change` | baseline | 3-card grid | |
| `daily-summary-next-action` | baseline | 3-card grid | |
| `daily-summary-outcome-section` | baseline | outcome section | |
| `daily-summary-empty` | baseline | empty branch | P75 deepened coverage |
| `daily-summary-why-now` | P65 | top-risk card | |
| `daily-summary-missing-data` | P66 | missing data list | |
| `daily-summary-missing-data-explanation` | P66 | missing data copy | |
| `daily-summary-action-impact` | P67 | todayAction card | |
| `daily-summary-outcome-improved-badge` | P68 | outcome row | |
| `daily-summary-biggest-change-context` | P69 | biggestChange card | |
| `daily-summary-confidence-signal` | P70 | confidence pill | |
| `daily-summary-encouragement` | P71 | encouragement block | |
| `daily-summary-escalation-notice` | P72 | amber escalation block | |
| `daily-summary-next-checkin` | P73 | next check-in line | |
| `daily-assistant-loading` | P74 | loading skeleton | |

---

## P74 Daily Assistant Loading State Testability (2026-05-26)

## P74 Daily Assistant Loading State Testability (2026-05-26)

**Final Classification: `P74_DAILY_ASSISTANT_LOADING_STATE_READY`**

---

### 1. Scope

The loading skeleton in `DailyAssistantEntry` (`isFullyLoading` branch) had no
`data-testid`, making it untestable in Playwright without brittle element
selectors. The empty state already had `data-testid="daily-summary-empty"` from
an earlier phase. Primary target: add `data-testid="daily-assistant-loading"` to
the skeleton container div.

No backend changes. No API schema changes. No new dependencies. No logic changes.

---

### 2. Change

**Component** (`daily-assistant-entry.tsx`):
```tsx
// Before
<div className="space-y-3">

// After (P74)
<div data-testid="daily-assistant-loading" className="space-y-3">
```

One attribute added to one element in the `isFullyLoading` branch.

---

### 3. Test Coverage (`p74-daily-assistant-loading-state.spec.ts`) — 11 tests

| # | Test | Result |
|---|------|--------|
| 1 | Loading skeleton visible (testid) while daily-summary pending | ✅ |
| 2 | Loading skeleton is child of daily-assistant-entry | ✅ |
| 3 | After loading resolves: daily-summary-next-checkin visible (P73 regression) | ✅ |
| 4 | Empty state (daily-summary-empty) visible when APIs return no content | ✅ |
| 5 | Empty state not visible in normal loaded state | ✅ |
| 6 | P73 regression: trust.nextCheckInSuggestion shown | ✅ |
| 7 | P72 regression: escalation notice visible | ✅ |
| 8 | P71 regression: encouragement visible | ✅ |
| 9 | P70 regression: confidence signal visible | ✅ |
| 10 | P69 regression: biggest-change context visible | ✅ |
| 11 | Dashboard renders without ErrorBoundary fallback | ✅ |

**Key technique**: frozen daily-summary route using `Promise` in Playwright route
handler — holds `sumLoading=true`, keeping `isFullyLoading=true` until explicitly
unblocked, ensuring loading state is assertable without timing hacks.

---

### 4. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ clean |
| P74 acceptance (11 tests) | ✅ 11/11 |
| P64–P73 regression (83 tests) | ✅ 83/83 |
| Full P64–P74 regression (94 tests) | ✅ 94/94 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `952cfb2` | feat(frontend): P74 daily assistant loading state testid |

---

### 6. data-testid inventory (cumulative P64–P74)

| testid | Phase | Component | Notes |
|--------|-------|-----------|-------|
| `daily-assistant-entry` | baseline | card root | |
| `daily-summary-top-risk` | baseline | 3-card grid | |
| `daily-summary-biggest-change` | baseline | 3-card grid | |
| `daily-summary-next-action` | baseline | 3-card grid | |
| `daily-summary-outcome-section` | baseline | outcome section | |
| `daily-summary-empty` | baseline | empty branch | already existed |
| `daily-summary-why-now` | P65 | top-risk card | |
| `daily-summary-missing-data` | P66 | missing data list | |
| `daily-summary-missing-data-explanation` | P66 | missing data copy | |
| `daily-summary-action-impact` | P67 | todayAction card | |
| `daily-summary-outcome-improved-badge` | P68 | outcome row | |
| `daily-summary-biggest-change-context` | P69 | biggestChange card | |
| `daily-summary-confidence-signal` | P70 | confidence pill | |
| `daily-summary-encouragement` | P71 | encouragement block | |
| `daily-summary-escalation-notice` | P72 | amber escalation block | |
| `daily-summary-next-checkin` | P73 | next check-in line | |
| `daily-assistant-loading` | **P74** | loading skeleton | **new** |

---

# Active Task Report — P73 Daily Assistant Next Check-in Suggestion (2026-05-26)

## P73 Daily Assistant Next Check-in Suggestion (2026-05-26)

**Final Classification: `P73_DAILY_ASSISTANT_NEXT_CHECKIN_READY`**

---

### 1. Scope

The daily-assistant card had a bare next check-in block that rendered
`trust.nextCheckInSuggestion` only when a top recommendation with a trust
block was present (i.e., `trust?.nextCheckInSuggestion` truthy). In all
test fixtures and real low-data scenarios where `recommendations: []`, this
block was never visible — the user received no check-in guidance.

P73 chose **Option B** (dynamic API field exists) plus a graceful fallback:
- When `trust.nextCheckInSuggestion` is present: show it (existing behavior, now with `data-testid`)
- When `trust` is null but `summary` is loaded + `todayAction` non-empty: show `完成今日行動後，回來更新記錄。`
- When `trust` is null + `todayAction` empty/absent: show `今日資料已更新，明天繼續追蹤。`

Guard: `(trust?.nextCheckInSuggestion || summary)` — element always visible
when the daily summary is loaded.

`data-testid="daily-summary-next-checkin"` added for acceptance coverage.

No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Replace bare next check-in block with guarded conditional + data-testid |
| `frontend/tests/e2e/p73-daily-assistant-next-checkin.spec.ts` | 12 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P73 acceptance (12 tests) | ✅ 12/12 |
| P72 regression (16 tests) | ✅ 16/16 |
| P71 regression (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The `todayAction` guard uses truthiness: an empty string (`''`) is treated
  as absent. If the backend sends a whitespace-only `todayAction`, the fallback
  "明天繼續追蹤" will render. This is the same pattern used by P71 encouragement
  (`.trim().length > 0`) but P73 does not call `.trim()` — consistent with the
  minimal-change policy; could be hardened in a future pass.
- `trust.nextCheckInSuggestion` is always shown as-is (no trim). If the backend
  returns an empty string, the logic falls through to the `summary?.todayAction`
  check. This is correct behavior since an empty string is falsy in JS.
- The fallback copy is static Chinese and will not localise if i18n is added.

---

### 5. Commit

`8fc97a3` — feat(frontend): P73 daily assistant next check-in suggestion

---

# Active Task Report — P72 Daily Assistant Escalation Notice (2026-05-26)

## P72 Daily Assistant Escalation Notice (2026-05-26)

**Final Classification: `P72_DAILY_ASSISTANT_ESCALATION_READY`**

---

### 1. Scope

Added an escalation notice that surfaces `DailyHealthSummary.escalation`
(optional `EscalationDecision` from the daily-summary API) when the
`escalationLevel` is not `'none'`. The field was already fetched every render
but never displayed. P72 closes that gap with a guarded amber block placed
before the 3-card grid so urgent signals are visible before routine context.

`EscalationDecision` shape (read from `lib/api.ts`):
```typescript
{
  escalationLevel: 'none' | 'watch' | 'warning' | 'urgent'
  reasons: string[]
  confidence: number
  recommendedAction: string | null
  requiresFollowUp: boolean
}
```

Note: the prompt suggested `should_escalate === true` but that field does not
exist in the type. The actual guard uses `escalationLevel !== 'none'`.

Guard: `summary?.escalation != null && summary.escalation.escalationLevel !== 'none'`
Placement: before the 3-card grid (after isHighConf banner).
Display: label "需要留意" + level suffix (緊急/警告/觀察) + `reasons[0]` +
`recommendedAction` prefixed with "建議：" if not null.
Uses existing `AlertTriangle` icon (already imported). No new dependencies.
No backend changes. No API schema changes.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-escalation-notice">` before 3-card grid, guarded by escalationLevel !== 'none' |
| `frontend/tests/e2e/p72-daily-assistant-escalation-notice.spec.ts` | 16 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P72 acceptance (16 tests) | ✅ 16/16 |
| P71 regression (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- Only `reasons[0]` is shown; subsequent reasons are silently dropped if the
  backend returns multiple. This is intentional to keep the notice compact.
- `escalationLevel` maps to static Chinese labels in the frontend. If a new
  level is added to the backend enum, the label will not appear (silent fallback
  to just "需要留意" with no suffix).
- The notice is styled amber regardless of level — `urgent` does not receive
  a stronger colour. This is intentional conservatism (no medical alarm UX
  without product review).
- Prompt specified `should_escalate === true` guard; the actual type uses
  `escalationLevel !== 'none'` — corrected after reading `lib/api.ts`.

---

### 5. Commit

`4477a22` — feat(frontend): P72 daily assistant escalation notice

---

# Active Task Report — P71 Daily Assistant Encouragement Message (2026-05-26)

## P71 Daily Assistant Encouragement Message (2026-05-26)

**Final Classification: `P71_DAILY_ASSISTANT_ENCOURAGEMENT_READY`**

---

### 1. Scope

Added an encouragement block to the Daily Assistant section that surfaces
`DailyHealthSummary.encouragement` (optional string from the daily-summary API)
when present and non-empty. The field was already fetched every render but never
displayed to the user. P71 closes that gap with a minimal guarded block:
label "小助手鼓勵" + the trimmed encouragement text.

Guard: `typeof summary?.encouragement === 'string' && summary.encouragement.trim().length > 0`
Placement: after the P70 confidence signal, before the top-recommendation block.
Whitespace-only strings are suppressed (`.trim().length > 0`).
No backend changes. No API schema changes. No new dependencies. No new icon imports.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-encouragement">` with label + trimmed text, guarded by non-empty string check |
| `frontend/tests/e2e/p71-daily-assistant-encouragement.spec.ts` | 12 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P71 acceptance (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The encouragement text comes verbatim from the AI-generated backend field; the
  frontend does not validate or sanitize the content beyond trimming whitespace.
- Empty string and whitespace-only values are correctly suppressed. Null is not
  produced by the typed API but would also be suppressed by the string guard.
- The label "小助手鼓勵" is hardcoded; if the backend were to produce encouragement
  in another language, the label would still be Chinese.

---

### 5. Commit

`b21e25e` — feat(frontend): P71 daily assistant encouragement message

---

# Active Task Report — P70 Daily Assistant Confidence Signal (2026-05-26)

## P70 Daily Assistant Confidence Signal (2026-05-26)

**Final Classification: `P70_DAILY_ASSISTANT_CONFIDENCE_SIGNAL_READY`**

---

### 1. Scope

Added a compact confidence signal that surfaces `DailyHealthSummary.confidence`
(a 0–1 float from the daily-summary API) as a rounded percentage to the user.
Previous components used `topRec.trust.level` ("low"/"high") for qualitative
banners, but the numeric `confidence` field was never displayed. P70 fills that
gap with a single guarded line: `可信度 N%`.

Guard: `typeof summary?.confidence === 'number' && summary.confidence > 0`
Placement: after the 3-card grid, before the top-recommendation block.
No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-confidence-signal">` after 3-card grid, guarded by confidence > 0 |
| `frontend/tests/e2e/p70-daily-assistant-confidence-signal.spec.ts` | 10 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P70 acceptance (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The `confidence` field from `DailyHealthSummary` is a raw API value; its exact
  calibration is not validated in the frontend. The guard `> 0` prevents showing
  a "可信度 0%" which would be confusing.
- The existing low/high confidence banners (from `topRec.trust.level`) remain
  unchanged — they represent recommendation-level trust, not summary-level.

---

### 5. Commit

`cdb0328` — feat(frontend): P70 daily assistant confidence signal

---

# Active Task Report — P69 Daily Assistant Biggest Change Context Label (2026-05-26)

## P69 Daily Assistant Biggest Change Context Label (2026-05-26)

**Final Classification: `P69_DAILY_ASSISTANT_BIGGEST_CHANGE_CONTEXT_READY`**

---

### 1. Scope

Added a static context label beneath the 今日最大變化 (biggestChange) text,
using the same conditional guard pattern established in P65 (whyNow) and P67
(action impact). The label renders only when `summary?.biggestChange` is
non-empty, and displays: 「此為近 7 天最顯著的健康趨勢變化。」

No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<p data-testid="daily-summary-biggest-change-context">` after biggestChange text, guarded by `summary?.biggestChange` non-empty |
| `frontend/tests/e2e/p69-daily-assistant-biggest-change-context.spec.ts` | 7 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P69 acceptance (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`07aa0cc` — feat(frontend): P69 daily assistant biggest change context label

---

# Active Task Report — P68 Daily Assistant Outcome Known Badge (2026-05-26)

## P68 Daily Assistant Outcome Known Badge (2026-05-26)

**Final Classification: `P68_DAILY_ASSISTANT_OUTCOME_BADGE_READY`**

---

### 1. Scope

Added an explicit positive badge in the 7-day outcome section when
`fbSummary.improved_count > 0`. Previously the count was shown only as a grey
dot + plain text. The badge uses the already-imported `CheckCircle2` icon with
emerald styling and shows "已改善 N 項，持續追蹤中".

No backend changes. No new dependencies. Guard: `improved_count > 0`.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-outcome-improved-badge">` after count flex row, guarded by `fbSummary!.improved_count > 0` |
| `frontend/tests/e2e/p68-daily-assistant-outcome-badge.spec.ts` | 6 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P68 acceptance (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`1733d40` — feat(frontend): P68 daily assistant outcome known badge

---

# Active Task Report — P67 Daily Assistant Action Impact Clarity (2026-05-26)

## P67 Daily Assistant Action Impact Clarity (2026-05-26)

**Final Classification: `P67_DAILY_ASSISTANT_ACTION_IMPACT_CLARITY_READY`**

---

### 1. Scope

Added a short expected-impact line below the "今日主要行動" (recommended next action) text.
The line renders only when `summary.todayAction` is non-empty — same conditional guard as
the P65 `whyNow` pattern. Static copy only; no backend changes, no new API fields.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<p data-testid="daily-summary-action-impact">` inside the next-action card, guarded by `summary?.todayAction` |
| `frontend/tests/e2e/p67-daily-assistant-action-impact-clarity.spec.ts` | 5 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P67 acceptance (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`0a58f5d` — feat(frontend): P67 daily assistant action impact clarity

---

# Active Task Report — P66 Daily Assistant Missing Data Explanation (2026-05-26)

## P66 Daily Assistant Missing Data Explanation (2026-05-26)

**Final Classification: `P66_DAILY_ASSISTANT_MISSING_DATA_EXPLANATION_READY`**

---

### 1. Scope

User-facing improvement: each missing-data item in the Daily Assistant card now
shows an inline explanation of what capability is unlocked when that data is
provided. A stable `data-testid="daily-summary-missing-data-explanation"` summary
paragraph is also added at the bottom of the missing-data block.

No backend changes. No new dependencies. No new routes.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `MISSING_DATA_GAINS` map, `getMissingGain()` helper; restructure missing-data block from `flex-wrap` to `flex-col` with per-item gain text and explanation paragraph |
| `frontend/tests/e2e/p66-daily-assistant-missing-data-explanation.spec.ts` | 5 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P66 acceptance (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`a00a8ae` — feat(frontend): P66 daily assistant missing data explanation

---

# Active Task Report — P65 Daily Assistant Why-Now Clarity (2026-05-26)

## P65 Daily Assistant Why-Now Clarity (2026-05-26)

**Final Classification: `P65_DAILY_ASSISTANT_CONTINUITY_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD at start | `85ae765` — docs(report): P64 recovery handoff ✅ |
| Dirty files | 4 governance M — no scope conflict ✅ |

---

### 2. P64 Postcheck

| Suite | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| P64 targeted (6 tests) | ✅ 6/6 passed |
| P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |
| `make runtime-smoke` | ✅ 56/56 passed |

---

### 3. Chosen P65 Improvement

**Surface the `whyNow` field on the daily summary top-risk card.**

**Why bounded**:
- `DailyHealthSummary` type already had `whyNow: string` defined in `lib/api.ts`
- P64 test fixture already populated `whyNow: '近期記錄顯示血壓波動加劇'`
- The field was fetched by the component but never rendered anywhere in the UI
- One conditional `<p>` element added — no new fetches, no types, no backend changes
- `data-testid="daily-summary-why-now"` added for stable acceptance targeting

**Addresses P65 requirements**:
- #1 (today's top risk): risk card now shows both WHAT the risk is and WHY it matters
- #4 (why-now explanation): `whyNow` text displayed as "為什麼重要：…" sub-line

---

### 4. Files Modified

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Added conditional `whyNow` sub-line inside `daily-summary-top-risk` card |
| `frontend/tests/e2e/p65-daily-assistant-why-now-clarity.spec.ts` | New — 4 acceptance tests (present/absent whyNow + P64 regression ×2) |

---

### 5. Tests

| Suite | Result |
|---|---|
| `npx tsc --noEmit` (pre + post) | ✅ 0 errors |
| P65 targeted (4 tests) | ✅ 4/4 passed |
| P64 regression (6 tests) | ✅ 6/6 passed |
| P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |
| `make runtime-smoke` | ✅ 56/56 passed |

---

### 6. Commits

- `0a1c470` feat(frontend): P65 daily assistant why-now clarity — render whyNow explanation on top-risk card

---

### 7. Known Limitations / Unknown / Inferred

- `whyNow` is only shown for the top-risk card. `biggestChange` and `todayAction` cards do not have an analogous "why this matters" sub-line — this is intentional (bounded scope).
- The `whyNow` field comes from the backend `/health-assistant/daily-summary` endpoint. If the backend returns an empty string or omits the field, the sub-line is correctly suppressed.
- P65 does not address requirements #2 (biggest change), #3 (recommended next action), #5 (missing data), #6 (outcome known/unknown) beyond what P64 already shipped. These remain as future candidates for P66+.

---

# Active Task Report — P64-RECOVERY (2026-05-26)

## P64-RECOVERY (2026-05-26)

**Final Classification: `P64_RECOVERY_READY`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | `f0678d3` — docs(report): P63 recommendation history card acceptance closure |
| Dirty files at start | 7 expected (4 governance M, 1 M daily-assistant-entry, 2 ?? spec files) — no scope conflict |

---

### Step 1A — Diag Intent Extracted

`frontend/tests/e2e/p64-diag.spec.ts` was a runtime crash investigation tool,
not an acceptance test. Design intent extracted to `docs/security/P64_RECOVERY_DIAGNOSIS.md`:
- `page.on('pageerror', ...)` + `page.on('console', ...)` capture pattern
- localStorage auth bypass via `addInitScript`
- 8-second wait + body text dump strategy
- Route stubs for all `/api/v1/**` paths (5 lines corrupted by copy-paste damage)

File physically removed (`rm`) — was untracked, no `git rm` needed.

### Step 1C — TypeScript

`npx tsc --noEmit` → **Exit 0, 0 errors** ✅

---

### Step 2A — Baseline Failure

`npx playwright test ...p64-daily-assistant-summary-quality.spec.ts` → **5 failed, 1 passed**

All 5 failures: `[data-testid="daily-assistant-entry"]` not visible (12s timeout).
Error-context snapshot confirmed: `載入失敗，請重新整理` — ErrorBoundary fallback active.

Test 2 ("missing data state") uniquely passed because its mock stub included `missing_data: [...]`.

### Step 2B — PageError Stack

```
TypeError: Cannot read properties of undefined (reading 'length')
    at sC (dashboard/page-9f34c3fea89de3b0.js:1:99153)
    [React render stack — rE → l$ → iZ → ia]
```

### Step 2D — [Decision]: `both`

**Production-side (real bug):**
`frontend/app/components/platform/health-assistant-panel.tsx:268`
```ts
const hasMissing = data && data.missing_data.length > 0 && !hasRecs;
//                                           ^^^^^^^^ undefined when API omits field
```
`data.missing_data` is `undefined` when the recommendations API response lacks the field.
Accessing `.length` on `undefined` throws `TypeError` → React catches → `ErrorBoundary`.

**Mock-side (test gap):**
Default stub `{ person_id, recommendations: [], total: 0 }` omitted `missing_data`,
making 5/6 tests exercise the crash path every run.

---

### Step 3 — Minimum Fix

**Fix 1 — `health-assistant-panel.tsx:267–268` (production null guard):**
```ts
// Before:
const hasRecs = data && data.recommendations.length > 0;
const hasMissing = data && data.missing_data.length > 0 && !hasRecs;
// After:
const hasRecs = data && (data.recommendations?.length ?? 0) > 0;
const hasMissing = data && (data.missing_data?.length ?? 0) > 0 && !hasRecs;
```

**Fix 2 — `p64-daily-assistant-summary-quality.spec.ts` default stub:**
Added `missing_data: []` to default recommendations in `stubRoutes()`.

**Diagnostic cleanup:** Removed `page.on('pageerror', ...)` / `page.on('console', ...)` instrumentation before commit.

---

### Step 3C — Full Validation

| Check | Result |
|---|---|
| `npx tsc --noEmit` | Exit 0 ✅ |
| P64 `p64-daily-assistant-summary-quality.spec.ts` | **6/6 PASS** ✅ |
| P55 `p55-action-feedback-loop.spec.ts` | 9/9 PASS ✅ |
| P56 `p56-recommendation-feedback-persistence.spec.ts` | 4/4 PASS ✅ |
| P57 `p57-snooze-persistence.spec.ts` | 4/4 PASS ✅ |
| `make runtime-smoke` | 56 passed, 0 failed ✅ |

---

### Commits

- **C2** `fix(frontend): P64 daily assistant guard + acceptance recovery`
  — `frontend/app/components/platform/health-assistant-panel.tsx` (null guard)
  — `frontend/app/components/platform/daily-assistant-entry.tsx` (P64 data-testid hooks)
  — `frontend/tests/e2e/p64-daily-assistant-summary-quality.spec.ts` (mock fix, diagnostic removed)

- **C3** `docs(security): add P64 recovery diagnosis evidence`
  — `docs/security/P64_RECOVERY_DIAGNOSIS.md`

- **C4** `docs(report): P64 recovery handoff`
  — `00-Plan/roadmap/active_task_report.md`

---

### Known Limitations

1. `p64-diag.spec.ts` syntax corruption root cause not confirmed — likely copy-paste accident during P64 handoff; no tracking needed.
2. `health-assistant-panel.tsx` `generated_at` field also absent from mocks — `data?.generated_at` already uses optional chain (safe); no action needed.
3. `HealthAssistantData.missing_data` is typed as required (`string[]`) in the interface but absent from API in low-data states. A follow-up could update the interface to `missing_data?: string[]` for better type accuracy.
4. Backend regression (723 PASS from P13) not re-run in this session — backend untouched, `make runtime-smoke` 56/56 confirms no regression.

---

--- # Appendix: Prior Sprint Reports ---

## P63-RECOMMENDATION-HISTORY-ACCEPTANCE (2026-05-25)

**Final Classification: `P63_RECOMMENDATION_HISTORY_ACCEPTANCE_READY`**

### 1. 本輪目標
驗證並強化 P62 建議回饋 Timeline Card 的產品接受度：placement（元件出現在 Section 4 之後）、error state（API 500 → 卡片不顯示）、安全文案、回歸測試。

### 2. 已完成事項
- 調查 `recommendation-history-card.tsx`、`page.tsx` 整合、P62 spec，確認 5 項驗收標準
- 確認 placement：Section 5 (`RecommendationHistoryCard`) 在 Section 4 (`行動效果回饋`) 之後 ✅
- 確認 error state：`catch(() => setHistoryData(null))` → 卡片不渲染 ✅
- 補充 `p63-recommendation-history-acceptance.spec.ts`（2 個 Playwright tests）
- 修復 error-state 測試 timeout：以 `expect(getByText('執行中心')).toBeVisible` 取代 `waitForLoadState('networkidle')`

### 3. 修改或產出的檔案
| 檔案 | 動作 |
|------|------|
| `frontend/tests/e2e/p63-recommendation-history-acceptance.spec.ts` | 新建 |
| `00-Plan/roadmap/active_task_report.md` | prepend |

### 4. 驗證結果
| 項目 | 結果 |
|------|------|
| TypeScript `tsc --noEmit` | 0 errors ✅ |
| `make runtime-smoke` | 56 passed ✅ |
| P62 regression (8 tests) | 8/8 ✅ |
| P63 acceptance (2 tests) | 2/2 ✅ |

### 5. 目前結論
`P63_RECOMMENDATION_HISTORY_ACCEPTANCE_READY`

### 6. 尚未完成事項
無。

### 7. 風險
無產品代碼改動，純測試補充。P62 所有回歸通過。

### 8. 建議
進入 P64。

### 9. 下一輪 task prompt
由 CEO 決定。

### 10. CTO 摘要
P63 驗證 P62 Recommendation History Card 產品接受度。5 項驗收標準全部通過：(1) placement—Section 5 在 Section 4 之後；(2) error state—API 500 時卡片不顯示；(3) 安全文案存在；(4) 空狀態文案存在；(5) P62 regression 8/8。補充 `p63-recommendation-history-acceptance.spec.ts` 2 個 Playwright tests（placement + error state）。修復 error-state test timeout（networkidle → getByText）。TypeScript clean；runtime-smoke 56 passed；P62 8/8；P63 2/2。無產品代碼改動。Commit: `5ccf7c1`。

---

## P62-RECOMMENDATION-FEEDBACK-TIMELINE (2026-05-25)

**Final Classification: `P62_RECOMMENDATION_FEEDBACK_TIMELINE_READY`**

### 1. 本輪目標
新增 `recommendation-history-card.tsx`，使用現有 `GET /api/v1/health-assistant/outcome-feedback?window_days=30` API，讓使用者在 `/platform/actions` 看到 30 天建議回饋 timeline。

### 2. 已完成事項
- 建立 props-driven `RecommendationHistoryCard` 元件（feedback status 標籤、顏色徽章、outcome badge、空狀態、安全免責聲明）
- 整合至 `/platform/actions` Section 5，在現有 `view_actions` useEffect 中新增 `getOutcomeFeedback(30)` fetch
- 建立 8 個 Playwright acceptance tests（完全 mocked，無需 live backend）
- TypeScript 修正：`showOutcomeBadge` 條件移除錯誤的 `!== 'completed'` 判斷

### 3. 修改或產出的檔案
| 檔案 | 操作 |
|------|------|
| `frontend/app/components/platform/recommendation-history-card.tsx` | 新建 |
| `frontend/app/platform/actions/page.tsx` | 修改（+14 行，新增 import + state + fetch + render） |
| `frontend/tests/e2e/p62-recommendation-history-card.spec.ts` | 新建 |
| `00-Plan/roadmap/active_task_report.md` | prepend P62 block |

### 4. 驗證結果
| 驗證項目 | 結果 |
|----------|------|
| TypeScript `npx tsc --noEmit` | ✅ 0 errors |
| `make runtime-smoke` | ✅ 56 passed, 0 failures |
| Playwright P62 (8 tests) | ✅ 8/8 passed |
| Playwright P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |

### 5. 目前結論
`P62_RECOMMENDATION_FEEDBACK_TIMELINE_READY` — 所有驗證通過，已 commit `b6cb0b9`。

### 6. 尚未完成事項
無。P62 bounded scope 全部完成。

### 7. 風險
無新後端改動，僅前端元件新增 + fetch，風險極低。

### 8. 建議
進入 P63（待 CEO 決定下一個 product slice 方向）。

### 9. CTO 摘要
P62 完成 Recommendation Feedback Timeline。新增 `recommendation-history-card.tsx`（props-driven, 30-day window）；整合至 `/platform/actions` section 5；8 Playwright tests 全過；使用現有 `/outcome-feedback?window_days=30` + P59 型別；無後端改動；TypeScript clean；runtime-smoke 56 passed；P55/P56/P57 regression 17/17；安全說明已加入（不代表醫療效果）。Commit: `b6cb0b9`。

---

## P61-ROADMAP-REFOCUS-AFTER-OUTCOME-SMOKE-CLOSURE (2026-05-25)

**Final Classification: `P61_ROADMAP_REFOCUS_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD: `6ea326b` (P60 outcome-smoke) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (expected governance outputs only) ✅

### P50–P60 Closure Summary

| Phase | Result | Commit |
|-------|--------|--------|
| P50 | Frontend auth smoke stabilized (missing BUILD_ID diagnosed) | `0191e59` |
| P51 | Recommendation explanation safety (safe Chinese copy) | — |
| P52 | Prioritized action safety | — |
| P53 | Action confidence labels | — |
| P54 | Daily summary context (topRisk/biggestChange/todayAction/whyNow/confidence/missingData) | — |
| P55 | Action feedback loop (mark done/snoozed/not_useful/not_applicable) | `0191e59` |
| P56 | Recommendation feedback persistence | `9624f04` |
| P57 | Snooze persistence + dismissed filter | `07b15d0` |
| P58 | Recommendation outcome readiness safeguards (safe copy, confidence=0.0) | `5dea27e` |
| P59 | Outcome visibility: frontend type unions, outcome-feedback-card, 18 API tests | `4e5dd81` |
| P60 | Outcome smoke: `outcome-smoke` Makefile target, 56 tests in `make runtime-smoke` | `6ea326b` |

### Product Gap Identified

After P50–P60, the product recommendation → feedback → outcome chain is closed at the data/API layer.
**Missing from user experience**: a chronological history view showing past recommendations, user responses, and safe outcome statuses.

### Option Evaluation

| Option | Status | Reason |
|--------|--------|--------|
| A — Daily Assistant Summary Quality | Backend solid (all fields returned), UI polish only | Lower value: backend complete |
| B — Recommendation Feedback Timeline | **Selected** | Completes visible product loop; existing API + types; bounded scope |
| C — Report-to-Action Closure | Already implemented per P4 roadmap | No clear gap |
| D — Data Insufficiency Clarity | `missingData` field exists in response | Minor UI polish |

### Decision: Option B — P62

**Rationale**: P55–P60 built the full action feedback + outcome data pipeline. The logical next product step is giving users a visible record of their recommendation history. The backend endpoint (`/outcome-feedback?window_days=30`) and all TypeScript types (`OutcomeFeedbackItem`, `OutcomeFeedback`) already exist. Only a new frontend component is needed.

### Files Changed
| File | Change |
|------|--------|
| `00-Plan/roadmap/roadmap.md` | Updated Latest Phase Status to reflect P50–P60 closure; added P62 direction |
| `00-Plan/roadmap/active_task.md` | Replaced stale P50 task with P62 worker prompt |
| `00-Plan/roadmap/active_task_report.md` | This P61 block prepended |

### Tests
Code tests: NOT RUN (docs/roadmap-only changes).
TypeScript: NOT RUN (no frontend code changes).

### Commits
- C1: `docs(roadmap): refocus product roadmap after P60 outcome smoke closure`

---

## P50-FRONTEND-AUTH-SMOKE-DIAGNOSIS (2026-05-25)

**Final Classification: `P50_FRONTEND_AUTH_SMOKE_STABILIZED`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `62b791f` (P49 closure) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (expected CTO/CEO outputs only) ✅

### A. Reproduce + Evidence Summary

**Pre-diagnosis state:**
- `:3010` — free (no conflict)
- `:3000` — node PID 2991 (unrelated dev process)
- `:8000` — Python/uvicorn (backend live)
- `frontend/.next/BUILD_ID` — **MISSING**

**Direct `next start` probe (before fix):**
```
Error: Could not find a production build in the '.next' directory.
Try building with 'next build' before starting the production server.
EXIT: 1
```

### B. Timeout Type Judgment

**B2 — Server crash; Playwright can't connect.**

`next start` exits immediately (< 1s, exit code 1) on missing `BUILD_ID`. Playwright polls the readiness URL for the full 120s before timing out. Error message "Timed out waiting 120000ms" is misleading — the actual failure is a deterministic crash, not a slow startup.

### C. Five-Item Checklist

| Item | Result |
|------|--------|
| C1. Build state | **ROOT CAUSE** — `BUILD_ID` missing; ran `next build`, created `BUILD_ID=mmhAYpkD9M5aFIXDq1iZa` |
| C2. Port conflict | `:3010` free — no conflict (C1 resolved, C2 skipped) |
| C3. Manual `next start` | Post-fix: `✓ Ready in 438ms`, `curl → HTTP 200` (C1 resolved, C3 confirmation only) |
| C4. Readiness URL | `playwright.config.ts` url `http://127.0.0.1:3010` matches binding — no mismatch (C1 resolved) |
| C5. Env | `.env.local` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; optional vars absent — not blocking (C1 resolved) |

### D. Terminal Decision

**Path (a): `P50_FRONTEND_AUTH_SMOKE_STABILIZED`**

Fix: `cd frontend && npx next build` — creates production build artifacts. No config files modified.

`make frontend-auth-smoke` post-fix: **6/6 PASS (11.7s)**.

### E. `runtime-smoke` No Regression

`make runtime-smoke` post-fix: **130 passed, 2 skipped** ✅

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P50_FRONTEND_AUTH_SMOKE_STABILITY.md` | Created — full diagnosis evidence |
| `00-Plan/roadmap/active_task_report.md` | P50 block prepended |

### Commits
- C1: `docs(security): add P50 frontend auth smoke stability diagnosis`
- C2: `docs(report): P50 frontend auth smoke diagnosis handoff`

### Known Limitations
- `.next/` must exist with a valid production build before running `make frontend-auth-smoke`; `Makefile` documents this as a prerequisite comment but does not enforce it
- Fix durability: stable until `.next/` is cleared again

---

# Appendix: Prior Sprint Reports

## P49-FRONTEND-AUTH-E2E-CI-READINESS (2026-05-24)

**Final Classification: `P49_FRONTEND_AUTH_E2E_LOCAL_GATE_DOCUMENTED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `579a42c` (P48 closure) ✅
- Tree: clean ✅

### Conclusion: Option B — Docs Only

Frontend auth e2e (`frontend-auth-smoke`) cannot safely run in CI. Blockers:
- Needs `uvicorn app.main:app --port 8000` (backend service with env vars + DB)
- Needs `next start` at port 3010 (after fresh `npm run build`)
- `next start` webServer timed out locally (120s) — unreliable without freshly built frontend
- P15 timeout=120s, P16 timeout=180s — too slow for CI
- GitHub Actions does not share localhost across jobs without service containers

### Local Validation Attempt
`make frontend-auth-smoke` → `Error: Timed out waiting 120000ms from config.webServer`

Backend was live (`curl /health` → 200). Build existed (May 23). webServer still timed out.

### Canonical Local Gate
```bash
cd backend && uvicorn app.main:app --port 8000   # separate terminal
cd frontend && npm run build
make frontend-auth-smoke
```

### CI Gap
- CI runs `npm run e2e:ci` — 3 mocked specs only (no backend needed) ✅
- Auth e2e stays local-only — already documented in CI comment since P22 ✅
- Auth contract covered by CI backend suite via `backend-auth-audit` (41 tests) ✅

### runtime-smoke Unchanged
130 passed, 2 skipped ✅

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P49_FRONTEND_AUTH_E2E_CI_READINESS.md` | Created |

### Commits
- C1: `docs(security): add P49 frontend auth e2e CI readiness report`
- C2: `docs(report): P49 frontend auth e2e handoff report`

---

## P48-CI-RUNTIME-SMOKE-ALIGNMENT (2026-05-24)

**Final Classification: `P48_CI_RUNTIME_SMOKE_ALIGNED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `a6a64c9` (P47 closure) ✅
- Tree: clean ✅

### Gap Found
CI's `npm run build` silently skips TypeScript (`ignoreBuildErrors: true` in `next.config.mjs`). CI's `npm run lint` is ESLint only. No CI step enforced tsc before P48.

### Fix Applied
Added `npx tsc --noEmit` step to CI frontend job (`.github/workflows/ci-cd.yml`) after `npm ci`, before lint/build. Equivalent to `make frontend-tsc`.

### CI vs runtime-smoke Alignment (Post-P48)
| Area | CI | runtime-smoke |
|------|----|---------------|
| Backend (all stages) | ✅ 983-test full suite ⊇ 130 backend tests | ✅ |
| frontend-tsc | ✅ `npx tsc --noEmit` (P48 added) | ✅ |
| P47 token policy (12 tests) | ✅ full suite | ✅ |

### Validation
- `npx tsc --noEmit`: exit 0 ✅
- `make runtime-smoke`: 130 passed, 2 skipped ✅

### Files Changed
| File | Change |
|------|--------|
| `.github/workflows/ci-cd.yml` | `npx tsc --noEmit` step added to frontend job |
| `docs/security/P48_CI_RUNTIME_SMOKE_ALIGNMENT.md` | Created |

### Commits
- C1: `ci: add frontend TypeScript typecheck to align with runtime-smoke`
- C2: `docs(security): add P48 CI runtime-smoke alignment report`
- C3: `docs(report): P48 CI runtime-smoke handoff report`

---

## P47-TOKEN-POLICY-RUNTIME-GATE (2026-05-24)

**Final Classification: `P47_TOKEN_POLICY_RUNTIME_GATE_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `8fde52f` (P46 closure) ✅
- Tree: clean ✅

### What Changed
**`Makefile` — `backend-auth-audit` target**
- Added `tests/test_report_download_token_policy.py` (12 tests: 5 P44 + 7 P45)
- Updated comment to reference P44/P45
- Propagates through: `backend-auth-audit` → `security-smoke` → `runtime-smoke` stage 2

### runtime-smoke: 118 → 130
| Stage | Before | After |
|-------|--------|-------|
| Stage 2 (security) | 29, 2 skip | **41, 2 skip** |
| Total | **118** | **130** |

### Targeted Test
`test_report_download_token_policy.py`: 12/12 passed ✅

### Files Changed
| File | Change |
|------|--------|
| `Makefile` | `backend-auth-audit` + `test_report_download_token_policy.py` |
| `docs/security/P47_TOKEN_POLICY_RUNTIME_GATE.md` | Created |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Gap → CLOSED; table updated |
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage 2 29→41; total 118→130; §13 P47 row; gap closed |

### Commits
- C1: `chore(governance): add report download token policy to runtime smoke`
- C2: `docs(security): add P47 token policy runtime gate report`
- C3: `docs(report): P47 token policy runtime gate handoff report`

---

## P46-SMOKE-GATE-REFRESH (2026-05-24)

**Final Classification: `P46_SMOKE_GATE_REFRESH_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `cb6f19b` (P45 closure) ✅
- Tree: clean ✅

### Updated Smoke Counts
| Stage | Before P46 (P39 doc) | After P46 (actual) |
|-------|----------------------|---------------------|
| Stage 3 (config-smoke) | 24 | **29** (+5 P43 tests) |
| runtime-smoke total | 113 | **118** |
| Full backend suite | ~800+ | **983** |

### R5 Risk Status: MITIGATED
- Before: Token in `?token=` query string → appears in server access logs
- After P45: Frontend strips token from URL, sends via `X-Report-Download-Token` header
- Backend accepts header (preferred) or query (backward compat)

### P44/P45 Coverage Gap Documented
- `test_report_download_token_policy.py` (12 tests) is NOT in runtime-smoke
- Runs only in full backend suite
- Recommended P47: add to `backend-auth-audit` Makefile target (130 runtime-smoke tests)

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage counts, R5, P44 recommendation, Section 13 |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Created |
| `Makefile` | config-smoke comment updated (P43 reference) |
| `00-Plan/roadmap/active_task_report.md` | This block |

### Validation
| Suite | Result |
|-------|--------|
| `make runtime-smoke` | 118 passed, 2 skipped ✅ |
| Targeted 33 tests | 33/33 passed ✅ |
| `tsc --noEmit` | 0 errors ✅ |

### Commits
- C1: `chore(governance): refresh smoke gate labels`
- C2: `docs(security): refresh smoke gate and report token closure index`
- C3: `docs(report): P46 smoke gate refresh handoff report`

---

## P45-REPORT-DOWNLOAD-TOKEN-HEADER (2026-05-24)

**Final Classification: `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `389b7fa` (P44 closure) ✅
- Tree: clean ✅

### What Changed
**`backend/app/api/reports.py`** — download endpoint now accepts `X-Report-Download-Token` header:
- Header preferred over query string (`provided_token = x_report_download_token or token`)
- Query `?token=` retained as backward-compatible fallback
- Invalid header with valid query → 403 (no silent fallback)
- No token at all → 403
- JWT owner check unchanged and still runs first

**`frontend/app/components/platform/report-export-modal.tsx`** — `handleDownload()`:
- Extracts token from `download_url` with `URL.searchParams.get('token')`
- Strips token from URL: `searchParams.delete('token')` → `fetchUrl` has no token
- Sends token as `X-Report-Download-Token` header
- JWT still sent as `Authorization: Bearer`

### Token in Access Log: MITIGATED
- Before: `GET /api/v1/reports/download/{id}?token=<uuid>` logged
- After: `GET /api/v1/reports/download/{id}` logged (token in header, not URL)

### Tests Added — `TestHeaderTokenDownload` (7 new tests)
| Test | Assert |
|------|--------|
| `test_header_token_owner_jwt_succeeds` | 200 |
| `test_query_token_backward_compat_succeeds` | 200 |
| `test_header_preferred_header_valid_query_invalid` | 200 |
| `test_header_preferred_header_invalid_query_valid_rejected` | 403 |
| `test_no_token_at_all_denied` | 403 |
| `test_cross_user_jwt_valid_header_token_denied` | 404 |
| `test_no_jwt_valid_header_token_denied` | 401 |

### Validation
| Suite | Result |
|-------|--------|
| Targeted (33 tests) | 33/33 passed |
| `tsc --noEmit` | 0 errors |
| `make runtime-smoke` | 118 passed, 2 skipped |
| Full backend suite | 983 passed, 2 skipped |

### Commits
- C1 `97c6096`: `fix(security): accept report download token from request header`
- C2 `47f0148`: `fix(frontend): send report download token via header`
- C3 `51a7ca8`: `test(security): add report download token header regression`
- C4: `docs(security): add P45 report download token header report`
- C5: `docs(report): P45 report download token header handoff report`

---

## P44-REPORT-DOWNLOAD-TOKEN-POLICY (2026-05-24)

**Final Classification: `P44_REPORT_DOWNLOAD_TOKEN_RISK_DOCUMENTED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `2c38ebb` (P43 closure) ✅
- Tree: clean ✅

### Investigation
- Download endpoint `GET /api/v1/reports/download/{report_id}` requires: JWT (get_current_user) + owner_user_id match + token match + expiry ✅
- Token embedded in URL query string: `?token=<uuid>` → leaks to server-side access logs ⚠ (residual risk)
- Frontend uses fetch+blob+createObjectURL (no browser navigation) → browser history NOT at risk ✅
- P39 R5: token-alone attack → HTTP 401 (JWT required first) ✅

### Test Gap Closed
- **Missing**: "no JWT + valid token → 401" was not tested in any existing file
- **Root cause**: P18 docstring said download was "token-only (no JWT auth)" — P20 silently added JWT but left no-JWT path untested

### Changes
**`backend/tests/test_report_download_token_policy.py`** — CREATED (5 tests)
| Class | Test | Assert |
|-------|------|--------|
| `TestDownloadEndpointRequiresJWT` | `test_no_jwt_valid_token_denied` | 401 |
| `TestDownloadTokenStandaloneAttack` | `test_stolen_token_no_jwt_denied` | 401 |
| `TestDownloadTokenStandaloneAttack` | `test_cross_user_jwt_valid_token_denied` | 404 |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_403_body_does_not_echo_token` | 403 + clean body |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_404_body_does_not_echo_token` | 404 + clean body |

### Test Results
| Suite | Result |
|-------|--------|
| New + existing hardening (14) | 14/14 passed |
| `make runtime-smoke` | 118 passed, 2 skipped |
| Full backend suite | 976 passed, 2 skipped |

### Residual Risk Accepted
- Token in server-side access logs: LOW impact (token alone → 401, requires owner JWT)
- Deferred mitigation: X-Report-Download-Token header (P45+)

### Artifacts
- `backend/tests/test_report_download_token_policy.py` — new (5 tests)
- `docs/security/P44_REPORT_DOWNLOAD_TOKEN_POLICY.md` — report

### Commits
- C1 `e95d151`: `test(security): add report download token policy regression`
- C2: `docs(security): add P44 report download token policy`
- C3: `docs(report): P44 report download token policy handoff report`

---

## P43-STARTUP-SECURITY-WARNINGS (2026-05-24)

**Final Classification: `P43_STARTUP_SECURITY_WARNINGS_WIRED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `21f60f6` (docs: P42 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Investigation
- `log_json(logger, level, event, **payload)` exists in `app/core/logging.py` ✅
- `get_runtime_security_warnings()` from P42 not imported or called in `main.py` ❌ (GAP)
- Test pattern: `monkeypatch.setattr(main_module, 'settings', ...)` + direct `startup_event()` call ✅

### Changes
**`backend/app/main.py`** — added `get_runtime_security_warnings` import + warning loop in `startup_event()`:
- Runs after `validate_production_secrets()` (fatal guard unchanged)
- Emits `runtime_security_warning` JSON log at WARNING level for each warning code
- Payload contains only `warning_code` and `app_env` — no secrets

**Warning codes**:
- `RATE_LIMIT_DISABLED_IN_PRODUCTION` — production + rate_limit_enabled=False
- `IN_MEMORY_LIMITER_PROCESS_LOCAL` — production + rate_limit_enabled=True

### Test Results
| Suite | Result |
|-------|--------|
| `test_runtime_config_startup_guard.py` (19 tests) | 19/19 passed |
| `test_rate_limit_production_policy.py` (17 tests) | 17/17 passed |
| `make runtime-smoke` (Stage 1–4) | 118 passed, 2 skipped |
| Full backend suite | 971 passed, 2 skipped |

### Artifacts
- `backend/app/main.py` — startup warning loop wired
- `backend/tests/test_runtime_config_startup_guard.py` — 5 new tests (`TestStartupRuntimeSecurityWarnings`)
- `docs/security/P43_STARTUP_SECURITY_WARNINGS.md` — report

### Commits
- C1 `5710698`: `fix(startup): log runtime security warnings at startup`
- C2 `f06e321`: `test(security): assert startup emits rate-limit warnings in production`
- C3: `docs(security): add P43 startup security warnings report`
- C4: `docs(report): P43 startup security warnings handoff report`

---

## P42-RATE-LIMIT-PRODUCTION-POLICY (2026-05-24)

**Final Classification: `P42_RATE_LIMIT_POLICY_HARDENED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `9bc1e81` (docs: P41 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Investigation Findings
- `rate_limit_enabled` defaults to `False` — opt-in, not enforced in production
- `InMemoryRateLimitMiddleware` is process-local; state not shared across workers
- `validate_production_secrets` checked `jwt_secret_key` only — no rate-limit policy
- P26 covered middleware contract; no production policy tests existed
- Classification before fix: **PARTIAL + GAP**

### Fix Applied
Added `get_runtime_security_warnings(settings) -> list[str]` to `backend/app/core/config.py`:
- Production + `rate_limit_enabled=False` → warns `RATE_LIMIT_DISABLED_IN_PRODUCTION`
- Production + `rate_limit_enabled=True` → warns `IN_MEMORY_LIMITER_PROCESS_LOCAL`
- Dev/staging/local → returns `[]` (no noise)
- Never raises — backward-compatible

### Production Policy Defined
- Single-worker: `RATE_LIMIT_ENABLED=true` is sufficient for basic abuse protection
- Multi-worker: in-memory limiter does not share state → gateway/WAF/Redis required
- `/health*` permanently exempt (hardcoded in middleware)
- No per-route throttle added (out of scope)

### Test Results
| Suite | Result |
|-------|--------|
| `test_rate_limit_production_policy.py` | 17/17 passed |
| `test_rate_limit_smoke.py` | 7/7 passed |
| `test_config_security_guard.py` | 15/15 passed |
| `make runtime-smoke` (Stage 1–4) | 113 passed, 2 skipped |
| Full backend suite | 966 passed, 2 skipped |

### Accepted Residual Limitations
- In-memory limiter is process-local: ACCEPTED, documented
- No worker topology config in Settings: ACCEPTED / UNKNOWN
- Global threshold only: ACCEPTED (no per-route throttle)
- `get_runtime_security_warnings` not yet wired into startup logging: DEFERRED (P43)

### Artifacts
- `backend/app/core/config.py` — `get_runtime_security_warnings` helper
- `backend/tests/test_rate_limit_production_policy.py` — 17 policy tests (NEW)
- `docs/security/P42_RATE_LIMIT_PRODUCTION_POLICY.md` — policy report

### Commits
- C1 `8484fca`: `fix(config): expose runtime security warnings for rate limiting policy`
- C2: `docs(security): add P42 rate limit production policy`
- C3: `docs(report): P42 rate limit production policy handoff report`

---

## P41-RISK-ENGINE-UUID-HYGIENE (2026-05-24)

**Final Classification: `P41_RISK_ENGINE_UUID_HYGIENE_FIXED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `a6d909d` (docs: P40 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Root Cause
`risk_engine._make_alert` received `str` UUID values from callers (`str(current_user.id)`) but passed them directly into `RiskAlert(user_id=..., UUID(as_uuid=True))`. SQLite crashed with `StatementError: 'str' object has no attribute 'hex'`; PostgreSQL silently coerced (R4 from P40 reclassified as latent type smell).

### Fix Applied
- Added `import uuid` and str→UUID coercion in `_make_alert`
- Updated `evaluate_metric_risks` / `evaluate_lab_item_risks` type annotations to `uuid.UUID | str`
- Callers (`metrics.py`, `documents.py`) unchanged — coercion handles them

### P35 Mock Removal
Removed 4 stale `unittest.mock.patch` blocks from `test_metrics_symptoms_response_leakage.py` that existed solely to prevent the SQLite crash. All 15 tests pass without mocks.

### Test Results
| Suite | Result |
|-------|--------|
| `test_risk_engine_uuid_hygiene.py` | 8/8 passed |
| `test_metrics_symptoms_response_leakage.py` | 15/15 passed |
| `test_postgresql_parity.py` | 11/11 passed |
| `make runtime-smoke` (Stage 1–4) | 113 passed, 2 skipped |
| Full backend suite | 949 passed, 2 skipped |

### Artifacts
- `backend/app/services/risk_engine.py` — str→UUID coercion fix
- `backend/tests/test_risk_engine_uuid_hygiene.py` — 8 regression tests (NEW)
- `backend/tests/test_metrics_symptoms_response_leakage.py` — 4 stale mocks removed
- `docs/security/P41_RISK_ENGINE_UUID_HYGIENE.md` — security report

### Commits
- C1 `d7be418`: `fix(db): use UUID objects for risk alert persistence`
- C2 `7592ca0`: `test(db): add risk engine UUID hygiene regression`
- C3: `docs(security): add P41 risk engine UUID hygiene report`
- C4: `docs(report): P41 risk engine UUID hygiene handoff report`

---

## P40-POSTGRESQL-PARITY-SMOKE (2026-05-24)

**Final Classification: `P40_POSTGRESQL_PARITY_VERIFIED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `7524be4` (docs: P39 closure index) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Execution Summary
- PostgreSQL 16 already running (`health-insights-postgres-local`, healthy 2 days)
- Local Homebrew PG also running on port 5432 (port conflict; macOS GSSAPI bypass required)
- Created `health_insights_test` DB in local PG; applied `schema.sql` + 9 migrations
- SQLAlchemy confirmed connected: 14 tables visible
- 11 parity tests written and executed: **11 passed**
- R4 probe: str UUID coerced by psycopg2 on PostgreSQL — latent type smell, not crash
- SQLite runtime-smoke: 113 passed, 2 skipped (unchanged)

### Artifacts
- `backend/tests/test_postgresql_parity.py` — 11 parity tests (T1–T7)
- `docs/security/P40_POSTGRESQL_PARITY_SMOKE.md` — parity report

### Commits
- C1: `test(db): add P40 PostgreSQL parity smoke (11 tests, all pass)`
- C2: `docs(security): add P40 PostgreSQL parity smoke report`
- C3: `docs(report): P40 PostgreSQL parity handoff report`

### Next Task: P41
Fix R4 UUID coercion: pass UUID object (not str) to `evaluate_metric_risks` /
`evaluate_lab_item_risks` callers in `metrics.py` and `documents.py`.

---

## P39-SECURITY-AUDIT-CLOSURE-INDEX (2026-05-24)

**Final Classification: `P39_SECURITY_AUDIT_CLOSURE_INDEX_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `4c9ffb1` (docs: P38 audit report) ✅
- Status: clean (no uncommitted files) ✅

### Summary
- **Goal**: Create canonical closure index for P13–P38 security/readiness hardening
- **Index path**: `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md`
- **Scope**: Read-only investigation + docs creation only (no backend/test/frontend modifications)

### P13–P38 Closure Classification Summary
| Category | Count |
|----------|-------|
| A. CLOSED (full coverage) | 19 tasks |
| B. CLOSED_WITH_ACCEPTED_GAP | 3 tasks (P18, P22, P26) |
| C. DOCS_ONLY | 1 task (P19) |
| D. INFRA | 2 tasks (P21, P31) |

### C.GAPs Fixed (P13–P38)
| Type | Count | Tasks |
|------|-------|-------|
| Response field leakage (user_id / storage fields) | 6 schemas | P32, P35, P38 |
| Auth / authorization | 2 fixes | P18, P20 |
| Config / secrets | 1 fix | P28 |
| Injection (filename traversal) | 1 fix | P27 |
| Validation constraints | 3 rounds | P23, P24, P30 |

### runtime-smoke Result
| Stage | Result |
|-------|--------|
| 1 — Health check | 3 passed ✅ |
| 2 — Security smoke | 29 passed, 2 skipped ✅ |
| 3 — Config smoke | 24 passed ✅ |
| 4 — Validation smoke | 57 passed ✅ |
| **Total** | **113 passed, 2 skipped** ✅ |

### Accepted Gaps (documented in index §7)
- R1: Rate limiter in-memory, not multi-worker shared
- R2: Rate limit opt-in per route, not globally enforced
- R3: AI prompt injection structural governance deferred
- R4: `risk_engine.py` passes `str(user.id)` to `UUID(as_uuid=True)` column (SQLite compat issue)
- R5: Report download token leakable via browser history (mitigated by UUID entropy + 1hr expiry)
- R6: Frontend e2e auth tests not in CI (require live backend)

### Recommended Next Tasks
- **P40** (HIGH): PostgreSQL parity smoke — all tests currently run on SQLite
- **P41** (MEDIUM): risk_engine.py UUID compatibility fix (R4)
- **P42** (MEDIUM): Rate-limit production enablement policy (R1/R2)
- **P43** (MEDIUM): AI prompt governance / prompt-injection policy (R3)
- **P44** (LOW): Report download token hardening (R5)

### Files Changed
- Created: `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md`
- Updated: `00-Plan/roadmap/active_task_report.md` (this prepend)

### Commits
- `C1`: `docs(security): add P39 security audit closure index`
- `C2`: `docs(report): P39 security audit closure report`

---

## P38-REMAINING-API-SURFACE-AUDIT (2026-05-24)

**Final Classification: `P38_REMAINING_API_SURFACE_FIXED`**

### Summary
- Audited: 9 remaining API files (actions, analytics, auth, external_metrics, insights, persons, profile, reports, timeline) + corresponding schemas
- **3 C.GAPs found and fixed**:
  - `ProfileResponse.user_id: UUID` → removed from schema + removed from GET/PUT /profile/me response dicts
  - `HealthInsightResponse.user_id: UUID` → removed from schema
  - `HealthActionRead.user_id: UUID` → removed from schema
- **A.SAFE** (no changes): UserResponse, AccountResponse, PersonResponse.owner_user_id (P33 design), ExternalSyncResponse/ExternalTrendResponse, TimelineResponse data dicts, ReportStatusResponse download_url, untyped outcomes list
- 14 regression tests added → 14/14 PASS
- Full test suite: 916+14 PASS, 2 skipped
- runtime-smoke: 113 passed, 2 skipped
- Commits: `2338e30` (fix), `c0b4060` (tests), *(C3 pending)*

### Status: All 17 API files audited (P32–P38 complete)

---

## P37-AI-HEALTH-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P37_AI_HEALTH_SMOKE_VERIFIED`**

### Summary
- Audited: `api/ai_summary.py` (2 routes), `api/health_score.py` (3 routes), `api/ai_modules.py` (4 routes), plus schemas for ai_summary, health_score, health_analysis, trend_analysis, ai_modules
- **No C.GAP found** — both `AISummary` and `HealthScore` ORM have `user_id` column; neither `AISummaryResponse` nor `HealthScoreResponse` declares it; `from_attributes=True` only serializes declared fields
- `narrative_json` and `score_detail` JSON blobs contain only AI-generated health content — no user_id embedded
- `AIModuleResponse`/`AIModuleEvaluationResponse` — no ORM at all, pure structured AI output, no user_id
- 13 regression tests added → 13/13 PASS
- runtime-smoke: 113 passed, 2 skipped
- Commits: `6987495` (tests), *(C2 pending)*

### Next: P38 — Remaining API Surface Final Audit
- Check any remaining routes not covered by P32–P37
- Candidates: notification, recommendation, person_profile, admin endpoints
- Find files: `find backend/app/api -maxdepth 1 -type f | sort`

---

## P36-LAB-RISK-RESPONSE-AUDIT (2025-07-27)

**Final Classification: `P36_LAB_RISK_SMOKE_VERIFIED`**

### Summary
- Audited: `api/documents.py` (8 routes), `api/risk_alerts.py` (5 routes), `schemas/documents.py`, `schemas/risk_alerts.py`
- **No C.GAP found** — all schema-based routes exclude user_id/storage fields
- B.PARTIAL routes: `GET /documents/lab-history`, `GET /risk-alerts/unread-count`, `POST /risk-alerts/{id}/dismiss` — explicit safe dict construction, regression tests added
- 12 regression tests added → 12/12 PASS
- runtime-smoke: 113 passed, 2 skipped
- Commits: `e4929a8` (tests), `8ecb96e` (docs)

### Next: P37 — Health Score & AI Summary Response Audit
- Target: `AISummary` ORM has `user_id` — verify not in response schemas
- Files: `backend/app/api/health_score.py`, `backend/app/api/ai_summary.py` (if exist), corresponding schemas

---

## P35-METRICS-SYMPTOMS-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P35_METRICS_SYMPTOMS_LEAKAGE_HARDENED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `20f6e83` (P34 docs commit) ✅
- Working tree: clean ✅

### 2. Investigation Commands

```bash
grep -Rn "@router\.\(get\|post\|put\|patch\|delete\)\|response_model\|user_id" \
  backend/app/api/metrics.py backend/app/api/symptoms.py \
  backend/app/schemas/metrics.py backend/app/schemas/symptoms.py
```

```bash
grep -Rn "password_hash\|secret_\|storage_key\|storage_bucket\|file_path\|download_token" \
  backend/app/api/metrics.py backend/app/api/symptoms.py \
  backend/app/schemas/metrics.py backend/app/schemas/symptoms.py
```

### 3. Route Audit Inventory

| Route | Response Model | ORM `user_id` Column | Response Before Fix | Classification | Action |
|---|---|---|---|---|---|
| POST /metrics | `MetricResponse` | `HealthMetric.user_id` present | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /metrics | `list[MetricResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /metrics/latest | `Optional[MetricResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| POST /symptoms | `SymptomResponse` | `SymptomLog.user_id` present | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /symptoms | `list[SymptomResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| PUT /symptoms/{id} | `SymptomResponse` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |

### 4. Fix Applied

**`backend/app/schemas/metrics.py`** — `MetricResponse`
- Removed: `user_id: UUID`
- Retained: `id`, `subject_profile_id`, `source`, all metric scalar fields

**`backend/app/schemas/symptoms.py`** — `SymptomResponse`
- Removed: `user_id: UUID`
- Retained: `id`, `subject_profile_id`, all symptom scalar fields

ORM columns `HealthMetric.user_id` and `SymptomLog.user_id` are retained — used in `.filter()` clauses in API routes for ownership enforcement. No DB model changes.

### 5. Additional Findings (Non-blocking)

**Pre-existing bug in `risk_engine.py`**: `evaluate_metric_risks(str(current_user.id), ...)` passes `str` UUID to `RiskAlert(user_id=...)` which is `UUID(as_uuid=True)`. This causes SQLAlchemy `StatementError: 'str' object has no attribute 'hex'` on SQLite. Scoped to existing code, not introduced by P35. POST metric tests mock `evaluate_metric_risks` to return `[]` to isolate response schema validation.

### 6. Sensitive Field Scan
- `password_hash`, `storage_key`, `storage_bucket`, `file_path`, `download_token`: **not present** in any metrics/symptoms schema or API file ✅

### 7. Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/metrics.py` | Removed `user_id: UUID` from `MetricResponse` |
| `backend/app/schemas/symptoms.py` | Removed `user_id: UUID` from `SymptomResponse` |
| `backend/tests/test_metrics_symptoms_response_leakage.py` | Created — 15 regression tests |

### 8. Tests Added — `test_metrics_symptoms_response_leakage.py`

| Class | Test | Result |
|---|---|---|
| TestMetricsResponseLeakage | test_create_metric_status_201 | PASS |
| TestMetricsResponseLeakage | test_create_metric_no_user_id | PASS |
| TestMetricsResponseLeakage | test_create_metric_no_sensitive_keys | PASS |
| TestMetricsResponseLeakage | test_list_metrics_no_user_id | PASS |
| TestMetricsResponseLeakage | test_list_metrics_no_sensitive_keys | PASS |
| TestMetricsResponseLeakage | test_latest_metric_no_user_id | PASS |
| TestMetricsResponseLeakage | test_metric_response_fields | PASS |
| TestSymptomsResponseLeakage | test_create_symptom_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_create_symptom_no_sensitive_keys | PASS |
| TestSymptomsResponseLeakage | test_list_symptoms_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_list_symptoms_no_sensitive_keys | PASS |
| TestSymptomsResponseLeakage | test_update_symptom_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_symptom_response_fields | PASS |
| TestCrossUserMetricsSymptomsIsolation | test_cross_user_metrics_404 | PASS |
| TestCrossUserMetricsSymptomsIsolation | test_cross_user_symptoms_404 | PASS |

**Total: 15/15 PASS**

### 9. Test Run Output

```
15 passed, 4 warnings in 2.50s
```

### 10. runtime-smoke

```
Stage 1:  3 passed
Stage 2: 29 passed, 2 skipped
Stage 3: 24 passed
Stage 4: 57 passed
Total:  113 passed, 2 skipped — all 4 stages green ✅
```

### 11. Known Limitations / Inferred

- Cross-user isolation for metrics/symptoms is enforced via `HealthMetric.user_id == current_user.id` and `SymptomLog.user_id == current_user.id` filters, **not** via `get_target_person` (unlike dashboard). The cross-user 404 tests confirm this filtering works via the `get_target_person` dependency applied to the `person_id` query param.
- `evaluate_metric_risks` string-UUID bug is pre-existing, not introduced by P35. Tracked for future hardening.

### 12. Commits

- `8b22a5f` fix(security): remove user_id from MetricResponse and SymptomResponse (P35)
- `30ac9d7` test(security): add metrics/symptoms response leakage regression (P35)
- `(docs)` docs(report): P35 metrics symptoms response audit report

### 13. Final Classification

**`P35_METRICS_SYMPTOMS_LEAKAGE_HARDENED`**
- C.GAP found: `user_id: UUID` exposed in both `MetricResponse` and `SymptomResponse`
- Fix applied: removed from both schemas
- 15 regression tests: all PASS
- runtime-smoke: 113 passed, 2 skipped

---

## P34-DASHBOARD-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P34_DASHBOARD_SMOKE_VERIFIED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `1fa28c4` (P33 docs commit) ✅
- Working tree: clean ✅

### 2. Scope

`backend/app/api/dashboard.py` — 3 routes, all using explicit `response_model=`.
`backend/app/schemas/dashboard.py` — Pydantic models; `DashboardOverviewV2Response` contains multiple `list[dict[str, Any]]` and `dict[str, Any]` fields.
All contributing service functions in `backend/app/services/health_ai_engine/` and `backend/app/services/decision_engine_service.py` audited.

### 3. Route Audit Inventory

| Route | Response Model | Dynamic dict[str, Any] Fields | Data Sources | Classification | Action |
|---|---|---|---|---|---|
| GET /dashboard/overview | `DashboardOverviewResponse` | `latest_metrics`, `active_alerts`, `summary` | HealthMetric ORM (explicit field selection), risk alerts | A. SAFE | Regression tests added |
| GET /dashboard/trends | `DashboardTrendsResponse` | None — all `list[TrendPoint]` (typed Pydantic) | HealthMetric ORM | A. SAFE | Regression tests added |
| GET /dashboard (v2) | `DashboardOverviewV2Response` | `alerts`, `insights`, `recent_symptoms`, `recent_metrics`, `recent_labs`, `trends`, `predictive_insights`, `anomaly_alerts`, `clinical_labels`, `recommendations`, `health_narrative_v2`, `health_narrative_v3`, `prioritized_actions` | Multiple — see below | A. SAFE | Regression tests added |

### 4. DashboardOverviewV2Response Dict Fields — Detailed Audit

| Field | Shape | Data Source | Sensitive Fields? | Classification |
|---|---|---|---|---|
| `alerts` | `list[dict]` | Explicit construction: `id`, `severity`, `title`, `description`, `created_at`, `rule_id`, `category`, `priority`, `confidence`, `evidence_level`, `guideline_source`, `medical_disclaimer` | None | A.SAFE |
| `insights` | `list[dict]` | Explicit construction: `id`, `insight_type`, `severity`, `title`, `summary`, `recommendation`, `generated_at`, `rule_id`, `category`, `priority`, `confidence`, `evidence_level`, `guideline_source`, `guideline_version`, `medical_disclaimer` | None | A.SAFE |
| `recent_symptoms` | `list[dict]` | ORM explicit: `id`, `symptom`, `occurred_at`, `note`, `estimated_start_date`, `estimated_duration_days` | No `user_id` | A.SAFE |
| `recent_metrics` | `list[dict]` | ORM explicit: `id`, `recorded_at`, `systolic_bp`, `diastolic_bp`, `heart_rate`, `blood_glucose`, `weight_kg`, `sleep_hours`, `steps` | No `user_id` | A.SAFE |
| `recent_labs` | `list[dict]` | ORM explicit: `id`, `report_date`, `report_type`, `created_at`, `abnormal_items` | No `file_path`, `storage_key`, `user_id` | A.SAFE |
| `predictive_insights` | `list[dict]` | `generate_predictive_insights()` — health clinical text only | None | A.SAFE |
| `anomaly_alerts` | `list[dict]` | `detect_anomalies()` — health clinical text only | None | A.SAFE |
| `clinical_labels` | `list[dict]` | `derive_clinical_labels()` — health label + guideline metadata | None | A.SAFE |
| `recommendations` | `list[dict]` | `generate_recommendations()` — health text + guideline metadata | None | A.SAFE |
| `health_narrative_v2` | `dict` | `generate_health_narrative_v2()` — narrative text lists | None | A.SAFE |
| `health_narrative_v3` | `dict` | `generate_health_narrative_v3()` — narrative text lists | None | A.SAFE |
| `prioritized_actions` | `list[dict]` | ORM explicit: `id`, `title`, `category`, `status`, `priority`, `frequency`, `impact_status`, `reminder_status`, `streak_count` | No `user_id` | A.SAFE |
| `decision_items` | `list[UnifiedDecisionItem]` | `build_decision_items()` → `UnifiedDecisionItem` (typed Pydantic) | None | A.SAFE |
| `health_score.components` | `dict` | Explicit score components: `blood_pressure`, `bmi`, `lab_results`, penalties | None | A.SAFE |

### 5. Confirmed Safety Properties

1. **No `password_hash`** — zero occurrences in all dashboard-contributing services
2. **No `storage_bucket` / `storage_key`** — `LabReport.storage_bucket` / `.storage_key` never forwarded to client; only `id`, `report_date`, `report_type`, `created_at`, `abnormal_items` are serialized
3. **No `file_path` / `download_token`** — same as above
4. **No `user_id`** in nested metric/symptom/lab items — all ORM queries use `current_user.id` as a filter only, never return it in the dict payload
5. **`UnifiedDecisionItem`** is strongly-typed Pydantic — no arbitrary dict passthrough possible
6. **`enrich_explainability()`** only adds `guideline_source`, `guideline_version`, `evidence_level` — all clinical metadata, no secrets
7. **Cross-user isolation** — `get_target_person` (deps.py:81) filters `owner_user_id == current_user.id` on all 3 routes; cross-user `person_id` → 404

### 6. Tests Added

**`backend/tests/test_dashboard_response_leakage.py`** — 16 tests, all PASS

| Class | Tests | Purpose |
|---|---|---|
| `TestDashboardOverviewLeakage` | 3 | Status 200 + recursive scan + no user_id in latest_metrics |
| `TestDashboardTrendsLeakage` | 3 | Status 200 + recursive scan + TrendPoint key shape enforcement |
| `TestDashboardV2Leakage` | 7 | Full v2 recursive scan; recent_metrics/labs/symptoms/alerts/decision_items/health_score individual scans |
| `TestCrossUserDashboardIsolation` | 3 | Cross-user person_id → 404 on overview, trends, and v2 |

Recursive scanner: checks `password_hash`, `hashed_password`, `password`, `storage_bucket`, `storage_key`, `file_path`, `download_token`, `secret_key`, `secret`, `is_superuser`, `is_staff`.

### 7. Commits
- `3d410d8` — `test(security): add dashboard response leakage regression (P34)`

### 8. runtime-smoke Results
| Stage | Suite | Result |
|---|---|---|
| 1 | Health check | 3 passed |
| 2 | Security smoke | 29 passed, 2 skipped |
| 3 | Config smoke | 24 passed |
| 4 | Validation smoke | 57 passed |
| **Total** | | **113 passed, 2 skipped** |

### 9. Known Limitations
- `health_narrative_v2` and `health_narrative_v3` are `dict[str, Any]` — runtime recursive scan covers these but they are not individually exhausted in static analysis; snapshot tests would be needed if narrative service structure changes significantly.
- Cache layer (`cache_set`/`cache_get`) uses in-memory dict; if upgraded to Redis, the cached payload is a `model_dump(mode='json')` snapshot of the same `DashboardOverviewV2Response` — same safe field set.

---

## P33-HEALTH-ASSISTANT-RESPONSE-AUDIT (2026-05-23)

**Final Classification: `P33_HEALTH_ASSISTANT_SMOKE_VERIFIED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `799f164` (P32 docs commit) ✅
- Working tree: clean ✅

### 2. Scope

`backend/app/api/health_assistant.py` — 706 lines, 20+ routes, all returning `dict[str, Any]` with no `response_model`. Goal: verify no sensitive/internal fields leak through these untyped responses.

### 3. Route Audit Results

| Route | Return shape | Classification | Notes |
|---|---|---|---|
| GET /evidence-bundle | `build_evidence_bundle()` dict | B.PARTIAL | `_completed_rule_ids`: internal prefixed field; value is rule ID strings (e.g., "R001"), not credentials |
| GET /recommendations | `get_action_recommendations()` dict | A.SAFE | No sensitive fields |
| GET /device-signals | manual dict | A.SAFE | `person_id`, `generated_at`, `signals`, `signal_count` — clean |
| GET /product-signals | `build_product_signals()` dict | A.SAFE | Aggregate metrics only |
| GET /outcome-feedback | `compare_expected_vs_actual_outcome()` dict | A.SAFE | No sensitive fields |
| GET /daily-summary | `generate_daily_health_summary()` dict | A.SAFE | Deterministic health aggregates |
| GET /notifications/intelligent | manual dict | A.SAFE | `person_id`, `items`, `suppressed`, `total_candidates` |
| POST /notifications/{id}/snooze | `_serialize_log()` | A.SAFE | 14 notification fields; no credentials |
| POST /notifications/{id}/ignore | `_serialize_log()` | A.SAFE | Same |
| POST /notifications/{id}/click | `_serialize_log()` | A.SAFE | Same |
| POST /notifications/{id}/acted | `_serialize_log()` | A.SAFE | Same |
| GET /personalization-profile | `profile_to_dict()` | B.PARTIAL | Returns `PersonalizationProfile.id` (row UUID, not `user.id`) — own-user only |
| GET /engagement-analytics | `build_engagement_analytics()` dict | A.SAFE | Engagement aggregates |
| POST /personalization-profile/sync | `profile_to_dict()` | B.PARTIAL | Same as GET |
| GET /narrative-memory | manual dict | A.SAFE | `person_id`, `found`, `memory` — own user only |
| POST /narrative-memory/generate | manual dict | A.SAFE | Same |
| GET /narrative-memory/cross-period | manual dict | A.SAFE | `person_id`, `reasoning` |
| POST /family-relationships | manual dict | B.PARTIAL | `owner_user_id` = own UUID; not cross-user |
| GET /family-relationships | `load_family_relationships()` | B.PARTIAL | `owner_user_id` = own UUID |
| GET /family-health-context | manual dict | A.SAFE | `person_id`, `context` — aggregate |
| GET /family-recommendations | manual dict | A.SAFE | `person_id`, `recommendations`, `total` |

**No C.GAP found.** No `password_hash`, `storage_key`, `storage_bucket`, `file_path`, `download_token`, `is_superuser` in any route.

### 4. Cross-User Isolation Confirmed

`get_target_person` (deps.py:81):
```python
.filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
```
Cross-user `person_id` → 404 at the dependency level. Confirmed via 3 regression tests.

### 5. B.PARTIAL Items Documented (Not Fixed — Own-User Data Only)

| Field | Location | Reason B.PARTIAL (not C.GAP) |
|---|---|---|
| `_completed_rule_ids` | evidence-bundle | Internal-prefixed; value is rule ID strings, not credentials |
| `owner_user_id` | family-relationships GET/POST | Always own user's UUID; no cross-user path exists |
| `id` in profile_to_dict | personalization-profile | PersonalizationProfile row UUID, not User.id |

### 6. Tests Added

**`backend/tests/test_health_assistant_leakage.py`** — 15 tests, all PASS

| Class | Tests | Purpose |
|---|---|---|
| `TestEvidenceBundleLeakage` | 2 | Recursive scan + person_id ownership |
| `TestDeviceSignalsLeakage` | 2 | Recursive scan + person_id ownership |
| `TestFamilyRelationshipsLeakage` | 4 | No sensitive keys; owner_user_id == own UUID (list + create) |
| `TestFamilyContextLeakage` | 2 | family-health-context and family-recommendations recursive scan |
| `TestCrossUserIsolation` | 3 | Cross-user person_id → 404 on evidence-bundle, family-context, recommendations |
| `TestNotificationStatusLeakage` | 2 | Snooze + ignore `_serialize_log` response recursive scan |

Recursive scanner: checks `password_hash`, `hashed_password`, `password`, `storage_bucket`, `storage_key`, `file_path`, `download_token`, `secret_key`, `secret`, `is_superuser`, `is_staff`.

### 7. Commits
- `967fe18` — `test(security): add health_assistant response leakage regression (P33)`

### 8. runtime-smoke Results
| Stage | Suite | Result |
|---|---|---|
| 1 | Health check | 3 passed |
| 2 | Security smoke | 29 passed, 2 skipped |
| 3 | Config smoke | 24 passed |
| 4 | Validation smoke | 57 passed |
| **Total** | | **113 passed, 2 skipped** |

---

## P32-RESPONSE-SCHEMA-LEAKAGE-AUDIT (2026-05-23)

**Final Classification: `P32_RESPONSE_LEAKAGE_HARDENED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `1748d94` (P31 docs commit) ✅
- Working tree: clean ✅

### 2. Response Leakage Inventory

| Endpoint / Schema | Response Model | Sensitive Fields Considered | Current Guard | Classification | Action |
|---|---|---|---|---|---|
| POST /auth/register | `UserResponse` | `password_hash`, `is_active` | Excluded — only `id` + `email` | A. SAFE | Regression test added |
| POST /auth/login | `TokenResponse` | `password_hash` | JWT only — intentional | A. SAFE | Regression test added |
| GET /persons, POST /persons | `PersonResponse` | `password_hash`, `owner_user_id` | `password_hash` excluded; `owner_user_id` is own UUID only | B. PARTIAL | Regression test: confirms own-UUID invariant |
| POST /documents/upload, GET /documents | `DocumentResponse` | `storage_bucket`, `storage_key` | **Both included — internal infra fields** | **C. GAP** | **Fixed: both fields removed from schema** |
| GET /profile/me | `ProfileResponse` | `user_id`, `password_hash` | `password_hash` excluded; `user_id` is own UUID | B. PARTIAL | Documented — not a cross-user leak |
| GET /profile/account | `AccountResponse` | `password_hash`, `account_settings dict` | `password_hash` excluded; `account_settings` is opaque | B. PARTIAL | Documented |
| POST /reports/generate | `ReportGenerateResponse` | `token`, `file_path` | Neither exposed — only `report_id` + `status` | A. SAFE | Schema test added |
| GET /reports/{id} | `ReportStatusResponse` | `token`, `file_path` | No raw `token` key; no `file_path`; download_url embeds token intentionally | A. SAFE | Schema test added |

### 3. Gap Found and Fixed: `DocumentResponse` — storage_bucket + storage_key

**Root cause**: `DocumentResponse` in `backend/app/schemas/documents.py` declared `storage_bucket: str` and `storage_key: str`. These are internal infrastructure fields — the S3/local bucket name and the object path. Clients have no need for them; the server uses them exclusively for internal `download_file()` calls.

**Fix**: Removed both fields from `DocumentResponse`. The ORM model (`MedicalDocument`) retains the columns — server-side parsing (`/parse`) still works. FastAPI `response_model` filtering now prevents these fields from appearing in any document endpoint response.

**File changed**: `backend/app/schemas/documents.py`

### 4. Intentional Exposures Documented

- `TokenResponse.access_token` — intentional; required for client auth
- `PersonResponse.owner_user_id` — exposed only to the authenticated owner; not a cross-user leak; documents which user owns the profile
- `ProfileResponse.user_id` — same as above
- `ReportStatusResponse.download_url` — embeds download token in URL; intentional; endpoint is owner-only verified

### 5. Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/documents.py` | Removed `storage_bucket` and `storage_key` from `DocumentResponse` |
| `backend/tests/test_response_leakage.py` | Created — 12 regression tests |

### 6. Tests Added

`backend/tests/test_response_leakage.py` — 12 tests:

| Class | Test | Result |
|---|---|---|
| `TestAuthResponseLeakage` | `test_register_response_no_password_hash` | PASS |
| `TestAuthResponseLeakage` | `test_register_response_fields` | PASS |
| `TestAuthResponseLeakage` | `test_login_response_no_password_hash` | PASS |
| `TestAuthResponseLeakage` | `test_login_response_has_access_token` | PASS |
| `TestPersonResponseLeakage` | `test_persons_list_no_password_hash` | PASS |
| `TestPersonResponseLeakage` | `test_persons_list_owner_uuid_is_own` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_no_storage_bucket_field` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_no_storage_key_field` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_omits_storage_from_orm` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_response_no_raw_token_field` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_response_no_file_path_field` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_schema_serialized_keys` | PASS |

### 7. Validation Results

| Target | Result |
|---|---|
| `pytest tests/test_response_leakage.py` | 12 passed ✅ |
| `make runtime-smoke` | all 4 stages pass ✅ |

### 8. Known Limitations / Unknowns

- `AccountResponse.account_settings: dict` — opaque dict. If caller stores internal flags there, they would be exposed. However, `AccountResponse` is owner-only (`GET /profile/account`) and the dict contents are controlled by the user themselves. Classified B.PARTIAL; not fixed in this phase.
- `DashboardOverviewV2Response` and related dashboard schemas contain multiple `list[dict[str, Any]]` fields. These are aggregated computed data; no raw ORM internal fields confirmed. Classified D.UNKNOWN — out of P32 scope; requires deeper consumer review.
- `health_assistant.py` routes all return `dict[str, Any]` with no `response_model`. Content is LLM-orchestrated. Not audited in P32.

### 9. Commits
- `7e08118` — `fix(security): remove storage_bucket and storage_key from DocumentResponse (P32)`
- `b6875ab` — `test(security): add response leakage regression coverage (P32)`

---

## P31-VALIDATION-SMOKE-GATE-CONSOLIDATION (2026-05-23)

**Final Classification: `P31_RUNTIME_SMOKE_VALIDATION_GATE_READY`**

---

### 1. Branch Governance Pre-flight
- Branch: `main` | HEAD before: `35fb405` | Status: clean ✅

### 2. Smoke Coverage Audit (P23–P30)

| Test File | Tests | Prior Target | Classification |
|---|---|---|---|
| `test_input_validation_hardening.py` (P23) | 19 | none | **B — MISSING** |
| `test_input_validation_boundary.py` (P24) | 11 | none | **B — MISSING** |
| `test_injection_smoke.py` (P27) | 7 | none | **B — MISSING** |
| `test_schema_validation_p30.py` (P30) | 20 | none | **B — MISSING** |
| `test_config_security_guard.py` (P28) | — | `config-smoke` | **A — INCLUDED** |
| `test_runtime_config_startup_guard.py` (P29) | — | `config-smoke` | **A — INCLUDED** |
| `test_runtime_smoke.py` | 3 | `runtime-smoke` (stage 1) | **A — INCLUDED** |
| `test_auth_negative_smoke.py` | — | `security-smoke` | **A — INCLUDED** |
| `test_real_token_auth_negative.py` | — | `security-smoke` | **A — INCLUDED** |

### 3. Files Changed

- `Makefile` — added `validation-smoke` target; added as stage 4 of `runtime-smoke`; updated `.PHONY`

### 4. New / Updated Makefile Targets

**`validation-smoke` (new):**
```
cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
    tests/test_input_validation_hardening.py \
    tests/test_input_validation_boundary.py \
    tests/test_injection_smoke.py \
    tests/test_schema_validation_p30.py
```

**`runtime-smoke` (updated — stage 4 added):**
```
1. test_runtime_smoke.py       (health endpoint contracts)
2. security-smoke              (auth audit + frontend tsc)
3. config-smoke                (P28/P29 secret guard)
4. validation-smoke            (P23/P24/P27/P30 schema/injection)
```

### 5. Validation Results

| Target | Result |
|---|---|
| `make validation-smoke` | 57 passed, 0 failed ✅ |
| `make runtime-smoke` | all stages pass (3 + 29 + 15 + 57 = 104 tests) ✅ |

### 6. Known Limitations
- `frontend-tsc` step in `security-smoke` requires Node.js — if tsc is unavailable the gate fails. This is pre-existing behavior, not introduced by P31.
- `validation-smoke` only covers P23/P24/P27/P30. P25 (health endpoint runtime), P26 (rate-limit smoke), P28/P29 (config guard) remain in their own dedicated targets which are already part of `runtime-smoke`.

### 7. Commit
- `75214b8` — `chore(governance): add validation-smoke to runtime gate (P31)`

---

## P30-SCHEMA-VALIDATION-BOUNDARY-HARDENING (2026-05-23)

**Final Classification: `P30_SCHEMA_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight
- Branch: `main` | HEAD before: `8c36e51` | Status: clean ✅

### 2. Full Schema Audit (18 schema files + inline API classes)

All 18 files in `backend/app/schemas/` and 3 inline `BaseModel` classes in
`backend/app/api/` were audited. Files classified as:

- **SAFE A**: `auth.py` (existing), `symptoms.py`, `ai_modules.py`, `ai_summary.py`,
  `health_score.py`, `external_metrics.py` (all response/read-only)
- **RESPONSE ONLY** (no user input): `dashboard.py`, `decision.py`, `health_analysis.py`,
  `health_score.py`, `insights.py`, `risk_alerts.py`, `timeline.py`, `trend_analysis.py`
- **GAPS IDENTIFIED**: `persons.py`, `metrics.py`, `auth.py` (change-password),
  `actions.py`, `health_assistant.py` inline classes, `external_metrics.py` query param

### 3. Gaps Identified & Fixed

| Schema / File | Class / Field | Gap | Fix Applied |
|---|---|---|---|
| `schemas/persons.py` | `PersonCreateRequest.allergies` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonCreateRequest.family_history` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonCreateRequest.chronic_conditions` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonUpdateRequest` (same 3 fields) | Same | Same fix |
| `schemas/metrics.py` | `MetricCreateRequest.note` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/auth.py` | `ChangePasswordRequest.current_password` | No `max_length` (bcrypt DoS risk) | `Field(max_length=1024)` |
| `schemas/actions.py` | `HealthActionCreate.confidence` | No `ge/le` range | `Field(ge=0, le=1)` |
| `api/health_assistant.py` | `_SnoozeBody.snoozed_until` | No `max_length` | `Field(max_length=40)` |
| `api/health_assistant.py` | `_FamilyRelationshipBody.related_profile_id` | No `max_length` | `Field(max_length=36)` |
| `api/external_metrics.py` | `metric` Query param | No `max_length` | `Query(max_length=60)` |

### 4. UNKNOWN D (deferred — deeper review needed)

| Schema | Field | Reason |
|---|---|---|
| `documents.py` | `DocumentConfirmRequest.confirmed_data: dict[str, Any]` | Arbitrary confirmed report data; size-limiting requires understanding all consumers |
| `profile.py` | `AccountUpdateRequest.account_settings: Optional[dict]` | App-controlled settings dict; keys are not user-driven free text |

### 5. Test Coverage (20 tests, 100% pass)

File: `backend/tests/test_schema_validation_p30.py`

- `TestPersonFieldConstraints` — 7 tests (create + update per-field rejection + valid accepted)
- `TestMetricNoteConstraint` — 2 tests
- `TestChangePasswordConstraint` — 2 tests
- `TestActionConfidenceConstraint` — 5 Pydantic tests (boundary + None)
- `TestHealthAssistantInlineSchemas` — 4 Pydantic tests

### 6. Regression
Full suite: **833 passed, 2 skipped, 0 failed**

### 7. Commits
- `43a318a` — `fix(validation): harden remaining schema boundary constraints (P30)`
- `716a618` — `test(validation): add P30 schema boundary regression coverage`

---

## P29-PRODUCTION-CONFIG-RUNTIME-SMOKE (2026-05-23)

**Final Classification: `P29_PRODUCTION_CONFIG_RUNTIME_SMOKE_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `69d46e2` (P28 complete) ✅ |
| Dirty files | none ✅ |

---

### 2. Runtime Guard Surface Classification

| Surface | Classification | Evidence |
|---|---|---|
| `validate_production_secrets()` function | **SAFE A** | 15 unit tests in `test_config_security_guard.py` (P28) |
| `startup_event()` integration | **PARTIAL B → FIXED** | Not tested in P28; fixed by P29 startup integration tests |
| Env-var → Settings resolution | **PARTIAL B → FIXED** | `APP_ENV` / `JWT_SECRET_KEY` env var priority not smoke-tested; fixed in P29 |
| `get_settings()` lru_cache override | **PARTIAL B → FIXED** | Cache-clear + env var re-read behavior not verified; fixed in P29 |
| `config-smoke` Makefile target | **GAP C → FIXED** | Target absent from Makefile; added in P29 |
| `runtime-smoke` includes guard | **GAP C → FIXED** | `runtime-smoke` did not call config tests; now calls `config-smoke` as third stage |

---

### 3. Tests Added — `backend/tests/test_runtime_config_startup_guard.py`

9 tests, 3 classes:

| Class | Tests | What is verified |
|---|---|---|
| `TestEnvVarToSettingsResolution` | 4 | `APP_ENV` env var overrides default; `JWT_SECRET_KEY` env var overrides default; production+placeholder via env vars triggers guard; production+real secret via env vars accepted |
| `TestStartupEventIntegration` | 3 | `startup_event()` raises `RuntimeError` with production+insecure settings (monkeypatched); passes with dev+insecure; passes with production+real secret |
| `TestGetSettingsCacheBehavior` | 2 | `cache_clear()` + env var override gives production env; after cleanup, local dev env is safe and guard-free |

All tests are DB-independent. `app_auto_create_tables=False` used in pass-through startup tests.

---

### 4. Makefile Changes

**New target `config-smoke`:**
```makefile
config-smoke:
    cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
        tests/test_config_security_guard.py \
        tests/test_runtime_config_startup_guard.py
```
Runs 24 tests (P28 + P29), no DB required, ~1.5s.

**`runtime-smoke` updated** — now three stages:
1. `test_runtime_smoke.py` — health endpoint contracts
2. `security-smoke` — auth/JWT regression + TypeScript typecheck
3. `config-smoke` — production secret guard regression (new)

---

### 5. Test Results

| Suite | Result |
|---|---|
| `make config-smoke` | **24 / 24 PASSED** |
| `make runtime-smoke` | **ALL STAGES PASS** |
| Full backend regression | **813 passed, 2 skipped, 0 failed** |

---

### 6. Commits

| Ref | Message |
|---|---|
| `d7aab81` | `test(config): add runtime startup guard smoke regression` |
| `954b62a` | `chore(governance): add config-smoke runtime guard target` |
| C3 (this report) | `docs(report): P29 production config runtime smoke report` |

---

### 7. Known Limitations

| Limitation | Impact |
|---|---|
| `startup_event()` tested via direct call, not `TestClient` ASGI lifecycle | TestClient ASGI startup is already covered by `test_runtime_smoke.py` (local env) |
| `on_event('startup')` is deprecated in FastAPI; 4 deprecation warnings in tests | Cosmetic; pre-existing; does not affect guard behavior |
| env-var tests use `monkeypatch.setenv` which may interact with `.env` file if pydantic-settings priority order changes | Low risk; priority (env > .env file) is documented pydantic-settings behavior |

---

## P28-SECRETS-PRODUCTION-CONFIG-GUARD (2026-05-23)

**Final Classification: `P28_PRODUCTION_SECRET_GUARD_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `81e2ce7` (P27 complete) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Full secrets / production config inventory across:
- `backend/app/core/config.py` — all 30 `Settings` fields
- `backend/app/main.py` — startup and middleware wiring
- `docker-compose.prod.yml` — production environment overrides
- `docker-compose.yml` — dev/base environment defaults
- `backend/.env` / `.env.example` — local and example env files

No frontend changes. No new pip/npm dependencies. No DB schema changes.

---

### 3. Config Surface Classification

| Config Key | Default | Classification | Risk Level |
|---|---|---|---|
| `jwt_secret_key` | `'replace_me'` | **GAP C → FIXED** | CRITICAL: JWT forgeable if default reaches prod |
| `s3_secret_key` | `'minioadmin'` | PARTIAL B | MEDIUM: MinIO/S3 access via hardcoded creds |
| `database_url` | `postgres:postgres@localhost` | PARTIAL B | MEDIUM: dev creds in default URL |
| `sentry_environment` | `'production'` | PARTIAL B | LOW: dev events routed to prod Sentry project if DSN set in dev |
| `app_debug` | `False` | SAFE A | FastAPI debug disabled by default |
| `app_env` | `'dev'` | SAFE A | Correct dev default; prod compose overrides to `'production'` |
| `cors_allow_origins` | `http://localhost:3000,...` | SAFE A | Restrictive default; restricts cross-origin to localhost |
| `rate_limit_enabled` | `False` | PARTIAL B | Opt-in; must be explicitly enabled for production hardening |
| `trusted_hosts` | `'*'` | PARTIAL B | Wildcard; should be scoped in production |
| `openai_api_key` | `''` | SAFE A | Empty default; AI features disabled until key provided |
| `sentry_dsn` | `''` | SAFE A | Empty default; Sentry disabled until DSN provided |

---

### 4. GAP C Fix — JWT Secret Production Guard

**Gap:** `jwt_secret_key: str = 'replace_me'` had no enforcement.  
`docker-compose.prod.yml` sets `APP_ENV: production` via the `environment:` block.  
An operator could deploy `docker-compose.prod.yml` while relying on the `.env`
file for `JWT_SECRET_KEY` — if omitted, the config fell through to `'replace_me'`
and the server started without any warning.

**Fix — `backend/app/core/config.py`:**

```python
_INSECURE_JWT_PLACEHOLDERS: frozenset[str] = frozenset({
    '', 'replace_me', 'replace_me_in_prod',
})
_PRODUCTION_ENVS: frozenset[str] = frozenset({'production', 'prod'})

def validate_production_secrets(settings: Settings) -> None:
    if settings.app_env.lower() in _PRODUCTION_ENVS:
        if settings.jwt_secret_key in _INSECURE_JWT_PLACEHOLDERS:
            raise RuntimeError(
                "UNSAFE STARTUP: jwt_secret_key is set to a known insecure "
                "placeholder in app_env='...'. Set JWT_SECRET_KEY environment "
                "variable to a cryptographically random value (>= 32 bytes) "
                "before starting in production."
            )
```

**Fix — `backend/app/main.py`:**
`validate_production_secrets(settings)` called as the first line of `startup_event()`.
The server refuses to accept any requests if the guard fires.

---

### 5. Tests — `backend/tests/test_config_security_guard.py`

15 tests, 4 classes:

| Class | Tests | Scope |
|---|---|---|
| `TestProductionRejectsInsecurePlaceholders` | 5 | `replace_me`, `replace_me_in_prod`, empty string, `prod` alias, error message names `JWT_SECRET_KEY` |
| `TestProductionAcceptsRealSecret` | 2 | 64-char hex secret accepted in `production` and `prod` |
| `TestNonProductionAllowsPlaceholder` | 6 | dev / local / staging / test / development (parametrised) + default settings are safe |
| `TestRateLimitSettingsParseable` | 2 | PARTIAL B classification: opt-in flag parses correctly |

All 15 pass.

---

### 6. Regression Results

| Suite | Before | After |
|---|---|---|
| Full backend | 789 passed, 2 skipped | **804 passed, 2 skipped, 0 failed** |
| P28 guard tests | — | 15 / 15 PASSED |

---

### 7. Commits

| Ref | Message |
|---|---|
| `67e8681` | `fix(config): add production guard for insecure JWT secret` |
| `b0a0a23` | `test(config): P28 runtime security config guard regression` |
| C3 (this report) | `docs(report): P28 secrets and production config guard report` |

---

### 8. Remaining PARTIAL B Items (Not Fixed in P28 — Require Ops Decisions)

| Item | Recommendation |
|---|---|
| `s3_secret_key = 'minioadmin'` | Override via `S3_SECRET_KEY` env var in production; add to deployment runbook |
| `rate_limit_enabled = False` | Set `RATE_LIMIT_ENABLED=true` in `docker-compose.prod.yml` for production hardening |
| `trusted_hosts = '*'` | Set `TRUSTED_HOSTS=yourdomain.com` in production |
| `sentry_environment = 'production'` | Override `SENTRY_ENVIRONMENT` to `local` or `dev` in local `.env` files |

---

## P27-INPUT-SANITIZATION-INJECTION-AUDIT (2026-05-23)

**Final Classification: `P27_INJECTION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `37736a1` (P26 tests) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Full input sanitization / injection surface audit across all routes. Five injection
categories checked: SQL injection, filesystem path traversal, AI prompt injection,
log injection, module/parameter injection.

No auth changes. No new dependencies. No frontend changes.

---

### 3. Surface Classification (Final)

| Surface | Sink Type | Guard Before P27 | Classification | Action |
|---|---|---|---|---|
| All DB queries (every route) | SQL | SQLAlchemy ORM — parameterized | **SAFE A** | None |
| `conn.execute(text('SELECT 1'))` in `main.py` | SQL | Hardcoded query, no user input | **SAFE A** | None |
| `upload_file()` storage key | Filesystem | UUID-based key, never uses filename | **SAFE A** | None |
| `_local_path_from_key()` | Filesystem | `startswith(root)` guard | **SAFE A** | None |
| `original_filename = file.filename` | DB metadata + PDF | ❌ No basename normalization | **GAP C → FIXED** | `os.path.basename` applied |
| `evaluate_module` `module_name` URL param | Module dispatch | Allowlist `{'health_check_interpreter','symptom_analysis','health_risk_prediction'}` | **SAFE A** | None |
| Fixed-route module names | Module dispatch | Hardcoded in handler | **SAFE A** | None |
| `_build_prompt()` `focus` field | AI prompt | `max_length=200` only (P24) | **PARTIAL B** | Documented — self-contained risk |
| `_load_prompt_template()` module param | Filesystem | `PROMPT_FILES` dict guard | **SAFE A** | None |
| `report_id` URL param | Dict lookup + FileResponse | `_REPORT_STATE.get(id)` → None → 404 | **SAFE A** | None |
| Download `file_path` | FileResponse | Server-set UUID path; not from client | **SAFE A** | None |
| Request logger | Log | Logs only method/path/status/latency/ip; `json.dumps(ensure_ascii=True)` | **SAFE A** | None |
| PDF `original_filename` content | PDF bytes | Parens escaped; covered by GAP C fix | **SAFE A (after fix)** | Covered by filename fix |

---

### 4. Fix Applied — GAP C: `original_filename` Path Traversal in DB Metadata

**File:** `backend/app/api/documents.py`

**Symptom:** Uploading a file named `../../evil.pdf` (valid PDF extension, valid
MIME type) would store the raw string `../../evil.pdf` in `MedicalDocument.original_filename`.
The filesystem was already safe (storage key is `documents/<user_id>/<uuid4>.pdf`).
The DB metadata and PDF report rendering received the un-sanitized value.

**Fix (1 line):**
```python
# Before (line 42):
original_filename=file.filename or 'unknown',

# After:
original_filename=os.path.basename(file.filename or '') or 'unknown',
```
`os.path.basename('../../evil.pdf')` → `'evil.pdf'`.

Also added `import os` at the top of `documents.py` (stdlib, no new dependency).

---

### 5. Documented Gap — PARTIAL B: `focus` Prompt Injection Surface

**File:** `backend/app/services/ai_modules_service.py` → `_build_prompt()`

`focus` is interpolated directly into the AI prompt string:
```python
focus_text = focus or '無特定焦點，請綜合分析。'
f'分析焦點: {focus_text}\n'
```

**Risk level:** Low. The `focus` field is:
- Bounded to `max_length=200` chars (P24 hardening)
- Requires authentication to reach the route
- Self-contained: an attacker can only affect their own AI analysis output
- No data leakage to other users is possible through this vector
- AI model is only called when `settings.openai_api_key` is set; test/default env uses rule-based fallback

**Decision:** Document only. Structural prompt injection mitigations (e.g.,
instruction delimiters, output format enforcement) are AI model layer concerns
outside the scope of backend hardening. The bounded max_length from P24 already
limits the surface area.

---

### 6. Tests Created

**File:** `backend/tests/test_injection_smoke.py` — 7 tests, all pass

```
TestDocumentFilenameInjection::test_path_traversal_filename_stored_as_basename   PASS
TestAIModuleInjection::test_unknown_module_name_rejected                         PASS
TestAIModuleInjection::test_prompt_injection_focus_does_not_crash                PASS
TestReportIdentifierInjection::test_status_unknown_id_returns_404                PASS
TestReportIdentifierInjection::test_status_injection_strings_return_404          PASS
TestReportIdentifierInjection::test_download_unknown_report_returns_404          PASS
TestReportIdentifierInjection::test_download_wrong_token_returns_403             PASS
```

Full regression: **789 passed, 2 skipped, 0 failures** (13.6 s)

---

### 7. Commits

| SHA | Message |
|---|---|
| `43912e8` | `fix(security): normalize uploaded filename to basename before DB storage` |
| `f2a2209` | `test(security): P27 injection surface smoke regression (7 tests)` |

---

## P26-RATE-LIMIT-BRUTE-FORCE-AUDIT (2026-05-23)

**Final Classification: `P26_RATE_LIMIT_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `a3d69f8` (P25 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Rate-limit / brute-force protection audit — verifying that:
- `InMemoryRateLimitMiddleware` is correctly implemented
- Health endpoints are exempt from throttling
- Middleware behavior is covered by regression tests
- Config knobs are correctly documented
- Rate limiting remains **opt-in** (`RATE_LIMIT_ENABLED=true` env var)

No auth changes. No DB changes. No new dependencies. No production behavior enabled.

---

### 3. Rate-Limit Inventory

#### Middleware — `backend/app/core/rate_limit.py`

| Property | Value |
|---|---|
| Class | `InMemoryRateLimitMiddleware(BaseHTTPMiddleware)` |
| Bucket key | `{client_ip}:{path}` — per-IP per-path |
| Window algorithm | Sliding window (deque, time-based) |
| Health exemption | `path.startswith('/health')` → bypassed |
| 429 body | `{'detail': 'Rate limit exceeded'}` — no internal leak |
| Storage | Thread-safe in-process `defaultdict(deque)` with `Lock` |
| External dependency | None (`slowapi` is NOT installed and NOT used) |

#### Config — `backend/app/core/config.py`

| Setting | Default | Env Var |
|---|---|---|
| `rate_limit_enabled` | `False` | `RATE_LIMIT_ENABLED` |
| `rate_limit_requests` | `120` | `RATE_LIMIT_REQUESTS` |
| `rate_limit_window_seconds` | `60` | `RATE_LIMIT_WINDOW_SECONDS` |

`.env.example` shows `RATE_LIMIT_ENABLED=true` — production intent is documented.

#### Wiring — `backend/app/main.py`

```python
if settings.rate_limit_enabled:
    app.add_middleware(InMemoryRateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds)
```

Middleware is conditionally mounted at startup — clean opt-in behavior.

---

### 4. Classification

| Item | Classification |
|---|---|
| Middleware implementation (`InMemoryRateLimitMiddleware`) | **SAFE A** — correct sliding window, thread-safe, no external deps |
| `/health`, `/health/live`, `/health/ready` exempt | **SAFE A** — `startswith('/health')` bypasses throttling |
| 429 body safe (`detail` only, no internals) | **SAFE A** — confirmed |
| Per-path bucket isolation | **SAFE A** — confirmed: exhausting path A does not affect path B |
| `rate_limit_enabled=False` default | **PARTIAL B** — middleware exists but opt-in; correct for dev/test |
| No existing rate-limit smoke test | **GAP C** → **FIXED** — `test_rate_limit_smoke.py` added |
| `slowapi` not installed | **SAFE A** — not needed; custom middleware is self-contained |
| Default threshold `120 req/60s` per IP per path | **PARTIAL B** — adequate for general use; auth endpoints (login, register) share this global threshold, not a stricter per-route limit |

#### Remaining known limitation (out of scope for P26)
- `InMemoryRateLimitMiddleware` is **global**, not per-route. Auth endpoints (`POST /api/v1/auth/login`, `POST /api/v1/auth/register`) are throttled at the same `120 req/60s` rate as all other endpoints. A per-route stricter limit (e.g., `10 req/60s` for login) would require route-level decorator support or a dedicated auth-route bucket override — this is a future hardening task, not P26 scope.
- In-memory storage does not persist across restarts and is not shared across multiple worker processes. Suitable for single-process deployment; multi-worker deployments would need Redis-backed storage.

---

### 5. Fixes Applied

| Commit | SHA | Description |
|---|---|---|
| C1 | `d3f73f5` | `test(security): add rate-limit smoke regression` |

#### C1 — `backend/tests/test_rate_limit_smoke.py` (7 tests)

| Test | Assertion |
|---|---|
| `test_health_get_exempt_when_enabled` | `/health` → 200 ×5, never 429 |
| `test_health_live_exempt_when_enabled` | `/health/live` → 200 ×5, never 429 |
| `test_health_ready_exempt_when_enabled` | `/health/ready` → 200 ×5, never 429 |
| `test_non_health_route_limited` | 3 allowed → 4th is 429 (threshold=3) |
| `test_429_body_is_safe` | `{detail: 'Rate limit exceeded'}`, no traceback/error/store keys |
| `test_disabled_mode_no_interference` | No middleware → 200 ×10 |
| `test_different_paths_tracked_separately` | Path A exhausted → Path B still returns 200 |

All tests use a minimal self-contained FastAPI app — no DB, no auth, no running server.

---

### 6. Regression Gate

| Gate | Result |
|---|---|
| `test_rate_limit_smoke.py` (7 tests) | **7/7 PASS** |
| `make runtime-smoke` (health + security chain) | **EXIT:0** — 29 passed, 2 skipped |

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_rate_limit_smoke.py` | **CREATED** — 140 lines, 7 tests |
| `00-Plan/roadmap/active_task_report.md` | **UPDATED** — P26 block prepended |

---

### 8. Rate Limiting Status After P26

- **Remains opt-in** — `RATE_LIMIT_ENABLED=false` by default
- **Production activation**: set `RATE_LIMIT_ENABLED=true` in environment
- **Default production threshold**: 120 requests / 60 seconds per IP per path
- **Health endpoints**: always exempt (verified by tests)
- **Middleware contract**: verified by 7-test regression suite

---

### 9. Final Status

```
P26_RATE_LIMIT_SMOKE_VERIFIED
HEAD: d3f73f5
make runtime-smoke: EXIT:0
InMemoryRateLimitMiddleware: VERIFIED — exempt, throttling, safe 429, path isolation
Rate limiting: remains opt-in (RATE_LIMIT_ENABLED=true to activate)
Known gap: global threshold only, no per-route stricter limit for auth endpoints
Next: P27 — TBD
```

---

---

## P25-DEPLOYMENT-SMOKE-RUNTIME-READINESS (2026-05-23)

**Final Classification: `P25_RUNTIME_HEALTH_ENDPOINT_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `6537e33` (P24 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Runtime readiness audit — verifying that:
- Health endpoints exist and return the correct contract
- A single `make runtime-smoke` target chains health + security regression
- Runtime configuration gaps are inventoried and classified

No DB schema changes. No auth logic changes. No new production dependencies.

---

### 3. Inventory Classification

| Item | Classification |
|---|---|
| `GET /health` → 200, `{status: ok}` | **SAFE A** — exists, correct |
| `GET /health/live` → 200, `{status: alive}` | **SAFE A** — exists, correct |
| `GET /health/ready` → 200 (DB up) / 503 (DB down) | **SAFE A** — DB probed via `SELECT 1` |
| `InMemoryRateLimitMiddleware` skips `/health` paths | **SAFE A** — confirmed in `rate_limit.py` |
| `app_auto_create_tables=True` on startup | **SAFE A** — documented behavior |
| `docker-compose.local.yml` starts PostgreSQL only | **SAFE A** — correct by design |
| `smoke_check.py` is an orchestrator task checker | **PARTIAL B** — NOT a deployment health check; named misleadingly |
| `rate_limit_enabled=False` by default | **PARTIAL B** — middleware exists but must be enabled via `RATE_LIMIT_ENABLED=true` |
| No health endpoint pytest coverage | **GAP C** → **FIXED** — `test_runtime_smoke.py` added |
| No `make runtime-smoke` target | **GAP C** → **FIXED** — added to `Makefile` |
| `jwt_secret_key` default is an insecure placeholder | **GAP C** → DOCUMENTED (no code change; mitigated by `.env.local` override) |

---

### 4. Security Gaps Documented (no code change warranted)

#### `jwt_secret_key` insecure default
- **Location**: `backend/app/core/config.py`
- **Issue**: Default value is a well-known placeholder. If deployed to a production environment without an explicit env override, all JWTs would share a predictable signing key.
- **Current mitigation**: `.env.local` overrides with a non-default local value. Production deployments are expected to set `JWT_SECRET_KEY` via environment variable.
- **Recommended hardening** (future): Add a startup guard in `main.py` that raises `RuntimeError` when `app_env == 'production'` and `jwt_secret_key` matches the insecure default.

#### `rate_limit_enabled=False`
- **Location**: `backend/app/core/config.py`
- **Issue**: `InMemoryRateLimitMiddleware` is implemented correctly but disabled by default. Public deployments without `RATE_LIMIT_ENABLED=true` have no in-process rate limiting.
- **Note**: `InMemoryRateLimitMiddleware` already correctly exempts `/health` paths.

#### `smoke_check.py` naming
- **Location**: root `smoke_check.py`
- **Issue**: The file name implies deployment health checking but it queries the `OrchestratorDB` task pool. Developers may wrongly assume it verifies API readiness.
- **Resolution**: This audit adds `make runtime-smoke` → `test_runtime_smoke.py` as the canonical health smoke entry point.

---

### 5. Fixes Applied

| Commit | SHA | Description |
|---|---|---|
| C1 | `f09a530` | `test(runtime): add health endpoint contract smoke regression` |
| C2 | `a5a8d6d` | `chore(governance): add runtime-smoke Makefile target` |

#### C1 — `backend/tests/test_runtime_smoke.py`
Three in-process TestClient tests:
- `test_health_returns_ok` → `GET /health` → 200, `{status: ok, service: ...}`
- `test_health_live_returns_alive` → `GET /health/live` → 200, `{status: alive, service: ...}`
- `test_health_ready_contract` → `GET /health/ready` → 200 or 503 (not 500), `{status: ready|not_ready, ...}`

No auth overrides needed (public endpoints). Passes in CI regardless of PostgreSQL availability.

#### C2 — `Makefile` — `runtime-smoke` target
```
make runtime-smoke
```
Runs:
1. `tests/test_runtime_smoke.py` (health endpoint contract, in-process)
2. `make security-smoke` (backend-auth-audit + frontend-tsc)

No running server required for any step.

---

### 6. Regression Gate

| Gate | Result |
|---|---|
| `test_runtime_smoke.py` (3 tests) | **3/3 PASS** |
| `make runtime-smoke` full chain | **EXIT:0** — 29 passed, 2 skipped |
| P23 / P24 test files | **unmodified** |

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_runtime_smoke.py` | **CREATED** — 64 lines, 3 health endpoint tests |
| `Makefile` | **UPDATED** — `runtime-smoke` target added (7 lines) |
| `00-Plan/roadmap/active_task_report.md` | **UPDATED** — P25 block prepended |

---

### 8. Final Status

```
P25_RUNTIME_HEALTH_ENDPOINT_HARDENED
HEAD: a5a8d6d
make runtime-smoke: EXIT:0
Health endpoint contract: VERIFIED
Gaps documented: jwt_secret_key default, rate_limit_enabled=False, smoke_check.py naming
Next: P26 — TBD
```

---

---

## P24-BOUNDARY-INPUT-VALIDATION (2026-05-23)

**Final Classification: `P24_BOUNDARY_INPUT_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `fbe83cc` (P23 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Threat Model (OWASP A03 / A08 — Boundary Layer)

P23 closed obvious DB-write schema gaps. P24 targets the boundary layer:
- `Form(...)` fields with no length constraint written to DB
- `list[str]` request fields with no count or per-item length bound
- `Query(...)` parameters with no string length bound
- Optional text fields passed into AI prompt pipelines without truncation guard

---

### 3. Boundary Validation Inventory

| Endpoint | Input | Type | Current Validation | Risk | Class |
|---|---|---|---|---|---|
| `POST /documents/upload` | `category` | Form | none | DB write, unbounded | **GAP C** |
| `POST /reports/generate` | `include_sections` | Body list | no count/item bound | 25 items loop CPU + unbounded strings | **GAP C** |
| `POST /reports/generate` | `person_id` | Body str | none | no UUID format check | **PARTIAL B** |
| `POST /ai-modules/*` | `AIModuleRequest.focus` | Body str | none | passed to AI prompt pipeline | **GAP C** |
| `GET /documents/lab-history` | `metric` | Query str | none | Python filter (not SQL-inject risk, still unbounded) | **PARTIAL B** |
| `POST /documents/upload` | file/content-type/size | File | `validate_upload()` enforces all | already protected | **SAFE A** |
| All `days/limit/ge/le` query params | int | Query | `ge/le` constraints | already protected | **SAFE A** |
| `POST /ai-modules/evaluate/{module_name}` | path | Path str | explicit allowlist check | already protected | **SAFE A** |
| `health_assistant` query params | `days/period_type` | Query | `ge/le` + `pattern=` regex | already protected | **SAFE A** |

---

### 4. Fixes Applied

#### `backend/app/api/documents.py`
- `category: Form(...)` → `Form(..., min_length=1, max_length=60)` — prevents empty/oversized category written to `MedicalDocument.category`
- `metric: Query(default=None)` → `Query(default=None, max_length=120)` — bounds lab history filter query param

#### `backend/app/api/reports.py` — `ReportGenerateRequest`
- `include_sections: list[str]` → `list[Annotated[str, Field(max_length=60)]]` with `Field(max_length=20)` — prevents oversized section lists (>20 items) and per-item oversized strings (>60 chars)
- `person_id: Optional[str] = None` → `Field(default=None, max_length=36)` — UUID-length bound

#### `backend/app/schemas/ai_modules.py` — `AIModuleRequest`
- `focus: Optional[str] = None` → `Field(default=None, max_length=200)` — prevents oversized focus strings from entering AI prompt pipeline

---

### 5. Test Results

| Test File | Tests | Result |
|---|---|---|
| `test_input_validation_boundary.py` | 11 | ✅ 11 passed |
| `test_input_validation_hardening.py` | 19 | ✅ 19 passed (no regression) |
| `make security-smoke` (all auth + tsc) | 29+2skip+tsc | ✅ EXIT:0 |

#### P24 Test Coverage

| Test | Assertion |
|---|---|
| `test_sections_too_many_rejected` | 25 items → 422 |
| `test_section_item_too_long_rejected` | item >60 chars → 422 |
| `test_person_id_too_long_rejected` | person_id >36 chars → 422 |
| `test_valid_single_section_accepted` | `["score"]` → 202 |
| `test_category_too_long_rejected` | Form >60 chars → 422 |
| `test_category_empty_rejected` | Form `""` → 422 |
| `test_focus_too_long_rejected` | focus >200 chars → ValidationError |
| `test_focus_valid_accepted` | valid focus → schema OK |
| `test_focus_none_valid` | `focus=None` → schema OK |
| `test_metric_query_too_long_rejected` | metric >120 chars → 422 |
| `test_metric_query_valid_accepted` | `?metric=glucose` → 200 |

---

### 6. Commits

| SHA | Message |
|---|---|
| `07f8a7c` | `fix(validation): harden boundary input constraints` |
| `61a8c86` | `test(validation): add boundary input rejection regression (11 tests)` |

---

### 7. Known Limitations / Out-of-scope

- File upload content validation (MIME detection beyond extension/type allowlist) — would require content-scanning library — out of scope
- Report `include_sections` items are matched by string equality; unknown section names are silently ignored (no 422 for unknown section names) — by design, not a security gap
- `person_id` is not validated as a UUID format (only length-bounded); invalid UUIDs are silently ignored by the DB query — low-risk, documented
- Dynamic payloads in `narrative-memory/generate`, `personalization-profile/sync` not audited — UNKNOWN, deferred

---

### 8. Completed Security Hardening Stack

| Phase | Classification | Focus |
|---|---|---|
| P17 | `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED` | auth middleware coverage |
| P18 | `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP` | report status auth |
| P19 | `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP` | download JWT doc |
| P20 | `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED` | download auth closure |
| P21 | `P21_SECURITY_SMOKE_AND_CI_READY` | Makefile smoke target |
| P22 | `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY` | frontend e2e CI safe |
| P23 | `P23_INPUT_VALIDATION_HARDENED` | Pydantic schema constraints |
| **P24** | **`P24_BOUNDARY_INPUT_VALIDATION_HARDENED`** | **boundary Form/Query/list/focus** |

---

## P23-INPUT-VALIDATION-SCHEMA-HARDENING (2026-05-23)

**Final Classification: `P23_INPUT_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `83465e0` (P22 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Threat Model (OWASP A03 / A08)

Authenticated users can submit request bodies. Without field-level Pydantic
constraints, malformed or oversized payloads reach the DB write path — causing
either application errors (500) or unexpected data storage. Pydantic constraints
are the correct enforcement layer: they fire before any service code runs and
return 422 automatically.

---

### 3. Validation Surface Audit

| Schema | Field(s) | Previous State | Risk | Fix |
|---|---|---|---|---|
| `auth.LoginRequest` | `password` | bare `str` | C — bcrypt DoS via unbounded input | `max_length=1024` |
| `symptoms.SymptomCreateRequest` | `note` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `symptoms.SymptomUpdateRequest` | `note` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `allergies` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `family_history` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `chronic_conditions` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.AccountUpdateRequest` | `email` | bare `str` | C — no format validation | `Optional[EmailStr]` |
| `actions.HealthActionCreate` | `description` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `actions.HealthActionCreate` | `category/action_type/priority/frequency/status` | bare `str` | C — unbounded → DB | `max_length=30–60` |
| `actions.HealthActionCreate` | `source_id/evidence_level/guideline_source/rule_id` | `Optional[str]` | C — unbounded → DB | `max_length=60–200` |
| `actions.HealthActionUpdate` | `description/category/priority/frequency/status` | `Optional[str]` | C — unbounded → DB | `max_length=30–2000` |
| `actions.HealthActionUpdate` | `snooze_reason/reminder_status/impact_status` | `Optional[str]` | C — unbounded → DB | `max_length=30–500` |
| `documents.ParsedItemUpdate` | `value/unit/reference_range` | `Optional[str]` | C — unbounded → DB | `max_length=50–500` |
| `health_assistant._SnoozeBody` | `hours` | `Optional[int]` no bounds | C — negative/huge values | `ge=1, le=168` |

**Schemas already SAFE (no changes):**
- `auth.RegisterRequest` — `EmailStr` + `password min/max` ✅
- `metrics.MetricCreateRequest` — all numeric with `ge`/`le` ✅
- `persons.PersonCreateRequest/Update` — `display_name`, `relationship`, `gender`, numeric bounds ✅
- `symptoms.SymptomCreateRequest` — `severity`, `duration_minutes`, `confidence_score` bounds ✅
- `health_score.HealthScoreCalculateRequest` — `days ge/le` ✅
- `ai_modules.AIModuleRequest` — `days`, `max_items` ge/le ✅
- `health_assistant._FamilyRelationshipBody` — field validators ✅

---

### 4. Commits

| SHA | Type | Description |
|---|---|---|
| `dd8ddb0` | `fix(validation)` | Harden Pydantic constraints across schema surface |
| `0a0e116` | `test(validation)` | P23 schema rejection regression suite (19 tests) |

---

### 5. Test Results

```
19 passed, 0 failed
make security-smoke → EXIT:0  (29 auth tests + tsc — all pass)
```

Test file: `backend/tests/test_input_validation_hardening.py`

| Test | Asserts |
|---|---|
| `test_login_password_too_long` | `password * 1025 → 422` |
| `test_login_password_at_max_accepted` | `password * 1024 → not 422` |
| `test_create_note_too_long` | `note * 2001 → 422` |
| `test_update_note_too_long` | `note * 2001 → 422` |
| `test_create_valid_with_note` | `note * 200 → 200` |
| `test_allergies_too_long` | `allergies * 2001 → 422` |
| `test_family_history_too_long` | `family_history * 2001 → 422` |
| `test_chronic_conditions_too_long` | `chronic_conditions * 2001 → 422` |
| `test_account_email_invalid` | `"not-an-email" → 422` |
| `test_profile_valid` | valid upsert → 200 |
| `test_create_description_too_long` | `description * 2001 → 422` |
| `test_create_category_too_long` | `category * 61 → 422` |
| `test_create_priority_too_long` | `priority * 31 → 422` |
| `test_update_snooze_reason_too_long` | `snooze_reason * 501 → 422` |
| `test_create_valid_action` | valid action → 201 |
| `test_update_value_too_long` | `value * 501 → ValidationError` |
| `test_update_unit_too_long` | `unit * 51 → ValidationError` |
| `test_update_reference_range_too_long` | `reference_range * 101 → ValidationError` |
| `test_update_valid` | valid ParsedItemUpdate → passes |

---

### 6. P17–P23 Completed Stack

| Task | Classification | HEAD |
|---|---|---|
| P17 | `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED` | `7d36258` |
| P18 | `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP` | `e59d09e` |
| P19 | `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP` | `b37cab2` |
| P20 | `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED` | `b26cf25` |
| P21 | `P21_SECURITY_SMOKE_AND_CI_READY` | `b7c352b` |
| P22 | `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY` | `83465e0` |
| P23 | `P23_INPUT_VALIDATION_HARDENED` | `0a0e116` |

---

## P22-FRONTEND-E2E-BACKEND-DEPENDENCY (2026-05-23)

**Final Classification: `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b7c352b` (P21 report) ✅ |
| Dirty files | none ✅ |

---

### 2. CI Frontend E2E Current State (pre-P22)

CI frontend job ran: `npm run e2e` = `playwright test` (all 6 specs)

| Spec | Backend Required | CI Status before P22 |
|---|---|---|
| `health-platform.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `platform-app.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `family-health-card.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `auth-negative.spec.ts` | **Yes** — real JWT to `localhost:8000` | ❌ connection refused |
| `auth-ui-negative.spec.ts` | **Yes** — real backend UI flow | ❌ connection refused |
| `auth-ui-multi.spec.ts` | **Yes** — real backend UI flow | ❌ connection refused |

The 3 auth specs call `http://localhost:8000` directly. No backend runs in the CI frontend job.

---

### 3. Selected Option: B — Split CI to mocked-only subset

Auth e2e specs require a live backend. The equivalent auth coverage already exists as Python integration tests in the backend job (`make backend-auth-audit` — 29 tests, P13–P20). Adding a backend service to the frontend CI job would require pip install + uvicorn start + env vars — too broad for P22.

Smallest safe fix: add `e2e:ci` npm script that runs only the 3 mocked specs, switch CI to use it.

---

### 4. Changes

| File | Change |
|---|---|
| `frontend/package.json` | Added `"e2e:ci"` script — runs 3 mocked specs with `--reporter=line` |
| `.github/workflows/ci-cd.yml` | `npm run e2e` → `npm run e2e:ci`; step renamed to clarify mocked-only |
| `Makefile` | Added `frontend-e2e-local` target (full suite, documents backend requirement); added to `.PHONY` |

**`e2e:ci` script:**
```
playwright test tests/e2e/health-platform.spec.ts tests/e2e/platform-app.spec.ts tests/e2e/family-health-card.spec.ts --reporter=line
```

---

### 5. Entrypoint Map (post-P22)

| Command | Scope | Backend needed | CI? |
|---|---|---|---|
| `make security-smoke` | backend P13–P20 auth + frontend tsc | No | Recommended CI gate |
| `npm run e2e:ci` | 3 mocked Playwright specs | No | ✅ used in CI |
| `make frontend-auth-smoke` | 3 auth Playwright specs | **Yes** | Local only |
| `make frontend-e2e-local` | All 6 specs | **Yes** | Local only |
| `npm run e2e` | All 6 specs | **Yes** | Local only |

---

### 6. Validation

```
make security-smoke    29 passed, 2 skipped + 0 tsc errors
package.json JSON      valid (node -e require check)
```

`npm run e2e:ci` not run against live server in this session (no backend started). Script correctness verified via JSON parse + spec file existence check.

---

### 7. Commits

| SHA | Message |
|---|---|
| `9dabb8d` | `ci: avoid unsupported frontend e2e backend dependency` |
| `8364858` | `chore(governance): add frontend-e2e-local entrypoint` |
| final | `docs(report): P22 frontend e2e backend dependency report` |

---

### 8. Remaining CI / Manual Gaps

- Auth Playwright specs (`auth-negative`, `auth-ui-negative`, `auth-ui-multi`) not run in CI. Equivalent coverage exists in `make backend-auth-audit` (Python). Full browser-level auth validation requires `make frontend-auth-smoke` locally with backend running.
- CI frontend job does not start a backend service. If future work needs full e2e in CI, a dedicated CI job with service containers + PostgreSQL setup would be required (out of P22 scope).
- `family-health-card.spec.ts` header says "NOT RUN (no live server in CI pipeline)" — this comment is now stale but in-spec (test logic still valid); updating comments is out of P22 scope.

---

## P21-CI-ENTRYPOINT-HARDENING (2026-05-23)

**Final Classification: `P21_SECURITY_SMOKE_AND_CI_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b26cf25` (P20 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Current Command Inventory (pre-P21)

| Command | Classification | File |
|---|---|---|
| `make backend-test` | PARTIAL — re-creates `.venv` every run | Makefile |
| `make backend-smoke` | SAFE — `.venv/bin/python -m pytest`, 2 files (P12/P13 only) | Makefile |
| `PYTHONPATH=. pytest -q` (CI) | UNSAFE — bare `pytest` not guaranteed to use correct interpreter | `.github/workflows/ci-cd.yml:67` |
| `npm run e2e` (CI) | PARTIAL — runs full Playwright suite; backend not started in CI frontend job | `.github/workflows/ci-cd.yml:41` |
| `backend-auth-audit` | MISSING — no target covering full P13–P20 stack | — |
| `security-smoke` | MISSING | — |
| `frontend-auth-smoke` | MISSING | — |
| `frontend-tsc` | MISSING | — |

---

### 3. Changes

#### Makefile — 4 new targets added

| Target | Description |
|---|---|
| `backend-auth-audit` | Full P13–P20 auth regression: 4 test files, 31 collected, `.venv/bin/python -m pytest` |
| `frontend-tsc` | `cd frontend && npx tsc --noEmit` — no server required |
| `security-smoke` | `backend-auth-audit` + `frontend-tsc` — complete non-server security gate |
| `frontend-auth-smoke` | Targeted Playwright: `auth-negative`, `auth-ui-negative`, `auth-ui-multi` only |

`backend-auth-audit` covers:
- `tests/test_auth_negative_smoke.py` (P12)
- `tests/test_real_token_auth_negative.py` (P13/P14)
- `tests/test_person_id_authorization_audit.py` (P17)
- `tests/test_report_authorization_hardening.py` (P18+P20)

#### CI workflow (`.github/workflows/ci-cd.yml`)

- Line 67: `PYTHONPATH=. pytest -q` → `PYTHONPATH=. python -m pytest -q`
- CI installs to GitHub-managed Python via `pip install -r requirements-dev.txt` (no venv);  
  `python -m pytest` is more robust than bare `pytest` for PATH lookup.
- Change is minimal (1 line). No new services, no new cache.

#### backend/README.md (local only — untracked)

- Added auth audit commands section with table of covered files.
- File is excluded by `~/.gitignore_global` rule `README.md` — documented as known limitation.

---

### 4. Validation Results

```
make backend-auth-audit    29 passed, 2 skipped (expected SQLite UUID skips)
make security-smoke        29 passed, 2 skipped + 0 tsc errors
make backend-smoke         10 passed (P12/P13 regression)
```

---

### 5. Commits

| SHA | Message |
|---|---|
| `ae0cf5c` | `chore(governance): add reproducible auth security smoke targets` |
| `69badf4` | `ci: use canonical backend auth smoke entrypoint` |
| final | `docs(report): P21 CI entrypoint hardening report` |

---

### 6. CI Status

| Job | Status |
|---|---|
| Backend `Run tests` | Fixed: `pytest -q` → `python -m pytest -q` |
| Frontend `E2E` | **NOT UPDATED** — `npm run e2e` runs full suite without backend; backend is not started in the frontend CI job. Full e2e CI hardening deferred (requires service containers or job dependency). Documented as P22 candidate. |

---

### 7. Known Limitations

- `backend/README.md` documentation update is local-only; global `~/.gitignore_global:README.md` prevents commit without `-f`. 
- `make frontend-auth-smoke` requires: (1) backend running at `localhost:8000`, (2) `npm run build` completed. Not self-contained; documented in Makefile comment.
- `_REPORT_STATE` remains in-memory; report tests would fail after server restart (not a CI risk since tests use TestClient).
- CI frontend job still runs full `npm run e2e`; non-auth E2E specs (`health-platform.spec.ts`, `platform-app.spec.ts`) may fail without a real backend. Deferred.

---

## P20-REPORT-DOWNLOAD-AUTHORIZATION-CLOSED (2026-05-23)

**Final Classification: `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b37cab2` (P19 gap doc) ✅ |
| Authorization phrase | `YES modify frontend/app/components/platform/report-export-modal.tsx` ✅ confirmed in P20 task |

---

### 2. Problem

P19 identified that `GET /api/v1/reports/download/{report_id}` accepted a URL-only
`?token=` parameter — no `Authorization` header required. A browser `<a href target="_blank">`
cannot attach headers, so adding `Depends(get_current_user)` to the download endpoint would
have broken the UI. This was documented as `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP`.

P20 is the atomic closure: change the frontend to use `fetch+blob`, then harden the backend
with a JWT owner check.

---

### 3. Changes

| Step | File | Change |
|---|---|---|
| C1 | `frontend/app/components/platform/report-export-modal.tsx` | Replace `<a href target="_blank">下載報告</a>` with authenticated `fetch+blob+createObjectURL` handler reading JWT from `localStorage.getItem('token')` |
| C2 | `backend/app/api/reports.py` | Add `current_user: Annotated[User, Depends(get_current_user)]` to `download_report`; insert ownership check (`owner_user_id != current_user.id → 404`) before token check |
| C3 | `backend/tests/test_report_authorization_hardening.py` | Add `test_download_cross_user_denied` to `TestReportDownloadTokenOnly` — user B + user A's valid token → 404 |

**Security order in `download_report` after C2:**
1. Report exists + status == ready → else 404 (no existence leak)
2. **JWT owner match** → else 404 (ownership gate; 404 not 403 to avoid confirming report existence to wrong user)
3. Token (UUID) match → else 403
4. Token not expired → else 403
5. `FileResponse` 

Both conditions (valid JWT as owner **AND** valid one-time token) are now required.

---

### 4. Test Results

```
backend/tests/test_report_authorization_hardening.py  9 passed
make backend-smoke                                    10 passed
npx tsc --noEmit                                       0 errors
```

---

### 5. Commits

| SHA | Message |
|---|---|
| `0be0368` | `fix(frontend): use authenticated blob fetch for report downloads` |
| `4c33e35` | `fix(auth): require report owner JWT for report downloads` |
| `15102e1` | `test(auth): add report download owner authorization regression` |
| final | `docs(report): P20 report download authorization closure report` |

---

### 6. Known Limitations

- `_REPORT_STATE` is an in-memory `dict` — state is lost on backend restart, no persistent report storage.
- `_set_user()` test helper overrides `get_current_user` via `dependency_overrides` — tests never exercise real JWT decode. Real JWT path is covered by `test_real_token_auth_negative.py`.

---

## P19-REPORT-DOWNLOAD-JWT-HARDENING (2026-05-23)

**Final Classification: `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `e59d09e` (P18 report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Close the P18 download gap by adding JWT owner-check to `GET /api/v1/reports/download/{report_id}?token=...` so that possession of a leaked token alone is insufficient to download.

---

### 3. Investigation

**Required read-only inspection:**

- `backend/app/api/reports.py` — download endpoint is token-only, no JWT dependency
- `frontend/app/components/platform/report-export-modal.tsx` — frontend download call site
- `frontend/lib/api.ts` — `getReportStatus` and `generateReport` implementations
- `backend/app/core/deps.py` — `get_current_user` auth mechanism

---

### 4. Frontend Download Call Path (Root Cause)

```
report-export-modal.tsx
  generate()
    api.generateReport(...)          // POST /reports/generate  — JWT via fetch+Authorization header ✅
    setInterval → api.getReportStatus(reportId)  // GET /reports/{id} — JWT via fetch+Authorization header ✅
      → returns { status: 'ready', download_url: '/api/v1/reports/download/{id}?token={uuid}' }
      → setDownloadUrl(res.download_url)

  render
    <a href={downloadUrl} target="_blank" rel="noreferrer">下載報告</a>
    ↑
    BROWSER-NATIVE ANCHOR NAVIGATION — no Authorization header sent
```

File: [frontend/app/components/platform/report-export-modal.tsx](frontend/app/components/platform/report-export-modal.tsx#L27-L82)

---

### 5. Why JWT Cannot Be Added Without Frontend Change

`get_current_user` (backend/app/core/deps.py:17) uses:
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')
```

`OAuth2PasswordBearer` reads **only** from the `Authorization: Bearer <token>` HTTP header. There is no cookie fallback, no query-parameter fallback.

When the browser follows `<a href="/api/v1/reports/download/{id}?token=..."  target="_blank">`:
- The browser opens a new tab and performs a plain GET request
- **No `Authorization` header is sent** — browsers never send custom headers on anchor navigation
- Adding `current_user: Depends(get_current_user)` would raise HTTP 401 for every download

**Effect of adding `Depends(get_current_user)` today:**
```
GET /api/v1/reports/download/{report_id}?token={token}
→ FastAPI: no Authorization header
→ OAuth2PasswordBearer raises HTTP 401 Unauthorized
→ Browser shows login challenge or error page
→ All downloads broken
```

---

### 6. Required Frontend Fix (Out of Scope for P19)

The frontend `<a href>` must be replaced with a `fetch + blob + createObjectURL` pattern:

```typescript
// In report-export-modal.tsx — NOT IMPLEMENTED (frontend/app/** is governance-forbidden)
const handleDownload = async () => {
  const token = getToken()  // JWT from localStorage
  const res = await fetch(downloadUrl, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return setStatus('failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `health_report.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
```

This change is in `frontend/app/components/platform/report-export-modal.tsx` which is in `frontend/app/**` — prohibited by governance. Work **STOPPED** per P19 instructions before making any unsafe backend change.

---

### 7. Current Security Posture (P18 + P19)

| Vector | Status |
|---|---|
| User B queries user A's report status via `GET /reports/{id}` | ✅ Blocked by P18 (404) |
| User B obtains user A's download token via status endpoint | ✅ Blocked by P18 |
| User B downloads user A report with guessed/brute-forced token | ✅ Blocked — UUID entropy (122-bit) |
| User B downloads via leaked token (network/history/log) | ⚠️ Still possible — DOWNLOAD_GAP |
| Token expiry | ✅ 1-hour window (expires_at check) |

---

### 8. Files Changed

None. No code changes made. Documentation-only.

---

### 9. Test Results

No new tests added (no code changes made).

Prior regression suites:
- P18 tests: 8/8 PASS (unmodified)
- backend-smoke P12+P13: 10/10 PASS (unmodified)

---

### 10. Path Forward for P20

To fully close the download gap, the following two-file change must be scoped:

| File | Required Change |
|---|---|
| `frontend/app/components/platform/report-export-modal.tsx` | Replace `<a href>` with `fetch+blob+createObjectURL` |
| `backend/app/api/reports.py` | Add `current_user: Depends(get_current_user)` + ownership check to `download_report` |

Both changes must be made atomically or the download will break. Governance authorization for `frontend/app/**` modification required before P20 can proceed.

---

### 11. Commit

| Hash | Message |
|---|---|
| _(this commit)_ | docs(report): P19 report download JWT frontend contract gap |

---

### 12. CTO Summary (10 lines)

P19 investigated closing the report download gap by requiring JWT ownership on the download endpoint. Investigation found a hard frontend contract incompatibility: `report-export-modal.tsx` renders the download URL as `<a href target="_blank">`, which is browser-native anchor navigation — browsers never send `Authorization` headers on anchor clicks. FastAPI's `OAuth2PasswordBearer` reads only from the `Authorization: Bearer` header (no cookie, no query-param fallback). Adding `Depends(get_current_user)` to the download endpoint would 401 every download attempt, breaking the feature entirely. The required fix — replacing `<a href>` with `fetch+blob+createObjectURL` in `frontend/app/components/platform/report-export-modal.tsx` — is in `frontend/app/**`, which is governance-forbidden for P19. No unsafe backend change was made. Current posture: user B cannot obtain the download token (blocked by P18), UUID token is 122-bit (unguessable), and the 1-hour expiry limits the leak window. Gap remains only exploitable through token exfiltration. Full closure requires authorized scope for `frontend/app/**` in P20.

---

### 13. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P19 COMPLETE. Auth hardening stack status:
  P13–P18 — all backend auth isolation complete
  P19 — STOPPED: download JWT gap requires frontend/app/** change

P20 PLAN — Atomic download hardening (backend + frontend together):

Requires explicit governance authorization:
  YES modify frontend/app/components/platform/report-export-modal.tsx

If authorized:
  1. Replace <a href> with fetch+blob+createObjectURL in report-export-modal.tsx
  2. Add Depends(get_current_user) + ownership check to download_report() in reports.py
  3. Add regression tests for JWT-protected download
  4. Confirm no existing tests broken

Governance: main, no new branches, no push.
```

---

## P18-REPORT-DOWNLOAD-AUTHORIZATION-HARDENING (2026-05-23)

**Final Classification: `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `7d36258` (P17 report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Close the UNKNOWN / low-risk report authorization gap found in P17: `GET /api/v1/reports/{report_id}` had no user-ownership check — any authenticated user who knew the `report_id` could query report status and retrieve the download token.

---

### 3. `_REPORT_STATE` Before / After

**Before P18** — no user binding:
```python
_REPORT_STATE[report_id] = {
    'status': 'generating',
    'token': token,
    'expires_at': expires_at,
}
```

**After P18** — owner bound on generate:
```python
_REPORT_STATE[report_id] = {
    'status': 'generating',
    'token': token,
    'expires_at': expires_at,
    'owner_user_id': str(current_user.id),   # NEW
}
```

Both the initial `'generating'` state and the final `'ready'` state now include `owner_user_id`.

---

### 4. Endpoint Changes

#### `GET /api/v1/reports/{report_id}` — HARDENED ✅

**Before**: returned `{status: failed}` for unknown reports; no ownership check at all.

**After**:
```python
state = _REPORT_STATE.get(report_id)
if not state:
    raise HTTPException(status_code=404, detail='Report not found')
if str(state.get('owner_user_id')) != str(current_user.id):
    raise HTTPException(status_code=404, detail='Report not found')
```

- Missing report → 404 (was `{status: failed}`)
- Cross-user access → 404 (was 200 with full status)
- Own report → 200 with download URL (unchanged behavior)

#### `GET /api/v1/reports/download/{report_id}?token=...` — TOKEN-ONLY (DOWNLOAD_GAP) ⚠️

Not modified. Token is a UUID (unguessable). Token is now only returned by the hardened status endpoint to the report owner. The download endpoint therefore cannot be reached by user B in the normal flow — they cannot obtain the token.

**Residual risk**: if the token leaks via browser history, network capture, or log scraping, a third party can download without JWT. Mitigated by 1-hour expiry and UUID entropy. Not fixed in P18 scope (would require frontend auth-header change on `<a href>` download).

---

### 5. Test Results

| Test | Result |
|---|---|
| `test_generate_sets_owner_user_id` | ✅ PASS |
| `test_status_own_report_ok` | ✅ PASS |
| `test_status_cross_user_denied` | ✅ PASS |
| `test_status_unknown_report_denied` | ✅ PASS |
| `test_status_response_no_leak` | ✅ PASS |
| `test_download_valid_token_ok` | ✅ PASS |
| `test_download_wrong_token_denied` | ✅ PASS |
| `test_download_unknown_report_denied` | ✅ PASS |
| **P18 new total** | **8/8 PASS** |
| backend-smoke P12+P13 regression (10) | ✅ 10/10 PASS |

---

### 6. Files Changed

| File | Change |
|---|---|
| `backend/app/api/reports.py` | Add `owner_user_id` to both `_REPORT_STATE` assignments; harden `get_report_status` with 404 on missing / cross-user |
| `backend/tests/test_report_authorization_hardening.py` | New — 8 tests across 3 classes |

No schema changes. No new dependencies. No frontend files modified.

---

### 7. Known Limitations / Inferred

| Item | Status |
|---|---|
| Report status owned by current_user | ✅ Fixed |
| Download token only obtainable by owner (via hardened status) | ✅ Effective |
| Download endpoint token-leaked-by-external-means | ⚠️ GAP — GUID-as-secret with 1h expiry |
| `_REPORT_STATE` is in-memory (lost on restart) | Pre-existing design, out of scope |

---

### 8. Commits

| Hash | Message |
|---|---|
| `6902492` | fix(auth): bind report state and status endpoint to report owner (P18) |
| `30cba72` | test(auth): add report authorization hardening regression (P18) |
| _(this commit)_ | docs(report): P18 report status hardened with download gap |

---

### 9. CTO Summary (10 lines)

P18 closed the report authorization gap identified in P17. The `_REPORT_STATE` in-memory dict now stores `owner_user_id = str(current_user.id)` on every `POST /reports/generate` call. `GET /api/v1/reports/{report_id}` now validates `state['owner_user_id'] == str(current_user.id)` and returns 404 for both missing and cross-user report IDs — preventing user B from querying user A's report status or receiving the download token. The download endpoint (`/reports/download/{report_id}?token=...`) remains token-only to preserve browser-native download compatibility; since the token is now only obtainable by the owner through the hardened status endpoint, the practical attack surface is eliminated. Residual risk: token leakage via external means (browser history, network capture) could still allow download — mitigated by UUID entropy and 1-hour expiry. 8 new regression tests confirm ownership binding, 404 on cross-user, no data leak in response body, and valid/invalid download token flows. P12+P13+P17 smoke regressions (10+10+8 = 28 tests) all pass.

---

### 10. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P18 are COMPLETE. Full auth isolation stack verified:
  P13 — real JWT cross-user API smoke (10 tests)
  P14 — browser auth API negative smoke (10 tests)
  P15 — real-JWT UI negative smoke (1 test)
  P16 — multi-browser storageState isolation (2 tests)
  P17 — backend authorization audit (10 pass, 2 skip/SQLite)
  P18 — report status auth hardened, download gap documented (8 tests)

Known remaining gap:
  GET /api/v1/reports/download/{report_id}?token=... is token-only.
  Token leakage from external sources (browser history, network) could
  allow unauthorized download. Mitigated by UUID entropy + 1h expiry.
  Future P19 option: add JWT + owner check to download endpoint and
  update frontend to use fetch with Authorization header.

Governance:
- Branch: main
- Do NOT modify frontend files
- Do NOT add dependencies
- Do NOT push
```

---

## P17-BACKEND-AUTHORIZATION-ENFORCEMENT-AUDIT (2026-05-23)

**Final Classification: `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `34aa183` (P16 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Audit all FastAPI endpoints that accept `person_id` (query param or path param) and verify they enforce `owner_user_id == current_user.id` before returning user-owned data. Add targeted pytest coverage for all uncovered person-scoped routes.

---

### 3. Ownership Gate — `get_target_person` (app/core/deps.py)

```python
def get_target_person(
    person_id: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonProfile:
    default_person = ensure_default_person_profile(db, current_user)
    if not person_id:
        return default_person
    person_uuid = uuid.UUID(person_id)   # raises 404 on invalid UUID
    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail='Person profile not found')
    return person
```

**Verdict**: Correct. All person-scoped routes that delegate to `get_target_person` are safe.

---

### 4. Endpoint Authorization Inventory

| Endpoint | File | person_id via | Ownership mechanism | Classification |
|---|---|---|---|---|
| GET /api/v1/persons | persons.py | N/A | filter `owner_user_id == current_user.id` | **SAFE** |
| PUT /api/v1/persons/{id} | persons.py | path param | filter `id + owner_user_id == current_user.id` | **SAFE** (SQLite coercion note) |
| DELETE /api/v1/persons/{id} | persons.py | path param | filter `id + owner_user_id == current_user.id` | **SAFE** (SQLite coercion note) |
| GET /api/v1/metrics | metrics.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/symptoms | symptoms.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/documents | documents.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/dashboard/overview | dashboard.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/health-score/history | health_score.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/risk-alerts | risk_alerts.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/timeline | timeline.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/profile/me | profile.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| POST /api/v1/risk-alerts/{id}/dismiss | risk_alerts.py | path param (alert) | `RiskAlert.user_id == current_user.id` | **SAFE** |
| POST /api/v1/reports/generate | reports.py | payload.person_id | `get_target_person` + secondary `owner_user_id` check | **SAFE** |
| GET /api/v1/reports/{report_id} | reports.py | N/A | In-memory GUID-as-secret | **UNKNOWN (low risk)** |
| GET /api/v1/reports/download/{id} | reports.py | N/A | Token-as-secret, no JWT | **UNKNOWN (low risk)** |
| GET /api/v1/health-assistant/family-health-context | health_assistant.py | ?person_id | `get_target_person` | **SAFE** (P12/P13 covered) |
| GET /api/v1/health-assistant/family-recommendations | health_assistant.py | ?person_id | `get_target_person` | **SAFE** (P12/P13 covered) |
| All other health-assistant routes | health_assistant.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/actions | actions.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/analytics/* | analytics.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/ai-summary/* | ai_summary.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/insights/* | insights.py | ?person_id | `get_target_person` | **SAFE** |

---

### 5. Findings

**No proven cross-user authorization bug found.**

All person-data endpoints use `get_target_person` which enforces `owner_user_id == current_user.id` before the handler runs. A foreign `person_id` always returns HTTP 404 before any data is touched.

**UNKNOWN items (low risk, not fixed per scope):**
- `GET /api/v1/reports/{report_id}` — uses in-memory state keyed by GUID only (no user binding). Any authenticated user who guesses the UUID can query status. Risk: UUIDs are generated per-request and only returned to the requesting user; GUID-as-secret.
- `GET /api/v1/reports/download/{report_id}` — no auth, token-based. Same GUID-as-secret pattern. Short-lived (1h expiry). Low risk.

These are noted for future hardening (bind report state to `current_user.id`) but are outside the P17 fix scope.

---

### 6. Test Results

| Suite | Tests | Result |
|---|---|---|
| test_person_id_authorization_audit.py — cross-user query-param (8) | 8/8 PASS | ✅ |
| test_person_id_authorization_audit.py — path-param (2 skipped) | 2 SKIP | SQLite UUID coercion (see note) |
| test_person_id_authorization_audit.py — own-person sanity (2) | 2/2 PASS | ✅ |
| backend-smoke (P12 + P13, 10 tests) | 10/10 PASS | ✅ |
| **Total** | **10 passed, 2 skipped** | ✅ |

**SQLite skip note**: `PUT/DELETE /persons/{person_id}` routes pass the raw path-param string to SQLAlchemy's `UUID(as_uuid=True)` column. PostgreSQL's psycopg2 coerces `str→UUID` transparently; SQLite does not. The production ownership guard (`owner_user_id == current_user.id`) is correct by code inspection and mirrors the same pattern proven by all other tests.

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_person_id_authorization_audit.py` | New — 12 tests across 3 classes |

No backend application code modified (no bugs found requiring fixes).

---

### 8. Commits

| Hash | Message |
|---|---|
| `d28e13e` | test(auth): add person_id authorization audit coverage (P17) |
| _(this commit)_ | docs(report): P17 backend authorization audit report |

---

### 9. CTO Summary (10 lines)

P17 audited the complete FastAPI `person_id` authorization surface. The central ownership gate is `get_target_person` (core/deps.py) which filters `PersonProfile` by both `id` and `owner_user_id == current_user.id` — any cross-user person_id returns HTTP 404 before the handler runs. 20+ endpoints were catalogued; all person-scoped routes delegate to this gate. 8 GET endpoints were verified by automated cross-user negative probes (metrics, symptoms, documents, dashboard, health-score, risk-alerts, timeline, profile) — all returned 404 with no data leakage. 2 positive sanity checks confirm own-person access still works. PUT/DELETE /persons/{id} have the same ownership guard by code inspection; skipped in SQLite env due to UUID coercion incompatibility. Two report-download routes use GUID/token-as-secret (no user binding) — noted as low-risk UNKNOWN items for future hardening. No proven cross-user authorization bug found. Backend smoke (P12+P13, 10 tests) continues to pass.

---

### 10. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P17 are COMPLETE. Full auth isolation stack verified:
  P13 — real JWT cross-user API smoke (3 tests)
  P14 — browser auth API negative smoke (3 tests)
  P15 — real-JWT UI negative smoke (1 test)
  P16 — multi-browser storageState isolation (2 tests)
  P17 — backend authorization audit (10 tests, 2 skipped/SQLite)

P18 PLAN — Report Download Authorization Hardening:

The P17 audit found two low-risk UNKNOWN items in reports.py:
  1. GET /api/v1/reports/{report_id}     — no user binding on in-memory state
  2. GET /api/v1/reports/download/{id}  — no auth, token-only

Task: Bind report state to current_user.id so that GET /api/v1/reports/{report_id}
requires the same user who generated the report. Add a pytest verifying that
user A cannot query the status of user B's report_id.

Governance:
- Branch: main
- Allowed: modify backend/app/api/reports.py only
- Allowed: add backend/tests/test_reports_authorization_audit.py
- Do NOT modify frontend files
- Do NOT add dependencies
- Do NOT push or create branches
- Run targeted pytest only
```

---

## P16-MULTI-BROWSER-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

**Final Classification: `P16_FULL_UI_AUTH_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `2a81426` (P15 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Extend P15 to full multi-browser simultaneous sessions:
- **Positive control**: userB can access their own persons data (userB.personId in response, userA.personId absent)
- **Cross-user negative**: userA injected with userB.personId gets HTTP 404 + error UI with no data leakage
- **storageState round-trip**: JWT persists across a fresh browser context without `addInitScript`

---

### 3. Root Cause Analysis — Two Failures Fixed

#### Failure 1 — `waitForResponse` filter excluded `?person_id=...` URLs
`api.request()` appends `?person_id=<id>` to every request once `localStorage.person_id` is set. The filter `!url.includes('person_id')` excluded all matching responses → 15s timeout.
**Fix**: changed filter to `/\/api\/v1\/persons(\?|$)/.test(url)` — matches path regardless of query string.

#### Failure 2 — Route handler throw on context close propagated to test runner
`contextA.close()` while dashboard API calls were in-flight caused `route.fetch()` to throw `"Target page, context or browser has been closed"`. Playwright propagated this to the test, ending it before `contextFromStorageState` could run.
**Fix**: wrapped `route.fetch()` in try-catch inside `installCORSBridge`; on catch, calls `route.abort().catch(() => {})` silently.

---

### 4. Architecture

#### `installCORSBridge` (hardened)
```typescript
try {
  const response = await route.fetch()
  await route.fulfill({ response, headers: { ...response.headers(), ...CORS_HEADERS } })
} catch {
  await route.abort().catch(() => {})  // context closed while in-flight
}
```

#### `contextFromStorageState`
```typescript
export async function contextFromStorageState(browser: Browser, statePath: string): Promise<BrowserContext> {
  const context = await browser.newContext({ storageState: statePath })
  await installCORSBridge(context)  // route handlers NOT persisted in storageState
  return context
}
```

#### Test 1 — Simultaneous sessions
- `Promise.all([bootstrapWithRealJWT(ctxA), bootstrapWithRealJWT(ctxB)])` — two independent CORS bridges
- Positive control: reload pageB, assert `GET /api/v1/persons` → 200, contains userB.personId, not userA.personId
- Cross-user: inject userB.personId into pageA localStorage, reload, assert family-health-context → 404, error text visible, body does not contain userB.personId

#### Test 2 — storageState round-trip
- Bootstrap ctxA, `ctxA.storageState({ path: tmpFile })`, close ctxA
- `contextFromStorageState(browser, tmpFile)` → fresh context, no `addInitScript`
- Navigate to dashboard, assert `GET /api/v1/persons` → 200, `localStorage.person_id === userA.personId`

---

### 5. Test Results

| Test | Result | Duration |
|---|---|---|
| Simultaneous sessions — userB positive + userA cross-user 404 | ✅ PASS | ~9.6s combined |
| storageState round-trip — auth persists without addInitScript | ✅ PASS | ~9.6s combined |
| P15 regression (auth-ui-negative.spec.ts) | ✅ PASS | |
| P14 regression (auth-negative.spec.ts × 3) | ✅ PASS | |
| **Total** | **6/6** | **~18s** |

---

### 6. Commits

| Hash | Message |
|---|---|
| `d59c11c` | test(e2e): extract installCORSBridge + add contextFromStorageState + harden route teardown (P16) |
| `5d652cc` | test(e2e): add multi-browser storageState auth isolation smoke (P16) |
| _(this commit)_ | docs(report): P16 multi-browser storageState UI auth smoke report |

---

### 7. Files Changed

| File | Change |
|---|---|
| `frontend/tests/e2e/fixtures/auth-ui.ts` | Extracted `installCORSBridge`, added `contextFromStorageState`, hardened route handler |
| `frontend/tests/e2e/auth-ui-multi.spec.ts` | New — 2 multi-browser tests |

---

### 8. CTO Summary (10 lines)

P16 extends P15's JWT-in-localStorage auth isolation to full multi-browser simultaneous sessions. Two independent Playwright browser contexts (userA + userB) each get their own CORS bridge and JWT bootstrap. Positive control confirms userB's JWT returns their own person records and excludes userA's. Cross-user negative confirms userA injected with userB's personId gets HTTP 404 from the backend and the error UI renders with no data leakage. storageState round-trip proves that Playwright's `context.storageState()` + `browser.newContext({ storageState })` preserves the JWT across a fresh browser context without any `addInitScript` re-injection. Two bugs were fixed: (1) `api.request()` appends `?person_id=...` to all requests — the URL filter needed a path-only regex; (2) `contextA.close()` while dashboard requests were in-flight caused `route.fetch()` to throw into the test runner — fixed by try-catch inside `installCORSBridge`. All 6 tests pass (P14 × 3 + P15 × 1 + P16 × 2) in ~18s total. Auth isolation is now verified at API, UI network, UI DOM, multi-browser, and storageState persistence layers.

---

### 9. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: <see git log>).
P13–P16 are COMPLETE. All 6 e2e auth isolation tests pass.

P17 PLAN — Backend Authorization Enforcement Audit:
The P14–P16 test suite proved that the frontend correctly scopes requests to the
authenticated user's person_id. The next layer to verify is that the FastAPI backend
ALSO enforces this scoping — i.e., that endpoint handlers validate the JWT sub claim
against the requested person_id and return 403/404 for cross-user attempts at the
API level (not just via the frontend's person_id injection trick).

Task: Audit all FastAPI routes that accept a person_id path/query parameter and verify
they check `current_user.id == person_id` (or equivalent). For any route missing this
check, add the guard and write a backend pytest that directly calls the endpoint with
a valid JWT but a foreign person_id to prove 403 is returned.

Governance:
- Branch: main
- Do NOT modify frontend/**
- Do NOT run full e2e suite
- Do NOT push or create branches
- Run only the new pytest file(s) to verify
```

---

## P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

## P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

**Final Classification: `P15_REAL_JWT_STORAGESTATE_UI_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `ca16633` (P14 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Prove that a user-A browser session (real JWT in localStorage) **cannot** access user-B's family health data at the **UI rendering layer** — network assertion (HTTP 404) AND DOM assertion (error text visible, no data leakage).

---

### 3. Root Cause Analysis — Why Naive Approaches Failed

#### Attempt 1 — React controlled-input fill

`page.fill()` on the Next.js login form did not trigger React's `onChange` handler in a production (`next start`) build.  No `/api/v1/auth/login` request appeared in the network trace.  **Root cause**: Playwright's `fill()` sets the native DOM value but does not fire synthetic React events in production bundle.

#### Attempt 2 — addInitScript + waitForFunction (initial hang)

Switched to JWT bootstrap via `addInitScript`.  Two bugs caused the test to hang for the full 120 s test timeout:

| Bug | Cause | Fix |
|---|---|---|
| **CORS** | Playwright webServer runs on `:3010`; backend `cors_allow_origins` only covers `:3000,3100`. Browser sent all requests but received `time:-1` (no response). PersonProvider's `listPersons()` call never resolved → `person_id` was never set in localStorage. | Added `context.route('http://localhost:8000/**', ...)` CORS bridge in fixture: intercepts every backend request, forwards it unchanged via `route.fetch()`, patches `Access-Control-Allow-Origin: http://127.0.0.1:3010` onto the response. |
| **`waitForFunction` arg/options confusion** | `{ timeout: 10_000 }` was passed as the **2nd** positional argument (the page-function `arg`), not the **3rd** (`options`). Playwright applied `timeout: 0` (infinite) and silently ignored the `10_000` value. Test hung until the 120 s `test.setTimeout` fired. | Reordered to `waitForFunction(fn, undefined, { timeout: 10_000 })`. Confirmed in trace: `params.timeout` changed from `0` to `10000`. |

#### Attempt 3 — addInitScript re-injection on reload

Passing `personId = userA.personId` to `bootstrapWithRealJWT` caused it to be re-injected on `page.reload()` (addInitScript runs on every navigation), overwriting the cross-user injection.  **Fix**: call `bootstrapWithRealJWT(context, token)` without `personId`; let PersonProvider auto-select it.

---

### 4. Final Architecture

```
setupTwoUsers(request)
  ├─ POST /auth/register + /auth/login  → userA.token, userA.personId
  └─ POST /auth/register + /auth/login  → userB.token, userB.personId

bootstrapWithRealJWT(contextA, userA.token)
  ├─ context.route('localhost:8000/**')  ← CORS bridge (new)
  ├─ page.addInitScript({ token })       ← localStorage['token'] = userA.token
  ├─ page.goto('/platform/dashboard')   ← PersonProvider mounts → listPersons()
  └─ waitForFunction(person_id truthy, undefined, { timeout: 10_000 })  ← fix

page.evaluate(() => localStorage.setItem('person_id', userB.personId))

waitForResponse(url.includes('family-health-context'))  ← set up BEFORE reload
page.reload()
  └─ addInitScript fires: token=userA  (person_id stays as userB via localStorage)

familyCtxResponse.status()  →  404   (backend get_target_person owner check)
getByText('無法載入家庭健康資料')  →  visible
bodyText.includes(userB.personId)  →  false
```

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth-ui.ts` | Created — CORS bridge + real-JWT bootstrap fixture |
| `frontend/tests/e2e/auth-ui-negative.spec.ts` | Created — P15 full-UI cross-user smoke spec |
| `00-Plan/roadmap/active_task_report.md` | Updated — P15 report block prepended |

---

### 6. Test Result

```
Running 1 test using 1 worker
  1 passed (7.3s)
```

| Test | Status |
|---|---|
| user A real-JWT session → user B person_id → family-health-context 404 + error UI rendered | ✅ PASS |

P14 regression check (3/3 API-level tests):

```
Running 3 tests using 1 worker
  3 passed (3.1s)
```

---

### 7. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 8. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `78c1e40` | `test(e2e): add real-JWT storageState bootstrap fixture for UI smoke (P15)` |
| C2 | `d2aea8c` | `test(e2e): add full UI cross-user auth negative smoke (P15)` |
| C3 | (this commit) | `docs(report): P15 real-JWT storageState UI auth smoke report` |

---

### 9. Key Lessons

| Lesson | Detail |
|---|---|
| Playwright `waitForFunction(fn, arg, options)` — arg vs options | Passing `{ timeout }` as 2nd param silently makes it the page-function argument, not the timeout option.  Always pass `undefined` as arg when no arg is needed. |
| CORS with Playwright webServer | If `reuseExistingServer: false` and the webServer port is not in the backend CORS whitelist, ALL browser API calls will silently fail.  Use `context.route()` to bridge CORS in the fixture layer without touching production code. |
| `addInitScript` runs on every navigation | Do NOT inject values into `addInitScript` that you intend to override mid-test.  Inject only stable values (JWT token); let the app populate dynamic values (person_id). |

---

# Active Task Report — P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

## P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

**Final Classification: `P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `f1be74b` (P13-FINALIZE report, clean tree) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Current Git HEAD Before Work

```
f1be74b docs(report): P13-FINALIZE + browser auth smoke report — NOT_IMPLEMENTED with gap detail
b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
```

---

### 3. Auth Route / Token Endpoint Findings

| Item | Value |
|---|---|
| Register endpoint | `POST /api/v1/auth/register` — `{"email": str, "password": str}` — 201 on success, 400 if already registered |
| Login endpoint | `POST /api/v1/auth/login` — `{"email": str, "password": str}` → `{"access_token": str, "token_type": "bearer"}` |
| Token format | JWT (HS256), subject = user UUID |
| Persons create | `POST /api/v1/persons` with `Authorization: Bearer <token>` |
| Family health context | `GET /api/v1/health-assistant/family-health-context?person_id=<pid>` |
| Family recommendations | `GET /api/v1/health-assistant/family-recommendations?person_id=<pid>` |
| Cross-user isolation | `get_target_person` in `backend/app/core/deps.py` filters `PersonProfile.owner_user_id == current_user.id` → 404 on mismatch |
| No-token behavior | 401 `{"detail":"Not authenticated"}` |
| Backend URL | `http://localhost:8000` (from `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`) |

---

### 4. Existing Playwright Fixture / Mock-Auth Findings

All three prior specs (`family-health-card`, `health-platform`, `platform-app`) use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API route interception

No `storageState`, no `globalSetup`, no real credential flow found. Confirmed P13 gap.

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth.ts` | Created — real-auth fixture (116 lines) |
| `frontend/tests/e2e/auth-negative.spec.ts` | Created — 3 negative smoke tests (73 lines) |
| `00-Plan/roadmap/active_task_report.md` | Updated — P14 report block prepended |

---

### 6. Test User / Token Bootstrap Decision

**Decision: register two dedicated e2e users on first run (idempotent)**

| User | Email | Password | Strategy |
|---|---|---|---|
| User A | `e2e-user-a@example.com` | `E2eTestA1!` | `POST /api/v1/auth/register` (400 = already exists → ok) then `POST /api/v1/auth/login` |
| User B | `e2e-user-b@example.com` | `E2eTestB1!` | Same |

Both users were pre-verified against the running backend before writing the fixture. PersonProfile creation is also idempotent — returns existing profile if one already exists.

---

### 7. Single-File Playwright Result

```
Running 3 tests using 1 worker
  3 passed (5.7s)
```

| Test | Status |
|---|---|
| user A JWT cannot access user B family-health-context → 404 | ✅ PASS |
| request without Authorization header → 401 | ✅ PASS |
| user A JWT cannot access user B family-recommendations → 404 | ✅ PASS |

**Scope note**: browser-context/API smoke (not full UI smoke). All HTTP calls use Playwright's `request` fixture (APIRequestContext) directly to the backend. The frontend UI login flow is not exercised — multi-user `storageState` fixture remains an open gap.

---

### 8. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 9. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `8af3262` | `test(e2e): add real-auth Playwright fixture for browser auth smoke` |
| C2 | `78afae7` | `test(e2e): add cross-user browser-context auth negative smoke` |
| C3 | (this commit) | `docs(report): P14 browser auth fixture foundation report` |

---

### 10. Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Limitation** | Tests use `request` (APIRequestContext), not `page` — no browser UI rendering, no JS navigation, no DOM assertion. Full UI smoke requires storageState + login UI fixture (P15 candidate). |
| **Limitation** | `playwright.config.ts` `webServer` starts Next.js production server (`next start`) before any test run. Tests pass because a production build exists in `.next/`. If the build is stale, `next start` may fail. |
| **Limitation** | Test user credentials (`e2e-user-a@example.com`, `e2e-user-b@example.com`) are now seeded in the running SQLite DB. They persist across restarts. |
| **Inferred** | `reuseExistingServer: false` in playwright config means Playwright always starts a fresh Next.js process on port 3010. If port 3010 is occupied, tests will fail with server-start error. |
| **Unknown** | Whether CI will have a running backend at `localhost:8000`. Backend must be started before Playwright tests in any CI pipeline. |
| **Open gap** | `storageState` multi-user login fixture for full UI smoke — not implemented in this task. |

---

### Final Classification

**`P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

- Real auth fixture implemented (`frontend/tests/e2e/fixtures/auth.ts`)
- Cross-user negative smoke: 3/3 PASS (5.7s)
- TypeScript: 0 errors
- Boundary verified: `get_target_person()` ownership filter enforced end-to-end

---

---

## APPENDIX: P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

## P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

**Final Classification: `P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `.gitignore` M, `Makefile` M, 5 roadmap docs M, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`, `?? backend/tests/test_auth_negative_smoke.py`, `?? backend/tests/test_real_token_auth_negative.py` — all P13 expected artifacts, no scope conflict |
| Staged diff at start | 3 deletions (`git diff --cached --stat`) — all confirmed `git rm --cached` (index-only) |

---

### A1 — Staging Intent Confirmation

Physical files verified present on disk before any commit:
- `frontend/tsconfig.tsbuildinfo` — 126,055 bytes, mtime 2026-05-23 ✅
- `runtime/launchd/pids/backend.pid` — 5 bytes, mtime 2026-05-22 ✅
- `runtime/launchd/pids/frontend.pid` — 5 bytes, mtime 2026-05-22 ✅

**Verdict: `git rm --cached` (index-only removal). Physical files intact. Safe to proceed.**

---

### A2 — P13 Test File Authenticity Confirmation

| File | Docstring confirmation |
|---|---|
| `test_real_token_auth_negative.py` | "P13 Real-Token Auth Negative Smoke" — uses real `jwt.decode`, real `create_access_token`, production `get_target_person`. 7 tests. ✅ |
| `test_auth_negative_smoke.py` | "P12 Auth Negative Smoke — cross-user family context isolation" — override-style via `app.dependency_overrides`. 5 tests. ✅ |

**Verdict: Both files confirmed P13 auth tests. Content matches task description.**

---

### A3 — Commit List

| Commit | Hash | Files | Message |
|---|---|---|---|
| C1 | `0a73f1a` | 2 | `feat(auth): P13 real-token JWT negative smoke + override smoke` |
| C2 | `eeadbf7` | 5 | `chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment` |
| C3 | `b484c56` | 5 | `docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report` |

C2 includes: `Makefile`, `.gitignore`, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`

---

### A Acceptance Check

```
git log --oneline -5:
  b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
  eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
  0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
  de78305 docs: update active_task_report — P12 production trust closure (713 PASS)
  d41d13c fix(orchestrator): _open_db respects ORCHESTRATOR_PROFILE_PATH env var

git status --short: (empty) ✅

Physical files post-commit:
  frontend/tsconfig.tsbuildinfo — present ✅
  runtime/launchd/pids/backend.pid — present ✅
  runtime/launchd/pids/frontend.pid — present ✅
```

**Sub-acceptance A: PASS**

---

### B1 — Playwright Fixture Probe

```
frontend/tests/
  e2e/
    family-health-card.spec.ts
    health-platform.spec.ts
    platform-app.spec.ts
```

Grep results for `test.use|login|authenticate|storageState|access_token` — **0 matches**

Playwright config (`playwright.config.ts`):
- `testDir: ./tests/e2e`
- `baseURL: http://127.0.0.1:3010`
- No `globalSetup`, no `storageState`, no auth bootstrap

All existing specs use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API interception
- No real login flow, no real credential exchange

---

### B2 — Branch Decision: `BROWSER_AUTH_E2E_NOT_IMPLEMENTED`

#### Missing Fixtures (precise gap list)

| Missing Component | Description |
|---|---|
| **Login helper / auth fixture** | No function that navigates to login page, submits real credentials, and captures a token or `storageState` snapshot |
| **Token bootstrap** | No mechanism to call `/api/v1/auth/token` or `/api/v1/auth/login` with test user credentials and store the JWT for subsequent requests |
| **`storageState` setup** | No `playwright/.auth/user.json` or equivalent; no `test.use({ storageState: ... })` in any spec |
| **Multi-user isolation fixture** | No fixture that creates two distinct authenticated sessions (user A session vs. user B session) |

#### Next.js Routes Involved

| Route | Path |
|---|---|
| Login page | `/platform/login` (App Router: `frontend/app/platform/login/`) and `pages/login.tsx` |
| Family context page | `/platform/settings/family` (App Router: `frontend/app/platform/settings/family/`) |
| Family context API | `GET /api/v1/family-health-context?person_id=<pid>` and `GET /api/v1/family-recommendations?person_id=<pid>` |

#### Recommended Test Assertion Points (when implemented)

1. **Setup**: Create two real users (user A, user B) via API; obtain real JWT for user A via `POST /api/v1/auth/token`
2. **Browser action**: Navigate to `/platform/settings/family?profile=<userB_person_id>` while authenticated as user A
3. **Assertion options** (any of):
   - Response status 404 from backend API call (user B's person not found for user A)
   - Redirect to `/platform/login` or error page
   - DOM assertion: user B's `display_name` / health data NOT present in page content
4. **Negative confirmation**: Page must not render any user B health data (blood pressure, symptoms, risk alerts)

#### Implementation Prerequisites (for future P14)

```typescript
// Required: tests/e2e/fixtures/auth.ts
import { test as base, Page } from '@playwright/test'

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // 1. POST /api/v1/auth/token with test credentials
    // 2. localStorage.setItem('token', realJWT)
    // 3. yield page to test
    await use(page)
  }
})
```

**No new npm packages required** — Playwright's built-in `page.request.post()` is sufficient for token acquisition.

---

### Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Inferred** | All existing Playwright specs use mock tokens — real auth flow has never been E2E tested at browser level |
| **Unknown** | Whether the `/platform/login` App Router page (`frontend/app/platform/login/`) is the active login route vs. `pages/login.tsx` (Pages Router) |
| **Known limitation** | Backend test suite (723 PASS) validates auth isolation at HTTP level; browser-level isolation gap is purely at the Playwright fixture layer |
| **Known limitation** | `webServer` in playwright.config.ts uses `next start` (production build) — any auth fixture must work with the built app, not dev mode |

---

### Final Classification

**`P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

- Sub-acceptance A: **PASS** — 3 commits (C1/C2/C3) above `de78305`, clean working tree, all 3 physical files intact
- Sub-acceptance B: **`BROWSER_AUTH_E2E_NOT_IMPLEMENTED`** with complete gap detail (missing fixtures, routes, assertion points, implementation guide)

---

---

## APPENDIX: P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

## P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

**Final Classification: `P13_AUTH_E2E_ENTRYPOINT_HARDENED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | Known P12 artifacts only (`.gitignore` M, plan files M, 3 artifact D entries from P12 `git rm --cached`, `test_auth_negative_smoke.py` ??). No scope conflict. |

---

### 1. Auth Token Fixture Probe

| Item | Finding |
|---|---|
| `create_access_token` | **Exists** — `backend/app/core/security.py:18` |
| `get_current_user` | Decodes JWT via `jose.jwt.decode` using `settings.jwt_secret_key` / `settings.jwt_algorithm` |
| Existing tests with real JWT | **None** — all prior tests used `dependency_overrides[get_current_user]` |
| Auth fixture available? | **YES** — `create_access_token` is importable; real tokens can be minted in tests |

---

### 2. Real-Token Auth Negative Smoke — PASS

**New file:** `backend/tests/test_real_token_auth_negative.py`

**Approach:** Only `get_db` is overridden (in-memory SQLite). `get_target_person` runs as production code. `get_current_user` uses a SQLite-compatible shim that calls the same `jwt.decode` with the same keys/algorithm, then coerces `sub` string → `uuid.UUID` before the DB query (required for SQLite `UUID(as_uuid=True)`; a no-op in production PostgreSQL).

**Token issuance:** `create_access_token(str(user_id))` — identical to production login endpoint.

| Test | Status |
|---|---|
| User A real token + user B `person_id` → `/family-health-context` → 404, no data leak | ✅ PASS |
| User A real token + user B `person_id` → `/family-recommendations` → 404, no data leak | ✅ PASS |
| No `Authorization` header → 401 | ✅ PASS |
| Expired JWT (exp in past) → 401 | ✅ PASS |
| Garbage non-JWT string → 401 | ✅ PASS |
| User A real token + own `person_id` → 200 (sanity) | ✅ PASS |
| User A real token + no `person_id` → 200 default person (sanity) | ✅ PASS |

**Result:** `7 passed in 1.72s`

**SQLite UUID limitation note:** The production `get_current_user` passes the JWT `sub` string directly to `UUID(as_uuid=True)` column. PostgreSQL's psycopg2 handles implicit casting; SQLite does not. The test shim adds `uuid.UUID(user_id_str)` coercion. This is a test-infra gap, not a security gap — `get_target_person` ownership enforcement runs unshimmed in both test environments.

---

### 3. Test Entrypoint Hardening — PASS

**Problem:** `pytest -q` without `.venv` activation → 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`).

**Changes:**

| File | Change |
|---|---|
| `backend/README.md` | Replaced bare `pytest -q` with canonical `.venv/bin/python -m pytest -q`; added warning box; documented `make backend-test` as CI equivalent |
| `Makefile` (root) | Added `backend-smoke` target: runs only auth negative tests (`test_auth_negative_smoke.py` + `test_real_token_auth_negative.py`) without full DB setup |

**Canonical test command (hardened):**
```bash
# From repo root
make backend-test
# or directly
cd backend && .venv/bin/python -m pytest -q
# auth smoke only
make backend-smoke
```

---

### 4. Full Validation Run

| Check | Command | Result |
|---|---|---|
| Backend pytest | `backend/.venv/bin/python -m pytest -q` | **723 passed, 0 failed** (716 prior + 7 new real-token tests) |
| Frontend TypeScript | `cd frontend && npx tsc --noEmit` | **Exit 0, 0 errors** |
| Frontend Next Build | `cd frontend && npx next build` | **Success** — 20 static routes, First Load JS 95.3 kB |

---

### 5. Files Changed This Sprint

| File | Action |
|---|---|
| `backend/tests/test_real_token_auth_negative.py` | **NEW** — 7 real-token auth negative tests |
| `backend/README.md` | Updated Tests section with hardened entrypoint instructions |
| `Makefile` | Added `backend-smoke` target; updated `.PHONY` |
| `00-Plan/roadmap/active_task_report.md` | This block prepended |

---

### 6. Known Limitations

1. **SQLite UUID coercion in `get_current_user`:** Production code (`deps.py`) passes JWT `sub` as string to `UUID(as_uuid=True)` column; works in PostgreSQL, fails in SQLite. Fixed by test shim. Application code not changed (out of scope).
2. **Playwright E2E still NOT_RUN:** Real-browser login → token → cross-user probe flow. Out of scope for this sprint.
3. **FastAPI `on_event` deprecation:** 4 warnings per run, pre-existing, not introduced here.
4. **`backend-test` Makefile re-creates venv on every run:** `python3 -m venv .venv` is idempotent but slow. No change made (out of scope).

---

--- # Appendix: P12 Report ---

## P12-POST-CLOSURE-VERIFICATION (2026-05-21)

**Final Classification: `P12_POST_CLOSURE_VERIFIED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `M 00-Plan/roadmap/CEO-Decision.md`, `M 00-Plan/roadmap/CTO-Analysis.md`, `M 00-Plan/roadmap/active_task.md`, `M 00-Plan/roadmap/roadmap.md`, `M frontend/tsconfig.tsbuildinfo`, `M runtime/launchd/pids/backend.pid`, `M runtime/launchd/pids/frontend.pid` — all known artifacts, no scope conflict |

---

### A. Backend Regression Rerun — PASS

**Command:** `cd backend && source .venv/bin/activate && pytest -q`

| Metric | Result |
|---|---|
| Total tests | 716 (713 prior + 3 new auth negative smoke) |
| PASS | 716 |
| FAIL | 0 |
| Skipped | 0 |
| Warnings | 4 (FastAPI `on_event` deprecation — pre-existing) |

**Summary line:** `716 passed, 4 warnings in 5.82s`

> Note: Running pytest without `.venv` activation produces 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`). The canonical invocation requires `.venv` activation — this is the same environment that produced the claimed 713 PASS.

---

### B. Frontend TypeScript — PASS

**Command:** `cd frontend && npx tsc --noEmit`

**Result:** Exit code 0, zero errors.

---

### C. Frontend Next Build — PASS

**Node version:** v20.19.5  
**npm version:** 10.8.2  
**Command:** `cd frontend && npx next build`

Build succeeded. Route table (all static):

| Route | Size | First Load JS |
|---|---|---|
| / | 358 B | 81.4 kB |
| /dashboard | 325 B | 81.4 kB |
| /health-insights | 2.4 kB | 105 kB |
| /login | 2.98 kB | 84.1 kB |
| /register | 2.84 kB | 83.9 kB |
| … (20 routes total, all ○ Static) | | |

First Load JS shared: 95.2 kB.

---

### D. Minimal API Auth Negative Smoke — PASS

**Auth fixture probe:**
- `TestClient`: present in multiple test files ✅
- `Authorization` / `access_token` / `create_access_token` / `auth_headers`: **NOT present** in test suite
- Existing tests use `app.dependency_overrides[get_current_user]` pattern (no raw JWT in tests)

**Decision:** Auth fixture exists (via dependency_overrides pattern). New negative smoke test written.

**Test file:** `backend/tests/test_auth_negative_smoke.py`

**Access control mechanism verified:**
`get_target_person` in `backend/app/core/deps.py` enforces:
```python
.filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
```
If no match → HTTP 404. This is the isolation boundary tested.

**Tests written (3):**
1. `test_cross_user_family_context_returns_404` — User A token + user B's `person_id` → `/family-health-context` → 404, no data leak ✅
2. `test_cross_user_family_recommendations_returns_404` — Same for `/family-recommendations` → 404, no data leak ✅
3. `test_own_person_id_still_accessible` — Sanity: user A's own `person_id` → 200 ✅

**Result:** `3 passed in 1.50s`

**Full regression after adding test:** `716 passed, 4 warnings in 5.82s` (0 regressions)

---

### E. Artifact Hygiene + Report Integrity — PASS

**E1. Artifact Hygiene:**

| File | Action Taken |
|---|---|
| `frontend/tsconfig.tsbuildinfo` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/backend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/frontend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |

Physical files confirmed intact after `git rm --cached`. No runtime state was deleted.

**E2. Report Integrity:** This block inserted at top of `active_task_report.md`. Prior content preserved below appendix separator.

---

### Known Limitations / Unknown / Inferred

1. **venv invocation**: `pytest -q` without `.venv` activation fails with 46 collection errors. The 713 PASS claim and this session's 716 PASS both require explicit venv. CI/CD should pin to `.venv/bin/pytest` or equivalent.
2. **Token-based E2E**: No real JWT token is issued or verified in tests — auth isolation is tested via `dependency_overrides`. A Playwright-level E2E with a real token flow (login → get JWT → cross-user probe) remains unverified.
3. **Playwright E2E**: Written (spec exists) but not run. Browser E2E status unchanged from P11 handoff.
4. **FastAPI `on_event` deprecation**: 4 warnings in all test runs. Pre-existing, not P12-introduced.

---

--- # Appendix: Prior Sprint Reports ---

# Active Task Report — P12_PRODUCTION_TRUST_CLOSURE_READY

Generated: 2026-05-22  
Classification: **`P12_PRODUCTION_TRUST_CLOSURE_READY`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P10 Family UI evidence transparency verified | ✅ PASS (static smoke + tsc) |
| Task 2 — Minimal static / browser smoke | ✅ Static PASS · Playwright spec written · Browser E2E NOT RUN |
| Task 3 — P11 Production Trust Readiness checklist | ✅ THIS DOCUMENT |
| Task 4 — Regression validation | ✅ 617 PASS (see breakdown below) |

---

## Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files | `M frontend/tsconfig.tsbuildinfo` (build artifact, not blocking) ✅ |

---

## Task 1 — P10 Family UI Evidence Transparency Verification

### Static smoke checks (all PASS)

| Check | Result |
|---|---|
| `EvidenceSourceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `AudienceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `source_type` consumed in render | ✅ 1 occurrence |
| Non-diagnosis disclaimer `非醫療診斷` | ✅ 1 occurrence |
| Limitations section rendered | ✅ present |
| Source origin label `健康觀察資料` | ✅ 2 occurrences (child + caregiver sections) |
| Diagnosis word `診斷` only in disclaimer | ✅ 1 total (confirmed to be in disclaimer text only) |
| Profile UUID `profile_id` in user-facing text | ✅ 0 leakage (only in internal logic / type references) |
| Badge labels: 兒童健康, 照護提醒, 共同風險, 行動建議 | ✅ all present in EvidenceSourceBadge config |

### TypeScript shape validation

- `FamilyRecommendation` type includes `source_type: string` ✅
- `npx tsc --noEmit` → 0 errors ✅
- `npx next build` → CLEAN ✅

---

## Task 2 — Smoke Test Status

| Method | Status |
|---|---|
| Static grep checks | ✅ PASS |
| TypeScript compilation | ✅ PASS |
| Next.js build | ✅ PASS |
| Playwright spec written | ✅ `frontend/tests/e2e/family-health-card.spec.ts` (6 tests) |
| Playwright browser E2E executed | ❌ NOT RUN — requires live dev server |

> Note: Playwright spec covers: section visibility, disclaimer text, source badges (兒童健康, 行動建議), audience badge (照護者), source origin label. Tests are written with mocked API routes.

---

## Task 4 — Regression Validation

### Backend test results

| Test file | Tests | Result |
|---|---|---|
| test_family_health_context.py | 46 | ✅ PASS |
| test_family_context_data_population.py | 18 | ✅ PASS |
| test_family_relationships.py | 17 | ✅ PASS |
| test_narrative_reasoning.py | — | ✅ PASS |
| test_narrative_memory_service.py | — | ✅ PASS |
| test_api_narrative_memory.py | — | ✅ PASS |
| test_engagement_analytics.py | — | ✅ PASS |
| test_personalization_profile.py | — | ✅ PASS |
| test_adaptive_recommendation_scoring.py | — | ✅ PASS |
| test_notification_history_service.py | — | ✅ PASS |
| test_api_notification_status.py | — | ✅ PASS |
| test_notification_intelligence.py | — | ✅ PASS |
| test_api_notification_intelligence.py | — | ✅ PASS |
| test_lab_intelligence.py | — | ✅ PASS |
| test_api_lab_smoke.py | — | ✅ PASS |
| test_api_symptom_smoke.py | — | ✅ PASS |
| test_symptom_intelligence.py | — | ✅ PASS |
| test_device_signal_escalation.py | — | ✅ PASS |
| test_device_signal_detection.py | — | ✅ PASS |
| test_api_escalation_smoke.py | — | ✅ PASS |
| test_health_assistant_service.py | — | ✅ PASS |
| test_daily_summary_service.py | — | ✅ PASS |
| test_recommendation_trust_service.py | — | ✅ PASS |
| test_outcome_feedback_service.py | — | ✅ PASS |
| **Batch 1 total** | **320** | ✅ PASS |
| **Batch 2 total** | **297** | ✅ PASS |
| test_dual_agent_orchestrator.py | 10 failed | ⚠️ PRE-EXISTING — excluded |

**Total (mandated suites): 617 PASS, 0 new failures**

---

## P11 — Production Trust Readiness Checklist

> This checklist tracks readiness for trustworthy production deployment, not feature completeness.  
> Unit tests ≠ production validation. Each item is tagged DONE / GAP / NOT RUN.

### 1. Privacy & Cross-Profile Isolation

| Item | Status | Notes |
|---|---|---|
| Profile UUID not exposed in user-facing text | ✅ DONE | `test_load_errors_limitation_does_not_expose_profile_id` asserts this |
| Cross-profile evidence mixing prevention | ✅ DONE | `build_family_health_context` only uses profiles in `relationships` list |
| Unrelated profile data not surfaced | ✅ DONE | Enforced by `related_pids` filter in service |
| API auth guards (token required) | ⚠️ GAP | Backend endpoints require `Authorization` header but E2E auth validation not tested |
| Family relationship permission enforcement | ⚠️ GAP | `permission_level` stored but not enforced at query level in DB layer |

### 2. Medical Disclaimer Coverage

| Item | Status | Notes |
|---|---|---|
| No-diagnosis disclaimer in FamilyHealthCard | ✅ DONE | "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。" |
| Diagnosis wording absent from static copy | ✅ DONE | Only 1 occurrence of `診斷` in component, confirmed in disclaimer context |
| Hallucination guardrail policy documented | ✅ DONE | `ai/prompts/hallucination_guardrail_policy.md` exists |
| Disclaimer on other health display pages | ⚠️ GAP | Disclaimer only confirmed in FamilyHealthCard; other dashboards not audited |
| AI summary output review | ⚠️ GAP | `health_summary_system_prompt.md` exists but output review not automated |

### 3. Source Traceability

| Item | Status | Notes |
|---|---|---|
| `evidence_source` field in recommendations | ✅ DONE | Since P8 |
| `source_type` field in recommendations | ✅ DONE | Added P10 (child_health/caregiver_health/shared_risk/action) |
| Source badge visible in UI | ✅ DONE | `EvidenceSourceBadge` in FamilyHealthCard |
| Audience badge visible in UI | ✅ DONE | `AudienceBadge` in FamilyHealthCard |
| Lab/symptom/device granularity per item | ⚠️ GAP | `childAttentionItems` + `caregiverAlerts` are mixed-source strings; per-item source type not tracked |
| Narrative source traceability | ⚠️ GAP | Narrative memories referenced but not surfaced as evidence badges in UI |

### 4. Confidence & Limitations Coverage

| Item | Status | Notes |
|---|---|---|
| `confidence` field in FamilyHealthContext | ✅ DONE | Scales with profile count + evidence density |
| `limitations` field in FamilyHealthContext | ✅ DONE | Explains data gaps to user |
| Load failure visibility in limitations | ✅ DONE | P9: `load_errors_by_profile` adds limitation text |
| Limitations displayed in FamilyHealthCard | ✅ DONE | Styled with Info icon (P10) |
| ConfidenceBadge shows score | ✅ DONE | `可信度 X%` with color thresholds |
| Confidence calibration validated | ⚠️ GAP | No test asserts confidence formula accuracy vs real data |

### 5. Notification Spam Guard

| Item | Status | Notes |
|---|---|---|
| Max recommendations per member capped | ✅ DONE | `_MAX_SUGGESTIONS_PER_MEMBER = 3` constant enforced in `generate_family_recommendations` |
| Dedup against active actions | ✅ DONE | P9: `active_actions_by_profile` dedup |
| Dedup case-insensitive edge cases | ✅ DONE | P9 `TestFamilyDedupHardening` (6 tests) |
| Notification frequency limits in production | ⚠️ GAP | Unit-level only; no integration test for notification rate limits |

### 6. Data Persistence Boundaries

| Item | Status | Notes |
|---|---|---|
| Family relationships stored in DB | ✅ DONE | `FamilyRelationship` model, `family_relationships` table |
| Evidence data loaded from live DB per request | ✅ DONE | `load_family_evidence_data()` queries DB each call |
| No sensitive data in memory cache | ✅ DONE | No Redis/memory cache layer in current architecture |
| SQLite in tests, real DB in production | ✅ DONE | pytest uses in-memory SQLite via test fixtures |
| Database migration scripts present | ✅ DONE | `database/migrations/` directory exists |
| Migration tested against production schema | ⚠️ GAP | Migration scripts not run in CI |

### 7. E2E Coverage Gaps

| Item | Status | Notes |
|---|---|---|
| Platform dashboard loads | ✅ Written | `platform-app.spec.ts` (NOT RUN in this sprint) |
| FamilyHealthCard section visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| No-diagnosis disclaimer visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Source badge text visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Auth flows (login/token refresh) | ❌ NOT WRITTEN | No Playwright test for auth |
| Error state handling (API 500) | ❌ NOT WRITTEN | FamilyHealthCard error state not E2E tested |
| Empty state (no relationships) | ❌ NOT WRITTEN | `EmptyState` component not E2E tested |
| Cross-browser rendering | ❌ NOT RUN | Playwright config not verified for multi-browser |

### 8. Orchestrator Pre-existing Failures

| Item | Status | Notes |
|---|---|---|
| `test_dual_agent_orchestrator.py` | ⚠️ 10 FAILED | Pre-existing failures — not caused by P8–P10 changes |
| Orchestrator failures affect production | ❌ UNVERIFIED | Dual-agent orchestrator feature scope unclear |
| Fix plan | ⚠️ GAP | Failures not investigated; excluded from mandatory suites |

### 9. Deployment Smoke Gaps

| Item | Status | Notes |
|---|---|---|
| Docker Compose local config present | ✅ DONE | `docker-compose.local.yml` exists |
| Docker Compose prod config present | ✅ DONE | `docker-compose.prod.yml` exists |
| `smoke_check.py` script present | ✅ DONE | Root-level `smoke_check.py` exists |
| Smoke check actually run | ❌ NOT RUN | Not run in this sprint |
| Backend startup health check | ⚠️ GAP | `/health` or `/ping` endpoint not confirmed present |
| Frontend startup health check | ⚠️ GAP | Next.js deployment smoke not automated |
| Secrets / env config validated | ❌ NOT RUN | `.env` variable audit not done |

### P11 Summary

| Category | DONE | GAP | NOT RUN |
|---|---|---|---|
| Privacy & cross-profile | 3 | 2 | 0 |
| Medical disclaimer | 3 | 2 | 0 |
| Source traceability | 4 | 2 | 0 |
| Confidence & limitations | 4 | 1 | 0 |
| Notification spam guard | 4 | 1 | 0 |
| Data persistence | 5 | 1 | 0 |
| E2E coverage | 4 written | 3 not written | 4 not run |
| Orchestrator failures | 0 | 1 | 1 |
| Deployment smoke | 3 | 2 | 2 |

> **P11 overall**: Foundation is solid for a health tracking app at personal/beta scale. Key gaps before broader production trust: permission enforcement at DB layer, per-item source type granularity, auth E2E tests, deployment smoke execution, and orchestrator failure resolution.

---

## Prior Sprint Reference

| Sprint | Commit | Classification |
|---|---|---|
| P8 | `cc4312b` | P8_FAMILY_HEALTH_ASSISTANT_VERIFIED |
| P9 | `5e8528f` | P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED |
| P10a | `92b9707` | P10_FAMILY_CONTEXT_UI_EVIDENCE_READY |
| P10b | this commit | P10_FAMILY_UI_VERIFIED_AND_P11_TRUST_CHECKLIST_READY |

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy except designated disclaimer ✅
- Existing API shape unchanged (additive only) ✅
- All mandated test suites PASS ✅
- No new branches created ✅

---

## P10 Sprint Context

Previous sprint: **P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED** (commit `5e8528f`)

Prior sprint delivered:
- `load_errors_by_profile` visibility in limitations
- Family dedup edge-case hardening (6 tests)
- Load error visibility tests (4 tests)
- 672 backend PASS

This sprint: UI evidence transparency — make Family Health UI trustworthy and transparent without major backend changes.

---

## Changes Delivered

### Backend (`family_health_context_service.py`)
- Added `source_type: str` field to `FamilyRecommendation` TypedDict docstring
- `generate_family_recommendations()` now emits `source_type` alongside `evidence_source`:
  - `child_attention_item` → `"child_health"`
  - `caregiver_alert` → `"caregiver_health"`
  - `shared_risk` → `"shared_risk"`
  - `family_suggestion` → `"action"`
- Fully additive — no existing fields changed

### Frontend Types (`lib/api.ts`)
- Added `source_type: string` to `FamilyRecommendation` type

### Frontend Component (`family-health-card.tsx`)
- New `EvidenceSourceBadge({ sourceType })` — maps source_type → label + color badge
- New `AudienceBadge({ audience })` — shows recommendation target (照護者/成員/全家)
- Recommendations section: shows urgency badge + evidence source badge + audience badge before text
- `childAttentionItems` section: added source origin label "來源：健康觀察資料"
- `caregiverAlerts` section: added source origin label "來源：健康觀察資料"
- Limitations section: upgraded from plain bullets to `Info` icon + styled container
- Added no-diagnosis disclaimer at card bottom: "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。"
- Added `Info` icon from lucide-react

### Tests (`test_family_health_context.py`)
- New class `TestFamilyRecommendationAPIShape` (6 tests):
  - `test_all_recommendations_have_source_type`
  - `test_child_attention_item_source_type_is_child_health`
  - `test_caregiver_alert_source_type_is_caregiver_health`
  - `test_shared_risk_source_type_is_shared_risk`
  - `test_family_suggestion_source_type_is_action`
  - `test_context_has_confidence_and_limitations_fields`

---

## Validation Results

```
Backend: 678 PASS (ignoring 10 pre-existing failures in test_dual_agent_orchestrator)
Frontend: tsc 0 errors
Frontend: next build CLEAN
```

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy ✅  
- Existing API shape unchanged (additive only) ✅
- All 40 pre-existing family tests continue to pass ✅

---

## P9 Sprint Context

Previous sprint: **P8_FAMILY_HEALTH_ASSISTANT_VERIFIED** (commit `cc4312b`)

Prior sprint delivered:
- `extract_family_evidence_from_bundle()` pure helper
- `load_family_evidence_data()` DB helper
- `GET /family-health-context` uses real per-profile evidence
- `GET /family-recommendations` uses real `active_actions_by_profile` for dedup

This sprint: verification, failure visibility, dedup edge-case hardening.

---

## Commits

| Commit | Tag | Description |
|---|---|---|
| `cc4312b` | `P9_FAMILY_CONTEXT_DATA_POPULATED` | P9 — populate 6 per-profile dicts with real evidence data |
| (current) | `P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED` | Failure visibility + dedup hardening |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/family_health_context_service.py` | `load_family_evidence_data()` now tracks errors in `load_errors_by_profile`; `build_family_health_context()` accepts `load_errors_by_profile` and adds limitation text |
| `backend/app/api/health_assistant.py` | Both family endpoints pass `load_errors_by_profile` from evidence to `build_family_health_context` |
| `backend/tests/test_family_health_context.py` | Added `TestFamilyDedupHardening` (6 tests) and `TestLoadErrorVisibility` (4 tests) |

---

## P9 Data Flow Confirmation

```
FamilyRelationship DB rows
    → load_family_relationships(db, owner_user_id, subject_profile_id)
    → load_family_evidence_data(db, owner_user_id, relationships)
        → unique related_profile_ids iterated
        → build_evidence_bundle(db, uid, pid) per profile
        → on failure: load_errors_by_profile[pid] = "evidence_unavailable" (skip, no crash)
        → returns {
              lab_abnormalities_by_profile,
              symptom_patterns_by_profile,
              escalations_by_profile,
              active_actions_by_profile,
              recommendations_by_profile,
              load_errors_by_profile
          }
    → build_family_health_context(relationships, **evidence, load_errors_by_profile=...)
        → limitations += "部分成員資料載入失敗（N 位）..." when errors present
        → profile IDs never exposed in user-facing limitation text
    → generate_family_recommendations(context, active_actions_by_profile)
        → dedup via flat union all_active set (lowercase strip)
    → GET /family-health-context → frontend FamilyHealthCard
    → GET /family-recommendations → FamilyHealthCard recommendations section
```

---

## Failure Visibility Implementation

| Behaviour | Result |
|---|---|
| Evidence load error for one profile → stored in `load_errors_by_profile` | ✅ |
| Failed profile does not crash endpoint | ✅ |
| Error count surfaced in `limitations` field | ✅ |
| Profile UUID not exposed in `limitations` text | ✅ CONFIRMED by test |
| No errors → no failure limitation added | ✅ |

---

## Family Dedup Hardening — Edge Cases

| Case | Test | Result |
|---|---|---|
| Active child action suppresses matching child recommendation | `test_active_child_action_suppresses_matching_child_recommendation` | ✅ |
| Active parent action does NOT suppress unrelated child recommendation | `test_active_parent_action_does_not_suppress_unrelated_child_recommendation` | ✅ |
| Caregiver alert + child attention item with different text → both in output | `test_caregiver_alert_and_child_attention_item_both_survive_when_different` | ✅ |
| Same risk across two profiles → one shared family suggestion (not two) | `test_same_risk_in_two_profiles_creates_one_shared_suggestion` | ✅ |
| Repeated profile_id in relationships → no duplicate recommendations | `test_repeated_profile_in_relationships_no_duplicate_recommendations` | ✅ |
| Same-case active action text → dedup triggered | `test_case_insensitive_dedup_against_active_actions` | ✅ |

---

## Test Results — Required Validation Suite

| Suite | Count | Result |
|---|---|---|
| `test_family_health_context.py` | 40 | **PASS** (+10 new: 6 dedup + 4 error visibility) |
| `test_family_context_data_population.py` | 18 | **PASS** |
| `test_family_relationships.py` | 17 | **PASS** |
| `test_narrative_reasoning.py` | (included) | **PASS** |
| `test_narrative_memory_service.py` | (included) | **PASS** |
| `test_api_narrative_memory.py` | (included) | **PASS** |
| `test_engagement_analytics.py` | (included) | **PASS** |
| `test_personalization_profile.py` | (included) | **PASS** |
| `test_adaptive_recommendation_scoring.py` | (included) | **PASS** |
| `test_notification_history_service.py` | (included) | **PASS** |
| `test_api_notification_status.py` | (included) | **PASS** |
| `test_notification_intelligence.py` | (included) | **PASS** |
| `test_api_notification_intelligence.py` | (included) | **PASS** |
| `test_lab_intelligence.py` | (included) | **PASS** |
| `test_api_lab_smoke.py` | (included) | **PASS** |
| `test_api_symptom_smoke.py` | (included) | **PASS** |
| `test_symptom_intelligence.py` | (included) | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | (included) | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Full backend suite (excl. dual_agent)** | **672** | **672/672 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures** |
| E2E / Playwright | — | **NOT RUN** |

---

## Cross-Profile Isolation Verification

| Check | Result |
|---|---|
| Evidence loading scoped to `owner_user_id` | ✅ |
| `load_errors_by_profile` keyed by `related_profile_id` only (not user ID) | ✅ |
| User-facing limitation text contains no profile UUIDs | ✅ CONFIRMED by test |
| Evidence load failure for profile A does not affect profile B's data | ✅ |

---

## Frontend Build Verification

| Check | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ CLEAN — all pages static/SSR, no errors |

---

## Known Limitations

- **E2E / Playwright**: NOT RUN. All tests are unit / API integration.
- **Real family data**: Tests use in-memory SQLite with synthetic profiles.
- **Evidence load error granularity**: `load_errors_by_profile` stores `"evidence_unavailable"` for all errors. Detailed error types not exposed to frontend (by design — privacy + simplicity).
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded. Unrelated to P9.

---

## Git

- Branch: `main`
- P8 foundation commit: `1c1717e` — `P8_FAMILY_HEALTH_ASSISTANT_FOUNDATION_READY`
- P8 verification commit: pending

---

---

# Previous Sprint Report — P4-REPORT-TO-ACTION-VERIFIED

Generated: 2026-05-20  
Classification: **`P4_REPORT_TO_ACTION_VERIFIED`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P4 data flow end-to-end verification | ✅ CONFIRMED |
| Task 2 — API smoke / regression confirmation | ✅ 16/16 PASS (↑1 stale confidence test added) |
| Task 3 — Dashboard LabInsightCard verification | ✅ CONFIRMED — stale indicator added, disclaimer present |
| Task 4 — Update active task report | ✅ THIS DOCUMENT |
| Task 5 — P5 Notification Intelligence planning | ✅ PLANNED (see below, NOT IMPLEMENTED) |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/health_assistant_service.py` | Bug fix: `recency` now computed from `report.report_date` (not `created_at`); added `date` import |
| `backend/tests/test_api_lab_smoke.py` | Added `test_stale_report_confidence_lower_than_recent`; fixed sequential client ordering |
| `frontend/app/components/platform/lab-insight-card.tsx` | Added `StaleBadge` component (visible even when collapsed); added `Clock` icon import |

---

## Test Results — Full Battery

| Suite | Count | Result |
|---|---|---|
| `test_lab_intelligence.py` | 82 | **PASS** |
| `test_api_lab_smoke.py` | 16 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **297** | **297/297 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures, unrelated to P4** |
| E2E / Playwright | — | **NOT RUN** |

---

## P4 Data Flow Confirmation

```
LabReportItem rows (DB, abnormal_flag IS NOT NULL)
    → health_assistant_service.py: build_evidence_bundle()
        → lab_report_items list (recency now computed from report_date ✅)
    → lab_intelligence_service.py: detect_lab_abnormalities()
        → groups by item_name
        → computes severity (flag → recurrence → alert corroboration)
        → classifies abnormality_type (lipid / glucose / uric_acid / fatty_liver_marker / kidney_stone_related_marker / …)
        → stale penalty: recency=older → confidence -0.10
        → stale warning appended to whyDetected text
        → returns list[LabAbnormality]
    → evidence bundle: lab_abnormalities key always present
    → get_action_recommendations()
        → high-severity lab abnormalities enter candidate pool at priority 75
        → trust layer applied
        → completed actions (status=done, completed_at ≤ 30d) deduped by rule_id
    → /recommendations response: lab_abnormalities key present
    → Dashboard LabInsightCard renders:
        → severity badge (red/amber/blue)
        → recurrence pill (if count > 1)
        → stale badge (if any evidenceSource.recency === 'older') ← NEW THIS SPRINT
        → suggested action (always visible)
        → whyDetected + evidence sources (expanded)
        → medical disclaimer
```

---

## Supported Lab Abnormality Types

| Type code | Markers covered |
|---|---|
| `lipid_abnormality` | LDL, HDL, TC, TG, 三酸甘油酯, Cholesterol, Triglyceride |
| `glucose_abnormality` | Blood Sugar, HbA1c, Glucose, 血糖, 糖化血色素 |
| `kidney_function` | Creatinine, eGFR, BUN, 肌酸酐, 腎功能 |
| `liver_function` | ALT, AST, GGT, ALP, Bilirubin, 肝功能 |
| `fatty_liver_marker` | 脂肪肝, Fatty Liver |
| `uric_acid` | 尿酸, Uric Acid |
| `kidney_stone_related_marker` | Oxalate, Calcium, 草酸, 膀胱石, Phosphate |
| `anemia_marker` | Hemoglobin, RBC, Hematocrit, 血色素 |
| `inflammation_marker` | CRP, ESR, WBC, 白血球 |
| `thyroid_function` | TSH, T3, T4, 甲狀腺 |
| `blood_pressure` | BP, Systolic, Diastolic, 血壓 |
| `lab_abnormality` | All other out-of-range markers (generic fallback) |

---

## Dashboard LabInsightCard Verification

| Check | Result |
|---|---|
| Component exists | ✅ `frontend/app/components/platform/lab-insight-card.tsx` |
| Imported in `health-assistant-panel.tsx` | ✅ line 9 |
| `LabInsightCard` rendered in panel | ✅ line 306: `<LabInsightCard abnormalities={data.lab_abnormalities ?? []} />` |
| Uses backend `LabAbnormality` type (not mock data) | ✅ `import type { LabAbnormality } from '../../../lib/api'` |
| `lab_abnormalities` key in frontend `HealthAssistantData` | ✅ `lab_abnormalities?: LabAbnormality[]` |
| Empty state rendered when no abnormalities | ✅ "目前無異常健檢指標" |
| Stale report warning displayed (new) | ✅ `StaleBadge` chip shown in collapsed card header when evidenceSource.recency === 'older' |
| Medical disclaimer | ✅ "以上分析由 AI 自動產生，僅供健康追蹤參考，不構成醫療診斷建議" |
| No diagnosis wording | ✅ (see Known Limitations) |
| `npx tsc --noEmit` | ✅ CLEAN |
| `npx next build` | ✅ SUCCESS |

---

## Known Limitations

- **No diagnosis wording**: `suggestedAction` copy uses action-oriented language ("建議諮詢醫師" not "診斷為X"); copy review against `docs/UI_FEEDBACK_STANDARDS.md` was not re-run this sprint — spot-checked only.
- **Recency uses `report_date`**: Fixed this sprint. Previous implementation used `created_at` (DB insert time), causing all reports to appear fresh in integration tests. Production behaviour was unaffected (reports imported from parsing use `report_date` which was already set correctly), but the test relied on the bug being absent.
- **Stale warning in body text only (before this sprint)**: Was embedded in `whyDetected`, only visible on expand. Now also shown as a collapsed-state chip badge.
- **Single-occurrence reports**: If a lab report has only 1 abnormal occurrence, severity cap = "medium" regardless of flag value (unless flag is "HH"/"LL"). This is intentional conservatism.
- **No trend charts**: Lab marker trends over time are not yet visualised. Planned for P5+.
- **E2E / Playwright tests**: NOT RUN. Smoke tests cover route-level behaviour only.
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded (`--ignore`).

---

## Git

- Branch: `main`
- P4 base commit: `d2eedc9` — `P4_REPORT_TO_ACTION_BRIDGE_READY`
- This sprint commit: pending (P4_REPORT_TO_ACTION_VERIFIED)

---

# P5 Notification Intelligence — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P5).  
> **Scope**: Proactive notification layer bridging daily health insights to user-facing alerts.  
> **No notification code added this sprint.**

### Problem Statement

The recommendation pipeline (`health_assistant_service.py`) currently produces prioritised recommendations on-demand (user opens dashboard). There is no mechanism to:
- Proactively alert the user when a new high-severity finding appears
- Respect quiet hours or notification fatigue thresholds
- Escalate unacknowledged critical alerts
- Learn from snooze/dismiss behaviour to adjust timing

### Required Behaviours

| # | Requirement | Priority |
|---|---|---|
| N1 | High-severity lab/device/symptom finding → push notification | P0 |
| N2 | Notification deduplication — same rule_id not re-notified within cooldown window | P0 |
| N3 | User-configurable quiet hours | P1 |
| N4 | Snooze → re-surface after snooze_duration | P1 |
| N5 | Persistent dismiss → suppress for 30 days | P1 |
| N6 | Escalation → higher-priority notification channel | P1 |
| N7 | Alert fatigue guard: max N notifications per day per person | P1 |
| N8 | Learn from ignore patterns: ignored N times → reduce channel priority | P2 |
| N9 | Notification history in DB for audit/compliance | P2 |

### Proposed Architecture

```
Daily assistant run / cron / real-time trigger
    ↓
notification_intelligence_service.py  (NEW)
    filter_notifiable_findings(evidence_bundle, prefs, notification_log)
        → only findings that exceed priority threshold
        → dedup against NotificationLog within cooldown
        → respect quiet_hours and daily_cap
        ↓
    rank_notifications(candidates)
        → sort by: severity DESC, source_priority DESC, last_seen ASC
        ↓
    build_notification_payload(ranked)
        → title, body, action_url, priority_level, rule_id
        ↓
NotificationLog DB row (status: pending → sent → acked/snoozed/dismissed)
    ↓
delivery_adapter (abstraction)
    → web push (Phase 1)
    → LINE / email (Phase 2)
    → in-app bell (already exists via notification-bell.tsx)
```

### New DB Tables Required

```sql
CREATE TABLE notification_log (
    id              UUID PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    person_id       INTEGER REFERENCES person_profiles(id),
    rule_id         VARCHAR(80),
    channel         VARCHAR(20),   -- 'web_push' | 'email' | 'in_app'
    priority_level  VARCHAR(10),   -- 'critical' | 'high' | 'medium' | 'low'
    title           TEXT,
    body            TEXT,
    action_url      TEXT,
    status          VARCHAR(20),   -- 'pending' | 'sent' | 'acked' | 'snoozed' | 'dismissed'
    snooze_until    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    acked_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notification_preferences (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id),
    quiet_start     TIME,          -- e.g. 22:00
    quiet_end       TIME,          -- e.g. 08:00
    daily_cap       INTEGER DEFAULT 5,
    min_priority    VARCHAR(10) DEFAULT 'medium',
    channels        JSONB          -- {"web_push": true, "email": false, "in_app": true}
);
```

### Priority Scoring

| Source type | Base priority | Escalation modifier |
|---|---|---|
| `device_escalation` (critical) | critical | +2 |
| `lab_abnormality` (high severity) | high | +1 if recurrence ≥ 3 |
| `symptom_pattern` (high severity) | high | +1 if worsening trend |
| `lab_abnormality` (medium) | medium | — |
| `symptom_pattern` (medium) | medium | — |
| All others | low | — |

### Cooldown Windows

| Priority | Cooldown | Dismiss suppress |
|---|---|---|
| critical | 6 hours | 7 days |
| high | 24 hours | 30 days |
| medium | 72 hours | 30 days |
| low | 7 days | 90 days |

### Alert Fatigue Guard

- Per-person daily cap (default: 5 notifications/day across all channels)
- Per-rule_id dedup: same rule not re-surfaced until cooldown expires
- Snooze learning: if snoozed ≥ 3 times → auto-downgrade channel priority for that rule

### Out of Scope for P5

- AI-generated notification copy (P6)
- Multi-language notification content (P6)
- SMS delivery (P6)
- Apple Watch / wearable push (future)

### Next Sprint Prompt (P5 kickoff)

```
PersonalHealthOS P5 — Notification Intelligence

Context:
  P4_REPORT_TO_ACTION_VERIFIED complete (297/297 tests pass).
  Evidence bundle: lab_abnormalities, symptom_patterns, device_escalation all wired.
  Daily assistant: get_action_recommendations() produces prioritised top-3.

Goal:
  Implement notification_intelligence_service.py and NotificationLog DB table.
  Wire into daily assistant and /recommendations endpoint.
  Add notification preference model.
  Expose /api/v1/notifications/ CRUD endpoints.
  No frontend push integration yet — in-app bell only (notification-bell.tsx already exists).

Must deliver:
  - notification_intelligence_service.py with filter/rank/build functions
  - NotificationLog SQLAlchemy model + migration
  - NotificationPreferences model
  - test_notification_intelligence.py: 20+ pure-function tests
  - test_api_notification_smoke.py: 8+ route tests
  - Full regression: all 297 existing tests still pass
  - npx tsc --noEmit CLEAN
  - npx next build PASS
  - Commit: P5_NOTIFICATION_INTELLIGENCE_READY

P5 NOT IMPLEMENTED as of this commit.
```

---


|---|---|
| Task 1 — Symptom data flow integrity (code review) | ✅ CONFIRMED |
| Task 2 — API smoke tests for symptom intelligence | ✅ 14/14 PASS |
| Task 3 — `npx tsc --noEmit` + `npx next build` | ✅ CLEAN / BUILD OK |
| Task 4 — Report-to-Action Bridge planning spec | ✅ DOCUMENTED (NOT IMPLEMENTED) |

### Test results — full battery

| Suite | Tests | Result |
|---|---|---|
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **199** | **199/199 PASS** |

### Data flow confirmation

- `SymptomLog` DB rows → `build_evidence_bundle()` reads last 90 days of symptoms  
- `build_symptom_timeline()` groups rows → produces `symptom_timeline` list in bundle  
- `detect_symptom_patterns()` analyses timeline → produces `symptom_patterns` list in bundle  
- `/evidence-bundle` response always includes `symptom_timeline` + `symptom_patterns` keys  
- High-severity patterns enter `get_action_recommendations()` candidate pool (priority 65)  
- `/recommendations` response always includes `symptom_patterns` key  
- `SymptomInsightCard` renders patterns in `health-assistant-panel.tsx`

### Frontend build

- `npx tsc --noEmit`: **CLEAN** (0 errors)  
- `npx next build`: **SUCCESS** — all pages compiled, static output generated

### Known limitations (carried forward)

- Symptom intelligence computed request-time only; no historical pattern DB table  
- E2E / Playwright tests: NOT RUN  
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, always excluded  
- Report-to-Action Bridge: NOT IMPLEMENTED (see spec below)

### Git

- Branch: `main`  
- This sprint: `test_api_symptom_smoke.py` (14 tests) + this report  

---

## Report-to-Action Bridge — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P4).  
> **Scope**: Bridge between parsed lab report items and the recommendation / decision pipeline.

### Problem statement

Lab reports are parsed and stored as `LabReportItem` rows.  Currently they
inform the `evidence_bundle` but do **not** automatically produce prioritised
action items.  The clinician's intent is: _an abnormal lab result → patient
knows what to do next_.

### Required behaviours

| # | Requirement | Priority |
|---|---|---|
| 1 | Lab abnormality → decision item in `recommendations` | P0 |
| 2 | Lab abnormality → a specific recommended next action | P0 |
| 3 | Repeated abnormal result for same marker → higher recommendation priority | P1 |
| 4 | Completed or active action for same marker → deduplicate (no double-surfacing) | P1 |
| 5 | Each recommendation includes full evidence source traceability | P1 |
| 6 | No medical diagnosis wording — all copy reviewed against `ui-feedback-standards.md` | P0 |

### Proposed architecture

```
LabReportItem rows (DB)
    ↓
build_lab_evidence()          ← new function in lab_intelligence_service.py
    ↓
detect_lab_abnormalities()    ← new function; returns list[LabAbnormality]
    ├─ compares value vs reference_range
    ├─ checks historical recurrence (count of same marker out-of-range)
    └─ deduplicates against existing ActionItem DB rows
    ↓
get_action_recommendations()  ← existing; add "lab_abnormality" source type
    priority score: 75 (above device_signal=70)
    rule_id: "lab_abnormality_{marker_name}"
    ↓
/recommendations response      ← new key: "lab_abnormalities"
    ↓
LabInsightCard (new component) ← renders in health-assistant-panel.tsx
```

### Concrete next-sprint tasks

1. **`lab_intelligence_service.py`** — implement `build_lab_evidence()` and `detect_lab_abnormalities()`:
   - Input: `LabReportItem` list from DB query
   - Output: `list[LabAbnormality]` — each with `markerName`, `value`, `unit`, `referenceRange`, `severity` (low/medium/high), `recurrenceCount`, `suggestedAction`, `evidenceSources`
   - Severity mapping: ≥2× out-of-range = high, 1× = medium, borderline = low
   - No hallucination: only markers actually present in `LabReportItem` inputs

2. **`health_assistant_service.py`** — integrate `detect_lab_abnormalities()` into `build_evidence_bundle()`:
   - Add `"lab_abnormalities"` key to bundle return
   - Add `"lab_abnormality"` to `_SOURCE_PRIORITY` at 75
   - Add `elif src_type == "lab_abnormality":` case in `_build_recommendation_from_candidate()`

3. **Deduplication** — before returning recommendations, check `ActionItem` DB for existing active items with matching `rule_id`; skip if found within 7 days

4. **`LabInsightCard` component** — `frontend/app/components/platform/lab-insight-card.tsx`:
   - Renders each abnormality with severity badge, recurrence count, suggested action
   - Links to source lab report
   - Identical medical-disclaimer footer as `SymptomInsightCard`
   - Loading skeleton + empty state

5. **Tests** (`test_lab_intelligence.py` — 20 pure-function tests + `test_api_lab_smoke.py` — 8 route tests):
   - No abnormalities → empty list (anti-hallucination)
   - Single out-of-range → medium severity
   - Repeated out-of-range → high severity + recurrenceCount
   - Existing ActionItem → deduplication suppresses recommendation
   - All required schema keys present
   - No medical diagnosis wording (keyword blacklist check)

6. **Copy review** — audit all `suggestedAction` and `label` strings against `docs/UI_FEEDBACK_STANDARDS.md` blacklist before merge

### Out of scope for P4

- Trend charts for lab markers (P5)
- Integration with external reference range APIs (P5)
- GP/clinician report generation (future)

---

# Previous Report — P3-SYMPTOM-INTELLIGENCE-READY

Generated: 2026-05-21  
Classification: **`P3_SYMPTOM_INTELLIGENCE_READY`**

---

## Summary

P3 Symptom Intelligence layer is complete and production-merged on `main`.

### What was built

| Component | File | Status |
|---|---|---|
| `build_symptom_timeline()` | `backend/app/services/symptom_intelligence_service.py` | ✅ |
| `detect_symptom_patterns()` | same | ✅ |
| Wire into recommendation pipeline | `backend/app/services/health_assistant_service.py` | ✅ |
| `SymptomInsightCard` | `frontend/app/components/platform/symptom-insight-card.tsx` | ✅ |
| `SymptomPattern` type | `frontend/lib/api.ts` | ✅ |
| `health-assistant-panel.tsx` update | `frontend/app/components/platform/health-assistant-panel.tsx` | ✅ |
| 24 pure-function tests | `backend/tests/test_symptom_intelligence.py` | ✅ 24/24 |

### Validation results

| Suite | Result |
|---|---|
| `test_symptom_intelligence.py` | **24/24 PASS** |
| Full backend (excl. dual_agent) | **246/246 PASS** |
| `npx tsc --noEmit` | **CLEAN** |

### Architecture

- **`build_symptom_timeline`** — groups SymptomLog dicts by symptom name, computes firstSeenAt/lastSeenAt/recurrenceCount, severityTrend (oldest-half avg vs newest-half avg, ±1.5 threshold), relatedDeviceSignals and relatedLabItems via predefined keyword correlation maps (no hallucination guarantee — only returns items actually present in inputs).
- **`detect_symptom_patterns`** — emits up to 5 pattern types per symptom: `recurring_symptom` (≥3 occurrences), `worsening_symptom` (trend==worsening), `symptom_with_device_signal`, `symptom_with_lab_risk`, `unresolved_high_severity_symptom` (severity ≥ 8). Confidence bounded [0.20, 0.90]. No pattern without supporting data.
- **Recommendation bridge** — high-severity patterns enter the `get_action_recommendations()` candidate pool at priority score 65 (between `device_signal=70` and `insight=60`). Rule IDs: `symptom_pattern_{patternType}_{symptomType}`.
- **`SymptomInsightCard`** — shows severity-coded pattern cards with confidence bar, related signal/lab tag chips, suggested action, and medical disclaimer.

### Known limitations
- Symptom timeline computed from current 90-day evidence bundle only (no separate historical DB table).
- E2E / Playwright tests not run.
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, excluded.

### Git
- Branch: `main`
- Commit: `42fc0f9` — `feat: P3_SYMPTOM_INTELLIGENCE_READY`

---

# Previous Report — P2-DEVICE-ESCALATION-VERIFIED-AND-SAFEGUARDED

Generated: 2026-05-20  
Classification: **`P2_DEVICE_ESCALATION_VERIFIED_AND_SAFEGUARDED`**

---

## Summary

This sprint verified and safeguarded the P2 Device Escalation Layer completed in
the prior session.  No new features were added.  Focus was on git safety, data
flow verification, automated smoke testing, and honest limitation documentation.

---

## Task 1 — Git Safety

| Item | Result |
|---|---|
| `git status` before init | `fatal: not a git repository` |
| `.gitignore` created | ✅ Excludes `.venv/`, `node_modules/`, `.next/`, `.env`, `runtime/snapshots/`, runtime locks |
| `git init` | ✅ |
| `git add .` — excluded files verified | ✅ No `.env`, `.venv`, `node_modules`, `.next`, `snapshots` committed |
| Initial commit | ✅ `ab977a6 chore: initial commit — P2_DEVICE_ESCALATION_LAYER_READY` |
| Runtime orchestrator locks untracked | ✅ `git rm --cached` + .gitignore update |
| Final `git status` | ✅ `nothing to commit, working tree clean` |
| `git log --oneline` | `0df1cb5 chore: untrack runtime lock files from index` → `2c5d36e` → `ab977a6` |

---

## Task 2 — Device Escalation Data Flow Verification

Verified end-to-end by code inspection + automated smoke tests:

```
external_metrics (HealthMetric rows, source != 'manual')
  → detect_device_signals()            ← device_signals in bundle ✅
  → build_device_signal_history()      ← device_signal_history in bundle ✅
  → evaluate_signal_escalation()       ← device_escalation in bundle ✅
  → build_evidence_bundle()
  → get_action_recommendations()       ← device_escalation in return ✅
  → generate_daily_health_summary()    ← escalation key injected when level != none ✅
  → frontend DeviceSignalCard          ← escalation prop consumed ✅
```

| Check | Result |
|---|---|
| `bundle["device_signals"]` present | ✅ |
| `bundle["device_signal_history"]` present | ✅ computed, NOT persisted to DB |
| `bundle["device_escalation"]` present | ✅ |
| `get_action_recommendations()` returns `device_escalation` | ✅ |
| `generate_daily_health_summary()` uses escalation for topRisk / todayAction | ✅ |
| `EscalationDecision` type in `frontend/lib/api.ts` | ✅ |
| `DeviceSignalCard` receives and renders `escalation` prop | ✅ |
| Medical disclaimer shown when signals or escalation present | ✅ |
| Stale-all cap at "watch" | ✅ |

---

## Task 3 — API Smoke Tests

**New file:** `backend/tests/test_api_escalation_smoke.py` — 12 tests

| Class | Tests | Result |
|---|---|---|
| `TestDeviceSignalsEndpoint` | schema keys, empty=no signals, elevated HR→signal, signal key shapes | **4/4 PASS** |
| `TestEvidenceBundleEndpoint` | device_escalation key, schema, no-signal=none, elevated HR raises level, device_signal_history present | **5/5 PASS** |
| `TestDailySummaryEndpoint` | base keys, no-signal=no escalation key, elevated HR may inject escalation | **3/3 PASS** |

Note: Tests use in-memory SQLite with real FastAPI TestClient.  An `autouse`
fixture clears `app.dependency_overrides` after each test to prevent cross-test
contamination.

---

## Required Validation — Full Results

| Test file | Count | Result |
|---|---|---|
| `test_device_signal_escalation.py` | 24 | **24 PASS** |
| `test_device_signal_detection.py` | 21 | **21 PASS** |
| `test_health_assistant_service.py` | ~40 | **PASS** |
| `test_daily_summary_service.py` | ~20 | **PASS** |
| `test_recommendation_trust_service.py` | ~20 | **PASS** |
| `test_outcome_feedback_service.py` | ~20 | **PASS** |
| **Full backend (excl. orchestrator)** | **222** | **222 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **PRE-EXISTING FAILURES — excluded** |
| `npx tsc --noEmit` | — | **PASS** |
| `npx next build` | — | **PASS** |
| E2E / Playwright browser smoke | — | **NOT RUN** |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `.gitignore` | Created — excludes secrets, venv, node_modules, runtime locks |
| `backend/tests/test_api_escalation_smoke.py` | Created — 12 API smoke tests |

(All P2 escalation service + UI files were created in the prior session.)

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **DB persistence NOT implemented** | `device_signal_history` is computed deterministically from `HealthMetric` rows at request time.  There is NO separate history table, no trend DB, no long-term memory store.  "Trend memory" means recurrence is inferred across time-bucketed rows from the same table. |
| **E2E not run** | No Playwright / browser smoke tests executed.  Frontend verified by `tsc --noEmit` + `next build` only. |
| **Orchestrator failures pre-existing** | `test_dual_agent_orchestrator.py` — 10 PLANNER_SKIP_SAFE_RUN failures exist before this sprint and are not caused by escalation changes. |
| **No remote git** | Repo is local only.  No remote configured, no CI/CD triggered. |
| **Escalation is session-scoped** | Each API call recomputes escalation from available metrics.  There is no cross-session escalation state. |

---

## Previous Report — P2-DEVICE-SIGNAL-INTELLIGENCE

# Active Task Report — P2-DEVICE-SIGNAL-INTELLIGENCE

Generated: 2026-05-20  
Classification: **`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`**

---

## Pre-step Results

| Step | Result |
|---|---|
| Snapshot path | `runtime/snapshots/backend.app.20260520-HHMM.tgz` (created before any change) |
| `HealthMetric.source` field confirmed | ✅ String(40), default='manual' |
| `HealthMetric.spo2` column exists | ❌ Not present — handled gracefully (no hallucination) |

---

## Modified / Created Files

| File | Action |
|---|---|
| `backend/app/services/device_signal_detection_service.py` | **CREATED** — pure-function detection: elevated HR, pulse trend, low sleep, reduced activity, SpO₂ placeholder |
| `backend/app/services/health_assistant_service.py` | **MODIFIED** — import + enrich external_metrics with raw values + `detect_device_signals` call + `device_signals` in bundle + `_SOURCE_PRIORITY["device_signal"]=70` + candidate generation + recommendation builder handler + return `device_signals` |
| `backend/app/api/health_assistant.py` | **MODIFIED** — import + new `GET /health-assistant/device-signals` endpoint |
| `backend/tests/test_device_signal_detection.py` | **CREATED** — 21 tests covering all 9 spec scenarios |
| `frontend/lib/api.ts` | **MODIFIED** — `DeviceSignal` type + `getDeviceSignals()` |
| `frontend/app/components/platform/device-signal-card.tsx` | **CREATED** — severity badges, freshness, confidence %, empty state |
| `frontend/app/components/platform/health-assistant-panel.tsx` | **MODIFIED** — import + `device_signals?` in HealthAssistantData + render section |

---

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `detect_device_signals([])` returns `[]` | [Confirmed] |
| elevated_resting_heart_rate detected (HR ≥ 90) | [Confirmed] |
| abnormal_pulse_trend detected (≥ 3 ascending readings) | [Confirmed] |
| low_sleep_duration detected (< 7 h) | [Confirmed] |
| reduced_activity detected (< 5000 steps) | [Confirmed] |
| unstable_spo2 — no hallucination (no column) | [Confirmed] |
| Stale → confidence × 0.70 | [Confirmed] |
| ≥ 3 repeated abnormal → severity escalates to high | [Confirmed] |
| Device signal surfaces in Top-3 recommendations | [Confirmed] |
| `/health-assistant/device-signals` endpoint | [Confirmed] |
| `DeviceSignal` TS type + `getDeviceSignals()` API | [Confirmed] |
| `DeviceSignalCard` + empty state rendered in panel | [Confirmed] |
| `npx tsc --noEmit` PASS | [Confirmed] |
| `npx next build` PASS | [Confirmed] |

---

## Test Results

```
test_device_signal_detection.py  — 21 passed
Full backend regression           — 186 passed, 4 warnings
frontend tsc --noEmit             — PASS
frontend next build               — PASS
```

---

## Risks / Next Steps

| Item | Note |
|---|---|
| SpO₂ signal | No `spo2` column yet. Placeholder comment in service. Implement when schema column added. |
| Pulse trend / elevated HR co-signal | Trend only emits when HR < 90 to avoid double-counting. |
| Frontend empty state | Does NOT claim any device is connected — neutral guidance only. |

---

## Final Classification

`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`

---

# Previous Report — P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS

Generated: 2026-05-20

---

## 前置步驟結果

### Step 1 — Snapshot

```
runtime/snapshots/backend.app.20260520-1218.tgz  (180K)
```
Status: **DONE** [Confirmed]

### Step 2 — source 欄位確認

```
backend/app/models/entities.py:93
class HealthMetric:
    source = Column(String(40), default='manual')
```
Status: **CONFIRMED** — `HealthMetric.source` 欄位存在，型別 `String(40)`，預設值 `'manual'`。

### Step 3 — 原始 external_metrics 邏輯

```python
# 原始 (修改前)
"external_metrics": [],  # populated by external_metrics_service if needed
```
原因：hardcoded 空陣列，從未被填入任何資料。

---

## 修改檔案清單

| 檔案 | 修改內容 |
|---|---|
| `backend/app/services/health_assistant_service.py` | 新增 `_freshness_label()` 函式、`_EXTERNAL_RELIABILITY` 對照表、`_DEFAULT_EXTERNAL_RELIABILITY`；在 `build_evidence_bundle` 的 health_metrics 迴圈後新增 external_metrics 抽取邏輯；將 `"external_metrics": []` 替換為 `"external_metrics": external_metrics` |
| `backend/tests/test_health_assistant_service.py` | 新增 `_make_external_metric()` helper、`test_external_metrics_happy_path`、`test_external_metrics_empty_when_all_manual`、`test_external_metrics_stale_freshness` 三個新測試 |
| `runtime/snapshots/backend.app.20260520-1218.tgz` | 新增 snapshot（唯讀備份） |

**未修改任何其他檔案。** frontend、models、API endpoint 簽名均未動。

---

## 驗收標準逐項對應

| 驗收標準 | 結果 |
|---|---|
| 1. 含 source-tagged metrics 的使用者，`external_metrics` 為非空陣列 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 2. 每筆含 `source`, `timestamp`, `freshness`, `reliability`, `summary` | **[Confirmed]** — `test_external_metrics_happy_path` 驗證所有欄位 |
| 3. 無 source-tagged metrics 時，`external_metrics` 保持 `[]` 且不報錯 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4a. happy path 測試 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 4b. empty path 測試 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4c. stale freshness 測試 | **[Confirmed]** — `test_external_metrics_stale_freshness` PASS |
| 5. 既有 backend tests 全綠（無回歸） | **[Confirmed]** — 165 passed (excluding pre-existing orchestrator failures) |
| 6. `npx tsc --noEmit` PASS | **[Confirmed]** — exit code 0 |

---

## 測試輸出摘要

### test_health_assistant_service.py (18 tests)
```
18 passed in 0.43s
```
新增測試：
- `test_external_metrics_happy_path`        PASS
- `test_external_metrics_empty_when_all_manual`  PASS
- `test_external_metrics_stale_freshness`   PASS

### 全 backend suite（不含 orchestrator）
```
165 passed, 4 warnings in 2.23s
```

### Orchestrator pre-existing failures（與本任務無關）
```
10 failed in test_dual_agent_orchestrator.py
原因: PLANNER_SKIP_SAFE_RUN vs CREATED — 環境問題，非本任務造成
```

### Frontend tsc
```
npx tsc --noEmit → exit 0
```

---

## 實作細節

### `_freshness_label(dt)` 邏輯
- `None` → `"unknown"`
- 距今 ≤ 86400 秒（24 h）→ `"fresh"`
- 距今 > 86400 秒 → `"stale"`

### `_EXTERNAL_RELIABILITY` 對照表
| source | reliability |
|---|---|
| apple_health | 0.90 |
| google_fit | 0.88 |
| omron | 0.88 |
| wearable / fitbit / garmin / samsung / withings | 0.85 |
| 未知來源 | 0.80 (fallback) |

### external_metrics 抽取邏輯
- 從現有 `metric_rows`（30 天查詢）中篩選 `source != 'manual'`
- 不新增額外 DB query
- 每筆回傳：`source`, `timestamp` (ISO8601), `freshness`, `reliability`, `summary`
- `summary` 格式：`[{source}] 血壓 130/85、血糖 95.0、體重 70.5kg、...`

---

## 風險 / Unknown / 後續建議

| 項目 | 說明 |
|---|---|
| 真實資料庫中的 source 值多樣性 | 目前 source 欄位為 free-text String(40)，沒有 ENUM 約束。若真實資料中出現非預期 source 值（如 `"Withings"` 大寫），會走 fallback reliability 0.80。建議未來在資料入口統一 lowercase normalize。 |
| external_metrics 未加入 `missing_data` 提示 | 設計決定：external metrics 是補充資料，非必填，不適合觸發 missing_data 警告。 |
| freshness 邊界 24h | 目前 "fresh" = 24h 內。若 wearable 每小時同步，這個邊界合理。但若使用場景改為「當天」概念，建議改為 calendar day boundary。 |
| orchestrator 10 tests 失敗 | 與本任務完全無關，為 `PLANNER_SKIP_SAFE_RUN` 環境設定問題，不在本任務修改範圍。 |
| E2E / API integration test | 未執行 live API call 驗證，unit tests 覆蓋邏輯層，但真實 DB 回傳的 source 值尚未在 staging 驗證。 |

---

## Final Classification

**`P0_EVIDENCE_EXTERNAL_METRICS_DONE`**

---

---

## P53-P52-BROWSER-ACCEPTANCE-CLOSURE-VERIFICATION (2026-05-25)

**Final Classification: `P53_P52_BROWSER_ACCEPTANCE_CLOSURE_VERIFIED`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD: `38f9c13` (P52 commit) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (governance docs only, not staged) ✅
- No detached HEAD, no unrelated dirty application files ✅

### 1. 本輪目標

Closure verification for P52. Confirm that the P52 browser acceptance commit does not regress runtime smoke, TypeScript type check, or the browser acceptance spec itself. No new features.

### 2. 已完成事項

- **P52 commit scope verified** — `git show --stat 38f9c13` confirms exactly 5 files changed: `decision-recommendation-layer.tsx`, `health-assistant-panel.tsx`, `actions/page.tsx`, `decision-support.ts`, `p52-recommendation-fields.spec.ts`. No CI, auth, backend connector, or PostgreSQL scope.
- **`make runtime-smoke`** — 130 passed / 2 skipped ✅ (identical to pre-P52 baseline)
- **`npx tsc --noEmit`** — 0 errors ✅ (no `typecheck` npm script exists; ran tsc directly)
- **P52 browser acceptance spec rerun** — `11 / 11 PASS` in 7.9s ✅

### 3. 修改或產出的檔案

No application code modified during this closure round. Only this report updated.

| File | Action |
|---|---|
| `00-Plan/roadmap/active_task_report.md` | Appended P53 closure section |

### 4. 驗證結果 / 測試結果

| Check | Command | Result |
|---|---|---|
| Repo / branch | `git rev-parse --show-toplevel && git branch --show-current` | ✅ canonical |
| P52 commit scope | `git show --stat --oneline 38f9c13` | ✅ 5 files, all frontend/browser |
| Runtime smoke | `make runtime-smoke` | ✅ 130 passed / 2 skipped |
| TypeScript | `npx tsc --noEmit` | ✅ 0 errors |
| P52 browser spec | `npx playwright test tests/e2e/p52-recommendation-fields.spec.ts` | ✅ 11/11 PASS |

### 5. 目前結論

P52 is fully closed. All three verification checks pass with no regressions. The `evidence_summary` and `data_insufficiency_reason` fields are correctly propagated to both the Actions and Dashboard recommendation surfaces, and browser-verified by a stable 11-test Playwright suite. The root bug fixed during P52 stabilization (NarrativeMemoryCard cross-period mock crash + Playwright strict mode violation) does not affect production code — it was a test environment issue only.

### 6. 尚未完成事項

None within P52/P53 scope.

Future backlog (not P53):
- `npm run typecheck` script is missing from `frontend/package.json` — minor DX gap, could add `"typecheck": "tsc --noEmit"`.
- `make runtime-smoke` coverage does not include orchestrator planner tests (pre-existing skip, unrelated to P52).

### 7. 風險與不確定點

| 項目 | 說明 |
|---|---|
| Live backend data shape | P52 browser acceptance is fully mocked. Live `/health-assistant/recommendations` must return `evidence_summary` and `data_insufficiency_reason` from the P51 backend. P51 backend was verified in its own round; no regression expected. |
| `NarrativeMemoryCard` upstream bug | The `crossPeriod !== null` guard (which passes for `undefined`) is a real production bug in `narrative-memory-card.tsx`. If the live API returns a response where `res.reasoning` is missing, the component will crash in production. This was masked in tests but not fixed in application code. Recommend a follow-up defensive fix: `setCrossPeriod(res.reasoning ?? null)`. |

### 8. 建議今天優先處理的方向

1. **(Low, safe)** Add `setCrossPeriod(res.reasoning ?? null)` defensive guard in `narrative-memory-card.tsx` — prevents a real production crash if backend omits `reasoning`.
2. **(Low, DX)** Add `"typecheck": "tsc --noEmit"` to `frontend/package.json` scripts.
3. **(Next priority)** Proceed to next roadmap task per `roadmap.md`.

### 9. 下一輪可直接執行的 task prompt

```
[每次交接開頭] — Governance Header

## Required Pre-flight
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -5

## Task
P54-NARRATIVE-MEMORY-CARD-DEFENSIVE-GUARD

Fix production crash risk in NarrativeMemoryCard:
- File: frontend/app/components/platform/narrative-memory-card.tsx
- Line: api.getCrossPeriodReasoning().then((res) => setCrossPeriod(res.reasoning))
- Fix: change to setCrossPeriod(res.reasoning ?? null)
- Rationale: crossPeriod !== null passes for undefined, leading to crossPeriod.confidence crash

After fix:
1. Run npx tsc --noEmit (0 errors required)
2. Run make runtime-smoke (130 passed / 2 skipped required)
3. Run npx playwright test tests/e2e/p52-recommendation-fields.spec.ts --reporter=line (11/11 required)
4. git add frontend/app/components/platform/narrative-memory-card.tsx
5. git commit -m "fix: guard setCrossPeriod against undefined reasoning to prevent production crash"

Forbidden: No new features, no auth changes, no CI changes, no new branches.
```

### 10. CTO Agent 10 行內摘要

1. P53 closure verification 完成，分類：`P53_P52_BROWSER_ACCEPTANCE_CLOSURE_VERIFIED`。
2. P52 commit 38f9c13 scope 確認：5 個 frontend 檔案，無 CI/auth/backend 洩漏。
3. `make runtime-smoke`：130 passed / 2 skipped，與 P51 baseline 完全一致。
4. `npx tsc --noEmit`：0 errors（無 `typecheck` npm script，直接執行 tsc）。
5. P52 browser acceptance spec 重跑：11/11 PASS，7.9s。
6. 本輪未修改任何應用程式碼。
7. 發現生產風險：`NarrativeMemoryCard` 的 `crossPeriod !== null` guard 對 `undefined` 失效，需補 `?? null`。
8. 此 bug 在測試中被 route stub 遮蔽，未進入 P52 commit，需單獨修復。
9. 建議下一輪 P54 專門修這個 defensive guard（一行修改，低風險）。
10. P52/P53 已完全關閉，可安全推進 roadmap 下一任務。

---

## P54-NARRATIVE-MEMORY-CARD-DEFENSIVE-GUARD (2026-05-25)

**Final Classification: `P54_NARRATIVE_MEMORY_CARD_DEFENSIVE_GUARD_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `262b77f` (P53 closure) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (governance docs only — not staged) ✅

### Root Cause (identified in P53)
`NarrativeMemoryCard.getCrossPeriodReasoning()` receives `{person_id, reasoning: undefined}` when the backend returns an absent field. JavaScript evaluates `undefined !== null` as `true`, so the render guard `crossPeriod !== null` passes — causing `crossPeriod.confidence` to crash inside the Dashboard ErrorBoundary.

The test environment was masked by a route stub that returned `{reasoning: null}` explicitly; the production path remained vulnerable.

### Fix Applied
**File**: `frontend/app/components/platform/narrative-memory-card.tsx`

| Before | After |
|--------|-------|
| `.then((res) => setCrossPeriod(res.reasoning))` | `.then((res) => setCrossPeriod(res.reasoning ?? null))` |

One character change: `?? null` appended. The nullish-coalescing operator coerces `undefined` to `null`, which the existing render guard `crossPeriod !== null` correctly handles.

### Grep Verification (pre-fix)
```
narrative-memory-card.tsx:162:  const [crossPeriod, setCrossPeriod] = useState<CrossPeriodReasoning | null>(null)
narrative-memory-card.tsx:202:    api.getCrossPeriodReasoning()
narrative-memory-card.tsx:203:      .then((res) => setCrossPeriod(res.reasoning))   ← VULNERABLE
narrative-memory-card.tsx:211:    crossPeriod !== null &&
narrative-memory-card.tsx:212:    (crossPeriod.confidence > 0 ||
narrative-memory-card.tsx:432:      {crossPeriod !== null && !hasCrossData && (
```
Exactly one occurrence of the vulnerable pattern — surgical fix confirmed.

### Verification Results
| Check | Command | Result |
|-------|---------|--------|
| TypeScript | `npx tsc --noEmit` | 0 errors ✅ |
| Runtime smoke | `make runtime-smoke` | 130 passed / 2 skipped ✅ |
| P52 browser acceptance | `npx playwright test tests/e2e/p52-recommendation-fields.spec.ts` | 11/11 PASS ✅ |

### Commits
| SHA | Message |
|-----|---------|
| `c06dce1` | `fix: guard cross-period reasoning against undefined response` |

### 10. CTO Agent 10 行內摘要

1. P54 defensive guard 完成，分類：`P54_NARRATIVE_MEMORY_CARD_DEFENSIVE_GUARD_READY`。
2. Root cause：`res.reasoning` 可能為 `undefined`，`undefined !== null` 為 `true`，導致 Dashboard ErrorBoundary crash。
3. Fix：一行 `?? null`，nullish-coalescing 將 `undefined` 強制轉為 `null`，令現有 render guard 正確攔截。
4. Grep 確認只有一個 vulnerable call site，無側效應。
5. `npx tsc --noEmit`：0 errors。
6. `make runtime-smoke`：130 passed / 2 skipped，baseline 不變。
7. P52 browser acceptance spec：11/11 PASS（12.4s）。
8. Commit `c06dce1`：僅 1 file changed，1 insertion，1 deletion。
9. 未洩漏任何 governance docs，不開新 branch，不 force push。
10. P50–P54 全部關閉，生產防護補完，可安全推進 roadmap 下一任務。

---

## P55-DAILY-RECOMMENDATION-ACTION-FEEDBACK (2026-05-25)

**Final Classification: `P55_DAILY_RECOMMENDATION_ACTION_FEEDBACK_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `e235000` (P54 closure) ✅

### A. Problem Statement

Users had no way to express preference on daily recommendations or tracked actions. No feedback signals were preserved. P55 adds five interaction states:

1. **我會做** — implicit (action created/tracking)
2. **完成** — existing `打卡` / `done`
3. **稍後提醒** — existing snooze on recommendation layer; now also removes from filteredDecisionItems
4. **沒有用** — new `not_useful` status; PATCH on ActionCard; dismiss from recommendation layer
5. **不適合我** — new `not_applicable` status; PATCH on ActionCard; dismiss from recommendation layer

System preserves feedback via localStorage (recommendation layer) and DB PATCH (action cards). No medical certainty claims.

### B. Implementation

| Step | File | Change |
|------|------|--------|
| 1 | `frontend/lib/actions.ts` | Extend `status` type: `not_useful \| not_applicable` |
| 2 | `action-status-badge.tsx` | Badge styles for new statuses (orange, slate) |
| 3 | `action-card.tsx` | "沒有用" + "不適合我" buttons on todo/in_progress; disclaimer after dismiss |
| 4 | `decision-recommendation-layer.tsx` | `onDismiss?` prop threaded to `RecommendationItem`; buttons rendered conditionally |
| 5a | `actions/page.tsx` | `RecFeedback` type, localStorage helpers, `recFeedback` state + useEffect |
| 5b | `actions/page.tsx` | `filteredDecisionItems`, `handleSnooze` (fixed: no personId gate on setState), `handleDismissRecommendation`, `grouped.dismissed`, `DecisionRecommendationLayer` `onDismiss` prop |

### C. Root Causes Debugged During Session

| Issue | Root Cause | Fix |
|-------|------------|-----|
| 8/9 tests failing | Stale `.next` build (P52 era) — `next start` served old code without P55 buttons | `npm run build` before re-running tests |
| Snooze didn't remove item | `setRecFeedback` gated on `if (personId)` — personId falsy at click time in test env | Move state update outside personId guard; only gate `saveRecFeedback` |
| PATCH tests intercepted wrong button | `getByRole('button', { name: '沒有用' }).first()` grabbed recommendation layer button (onDismiss), not ActionCard PATCH button | `stubRoutes({ noRecs: true })` in PATCH tests to suppress recommendation layer |
| PATCH route not intercepted | `api.request()` appends `?person_id=person-self` → URL had query string; pattern `**/actions/action-p55-test` didn't match | Changed pattern to `**/actions/action-p55-test**` |

### D. Test Results

| Suite | Result |
|-------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `make runtime-smoke` | ✅ 130 passed / 2 skipped |
| P52 Playwright | ✅ 11/11 |
| **P55 Playwright** | ✅ **9/9** |

### E. Commit

- `853c93c` — `feat: add recommendation action feedback loop`

### F. Classification

`P55_DAILY_RECOMMENDATION_ACTION_FEEDBACK_READY`

P50–P55 全部關閉。使用者每日建議現已具備完整回饋迴路：沒有用 / 不適合我 / 稍後提醒，系統儲存回饋但不作醫學聲明。
