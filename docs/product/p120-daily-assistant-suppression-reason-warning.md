# P120 Daily Assistant Suppression Reason Warning — Evidence Gap and Blocked Implementation

## 1. P119 Recap
- Mapped `abnormal_flag_reason` (esp. `suppressed_unit_scale_mismatch`) propagation across all evidence surfaces.
- Only Documents/parsed-items-drawer surfaces and renders suppression reasons (P118).
- All other evidence surfaces ignore or do not receive `abnormal_flag_reason`.
- Backend only includes `abnormal_flag_reason` in parsed items API; other surfaces do not receive or propagate this field.

## 2. P120 Attempted Goal
- Propagate and display suppression reason ("單位不同，暫不判斷異常") for `suppressed_unit_scale_mismatch` in Daily Assistant evidence.
- Strictly forbidden to change backend runtime, DB, schema, or frontend contract outside allowed scope.

## 3. Baseline Validation Summary
| Check                        | Result |
|------------------------------|--------|
| Contract/smoke tests         | PASS   |
| Backend regression           | PASS   |
| P118 E2E                     | PASS   |
| Next.js build                | PASS   |

## 4. Actual Evidence Data Path Map
- `lab_report_items` includes `abnormal_flag_reason` (from backend/app/api/documents.py)
- `lab_abnormalities` does **not** propagate `abnormal_flag_reason`
- Daily Assistant summary/recommendation evidence consumes `lab_abnormalities` or derived evidence, not `lab_report_items`
- `suppressed_unit_scale_mismatch` is **unavailable** to Daily Assistant evidence surface

## 5. Evidence Gap Classification
**P120_BLOCKED_BY_IMPLEMENTATION_EVIDENCE_GAP**

## 6. Why No Implementation Was Performed
- Frontend cannot safely infer or guess suppression reason for Daily Assistant evidence
- Backend evidence path needs explicit propagation of `abnormal_flag_reason` to `lab_abnormalities`/evidence bundle
- No DB/API/schema expansion authorized in P120

## 7. Non-goals
- No backend runtime implementation
- No frontend runtime implementation
- No DB migration
- No new DB column
- No real unit conversion
- No historical backfill

## 8. Recommended Corrected Next Scope
**P121 Backend Evidence Bundle Suppression Reason Propagation Contract**
- Goal: propagate `abnormal_flag_reason` from `lab_report_items` into `lab_abnormalities`/Daily Assistant evidence bundle without DB migration, if source data already contains it.

## 9. Known Limitations
- Current evidence path does not allow Daily Assistant to display suppression reason for unit-scale mismatch.
- Any propagation requires backend contract and evidence bundle changes.

---

**Classification:** P120_BLOCKED_BY_IMPLEMENTATION_EVIDENCE_GAP
**Date:** 2026-05-31
**Author:** Worker agent
