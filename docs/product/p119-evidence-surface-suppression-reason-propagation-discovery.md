# P119 Evidence Surface Suppression Reason Propagation Discovery

## Objective
Map how `abnormal_flag_reason` (especially `suppressed_unit_scale_mismatch`) propagates across all evidence surfaces in the PersonalHealthOS platform. Classify each surface as: reason available and consumed, reason available but ignored, reason not available in data path, reason collapsed into abnormal_flag null, or unknown/needs fixture evidence.

## Methodology
- Grep/code archaeology for `abnormal_flag_reason`, `suppressed_unit_scale_mismatch`, `abnormal_flag`, `is_abnormal` across backend, frontend, and tests.
- Review all evidence surface components and their data contracts.
- Confirm actual UI rendering and test coverage.

## Evidence Surfaces and Findings

### 1. Documents (parsed-items-drawer)
- **Status:** `abnormal_flag_reason` is surfaced and rendered in UI (yellow badge for `suppressed_unit_scale_mismatch`).
- **Code:** `frontend/app/components/platform/parsed-items-drawer.tsx`
- **Test:** `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.ts`
- **Classification:** Reason available and consumed.

### 2. Daily Assistant Evidence
- **Component:** `frontend/app/components/platform/daily-assistant-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Only** uses `is_abnormal`/`abnormal_flag`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

### 3. Actions Evidence
- **Component:** `frontend/app/components/platform/actions-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

### 4. Lab Trend/History Evidence
- **Component:** `frontend/app/components/platform/lab-trend-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

### 5. Symptom Recommendation Evidence
- **Component:** `frontend/app/components/platform/symptom-recommendation-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

### 6. Documents Evidence Table
- **Component:** `frontend/app/components/platform/documents-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

### 7. Summary Card Evidence
- **Component:** `frontend/app/components/platform/summary-card-evidence.tsx`
- **Status:** No reference to `abnormal_flag_reason` or `suppressed_unit_scale_mismatch`.
- **Classification:** Reason not available in data path; only abnormal_flag is used.

## Backend Data Path
- `abnormal_flag_reason` is only included in the API response for parsed items (see `backend/app/api/documents.py`, `schemas/documents.py`).
- Other evidence surfaces do not receive or propagate this field.

## Test Coverage
- Only `parsed-items-drawer` and its E2E test (`p118-suppression-reason-badge-contract.spec.ts`) cover suppression reason rendering.
- All other surfaces/tests only check `abnormal_flag`/`is_abnormal`.

## Summary Table
| Evidence Surface                | abnormal_flag_reason surfaced? | Consumed in UI? | Classification                  |
|---------------------------------|-------------------------------|-----------------|----------------------------------|
| Documents (parsed-items-drawer) | Yes                           | Yes             | Reason available and consumed    |
| Daily Assistant Evidence        | No                            | N/A             | Reason not available in data path|
| Actions Evidence                | No                            | N/A             | Reason not available in data path|
| Lab Trend/History Evidence      | No                            | N/A             | Reason not available in data path|
| Symptom Recommendation         | No                            | N/A             | Reason not available in data path|
| Documents Evidence Table        | No                            | N/A             | Reason not available in data path|
| Summary Card Evidence           | No                            | N/A             | Reason not available in data path|

## Conclusion
- Only the Documents/parsed-items-drawer surface exposes and renders suppression reasons (P118).
- All other evidence surfaces ignore or do not receive `abnormal_flag_reason`.
- No evidence of accidental/implicit propagation or UI rendering outside parsed-items-drawer.
- Future work: To propagate suppression reasons to other surfaces, backend and contract changes are required.
