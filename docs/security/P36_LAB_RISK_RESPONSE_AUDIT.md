# P36 — Lab Reports & Risk Alerts API Response Audit

**Date**: 2025-07-27  
**Branch**: main  
**Base commit**: 38b202c (P35 complete)  
**Outcome**: `P36_LAB_RISK_SMOKE_VERIFIED` — no C.GAP found  
**Tests**: 12 added, 12/12 PASS  
**Runtime-smoke**: 113 passed, 2 skipped (all stages green)

---

## Scope

Audit of all API routes and response schemas in the lab reports and risk alerts
domain to verify that no sensitive or internal fields are exposed to client
responses.

Files audited:
- `backend/app/api/documents.py` — 8 routes
- `backend/app/api/risk_alerts.py` — 5 routes
- `backend/app/schemas/documents.py`
- `backend/app/schemas/risk_alerts.py`
- `backend/app/models/entities.py` — ORM reference (MedicalDocument, LabReport, LabReportItem, RiskAlert)

---

## Route Inventory & Classification

### Documents (`api/documents.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /documents/upload | `DocumentResponse` | A.SAFE | P32-hardened; storage_key/storage_bucket/user_id absent |
| GET /documents | `list[DocumentResponse]` | A.SAFE | Same schema |
| POST /documents/{id}/parse | `ParseResponse` | A.SAFE | Explicit dict construction; document_id, report_id, parsed_items only |
| PUT /documents/{id}/confirm | `DocumentResponse` | A.SAFE | |
| POST /documents/{id}/confirm | `DocumentResponse` | A.SAFE | |
| GET /documents/{id}/parsed-items | `list[ParsedItemResponse]` | A.SAFE | Explicit construction; no user_id, no report_id, no storage |
| PATCH /documents/{id}/parsed-items/{item_id} | `ParsedItemResponse` | A.SAFE | Explicit construction |
| GET /documents/lab-history | `list[dict]` (untyped) | B.PARTIAL | Explicit dict: metric, report_date, document_id, document_name, value, unit, is_abnormal, reference_range — no user_id/storage |

### Risk Alerts (`api/risk_alerts.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /risk-alerts | `list[RiskAlertResponse]` | A.SAFE | user_id not in schema; from_attributes=True only serializes declared fields |
| POST /risk-alerts/recalculate | `list[RiskAlertResponse]` | A.SAFE | response_model enforces schema; risk-engine str-UUID bug exists but does not affect response safety |
| POST /risk-alerts/monitor | `list[RiskAlertResponse]` | A.SAFE | response_model enforces schema |
| GET /risk-alerts/unread-count | `{'count': N}` (untyped) | B.PARTIAL | Explicit dict; only 'count' key — no user_id |
| POST /risk-alerts/{id}/dismiss | `{'ok': True}` (untyped) | B.PARTIAL | Explicit dict; only 'ok' key — no user_id |

---

## Schema Audit

### `DocumentResponse`

```python
class DocumentResponse(BaseModel):
    id: UUID
    category: str
    subject_profile_id: Optional[UUID]
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    parse_status: str
    confirmed_data: Optional[dict]
    confirmed_at: Optional[datetime]
    uploaded_at: datetime
```

- `storage_bucket`, `storage_key`, `user_id` **NOT declared** → ORM serialization (`from_attributes=True`) does not expose them ✅
- P32 already removed these fields

### `ParsedItemResponse`

```python
class ParsedItemResponse(BaseModel):
    id: UUID
    item_name: str
    value_num: Optional[float]
    value_text: Optional[str]
    unit: Optional[str]
    ref_range: Optional[str]
    abnormal_flag: Optional[str]
    parser_confidence: Optional[float]
    is_abnormal: bool
```

- No `user_id`, no `report_id`, no storage fields ✅

### `RiskAlertResponse`

```python
class RiskAlertResponse(BaseModel):
    id: UUID
    risk_type: Optional[str]
    source_type: str
    source_id: Optional[UUID]
    rule_code: str
    severity: str
    title: str
    message: str
    description: Optional[str]
    recommendation: Optional[str]
    status: str
    resolved_at: Optional[datetime]
    created_at: datetime
```

- `user_id` **NOT declared** → ORM serialization does not expose it ✅
- `rule_code` (e.g., `BP_HIGH`) and `source_id` are health-logic identifiers, not system secrets — intentional exposure, A.SAFE
- `subject_profile_id` is the person-level identifier (not user-level), intentionally exposed

---

## ORM Internal Fields Verified Not in Responses

| ORM Model | Internal Fields | Status |
|-----------|----------------|--------|
| `MedicalDocument` | `storage_bucket`, `storage_key`, `user_id` | Not in `DocumentResponse` ✅ |
| `LabReport` | `user_id`, `raw_text` | Not in any response schema ✅ |
| `LabReportItem` | `report_id`, `item_code`, `range_source`, `ref_low`, `ref_high` | Not in `ParsedItemResponse` ✅ |
| `RiskAlert` | `user_id` | Not in `RiskAlertResponse` ✅ |

---

## Findings

**No C.GAP found.**

All schema-based routes properly exclude sensitive fields. The three untyped
routes (`lab-history`, `unread-count`, `dismiss`) use explicit dict construction
with safe, minimal content — classified as B.PARTIAL pending typed `response_model`
migration (deferred to a future hardening pass).

### Pre-existing issue noted (not in scope)

`POST /risk-alerts/recalculate` calls `evaluate_metric_risks(str(current_user.id), ...)`
which passes a string into a `UUID(as_uuid=True)` ORM column. This causes
`StatementError: 'str' object has no attribute 'hex'` on SQLite test environments.
**This is a data-integrity bug, not a security exposure** — the response schema still
enforces `RiskAlertResponse` (no user_id). Tracked separately.

---

## Tests Added

**File**: `backend/tests/test_lab_alerts_response_leakage.py`  
**Count**: 12 tests, 12/12 PASS

| Class | Test | Coverage |
|-------|------|----------|
| `TestDocumentResponseLeakage` | `test_list_documents_no_storage_fields` | GET /documents → storage fields absent |
| | `test_list_documents_no_user_id` | GET /documents → user_id absent |
| | `test_list_documents_no_sensitive_keys` | GET /documents → recursive scan |
| | `test_parsed_items_no_sensitive_keys` | GET parsed-items → recursive scan |
| | `test_parsed_items_no_user_id` | GET parsed-items → user_id/report_id absent |
| | `test_lab_history_no_sensitive_keys` | GET lab-history → recursive scan on explicit dict |
| `TestRiskAlertResponseLeakage` | `test_list_alerts_no_user_id` | GET /risk-alerts → user_id absent |
| | `test_list_alerts_no_sensitive_keys` | GET /risk-alerts → recursive scan |
| | `test_unread_count_shape` | GET unread-count → {'count': N} shape, no user_id |
| | `test_dismiss_alert_shape` | POST dismiss → {'ok': True} shape, no user_id |
| `TestCrossUserLabAlertsIsolation` | `test_cross_user_documents_404` | Foreign person_id → 404 on /documents |
| | `test_cross_user_risk_alerts_404` | Foreign person_id → 404 on /risk-alerts |

---

## Commits

| Hash | Description |
|------|-------------|
| `e4929a8` | `test(security): add lab/risk response leakage regression (P36)` |
| *(this commit)* | `docs(report): P36 lab risk response audit report` |

---

## Final Classification

```
P36_LAB_RISK_SMOKE_VERIFIED
- No C.GAP found
- Regression tests added for all B.PARTIAL untyped routes
- runtime-smoke: 113 passed, 2 skipped (all 4 stages green)
```

---

## Next: P37 — Health Score & AI Summary Response Audit

**Target files:**
- `backend/app/api/` — health_score/ai_summary routes
- `backend/app/schemas/` — HealthScoreResponse, AISummaryResponse

**Known concern:**
- `AISummary` ORM (entities.py line ~204) has `user_id = Column(UUID(as_uuid=True), ...)`
- Must verify `user_id` is NOT declared in any AI summary or health score response schema
- Route check: if any route returns ORM object with `from_attributes=True` and schema declares `user_id` → C.GAP

**Pre-flight command:**
```bash
grep -n "user_id" backend/app/schemas/health_score.py backend/app/schemas/ai_summary.py 2>/dev/null
```
