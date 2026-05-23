# P37 — AI Summary & Health Score API Response Audit

**Date**: 2026-05-24  
**Branch**: main  
**Base commit**: c454361 (P36 active task report update)  
**Outcome**: `P37_AI_HEALTH_SMOKE_VERIFIED` — no C.GAP found  
**Tests**: 13 added, 13/13 PASS  
**Runtime-smoke**: 113 passed, 2 skipped (all stages green)

---

## Scope

Audit of all AI summary, health score, and AI module API routes and response
schemas to verify that user_id and any sensitive/internal fields are not
exposed to client responses.

Files audited:
- `backend/app/api/ai_summary.py` — 2 routes
- `backend/app/api/health_score.py` — 3 routes
- `backend/app/api/ai_modules.py` — 4 routes
- `backend/app/schemas/ai_summary.py`
- `backend/app/schemas/health_score.py`
- `backend/app/schemas/health_analysis.py`
- `backend/app/schemas/trend_analysis.py`
- `backend/app/schemas/ai_modules.py`
- `backend/app/services/ai_service.py` (narrative_json content)
- `backend/app/services/health_ai_engine/health_score_engine.py` (score_detail assembly)
- `backend/app/models/entities.py` — ORM reference (AISummary, HealthScore)

---

## Route Inventory & Classification

### AI Summary (`api/ai_summary.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /ai-summary/generate | `AISummaryResponse` | A.SAFE | user_id in ORM, NOT in schema; from_attributes only serializes declared fields |
| GET /ai-summary | `list[AISummaryResponse]` | A.SAFE | same schema |

### Health Score (`api/health_score.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /health-score/calculate | `HealthScoreResponse` | A.SAFE | user_id in ORM, NOT in schema; score_detail content verified safe |
| GET /health-score/latest | `Optional[HealthScoreResponse]` | A.SAFE | cache_get returns None in test env; DB query falls through; same schema |
| GET /health-score/history | `list[HealthScoreResponse]` | A.SAFE | same schema |

### AI Modules (`api/ai_modules.py`)

| Route | Response Type | Classification | Notes |
|-------|---------------|----------------|-------|
| POST /ai-modules/health-check-interpretation | `AIModuleResponse` | A.SAFE | no ORM; pure structured AI output; user_id only used internally for DB queries |
| POST /ai-modules/symptom-analysis | `AIModuleResponse` | A.SAFE | same |
| POST /ai-modules/risk-prediction | `AIModuleResponse` | A.SAFE | same |
| POST /ai-modules/evaluate/{module_name} | `AIModuleEvaluationResponse` | A.SAFE | explicit typed construction; `AIModuleEvaluationResponse(module=module_name, **evaluation)` |

---

## Schema Audit

### `AISummaryResponse`

```python
class AISummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    period_start: Optional[date]
    period_end: Optional[date]
    summary_text: str
    abnormal_explanation: Optional[str]
    recommendations: Optional[str]
    disclaimer: str
    model_name: Optional[str]
    narrative_json: Optional[dict[str, Any]] = None
    narrative_version: Optional[str] = None
    summary_type: Optional[str] = None
    generated_at: Optional[datetime] = None
    based_on_score_id: Optional[UUID] = None
    based_on_alert_snapshot: Optional[str] = None
    created_at: datetime
```

- `user_id` NOT declared → `from_attributes=True` does not serialize it ✅
- `subject_profile_id` NOT declared → not exposed ✅
- `narrative_json`: JSON blob from `generate_health_summary()` which returns only `summary_text/disclaimer/model_name/recommendations/abnormal_explanation/period_start/period_end` — no user_id embedded ✅
- `based_on_alert_snapshot`: 64-char snapshot ID (hash), not a sensitive field ✅

### `HealthScoreResponse`

```python
class HealthScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_period_days: int
    overall_score: int
    cardiovascular_score: int
    metabolic_score: int
    weight_score: int
    sleep_score: int
    score_detail: Optional[dict[str, Any]]
    calculated_at: datetime
```

- `user_id` NOT declared → not serialized ✅
- `subject_profile_id` NOT declared → not exposed ✅
- `score_detail` content (from `health_score_engine.py`):
  - `cardiovascular`: `{score, avg_systolic, avg_diastolic}` — health metrics only
  - `metabolic`: `{score, avg_glucose, latest_lipids, alt_above_ref}` — health metrics only
  - `weight`: `{score, latest_weight, bmi}` — health metrics only
  - `activity`: `{score, avg_sleep_hours, avg_steps}` — health metrics only
  - `rule_penalties`, `applied_rules` — scoring metadata only
  - **No user_id, no storage fields in any sub-dict** ✅

### `AIModuleResponse`

```python
class AIModuleResponse(BaseModel):
    module: str
    model_name: str
    generated_at: datetime
    health_risks: list[AIHealthRisk]
    lifestyle_recommendations: list[AIRecommendation]
    follow_up_items: list[AIFollowUpItem]
    confidence: float
    guardrail_report: AIGuardrailReport
    disclaimer: str
```

- No ORM backing; no `user_id` declared → A.SAFE ✅
- `user_id` parameter in `run_ai_module()` is used only for DB queries (not reflected in response) ✅
- Sub-models (`AIHealthRisk`, `AIRecommendation`, `AIFollowUpItem`) contain: `title`, `level/action/priority/item/timeline`, `reason/why`, `evidence_ids` — no user_id ✅

### `AIModuleEvaluationResponse`

```python
class AIModuleEvaluationResponse(BaseModel):
    module: str
    format_valid: bool
    grounded_ratio: float
    safety_pass: bool
    actionability_score: float
    overall_score: float
```

- No ORM backing; no `user_id` → A.SAFE ✅

### Supporting Schemas (via health_assistant — covered P33)

- `HealthAnalysisResponse`: `person_id`, `analyzed_at`, `data_sufficient`, health arrays, `recommendations`, `disclaimer` — no user_id ✅
- `TrendsAnalysisResponse`: `period_days`, `summaries: list[TrendSummary]` — no user_id ✅

---

## ORM Internal Fields Verified Not in Responses

| ORM Model | Internal Fields | Status |
|-----------|----------------|--------|
| `AISummary` | `user_id` | Not in `AISummaryResponse` ✅ |
| `HealthScore` | `user_id` | Not in `HealthScoreResponse` ✅ |

---

## Findings

**No C.GAP found.**

Both `AISummary` and `HealthScore` ORM models have `user_id = Column(UUID(as_uuid=True), nullable=False)`. The corresponding response schemas (`AISummaryResponse`, `HealthScoreResponse`) do NOT declare `user_id`. Because `from_attributes=True` only serializes fields explicitly declared in the Pydantic schema, the ORM `user_id` column is silently excluded from every API response.

The `narrative_json` and `score_detail` dynamic dict fields contain only AI-generated health content and scoring metrics — no user_id, storage paths, or secrets are embedded by the service layer.

AI module routes pass `user_id=str(current_user.id)` into `run_ai_module()` for internal DB queries only. The parameter does not propagate into `AIModuleResponse` or `AIModuleEvaluationResponse`.

---

## Tests Added

**File**: `backend/tests/test_ai_health_response_leakage.py`  
**Count**: 13 tests, 13/13 PASS

| Class | Test | Coverage |
|-------|------|----------|
| `TestAISummaryResponseLeakage` | `test_generate_summary_no_user_id` | POST /ai-summary/generate → user_id absent |
| | `test_generate_summary_no_sensitive_keys` | POST /ai-summary/generate → recursive scan |
| | `test_list_summary_no_user_id` | GET /ai-summary → user_id absent |
| | `test_list_summary_no_sensitive_keys` | GET /ai-summary → recursive scan |
| | `test_generate_summary_field_contract` | Public fields present; user_id/subject_profile_id absent |
| `TestHealthScoreResponseLeakage` | `test_calculate_score_no_user_id` | POST /health-score/calculate → user_id absent |
| | `test_calculate_score_no_sensitive_keys` | POST calculate → recursive scan (includes score_detail) |
| | `test_latest_score_no_user_id` | GET /health-score/latest → user_id absent |
| | `test_latest_score_no_sensitive_keys` | GET latest → recursive scan (includes score_detail) |
| | `test_history_score_no_user_id` | GET /health-score/history → user_id absent |
| | `test_history_score_no_sensitive_keys` | GET history → recursive scan |
| `TestCrossUserAIHealthIsolation` | `test_cross_user_ai_summary_404` | Foreign person_id → 404 on /ai-summary |
| | `test_cross_user_health_score_404` | Foreign person_id → 404 on /health-score/latest |

---

## Commits

| Hash | Description |
|------|-------------|
| `6987495` | `test(security): add AI/health response leakage regression (P37)` |
| *(this commit)* | `docs(report): P37 AI health response audit report` |

---

## Final Classification

```
P37_AI_HEALTH_SMOKE_VERIFIED
- No C.GAP found
- Regression tests added for all P37 routes
- runtime-smoke: 113 passed, 2 skipped (all 4 stages green)
```

---

## Next: P38 — Remaining API Surface Final Audit

**Goal**: Check any API files not yet covered by P32–P37.

**Pre-flight command**:
```bash
find backend/app/api -maxdepth 1 -type f -name "*.py" | sort
```

**Known covered surfaces** (P32–P37):
- documents, risk_alerts, health_assistant, dashboard, metrics, symptoms, ai_summary, health_score, ai_modules

**Likely remaining**:
- `notifications.py` / `recommendations.py` — if present
- `person_profiles.py` / `user.py` / `admin.py` — profile/user endpoints
- `action_plans.py` / `insights.py` — if present
- Any untyped dict responses in remaining routes

**Pre-flight scan**:
```bash
grep -n "user_id\|password_hash\|storage_key" backend/app/api/*.py 2>/dev/null | grep -v "filter\|==\|\.id\)" | head -50
```
