# P115: Abnormal Flag Suppression Reason Discovery

## 1. Current abnormal_flag value semantics
| Value | Meaning (current) |
|-------|-------------------|
| H     | High (above upper reference) |
| L     | Low (below lower reference)  |
| N     | Normal (within reference)    |
| None  | Ambiguous: can mean normal, unknown, no local rule, or suppressed by unit-scale mismatch |

## 2. Current None ambiguity map
- None is used for:
  - No abnormality detected (sometimes)
  - No local rule available
  - Parser unavailable
  - Suppressed by unit-scale mismatch (P114)
- No explicit field or reason is exposed in API/schema to distinguish these cases.

## 3. Downstream consumption map
- Daily Assistant, Actions, and evidence logic treat abnormal_flag None as:
  - Not abnormal (not flagged)
  - May be omitted from abnormal evidence
  - May appear as normal or unknown, depending on context
- No mechanism to distinguish suppressed None from other None in downstream logic.

## 4. API/schema exposure map
- API response includes abnormal_flag (H/L/N/None)
- No abnormal_flag_reason or suppression_reason field is present
- Client cannot distinguish why abnormal_flag is None

## 5. Risk classification
**ACTIVE_AMBIGUITY**
- None is overloaded and user-facing logic cannot distinguish suppressed (unit-scale mismatch) from other None cases.
- User may see results disappear or appear normal/unknown without clear reason.

## 6. Evidence from P115 tests
- P114 unit mismatch results in abnormal_flag None
- Same-unit normal result is 'N', not None
- None is used for multiple states (normal, unknown, no rule, suppressed)
- Downstream logic and API do not distinguish suppressed None

## 7. Recommended next lane and rationale
- **Option A: Add internal abnormal_flag_reason field only**
  - Rationale: Enables future API/schema clarity without breaking current clients. Allows backend to trace and expose suppression reason if/when needed.
- No real unit conversion, no historical backfill, no frontend runtime change, no clinical rules invented.

## 8. Non-goals
- No real unit conversion
- No historical backfill
- No frontend runtime change
- No clinical rules invented

---

**Summary:**
- abnormal_flag None is actively ambiguous and can represent multiple states, including suppression by unit-scale guard. No current API/schema or downstream logic distinguishes these cases. Recommend adding an internal abnormal_flag_reason for future clarity.
