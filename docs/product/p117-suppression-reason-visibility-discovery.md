# P117 Suppression Reason Visibility Discovery

## 1. P116 Recap
- P116 exposed `abnormal_flag_reason` (e.g., `suppressed_unit_scale_mismatch`) at the API response level for lab report items.
- No DB migration, no frontend runtime change, no historical backfill.

## 2. Backend Response Availability Map
- `backend/app/schemas/documents.py`: `ParsedItemResponse` includes `abnormal_flag_reason`.
- `backend/app/api/documents.py`: `/documents/{document_id}/parsed-items` endpoint computes and returns `abnormal_flag_reason` for each item, including `suppressed_unit_scale_mismatch` when applicable.

## 3. Frontend Consumption Map
- Searched all frontend code and tests for `abnormal_flag_reason` and `suppressed_unit_scale_mismatch`.
- No evidence that any frontend page, component, or test consumes or renders `abnormal_flag_reason`.
- All frontend logic, including `documents-confirmation.tsx`, `parsed-items-drawer.tsx`, and `document-review-table.tsx`, only reference `abnormal_flag`.
- No badge, copy, or UI element for suppression reason.

## 4. Evidence Surface Map
- Documents confirmed data: does NOT display suppression reason.
- Lab history/trend: does NOT display suppression reason.
- Daily Assistant evidence: does NOT display suppression reason.
- Actions evidence: does NOT display suppression reason.
- No evidence surface or table renders `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.

## 5. User-Facing Ambiguity Risk Classification
- **BACKEND_ONLY_SAFE_BUT_NOT_VISIBLE**: Suppression reason is available in API but not surfaced in any frontend or evidence UI.
- Users and clinicians cannot distinguish suppressed vs. normal vs. no-rule from the UI.

## 6. Test or Grep Evidence
- Grep of frontend code and tests: only `abnormal_flag` is referenced; `abnormal_flag_reason` is ignored.
- No e2e or unit test asserts on suppression reason.
- Example: `frontend/pages/documents-confirmation.tsx` and `frontend/components/redesign/document-review-table.tsx` only use `abnormal_flag`.

## 7. Recommended Next Lane
- **Option A**: Implement frontend display (badge/copy) for suppression reason (e.g., show suppressed_unit_scale_mismatch in documents/lab history/evidence).
- Option B: Daily Assistant evidence-only warning (not recommended as sole fix).
- Option C: Backend-only is insufficient for user clarity.
- Option D: API contract is already sufficient for UI.

## 8. Non-Goals
- No backend runtime code change.
- No DB migration or new column.
- No real unit conversion or historical backfill.
- No UI implementation in this discovery.

## 9. Validation Table
| Area                | Status   |
|---------------------|----------|
| Backend API         | PASS     |
| Frontend build      | PASS     |
| Contract tests      | PASS     |
| Evidence surfaces   | Not visible |
| User-facing clarity | Ambiguous |

## 10. Files Changed
- docs/product/p117-suppression-reason-visibility-discovery.md (this file)

## 11. Commit Hashes
- P116 impl: e57dafb
- P116 report: d549de8

## 12. Known Limitations
- Suppression reason is not visible to users in any UI.
- All ambiguity remains at the UI layer until frontend is updated.

## 13. Governance Notes
- No backend or frontend runtime code changed in P117.
- No DB migration or schema change.
- No Makefile or governance file touched.

## 14. CTO 5-line Summary
- Backend exposes suppression reason but frontend ignores it.
- No evidence surface or UI displays suppressed_unit_scale_mismatch.
- User-facing ambiguity persists for suppressed/normal/no-rule.
- All tests and builds pass; no regressions.
- Next lane: implement frontend badge/copy for suppression reason.

## 15. CEO 5-line Summary
- Suppression reason is available in API but not visible to users.
- No UI or evidence surface distinguishes suppressed from normal.
- User-facing ambiguity remains unresolved.
- All validation gates pass.
- Recommend UI update to surface suppression reason.
