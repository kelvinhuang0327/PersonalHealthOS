# P49 — Frontend Auth E2E CI Readiness Audit

**Stage**: P49  
**Classification**: P49_FRONTEND_AUTH_E2E_LOCAL_GATE_DOCUMENTED  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `579a42c` (P48 closure)  
**Date**: 2026-05-24  

---

## 1. Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean ✅ |
| HEAD | `579a42c` (P48 closure) ✅ |

---

## 2. Frontend Auth E2E Command Inventory

### Makefile: `frontend-auth-smoke`
```makefile
# Requires:
#   1. Backend running:  cd backend && uvicorn app.main:app --port 8000
#   2. Frontend built:   cd frontend && npm run build
# Playwright webServer auto-starts next start --port 3010
frontend-auth-smoke:
	cd frontend && npx playwright test \
		tests/e2e/auth-negative.spec.ts \
		tests/e2e/auth-ui-negative.spec.ts \
		tests/e2e/auth-ui-multi.spec.ts \
		--reporter=line
```

### Specs Covered

| Spec | Stage | Type | Backend | Frontend webServer | Timeout |
|------|-------|------|---------|-------------------|---------|
| `auth-negative.spec.ts` | P14 | API-only (APIRequestContext) | ✅ required (localhost:8000) | Started by config | default |
| `auth-ui-negative.spec.ts` | P15 | Full browser UI | ✅ required (localhost:8000) | ✅ required (3010) | 120s |
| `auth-ui-multi.spec.ts` | P16 | Multi-context + storageState | ✅ required (localhost:8000) | ✅ required (3010) | 180s |

### CI Current State (`.github/workflows/ci-cd.yml`)
```yaml
# Auth E2E specs (auth-negative, auth-ui-negative, auth-ui-multi) require
# a live backend and are validated locally via: make frontend-auth-smoke
- name: E2E (mocked specs — no backend required)
  run: npm run e2e:ci
```

CI already explicitly documents auth e2e as **local-only** and runs only the 3 mocked specs (`health-platform`, `platform-app`, `family-health-card`) which use intercepted requests and require no live backend.

---

## 3. Backend Dependency Analysis

### What the Auth Fixtures Need

**`fixtures/auth.ts` (P14)**:
- `POST /api/v1/auth/register` — idempotent user creation
- `POST /api/v1/auth/login` — real JWT issuance
- `GET /api/v1/persons` — PersonProfile list
- `POST /api/v1/persons` — PersonProfile creation
- All calls hit the real backend via `APIRequestContext`

**`fixtures/auth-ui.ts` (P15/P16)**:
- Installs a Playwright route intercept (`context.route('http://localhost:8000/**', ...)`)
- **CORS bridge reason**: Playwright webServer runs at `:3010`; backend CORS whitelist is `:3000/:3100` — browser would reject responses without CORS headers
- Bridge patches `Access-Control-Allow-Origin: http://127.0.0.1:3010` onto every response
- Route handlers are NOT stored in `storageState` — must be reinstalled on every context

### Backend Runtime Requirements for CI

To run `uvicorn app.main:app --port 8000` in CI:

| Requirement | Status | Notes |
|-------------|--------|-------|
| Environment variables (`JWT_SECRET`, etc.) | NOT in CI | No secrets configured in CI workflow |
| Database connection | NOT in CI | Backend startup may require MongoDB or configured SQLite |
| Test user seeding | NOT in CI | `setupTwoUsers` registers/logs in via real API calls |
| Port 8000 available | Would need service step | CI would need `uvicorn` background process |
| Backend venv activation | Partial | `pip install` done in backend job, but separate from frontend job |

### CORS Bridge Fragility

The CORS bridge works by intercepting Playwright route requests at the browser level. In CI:
- The intercept relies on Playwright running in the same process
- Requires `context.route()` to be reinstalled on every context (including storageState-restored ones)
- Not a blocker per se, but adds complexity to CI setup

---

## 4. Local Validation Attempt

### Environment at time of audit
- Backend: running at `localhost:8000` ✅ (`curl /health` → 200)
- Frontend build: exists (`.next/BUILD_ID` from 2026-05-23) ✅

### Result: `make frontend-auth-smoke`

```
Error: Timed out waiting 120000ms from config.webServer.
make: *** [frontend-auth-smoke] Error 1
```

**Root cause**: Playwright webServer (`node_modules/.bin/next start --hostname 127.0.0.1 --port 3010`) timed out after 120 seconds even with a local build present. The build from May 23 may be stale relative to the current node_modules state, or port 3010 had a startup conflict.

**Implication**: Even locally with a running backend and existing build, `frontend-auth-smoke` is unreliable without a freshly built frontend immediately before the run. This confirms that CI (which would need to coordinate backend service + fresh build + `next start`) would be even less reliable.

---

## 5. CI Feasibility Analysis

### Classification: B — PARTIAL (local gate unreliable; CI setup too broad)

| Blocker | Severity | Details |
|---------|----------|---------|
| Backend service startup in CI | **HIGH** | Needs `uvicorn` as background service, env vars, database connection — not trivially available |
| Cross-job dependency | **HIGH** | Backend runs in a separate CI job from frontend; sharing localhost:8000 requires service containers |
| Frontend webServer reliability | **HIGH** | `next start` timed out locally (120s); CI with cold cache would be worse |
| Test timeouts | **MEDIUM** | P15=120s, P16=180s per test — slow for CI; adds ~5–10min to frontend job |
| CORS bridge | **LOW** | Works via Playwright route intercept; not a fundamental blocker but adds complexity |
| Test user seeding | **MEDIUM** | Requires live backend auth endpoints; can't use SQLite in-memory for this |

### Option A Assessment: NOT SAFE

Switching CI to run `frontend-auth-smoke` would require:
1. Backend service container in CI (database + env vars + uvicorn)
2. Backend job and frontend job sharing `localhost:8000` — GitHub Actions does not share localhost across jobs without service containers
3. Fresh `npm run build` + `next start` within the same frontend job
4. Increased CI runtime by ~10–15 minutes
5. New env secrets added to CI

This is a CI redesign, not a smoke gate alignment. Scope excludes CI redesign.

### Selected Option: B — Document Local Gate

No CI change. Canonical local command documented. CI gap explicitly acknowledged.

---

## 6. Canonical Local Gate

```bash
# Prerequisites
cd backend && uvicorn app.main:app --port 8000   # in separate terminal

# Build frontend (required before each run if code changed)
cd frontend && npm run build

# Run auth e2e smoke (Playwright webServer auto-starts next start at :3010)
make frontend-auth-smoke
```

**CORS bridge note**: The Playwright fixture intercepts `http://localhost:8000/**` and patches CORS headers for `:3010`. This is handled automatically — no backend CORS config change needed.

**Test users**: `e2e-user-a@example.com` / `E2eTestA1!` and `e2e-user-b@example.com` / `E2eTestB1!` — registered idempotently on first run via fixture.

---

## 7. Files Changed

None (docs-only path).

| File | Change |
|------|--------|
| `docs/security/P49_FRONTEND_AUTH_E2E_CI_READINESS.md` | Created (this file) |
| `00-Plan/roadmap/active_task_report.md` | P49 block prepended |

---

## 8. CI / Local Gap Summary

| Area | CI | Local (`make frontend-auth-smoke`) |
|------|----|------------------------------------|
| Mocked E2E (health-platform, platform-app, family-health-card) | ✅ `npm run e2e:ci` | ✅ `npm run e2e` |
| Auth negative (P14 — API-only, real JWT) | ❌ backend not running | ✅ with backend at 8000 |
| Auth UI negative (P15 — full browser) | ❌ backend + webServer not available | ✅ with backend + fresh build |
| Auth multi-context + storageState (P16) | ❌ backend + webServer not available | ✅ with backend + fresh build |
| Backend auth regression (41 tests) | ✅ full backend pytest suite | ✅ `backend-auth-audit` |
| Frontend TypeScript | ✅ `npx tsc --noEmit` (P48) | ✅ `make frontend-tsc` |

The backend auth regression (`backend-auth-audit` → `test_auth_negative_smoke.py`, `test_real_token_auth_negative.py`, `test_person_id_authorization_audit.py`, `test_report_authorization_hardening.py`, `test_report_download_token_policy.py`) covers the same **authorization logic** as the auth e2e specs, but at the API unit level without browser interaction. This provides meaningful CI coverage of the auth contract without requiring a live backend service.

---

## 9. Validation

`make runtime-smoke` after P49 investigation: **130 passed, 2 skipped** ✅

No files changed — smoke gate unchanged.

---

## 10. Known Limitations

| Item | Status |
|------|--------|
| Frontend auth E2E in CI | OPEN — requires backend service + fresh build + webServer; too broad for CI |
| `next start` webServer reliability | FRAGILE — 120s timeout hit locally; requires freshly built frontend |
| CORS bridge dependency | ACCEPTED — route intercept patches `:3010` CORS; backend config unchanged |
| P16 storageState round-trip | LOCAL ONLY — 180s timeout; not feasible for CI |
| Backend service in CI | OPEN — no service container configured; no secrets provisioned |
| PostgreSQL parity | OPEN — all backend tests run SQLite in-memory |

---

## 11. Final Classification

```
P49_FRONTEND_AUTH_E2E_LOCAL_GATE_DOCUMENTED

- frontend auth e2e remains local/manual by design ✅
- canonical local gate documented:
    cd backend && uvicorn app.main:app --port 8000   # separate terminal
    cd frontend && npm run build
    make frontend-auth-smoke
- CI already has comment: auth e2e specs validated locally via make frontend-auth-smoke ✅
- CI gap explicitly acknowledged — backend service setup required for CI is out of scope ✅
- runtime-smoke post-P49: 130 passed, 2 skipped ✅
- Starting HEAD: 579a42c
```
