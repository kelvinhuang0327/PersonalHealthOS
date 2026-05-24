# P39 — Security Audit Closure Index

**Date**: 2026-05-24  
**Branch**: main  
**HEAD**: 4c9ffb1  
**Final Classification**: `P39_SECURITY_AUDIT_CLOSURE_INDEX_READY`

---

## 1. Executive Summary

P13–P38 delivered a 26-task security and readiness hardening chain across the PersonalHealthOS backend. This index provides a canonical, single-document closure record for that chain. All 17 API route files have been audited. The runtime smoke gate passes. Six response-schema C.GAPs have been fixed. This document is the authoritative reference for the next agent — no re-auditing of surfaces covered here is required unless a specific commit reintroduces a risk.

**Total hardening delivered (P13–P38):**
- 6 response-schema C.GAPs fixed (user_id leakage from MetricResponse, SymptomResponse, DocumentResponse, ProfileResponse, HealthInsightResponse, HealthActionRead)
- 1 injection C.GAP fixed (filename traversal: `os.path.basename` normalization)
- 1 auth C.GAP fixed (report download requires authenticated owner JWT)
- 1 config C.GAP fixed (insecure JWT secret blocked at startup in production)
- ~197 regression tests added across P13–P38
- 4-stage runtime smoke gate established and passing

---

## 2. Current HEAD and Branch

```
Repo:   /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
Branch: main
HEAD:   4c9ffb1  docs(report): P38 remaining API surface audit report
Status: clean (no uncommitted files)
```

---

## 3. Smoke Gates

### runtime-smoke (4 stages)

| Stage | Target | Coverage | Result |
|-------|--------|----------|--------|
| 1 — Health | `tests/test_runtime_smoke.py` | `/health`, `/api/v1/health` contract | 3 passed ✅ |
| 2 — Security | `make security-smoke` | Auth audit (29 tests) + frontend tsc | 29 passed, 2 skipped ✅ |
| 3 — Config | `make config-smoke` | P28/P29/P43 secret guard + startup warnings (29 tests) | 29 passed ✅ |
| 4 — Validation | `make validation-smoke` | P23/P24/P27/P30 schema/injection (57 tests) | 57 passed ✅ |
| **Total** | | | **118 passed, 2 skipped** ✅ *(P46 update 2026-05-24: +5 P43 startup warning tests)* |

Stage 2 skips: frontend tsc skipped if Node.js/tsc unavailable (pre-existing behavior, not a regression).

---

## 4. P13–P38 Closure Table

### Classification Legend
- **A. CLOSED** — tests and smoke coverage exist; no remaining gap
- **B. CLOSED_WITH_ACCEPTED_GAP** — gap intentionally documented; residual risk acknowledged
- **C. DOCS_ONLY** — no code change; governance/process output only
- **D. INFRA** — CI/Makefile/entrypoint hardening; no application logic changed

| Task | Final Classification | Surface | Status | Evidence |
|------|----------------------|---------|--------|----------|
| P13 | `P13_AUTH_E2E_ENTRYPOINT_HARDENED` | Real-JWT cross-user API negative smoke; backend-smoke Makefile target | **A. CLOSED** | `test_auth_negative_smoke.py`, `test_real_token_auth_negative.py` (10 backend tests); commits `0a73f1a`, `eeadbf7` |
| P14 | `P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED` | Browser (Playwright) API-level auth isolation fixture | **A. CLOSED** | `auth-negative.spec.ts` (3 Playwright tests); commits `78afae7`, `8af3262` |
| P15 | `P15_REAL_JWT_STORAGESTATE_UI_NEGATIVE_SMOKE_VERIFIED` | Full UI cross-user smoke with storageState + CORS bridge | **A. CLOSED** | `auth-ui-negative.spec.ts` (1 test adds to suite); commits `d2aea8c`, `78c1e40` |
| P16 | `P16_FULL_UI_AUTH_NEGATIVE_SMOKE_VERIFIED` | Multi-browser simultaneous session isolation | **A. CLOSED** | P16 ×2 tests (total 6 e2e: P14×3 + P15×1 + P16×2); commits `d59c11c`, `5d652cc` |
| P17 | `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED` | All 20+ FastAPI endpoints: `get_target_person` ownership gate audit | **A. CLOSED** | `test_person_id_authorization_audit.py` (10 tests, 2 skipped SQLite); commit `d28e13e` |
| P18 | `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP` | Report status endpoint bound to owner; download-token gap surfaced | **B. CLOSED_WITH_ACCEPTED_GAP** | `test_report_authorization_hardening.py` (8 tests); commits `6902492`, `30cba72`. Gap: download URL token leakable via browser history — mitigated by UUID entropy + 1hr expiry; addressed in P20 |
| P19 | `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP` | Report download frontend contract gap documented | **C. DOCS_ONLY** | Gap documented in P18; frontend fix in P20; commit `b37cab2` |
| P20 | `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED` | Report download requires authenticated owner JWT (frontend + backend) | **A. CLOSED** | `test_report_authorization.py` (owner regression); commits `0be0368`, `4c33e35`, `15102e1` |
| P21 | `P21_SECURITY_SMOKE_AND_CI_READY` | CI entrypoint: canonical `backend-auth-audit` make target | **D. INFRA** | `make backend-auth-audit` (4 test files, 31 collected); commits `ae0cf5c`, `69badf4` |
| P22 | `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY` | Frontend e2e CI: avoids live-backend dependency | **B. CLOSED_WITH_ACCEPTED_GAP** | CI uses API request only (not full browser); commits `9dabb8d`, `8364858`. Gap: browser e2e auth smoke requires live backend — not run in CI frontend job |
| P23 | `P23_INPUT_VALIDATION_HARDENED` | Pydantic schema input constraint hardening across 5+ schemas | **A. CLOSED** | `test_input_validation_hardening.py` (19 tests); commits `dd8ddb0`, `0a0e116`; included in validation-smoke |
| P24 | `P24_BOUNDARY_INPUT_VALIDATION_HARDENED` | Numeric boundary constraints (min/max) on health inputs | **A. CLOSED** | `test_input_validation_boundary.py` (11 tests); commits `07f8a7c`, `61a8c86`; included in validation-smoke |
| P25 | `P25_RUNTIME_HEALTH_ENDPOINT_HARDENED` | Health endpoint contract smoke; runtime-smoke Makefile target | **A. CLOSED** | `test_runtime_smoke.py` (3 tests = stage 1 of runtime-smoke); commits `f09a530`, `a5a8d6d` |
| P26 | `P26_RATE_LIMIT_SMOKE_VERIFIED` | Rate-limit smoke: opt-in per-route enforcement verified | **B. CLOSED_WITH_ACCEPTED_GAP** | `test_rate_limit_smoke.py`; commits `d3f73f5`. Gaps: (1) in-memory limiter not shared across multiple worker processes; (2) opt-in per-route vs global enforcement — see §7 |
| P27 | `P27_INJECTION_HARDENED` | Injection surface audit: filename traversal, SQL, command | **A. CLOSED** | `test_injection_smoke.py` (7 tests); fix: `os.path.basename` normalization on upload; commits `43912e8`, `f2a2209`; included in validation-smoke |
| P28 | `P28_PRODUCTION_SECRET_GUARD_HARDENED` | Insecure JWT secret blocked at startup in production env | **A. CLOSED** | `test_config_security_guard.py` (15 tests); commits `67e8681`, `b0a0a23`; included in config-smoke |
| P29 | `P29_PRODUCTION_CONFIG_RUNTIME_SMOKE_READY` | Config-smoke Makefile target; startup integration tests | **A. CLOSED** | `test_runtime_config_startup_guard.py` (9 tests); commits `d7aab81`, `954b62a`; included in config-smoke (stage 3: 24 total) |
| P30 | `P30_SCHEMA_VALIDATION_HARDENED` | Remaining schema boundary constraints (persons, metrics, actions, health-assistant) | **A. CLOSED** | `test_schema_validation_p30.py` (20 tests: 7+2+2+5+4); commits `43a318a`, `716a618`; included in validation-smoke |
| P31 | `P31_RUNTIME_SMOKE_VALIDATION_GATE_READY` | Validation-smoke added as stage 4 of runtime-smoke | **D. INFRA** | Makefile consolidation; commits `75214b8`. Gate now covers P23/P24/P27/P30 atomically |
| P32 | `P32_RESPONSE_LEAKAGE_HARDENED` | `DocumentResponse`: `storage_bucket`, `storage_key` removed | **A. CLOSED** | `test_response_leakage.py` (12 tests); commits `7e08118`, `b6875ab` |
| P33 | `P33_HEALTH_ASSISTANT_SMOKE_VERIFIED` | `health_assistant.py`: 6 untyped routes audited; `owner_user_id` = intentional design | **A. CLOSED** | `test_health_assistant_leakage.py` (15 tests); commit `967fe18` |
| P34 | `P34_DASHBOARD_SMOKE_VERIFIED` | `dashboard.py`: 3 routes (overview, trends, v2) — all A.SAFE | **A. CLOSED** | `test_dashboard_response_leakage.py` (16 tests); commits `3d410d8` |
| P35 | `P35_METRICS_SYMPTOMS_LEAKAGE_HARDENED` | `MetricResponse.user_id`, `SymptomResponse.user_id` removed | **A. CLOSED** | `test_metrics_symptoms_response_leakage.py` (15 tests); commits `8b22a5f`, `30ac9d7` |
| P36 | `P36_LAB_RISK_SMOKE_VERIFIED` | `risk_alerts.py`, `lab_results.py`: all A.SAFE (no C.GAP) | **A. CLOSED** | `test_lab_risk_response_leakage.py` (12 tests); commits `e4929a8` |
| P37 | `P37_AI_HEALTH_SMOKE_VERIFIED` | `ai_summary.py`, `health_score.py`, `ai_modules.py`: all A.SAFE | **A. CLOSED** | `test_ai_health_response_leakage.py` (13 tests); commits `6987495` |
| P38 | `P38_REMAINING_API_SURFACE_FIXED` | 9 remaining routes: 3 C.GAPs fixed; 8 A.SAFE classified | **A. CLOSED** | `test_profile_insights_actions_leakage.py` (14 tests); commits `2338e30`, `c0b4060` |

---

## 5. C.GAP Fixes Table

### 5a. Response Leakage Fixes (P32–P38)

| Task | Schema | Field Removed | Route(s) Affected | Fix Commit |
|------|--------|---------------|-------------------|------------|
| P32 | `DocumentResponse` | `storage_bucket: str`, `storage_key: str` | GET /documents, GET /documents/{id} | `7e08118` |
| P35 | `MetricResponse` | `user_id: UUID` | GET /metrics, POST /metrics, GET /metrics/{id} | `8b22a5f` |
| P35 | `SymptomResponse` | `user_id: UUID` | GET /symptoms, POST /symptoms | `8b22a5f` |
| P38 | `ProfileResponse` | `user_id: UUID` | GET /profile/me, PUT /profile/me (schema + dict) | `2338e30` |
| P38 | `HealthInsightResponse` | `user_id: UUID` | GET /insights, POST /insights/generate, POST /insights/{id}/dismiss | `2338e30` |
| P38 | `HealthActionRead` | `user_id: UUID` | GET /actions, GET /actions/prioritized, POST /actions, PATCH /actions/{id}, POST /actions/{id}/complete | `2338e30` |

### 5b. Auth / Authorization Fixes

| Task | Fix | Location | Commit |
|------|-----|----------|--------|
| P18 | Report status endpoint bound to `owner_user_id` | `backend/app/api/reports.py` | `6902492` |
| P20 | Report download requires authenticated owner JWT (frontend + backend) | `backend/app/api/reports.py`, `frontend/` | `0be0368`, `4c33e35` |

### 5c. Config / Secrets Fixes

| Task | Fix | Location | Commit |
|------|-----|----------|--------|
| P28 | Insecure JWT secret (`secret` or `change-me` in production) blocked at startup | `backend/app/config/security.py` | `67e8681` |

### 5d. Injection Fixes

| Task | Fix | Location | Commit |
|------|-----|----------|--------|
| P27 | Uploaded filename normalized to `os.path.basename` before DB storage | `backend/app/api/documents.py` | `43912e8` |

### 5e. Validation Fixes (P23/P24/P30)

| Task | Fix | Schemas Hardened | Commits |
|------|-----|------------------|---------|
| P23 | Pydantic field constraints (min_length, max_length, ge, le, pattern) | Auth (password), Metrics, Symptoms, Persons | `dd8ddb0` |
| P24 | Numeric boundary constraints (min/max) on health inputs | HealthMetric, SymptomLog, HealthAction | `07f8a7c` |
| P30 | Remaining boundary constraints: persons, metric notes, passwords, action confidence, health-assistant inline schemas | PersonProfile, HealthMetric, HealthAction, inline request schemas | `43a318a` |

---

## 6. Test Inventory

### 6a. Backend Auth/Security Tests (included in `backend-auth-audit` / `security-smoke`)

| File | Task Origin | Tests | Coverage |
|------|-------------|-------|----------|
| `test_auth_negative_smoke.py` | P13 | ~7 | Backend auth smoke; cross-user API negative |
| `test_real_token_auth_negative.py` | P13 | ~7 | Real JWT decode; `create_access_token` + `get_target_person` override |
| `test_person_id_authorization_audit.py` | P17 | 10 (2 skip) | 8 GET endpoints cross-user → 404; 2 positive sanity |
| `test_report_authorization_hardening.py` | P18/P20 | 8+ | Report status owner binding; cross-user 404; download token flows |

### 6b. Response Leakage Tests (P32–P38)

| File | Task | Tests | Schema Coverage |
|------|------|-------|-----------------|
| `test_response_leakage.py` | P32 | 12 | DocumentResponse, auth, report |
| `test_health_assistant_leakage.py` | P33 | 15 | 6 health-assistant routes (family + dynamic) |
| `test_dashboard_response_leakage.py` | P34 | 16 | DashboardOverview, DashboardTrends, DashboardOverviewV2 |
| `test_metrics_symptoms_response_leakage.py` | P35 | 15 | MetricResponse, SymptomResponse |
| `test_lab_risk_response_leakage.py` | P36 | 12 | LabResult, RiskAlert routes |
| `test_ai_health_response_leakage.py` | P37 | 13 | AISummaryResponse, HealthScoreResponse |
| `test_profile_insights_actions_leakage.py` | P38 | 14 | ProfileResponse, HealthInsightResponse, HealthActionRead, AccountResponse |
| **Subtotal** | P32–P38 | **97** | All 17 API route files |

### 6c. Validation-Smoke Tests (stage 4 of runtime-smoke)

| File | Task | Tests | Coverage |
|------|------|-------|----------|
| `test_input_validation_hardening.py` | P23 | 19 | Password, metric, symptom, person constraints |
| `test_input_validation_boundary.py` | P24 | 11 | Numeric boundary rejection |
| `test_injection_smoke.py` | P27 | 7 | Filename traversal, SQL-injection probe, command-injection probe |
| `test_schema_validation_p30.py` | P30 | 20 | Person field constraints, metric note, password change, action confidence, health-assistant inline |
| **Subtotal** | | **57** | All validation-smoke |

### 6d. Config-Smoke Tests (stage 3 of runtime-smoke)

| File | Task | Tests | Coverage |
|------|------|-------|----------|
| `test_config_security_guard.py` | P28 | 15 | `validate_production_secrets()` unit coverage |
| `test_runtime_config_startup_guard.py` | P29/P43 | 14 | `startup_event()` integration; env-var resolution; startup security warning emission |
| **Subtotal** | | **29** | All config-smoke *(P46 update: +5 P43 tests)* |

### 6e. Runtime Health Tests (stage 1 of runtime-smoke)

| File | Task | Tests | Coverage |
|------|------|-------|----------|
| `test_runtime_smoke.py` | P25 | 3 | `/health`, `/api/v1/health` contract; response shape |

### 6f. E2E Browser Auth Tests (Playwright — not in runtime-smoke)

| File | Task | Tests | Coverage |
|------|------|-------|----------|
| `auth-negative.spec.ts` | P14 | 3 | Playwright API cross-user auth negative |
| `auth-ui-negative.spec.ts` | P15/P16 | 3 | Full UI storageState; multi-browser session isolation |
| **Subtotal** | | **6** | Browser auth isolation |

### Total Tests Added P13–P38

| Category | Count |
|----------|-------|
| Backend auth/auth-audit | ~32 |
| Response leakage (P32–P38) | 97 |
| Validation-smoke | 57 |
| Config-smoke | 24 |
| Runtime health | 3 |
| E2E browser auth | 6 |
| **Grand total** | **~219** |

---

## 7. Accepted Remaining Risks

These risks are intentionally documented and accepted. They should be revisited before production scale-out.

### R1 — Rate Limiter: In-Memory, Not Multi-Worker Shared
**Task**: P26  
**Risk**: The `slowapi` rate limiter stores counters in process memory. With multiple Uvicorn workers (`--workers N`), each worker has an independent counter — effective rate limit is `N × configured_limit` in practice.  
**Mitigation in place**: Current deployment runs single-worker. Documented.  
**Required before**: multi-worker or load-balanced production deployment  
**Fix**: Replace with Redis-backed limiter (e.g. `slowapi` + Redis storage, or `fastapi-limiter` with Redis backend)

### R2 — Rate Limit: Opt-In Per Route, Not Globally Enforced
**Task**: P26  
**Risk**: Rate limiting requires explicit `@limiter.limit()` decorator on each route. New routes can be added without limits silently.  
**Mitigation in place**: Existing protected routes covered. Code review is the current guard.  
**Required before**: production with auth endpoints exposed to internet  
**Fix**: Global default limiter middleware or CI lint rule requiring `@limiter.limit` on all POST/PUT/PATCH auth-adjacent routes

### R3 — AI Prompt Injection: Structural Governance Deferred
**Task**: P27  
**Risk**: User-controlled health narrative text flows into AI prompt templates via `health_summary_system_prompt.md` and related prompts. Structural guardrails (input sanitization, output validation, prompt sandboxing) were inventoried but not implemented.  
**Mitigation in place**: `hallucination_guardrail_policy.md` exists. No direct code execution path from user input.  
**Required before**: AI features exposed to untrusted/multi-tenant production traffic  
**Fix**: P43 — implement structured prompt input validation, output schema validation, and prompt-injection policy enforcement

### R4 — risk_engine.py: str UUID Passed to UUID(as_uuid=True) Column
**Task**: P36 (surfaced), P35 (noted)  
**Risk**: `evaluate_metric_risks(str(current_user.id), ...)` passes `str` to `RiskAlert(user_id=...)` which is a `UUID(as_uuid=True)` SQLAlchemy column. On SQLite, this causes `StatementError: 'str' object has no attribute 'hex'`. On PostgreSQL, this is compatible but is a latent type coercion issue.  
**Current state**: P35/P36 tests mock `evaluate_metric_risks` to return `[]` to isolate response schema tests. Not introduced by any P-task fix.  
**Required before**: Direct (unmocked) risk evaluation in test coverage or SQLite-parity testing  
**Fix**: P41 — change `str(current_user.id)` to `current_user.id` in `risk_engine.py` call site

### R5 — Report Download Token: Leakable via Browser History ✅ MITIGATED (P44+P45)
**Task**: P18 (documented), P20 (JWT added), P44 (audit+tests), P45 (header migration)  
**Risk**: `download_url` includes a short-lived token as a query parameter. Token can appear in browser history, server logs, or network captures.  
**Mitigation in place**:
- Frontend now extracts token from `download_url`, strips it from fetch URL, sends as `X-Report-Download-Token` header.
- Fetch URL received by server: `/api/v1/reports/download/{id}` — no token in URL; not captured by standard access logs.
- Backend accepts header (preferred) or query (backward-compat fallback).
- Invalid header + valid query → 403 (no silent fallback exploitation).

**Status**: MITIGATED as of P45 (2026-05-24). Commits: `97c6096` (backend), `47f0148` (frontend), `51a7ca8` (tests).  
**Remaining**: `download_url` in status response still contains `?token=` — needed for frontend extraction; status endpoint requires owner JWT so this is owner-scoped only. Query token fallback intentionally kept for backward compat.

### R6 — Frontend E2E Auth Tests Require Live Backend (Not in CI)
**Task**: P22  
**Risk**: Playwright browser auth smoke tests (`auth-ui-negative.spec.ts`) require a live backend. They are not run in the frontend CI job.  
**Mitigation in place**: Backend auth audit (`make backend-auth-audit`) covers the same auth logic without browser overhead.  
**Required before**: full CI browser smoke is desired  
**Fix**: Add a backend service dependency to the frontend CI job (with uvicorn startup + env vars)

---

## 8. API Route Coverage (P32–P38 Complete)

| API File | Task | Routes Audited | Outcome |
|----------|------|----------------|---------|
| `documents.py` | P32 | GET /documents, GET /documents/{id}, POST /documents | C.GAP: storage_bucket/key removed |
| `health_assistant.py` | P33 | GET /health-assistant/summary, /family-summary, /conversation, /recommendations, /clinical-labels, /dynamic-response | A.SAFE: owner_user_id = intentional |
| `dashboard.py` | P34 | GET /dashboard/overview, /trends, v2 | A.SAFE |
| `metrics.py` | P35 | GET/POST /metrics, GET /metrics/{id} | C.GAP: MetricResponse.user_id removed |
| `symptoms.py` | P35 | GET/POST /symptoms | C.GAP: SymptomResponse.user_id removed |
| `risk_alerts.py` | P36 | GET /risk-alerts, /unread-count, POST /risk-alerts/{id}/dismiss | A.SAFE |
| `ai_summary.py` | P37 | GET /ai-summary, POST /ai-summary/generate | A.SAFE |
| `health_score.py` | P37 | GET /health-score | A.SAFE |
| `ai_modules.py` | P37 | GET /ai-modules/predictions, /trends-analysis | A.SAFE |
| `auth.py` | P38 | POST /auth/register, /login, /change-password | A.SAFE |
| `profile.py` | P38 | GET/PUT /profile/me, GET/PUT /profile/account | C.GAP: ProfileResponse.user_id removed |
| `persons.py` | P38 | GET/POST/PUT /persons | A.SAFE: owner_user_id = P33 intentional |
| `analytics.py` | P38 | GET /analytics/trends, /health-analysis | A.SAFE (P33/P37 coverage) |
| `external_metrics.py` | P38 | POST /external-metrics/sync, GET /trends | A.SAFE |
| `insights.py` | P38 | GET /insights, POST /generate, POST /{id}/dismiss | C.GAP: HealthInsightResponse.user_id removed |
| `actions.py` | P38 | GET/POST /actions, GET /prioritized, PATCH /{id}, POST /{id}/complete, GET /{id}/outcomes | C.GAP: HealthActionRead.user_id removed |
| `reports.py` | P38 | POST /generate, GET /{id}, GET /download/{id} | A.SAFE (P18/P20 auth bound) |
| `timeline.py` | P38 | GET /timeline | A.SAFE: verified all data dict types |

---

## 9. Recommended Next Tasks

### P40 — PostgreSQL Parity Smoke
**Priority**: HIGH  
**Rationale**: All backend tests run against SQLite in-memory. Several production risks (UUID coercion — R4, connection pooling, migration compatibility) are not covered.  
**Scope**: Docker-compose up with PostgreSQL; run backend test suite against real DB; verify all ORM queries.  
**Pre-requisites**: `docker-compose.local.yml` available; PostgreSQL service defined.

### P41 — risk_engine.py UUID Compatibility Fix
**Priority**: MEDIUM  
**Rationale**: R4 — `str(user.id)` passed to `UUID(as_uuid=True)` column. Causes `StatementError` on SQLite; latent on PostgreSQL.  
**Scope**: Single fix in `risk_engine.py` call site; unmock `evaluate_metric_risks` in affected tests.  
**Allowed**: `backend/app/` (single-line fix); `backend/tests/` (update mocks)

### P42 — Rate-Limit Production Enablement Policy
**Priority**: MEDIUM  
**Rationale**: R1 + R2 — in-memory limiter, opt-in per route. Must be resolved before multi-worker deployment.  
**Scope**: Evaluate Redis-backed limiter; document enforcement policy; optionally add CI lint rule.  
**Pre-requisites**: Redis service in docker-compose.

### P43 — AI Prompt Governance / Prompt-Injection Policy
**Priority**: MEDIUM  
**Rationale**: R3 — user-controlled text flows into AI prompts without structural guardrails.  
**Scope**: Implement input sanitization at AI service boundary; add output schema validation; formalize prompt injection policy in `ai/prompts/`.  
**Pre-requisites**: Define which endpoints accept user-controlled text into prompt templates.

### P44 — Report Download Token Hardening ✅ COMPLETE
**Priority**: LOW  
**Rationale**: R5 — download token in URL query parameter is leakable.  
**Outcome**: P44 added audit + 5 regression tests documenting token policy (no-JWT → 401, cross-user → 404). P45 migrated frontend to send token as `X-Report-Download-Token` header; backend accepts header (preferred) or query (compat). 12 tests in `test_report_download_token_policy.py` (not yet in runtime-smoke — see P46 gap note).  
Commits P44: `e95d151`, `1d64399`, `389b7fa`. Commits P45: `97c6096`, `47f0148`, `51a7ca8`.

---

## 10. Files Produced by P13–P38

### Security Docs
| File | Task |
|------|------|
| `docs/security/P36_LAB_RISK_RESPONSE_AUDIT.md` | P36 |
| `docs/security/P37_AI_HEALTH_RESPONSE_AUDIT.md` | P37 |
| `docs/security/P38_REMAINING_API_SURFACE_AUDIT.md` | P38 |
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | P39 (this file) |

### Key Backend Files Modified
| File | Task | Change |
|------|------|--------|
| `backend/app/schemas/metrics.py` | P35 | Removed `user_id` from `MetricResponse` |
| `backend/app/schemas/symptoms.py` | P35 | Removed `user_id` from `SymptomResponse` |
| `backend/app/schemas/profile.py` | P38 | Removed `user_id` from `ProfileResponse` |
| `backend/app/schemas/insights.py` | P38 | Removed `user_id` from `HealthInsightResponse` |
| `backend/app/schemas/actions.py` | P38 | Removed `user_id` from `HealthActionRead` |
| `backend/app/api/profile.py` | P38 | Removed `user_id` key from GET/PUT /profile/me dicts |
| `backend/app/schemas/documents.py` | P32 | Removed `storage_bucket`, `storage_key` from `DocumentResponse` |
| `backend/app/api/documents.py` | P27 | `os.path.basename` normalization on upload filename |
| `backend/app/api/reports.py` | P18 | Bound report state to `owner_user_id` |
| `backend/app/config/security.py` | P28 | Production startup guard for insecure JWT secret |
| `Makefile` | P25/P26/P29/P31 | `runtime-smoke`, `security-smoke`, `config-smoke`, `validation-smoke`, `backend-auth-audit` targets |

---

## 11. Known Limitations / Inferred / Unknown

| Item | Status | Notes |
|------|--------|-------|
| P36 A.SAFE classifications from `docs/security/P36_LAB_RISK_RESPONSE_AUDIT.md` | VERIFIED via file + tests | 12/12 PASS |
| P13 exact test count split between `test_auth_negative_smoke.py` and `test_real_token_auth_negative.py` | INFERRED (~7 each) | Total `backend-smoke` = 10 (P12+P13); `backend-auth-audit` = 31 collected |
| P20 test file name | INFERRED (git log: `test_report_authorization.py` or merged into P18 file) | Owner regression commit `15102e1` confirmed |
| P19 had no code or test commit — docs only | CONFIRMED by git log | Frontend fix landed in P20 |
| PostgreSQL compatibility of all fixes | UNTESTED | All tests run on SQLite in-memory; P40 recommended |
| Multi-worker rate-limit behavior | UNTESTED | R1 documented; single-worker assumed |

---

## 12. Final Classification

```
P39_SECURITY_AUDIT_CLOSURE_INDEX_READY

- P13–P38 closure index created
- All 17 API route files accounted for
- runtime-smoke: 118 passed, 2 skipped (all 4 stages green) *(P46 update: P43 +5 config-smoke tests)*
- 6 accepted gaps documented (R1–R6); R5 MITIGATED by P44+P45
- HEAD at P39 creation: 4c9ffb1 | HEAD at P46 update: cb6f19b
```

---

## 13. Post-P39 Supplement (P40–P45 Closure)

*Added by P46 governance refresh — 2026-05-24*

| Task | Final Classification | Summary |
|------|----------------------|---------|
| P40 | `P40_RISK_ENGINE_UUID_HYGIENE_PREP` | R4 pre-investigation; risk_engine UUID coercion documented |
| P41 | `P41_RISK_ENGINE_UUID_HYGIENE_HARDENED` | `str(user.id)` → `user.id` fix in risk_engine.py; unmocked UUID tests |
| P42 | `P42_RATE_LIMIT_PRODUCTION_POLICY_READY` | R1+R2 rate-limit production policy + `get_runtime_security_warnings()`; no Redis dep |
| P43 | `P43_STARTUP_SECURITY_WARNINGS_WIRED` | Wired `get_runtime_security_warnings()` into `startup_event()`; +5 config-smoke tests |
| P44 | `P44_REPORT_DOWNLOAD_TOKEN_POLICY_AUDITED` | OPTION A (docs+tests): no-JWT→401, cross-user→404 confirmed; 5 regression tests |
| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED` | Frontend sen| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED` | Frontend sen| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED` | Fronrep| t_download_token_policy.py` (12 tests: 5 P44 + 7 P4| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDEin | P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEonly in the full backend suite (983 passed). Ad| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED` | Frontend sen| P45 | `P45_REPORT_DOWNLOAD_TOKEN_HEAD Count After P45
- **983 passed, 2 skipped** (baseline P39: ~800+; P40–P45 added ~180+ tests)
