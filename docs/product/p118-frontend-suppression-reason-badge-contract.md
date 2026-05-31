# P118 — Frontend Suppression Reason Badge Contract

## Purpose
This document describes the minimal frontend contract for displaying suppression reasons (specifically `suppressed_unit_scale_mismatch`) in the Documents/lab result UI. It covers the badge/copy logic, test coverage, and user-facing clarity requirements.

## Scope
- Surfaces suppression reason for lab items where abnormal_flag_reason === 'suppressed_unit_scale_mismatch'.
- Ensures no misleading '正常' badge is shown for suppressed items.
- Ensures high/low abnormal flags remain visible as before.
- Ensures contract is covered by E2E test.

## UI Contract
- If abnormal_flag_reason === 'suppressed_unit_scale_mismatch', show a yellow badge with text: `單位不同，暫不判斷異常`.
- If abnormal_flag === 'H', show red badge: `偏高`.
- If abnormal_flag === 'L', show red badge: `偏低`.
- If abnormal_flag is null and abnormal_flag_reason is not suppressed_unit_scale_mismatch, show green badge: `正常`.

## Test Coverage
- Lab item with abnormal_flag = null and abnormal_flag_reason = suppressed_unit_scale_mismatch displays the yellow badge/copy.
- Same-unit normal does not show the suppression badge.
- High/low abnormal flags remain visible as before.
- No misleading '正常' wording appears for suppressed_unit_scale_mismatch.
- Existing Documents/lab trend contracts still pass.

## Implementation Notes
- See parsed-items-drawer.tsx for rendering logic.
- See backend/app/schemas/documents.py and backend/app/api/documents.py for abnormal_flag_reason contract.

---
P118 — 2026-xx-xx
