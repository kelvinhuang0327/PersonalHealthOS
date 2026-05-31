# P116: Abnormal Flag Suppression Reason Response Contract

## 1. P115 Active Ambiguity Recap
- Prior to P116, abnormal_flag=None could mean: normal, unknown, no local rule, or suppressed by unit-scale mismatch.
- API/schema did not expose the suppression reason, causing ambiguity for downstream consumers.

## 2. Implemented Response-Level Contract
- Added optional `abnormal_flag_reason` field to API response (ParsedItemResponse).
- Reason is computed at response time, not persisted to DB.
- Values are deterministic and conservative.

## 3. Reason/Status Decision Table
| abnormal_flag | abnormal_flag_reason              | Meaning                                      |
|---------------|-----------------------------------|----------------------------------------------|
| 'H'           | flagged_high                      | Value flagged high by rule                   |
| 'L'           | flagged_low                       | Value flagged low by rule                    |
| 'N'           | normal_by_rule                    | Value normal by rule                         |
| None          | suppressed_unit_scale_mismatch    | Suppressed by unit-scale mismatch (P114)     |
| None          | no_reference_rule                 | No rule available for item                   |
| None          | parser_unavailable                | Parser confidence too low                    |
| None          | unknown                           | Fallback/ambiguous case                      |

## 4. API/Schema Exposure Summary
- Field: `abnormal_flag_reason: Optional[str]` (response only)
- Exposed on `/documents/{document_id}/parsed-items` endpoint
- No DB column or migration required
- No frontend runtime change

## 5. Why DB Column/Migration Was Not Added
- Reason is computed at response time, not persisted
- Avoids schema migration and historical backfill
- Follows minimal contract extension principle

## 6. Tests Added
- `backend/tests/test_p116_abnormal_flag_suppression_reason_response_contract.py` covers:
  - P114 unit mismatch → abnormal_flag=None, reason=suppressed_unit_scale_mismatch
  - Same-unit normal → abnormal_flag='N', reason=normal_by_rule
  - High/low abnormal → flagged_high/flagged_low
  - No rule → no_reference_rule
  - Parser unavailable → parser_unavailable
  - No DB column/migration
  - No real conversion
  - Downstream does not collapse suppressed mismatch into normal

## 7. Known Limitations
- Some ambiguous None cases may still be classified as 'unknown' if evidence is insufficient
- No historical backfill; only new responses include reason
- No frontend UI change in this lane

## 8. Next Recommended Lane
- If further disambiguation is required, consider deeper parser instrumentation or DB trace
- For UI/UX, coordinate with frontend for reason display if needed
- For historical data, consider migration only if justified by downstream requirements
