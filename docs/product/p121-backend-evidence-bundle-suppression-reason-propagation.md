# P121 — Backend Evidence Bundle Suppression Reason Propagation (2026-06-01)

## Final Classification
`P121_BACKEND_EVIDENCE_BUNDLE_SUPPRESSION_REASON_READY`

## Scope
- Lane: trust lane after P122 discovery.
- Goal: make `suppressed_unit_scale_mismatch` observable in Daily Assistant evidence path without DB/schema expansion.
- Constraint: no DB migration, no new column, no frontend runtime changes, no conversion/backfill.

## Phase 0 Observations (Actual)
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree, not detached)
- P122 commit present at HEAD: `308bd11 docs(product): P122 first-run journey discovery`
- P120 commit present in history: `9413929`
- Dirty/untracked matched known set only (governance dirty + known runtime/test artifacts)
- Source grep reconfirmed:
  - `backend/app/services/health_assistant_service.py` filtered evidence `lab_report_items` via `LabReportItem.abnormal_flag.isnot(None)`.
  - `abnormal_flag_reason` existed in `backend/app/api/documents.py` parsed-items response path, not in assistant bundle path.

## Correction Of Old P120 Assumption
Old assumption was incorrect for assistant path: "evidence bundle `lab_report_items` already includes `abnormal_flag_reason`".

Correct state before P121:
1. parsed-items API had reason (`documents.py` response-level compute),
2. assistant evidence bundle excluded `abnormal_flag=None` rows,
3. therefore suppressed rows never reached Daily Assistant evidence candidates.

## Evidence Path Before / After

## Before
- `LabReportItem.abnormal_flag.isnot(None)` filter in `build_evidence_bundle()`.
- only `lab_report_items` (clinically judged rows) flowed into:
  - `lab_abnormalities` detection,
  - recommendation candidate construction,
  - `summary.abnormal_lab_count`.
- suppressed rows (`abnormal_flag=None`) were invisible to assistant evidence path.

## After
- `build_evidence_bundle()` now scans all report items for the selected reports.
- deterministic helper `_derive_abnormal_flag_reason()` added (no schema change).
- split path:
  - clinically judged rows (`abnormal_flag != None`) stay in `lab_report_items` (existing behavior path),
  - `suppressed_unit_scale_mismatch` rows go to new `lab_not_judged_items` path.
- `lab_not_judged_items` rows are explicitly marked with:
  - `abnormal_flag_reason = suppressed_unit_scale_mismatch`,
  - `not_judged = true`,
  - `judgement = uncertain`,
  - non-abnormal summary copy.
- recommendations response now also carries `lab_not_judged_items` for evidence visibility.

## Suppressed Evidence Semantics Table
| Case | Path | Counts into abnormal_lab_count | Enters lab_abnormalities | Severity impact |
|---|---|---:|---:|---:|
| `abnormal_flag = H/L` | `lab_report_items` | Yes | Yes | Yes (existing behavior) |
| `abnormal_flag = None` + `suppressed_unit_scale_mismatch` | `lab_not_judged_items` | No | No | No |
| `abnormal_flag = None` + no-rule/unknown/parser-low-conf | excluded from both assistant lab lists | No | No | No |
| `abnormal_flag = N` | `lab_report_items` (existing semantics) | existing behavior unchanged | existing behavior unchanged | existing behavior unchanged |

## Safety Evidence (No Count/Severity Inflation)
Implemented guarantees:
1. `summary.abnormal_lab_count` still derived only from `lab_report_items`.
2. `lab_abnormalities` still derived only from `lab_report_items`.
3. `lab_not_judged_items` is isolated from recommendation abnormal candidate logic.
4. suppressed rows do not become H/L/N and never imply clinically normal/abnormal.

## Tests

## Required targeted test
- Command:
  - `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py -v`
- Result: `PASS` (6 passed)

Covered assertions:
1. suppressed unit-scale row becomes observable with `abnormal_flag_reason=suppressed_unit_scale_mismatch` in not-judged path.
2. suppressed row does not increase `abnormal_lab_count`.
3. suppressed row does not raise recommendation severity/ranking.
4. H/L rows keep existing abnormal behavior.
5. no-rule/unknown/normal rows are not mislabeled as `suppressed_unit_scale_mismatch`.
6. `lab_abnormalities` remains true-abnormal path; suppressed evidence remains separate not-judged path.

## Impacted existing service tests
- Command:
  - `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_health_assistant_service.py -q`
- Result: `PASS` (23 passed)

## Not run (by design)
- Next.js build: `NOT RUN` (no frontend runtime changes)
- Playwright suites: `NOT RUN` (backend-only scope)
- runtime-smoke: `NOT RUN` (no broad runtime contract break observed)

## Files Changed
- `backend/app/services/health_assistant_service.py`
- `backend/tests/test_p121_backend_evidence_bundle_suppression_reason_propagation.py`
- `docs/product/p121-backend-evidence-bundle-suppression-reason-propagation.md`
- `00-Plan/roadmap/active_task_report.md`

## Known Limitations
1. `abnormal_flag_reason` is still computed deterministically at service/response layer (no persisted DB field introduced).
2. non-suppressed `abnormal_flag=None` rows (no-rule/parser unavailable/unknown) are not surfaced in assistant path in this lane.
3. this lane intentionally avoids any API/schema broadening beyond additive response fields in existing backend path.

## Next Lane Suggestion
- Proceed with first-run journey implementation lane (from P122), now that P121 trust-path blocker is cleared.
- Keep suppression reason semantics as not-judged/uncertain evidence and avoid mapping to clinical abnormality unless medically judged data exists.
