# P38 — Remaining API Surface Response Audit

**Date**: 2026-05-24  
**Branch**: main  
**Base commit**: 2bd9028 (P37 docs)  
**Outcome**: `P38_REMAINING_API_SURFACE_FIXED` — 3 C.GAPs found and fixed  
**Tests**: 14 added, 14/14 PASS  
**Runtime-smoke**: 113 passed, 2 skipped (all stages green)

---

## Scope

Final audit of all remaining API route files not covered by P32–P37.

P32–P37 covered: documents, health_assistant, dashboard, metrics, symptoms, risk_alerts, ai_summary, health_score, ai_modules

P38 covers: actions, analytics, auth, external_metrics, insights, persons, profile, reports, timeline

---

## Route Inventory & Classification

### Auth (`api/auth.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /auth/register | `UserResponse` | A.SAFE | Only `id`, `email` — no `password_hash` in schema |
| POST /auth/login | `TokenResponse` | A.SAFE | Only `access_token`, `token_type` |
| POST /auth/change-password | `{'status': 'ok'}` | A.SAFE | Plain status dict; no sensitive fields |

`UserResponse` schema:
```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
```
`password_hash` in ORM but NOT in `UserResponse` → from_attributes excludes it ✅

### Profile (`api/profile.py`) — **C.GAP FOUND & FIXED**

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /profile/me | `ProfileResponse` | **C.GAP → FIXED** | `user_id` was declared in schema AND injected in dict; removed both |
| PUT /profile/me | `ProfileResponse` | **C.GAP → FIXED** | same fix |
| GET /profile/account | `AccountResponse` | A.SAFE | Only `id`, `email`, `account_settings` |
| PUT /profile/account | `AccountResponse` | A.SAFE | same |

**Before fix** (`ProfileResponse`):
```python
class ProfileResponse(ProfileUpsertRequest):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID    # ← C.GAP: unnecessary exposure of user's own UUID
```

**After fix**:
```python
class ProfileResponse(ProfileUpsertRequest):
    model_config = ConfigDict(from_attributes=True)
    id: UUID         # ← user_id removed
```

Also removed from `profile.py` route dicts:
- Line 15: `'user_id': target_person.owner_user_id` → removed
- Line 47: `'user_id': current_user.id` → removed

### Persons (`api/persons.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /persons | `list[PersonResponse]` | A.SAFE | `owner_user_id` = P33 intentional design for multi-person management |
| POST /persons | `PersonResponse` | A.SAFE | same |
| PUT /persons/{id} | `PersonResponse` | A.SAFE | same |

`PersonResponse.owner_user_id` — same pattern as P33 family relationship `owner_user_id` — intentional design; the client needs to know which user account owns a person profile for family management. Not a C.GAP.

### Analytics (`api/analytics.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /analytics/trends | `TrendsAnalysisResponse` | A.SAFE | Covered in P37: `period_days` + summaries, no user_id |
| GET /analytics/health-analysis | `HealthAnalysisResponse` | A.SAFE | Covered in P33: `person_id: str`, health arrays, no user_id |

### External Metrics (`api/external_metrics.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /external-metrics/sync | `ExternalSyncResponse` | A.SAFE | Only `synced_count`, `source` |
| GET /external-metrics/trends | `ExternalTrendResponse` | A.SAFE | Only `metric`, `points: list[ExternalTrendPoint]` |

Both schemas have no ORM backing, no user_id fields.

### Insights (`api/insights.py`) — **C.GAP FOUND & FIXED**

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /insights | `list[HealthInsightResponse]` | **C.GAP → FIXED** | `user_id` was declared in schema |
| POST /insights/generate | `list[HealthInsightResponse]` | **C.GAP → FIXED** | same fix |
| POST /insights/{id}/dismiss | `HealthInsightResponse` | **C.GAP → FIXED** | same fix |

**Before fix** (`HealthInsightResponse`):
```python
class HealthInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID            # ← C.GAP: ORM user_id column in schema
    subject_profile_id: Optional[UUID] = None
    ...
```

**After fix**:
```python
class HealthInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    subject_profile_id: Optional[UUID] = None   # user_id removed
    ...
```

`subject_profile_id` retained — identifies which person this insight is for (needed for multi-person management). Not a C.GAP (P33 precedent).

### Actions (`api/actions.py`) — **C.GAP FOUND & FIXED**

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /actions | `list[HealthActionRead]` | **C.GAP → FIXED** | `user_id` was declared in schema |
| GET /actions/prioritized | `list[HealthActionRead]` | **C.GAP → FIXED** | same fix |
| POST /actions | `HealthActionRead` | **C.GAP → FIXED** | same fix |
| PATCH /actions/{id} | `HealthActionRead` | **C.GAP → FIXED** | same fix |
| POST /actions/{id}/complete | `HealthActionRead` | **C.GAP → FIXED** | same fix |
| GET /actions/{id}/outcomes | `list` (untyped) | A.SAFE | Manually constructed dict with health metrics only (`metric_type`, `before_value`, `after_value`, `delta`, `outcome_label`, etc.) — no user_id |

**Before fix** (`HealthActionRead`):
```python
class HealthActionRead(BaseModel):
    id: UUID
    user_id: UUID    # ← C.GAP
    person_id: Optional[UUID] = None
    ...
```

**After fix**:
```python
class HealthActionRead(BaseModel):
    id: UUID
    person_id: Optional[UUID] = None  # user_id removed
    ...
```

`person_id` retained — identifies which person this action belongs to (multi-person management). Not a C.GAP.

### Reports (`api/reports.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /reports/generate | `ReportGenerateResponse` | A.SAFE | Only `report_id: str`, `status: str` |
| GET /reports/{id} | `ReportStatusResponse` | A.SAFE | `status: str`, `download_url: Optional[str]` |
| GET /reports/download/{id} | `FileResponse` | A.SAFE | Authenticated file download; validates token + owner |

`download_url` format: `/api/v1/reports/download/{report_id}?token={short_lived_token}` — relative API path, not a filesystem path or storage bucket URL. `file_path` is stored server-side in `_REPORT_STATE`, never exposed in response. A.SAFE.

### Timeline (`api/timeline.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| GET /timeline | `TimelineResponse` | A.SAFE | Items contain only health data |

`TimelineItem.data` dict content verified by tracing `timeline_engine.py`:
- `lab` events: `report_id`, `report_type`, `abnormal_items` — no user_id ✅
- `symptom` events: `symptom`, `severity`, `estimated_start_date`, `estimated_duration_days` ✅
- `metric` events: `systolic_bp`, `diastolic_bp`, `heart_rate`, `blood_glucose`, `weight_kg`, `sleep_hours`, `steps`, `source` ✅
- `insight` events (AI summary): `summary_id`, `model_name`, `narrative_version`, `summary_type`, `delta_summary` ✅
- `insight` events (health): `insight_type`, `severity`, `recommendation` ✅
- `alert` events: `risk_type`, `severity`, `recommendation`, `status` ✅

`metadata` dicts contain only resource UUIDs (not user UUIDs). A.SAFE.

---

## C.GAP Summary

| Schema | Field Removed | Fix Location |
|--------|---------------|--------------|
| `ProfileResponse` | `user_id: UUID` | `app/schemas/profile.py` + `app/api/profile.py` (2 dicts) |
| `HealthInsightResponse` | `user_id: UUID` | `app/schemas/insights.py` |
| `HealthActionRead` | `user_id: UUID` | `app/schemas/actions.py` |

---

## A.SAFE Classifications (No Changes)

| Schema / Route | Classification | Rationale |
|----------------|----------------|-----------|
| `UserResponse` | A.SAFE | `id`, `email` only; `password_hash` in ORM but NOT declared in schema |
| `AccountResponse` | A.SAFE | `id`, `email`, `account_settings`; no `password_hash` |
| `PersonResponse.owner_user_id` | A.SAFE (P33 design) | Intentional multi-person management field |
| `ExternalSyncResponse` | A.SAFE | `synced_count`, `source` only |
| `ExternalTrendResponse` | A.SAFE | `metric`, `points` only (health metrics) |
| `TimelineResponse.data` | A.SAFE | Health metrics only in all event types |
| `ReportStatusResponse.download_url` | A.SAFE | Relative API path; `file_path` kept server-side |
| `/actions/{id}/outcomes` (untyped list) | A.SAFE | Manually constructed dict with health metrics only |
| `TrendsAnalysisResponse` | A.SAFE | Covered by P37 |
| `HealthAnalysisResponse` | A.SAFE | Covered by P33 |

---

## Tests Added

**File**: `backend/tests/test_profile_insights_actions_leakage.py`  
**Count**: 14 tests, 14/14 PASS

| Class | Test | Coverage |
|-------|------|----------|
| `TestProfileResponseLeakage` | `test_get_profile_no_user_id` | GET /profile/me: user_id absent |
| | `test_get_profile_no_sensitive_keys` | GET /profile/me: recursive scan |
| | `test_put_profile_no_user_id` | PUT /profile/me: user_id absent |
| | `test_get_profile_field_contract` | id, full_name present; user_id, password_hash absent |
| | `test_account_no_password_hash` | GET /profile/account: password_hash absent; id, email, account_settings present |
| `TestInsightResponseLeakage` | `test_list_insights_no_user_id` | GET /insights: user_id absent |
| | `test_list_insights_no_sensitive_keys` | GET /insights: recursive scan |
| | `test_dismiss_insight_no_user_id` | POST /insights/{id}/dismiss: user_id absent |
| `TestActionResponseLeakage` | `test_list_actions_no_user_id` | GET /actions: user_id absent |
| | `test_list_actions_no_sensitive_keys` | GET /actions: recursive scan |
| | `test_create_action_no_user_id` | POST /actions: user_id absent |
| | `test_create_action_no_sensitive_keys` | POST /actions: recursive scan |
| `TestCrossUserProfileInsightIsolation` | `test_cross_user_insights_empty` | Foreign person_id → 404 |
| | `test_cross_user_insights_own_visible` | Own person_id → insights returned; no user_id |

---

## Commits

| Hash | Description |
|------|-------------|
| `2338e30` | `fix(security): remove user_id from ProfileResponse, HealthInsightResponse, HealthActionRead (P38)` |
| `c0b4060` | `test(security): add profile/insights/actions response leakage regression (P38)` |
| *(this commit)* | `docs(report): P38 remaining API surface audit report` |

---

## Final Classification

```
P38_REMAINING_API_SURFACE_FIXED
- 3 C.GAPs found and fixed across 3 schemas
- 14 regression tests added, 14/14 PASS
- runtime-smoke: 113 passed, 2 skipped (all 4 stages green)
- All 17 API route files audited (P32–P38 complete)
```

---

## Full Audit Coverage (P32–P38)

| Task | Scope | C.GAPs Fixed | Tests Added |
|------|-------|--------------|-------------|
| P32 | documents.py | 1 (DocumentResponse storage fields) | 12 |
| P33 | health_assistant.py | 0 (family owner_user_id = intentional design) | 15 |
| P34 | dashboard.py | 0 | 16 |
| P35 | metrics.py, symptoms.py | 2 (MetricResponse.user_id, SymptomResponse.user_id) | 15 |
| P36 | risk_alerts.py | 0 | 12 |
| P37 | ai_summary.py, health_score.py, ai_modules.py | 0 | 13 |
| P38 | actions.py, analytics.py, auth.py, external_metrics.py, insights.py, persons.py, profile.py, reports.py, timeline.py | 3 (ProfileResponse, HealthInsightResponse, HealthActionRead) | 14 |
| **Total** | **17 route files** | **6 C.GAPs fixed** | **97 tests** |

---

## Next: P39 — Final Regression Gate & Security Summary

**Goal**: Run the complete test suite and produce a security hardening summary report covering P17–P38.

**Command**:
```bash
cd backend && PYTHONPATH=. python -m pytest -q && make -C .. runtime-smoke
```
