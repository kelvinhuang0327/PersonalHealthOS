# Active Task Report — P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

## P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

**Final Classification: `P15_REAL_JWT_STORAGESTATE_UI_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `ca16633` (P14 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Prove that a user-A browser session (real JWT in localStorage) **cannot** access user-B's family health data at the **UI rendering layer** — network assertion (HTTP 404) AND DOM assertion (error text visible, no data leakage).

---

### 3. Root Cause Analysis — Why Naive Approaches Failed

#### Attempt 1 — React controlled-input fill

`page.fill()` on the Next.js login form did not trigger React's `onChange` handler in a production (`next start`) build.  No `/api/v1/auth/login` request appeared in the network trace.  **Root cause**: Playwright's `fill()` sets the native DOM value but does not fire synthetic React events in production bundle.

#### Attempt 2 — addInitScript + waitForFunction (initial hang)

Switched to JWT bootstrap via `addInitScript`.  Two bugs caused the test to hang for the full 120 s test timeout:

| Bug | Cause | Fix |
|---|---|---|
| **CORS** | Playwright webServer runs on `:3010`; backend `cors_allow_origins` only covers `:3000,3100`. Browser sent all requests but received `time:-1` (no response). PersonProvider's `listPersons()` call never resolved → `person_id` was never set in localStorage. | Added `context.route('http://localhost:8000/**', ...)` CORS bridge in fixture: intercepts every backend request, forwards it unchanged via `route.fetch()`, patches `Access-Control-Allow-Origin: http://127.0.0.1:3010` onto the response. |
| **`waitForFunction` arg/options confusion** | `{ timeout: 10_000 }` was passed as the **2nd** positional argument (the page-function `arg`), not the **3rd** (`options`). Playwright applied `timeout: 0` (infinite) and silently ignored the `10_000` value. Test hung until the 120 s `test.setTimeout` fired. | Reordered to `waitForFunction(fn, undefined, { timeout: 10_000 })`. Confirmed in trace: `params.timeout` changed from `0` to `10000`. |

#### Attempt 3 — addInitScript re-injection on reload

Passing `personId = userA.personId` to `bootstrapWithRealJWT` caused it to be re-injected on `page.reload()` (addInitScript runs on every navigation), overwriting the cross-user injection.  **Fix**: call `bootstrapWithRealJWT(context, token)` without `personId`; let PersonProvider auto-select it.

---

### 4. Final Architecture

```
setupTwoUsers(request)
  ├─ POST /auth/register + /auth/login  → userA.token, userA.personId
  └─ POST /auth/register + /auth/login  → userB.token, userB.personId

bootstrapWithRealJWT(contextA, userA.token)
  ├─ context.route('localhost:8000/**')  ← CORS bridge (new)
  ├─ page.addInitScript({ token })       ← localStorage['token'] = userA.token
  ├─ page.goto('/platform/dashboard')   ← PersonProvider mounts → listPersons()
  └─ waitForFunction(person_id truthy, undefined, { timeout: 10_000 })  ← fix

page.evaluate(() => localStorage.setItem('person_id', userB.personId))

waitForResponse(url.includes('family-health-context'))  ← set up BEFORE reload
page.reload()
  └─ addInitScript fires: token=userA  (person_id stays as userB via localStorage)

familyCtxResponse.status()  →  404   (backend get_target_person owner check)
getByText('無法載入家庭健康資料')  →  visible
bodyText.includes(userB.personId)  →  false
```

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth-ui.ts` | Created — CORS bridge + real-JWT bootstrap fixture |
| `frontend/tests/e2e/auth-ui-negative.spec.ts` | Created — P15 full-UI cross-user smoke spec |
| `00-Plan/roadmap/active_task_report.md` | Updated — P15 report block prepended |

---

### 6. Test Result

```
Running 1 test using 1 worker
  1 passed (7.3s)
```

| Test | Status |
|---|---|
| user A real-JWT session → user B person_id → family-health-context 404 + error UI rendered | ✅ PASS |

P14 regression check (3/3 API-level tests):

```
Running 3 tests using 1 worker
  3 passed (3.1s)
```

---

### 7. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 8. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `78c1e40` | `test(e2e): add real-JWT storageState bootstrap fixture for UI smoke (P15)` |
| C2 | `d2aea8c` | `test(e2e): add full UI cross-user auth negative smoke (P15)` |
| C3 | (this commit) | `docs(report): P15 real-JWT storageState UI auth smoke report` |

---

### 9. Key Lessons

| Lesson | Detail |
|---|---|
| Playwright `waitForFunction(fn, arg, options)` — arg vs options | Passing `{ timeout }` as 2nd param silently makes it the page-function argument, not the timeout option.  Always pass `undefined` as arg when no arg is needed. |
| CORS with Playwright webServer | If `reuseExistingServer: false` and the webServer port is not in the backend CORS whitelist, ALL browser API calls will silently fail.  Use `context.route()` to bridge CORS in the fixture layer without touching production code. |
| `addInitScript` runs on every navigation | Do NOT inject values into `addInitScript` that you intend to override mid-test.  Inject only stable values (JWT token); let the app populate dynamic values (person_id). |

---

# Active Task Report — P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

## P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

**Final Classification: `P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `f1be74b` (P13-FINALIZE report, clean tree) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Current Git HEAD Before Work

```
f1be74b docs(report): P13-FINALIZE + browser auth smoke report — NOT_IMPLEMENTED with gap detail
b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
```

---

### 3. Auth Route / Token Endpoint Findings

| Item | Value |
|---|---|
| Register endpoint | `POST /api/v1/auth/register` — `{"email": str, "password": str}` — 201 on success, 400 if already registered |
| Login endpoint | `POST /api/v1/auth/login` — `{"email": str, "password": str}` → `{"access_token": str, "token_type": "bearer"}` |
| Token format | JWT (HS256), subject = user UUID |
| Persons create | `POST /api/v1/persons` with `Authorization: Bearer <token>` |
| Family health context | `GET /api/v1/health-assistant/family-health-context?person_id=<pid>` |
| Family recommendations | `GET /api/v1/health-assistant/family-recommendations?person_id=<pid>` |
| Cross-user isolation | `get_target_person` in `backend/app/core/deps.py` filters `PersonProfile.owner_user_id == current_user.id` → 404 on mismatch |
| No-token behavior | 401 `{"detail":"Not authenticated"}` |
| Backend URL | `http://localhost:8000` (from `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`) |

---

### 4. Existing Playwright Fixture / Mock-Auth Findings

All three prior specs (`family-health-card`, `health-platform`, `platform-app`) use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API route interception

No `storageState`, no `globalSetup`, no real credential flow found. Confirmed P13 gap.

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth.ts` | Created — real-auth fixture (116 lines) |
| `frontend/tests/e2e/auth-negative.spec.ts` | Created — 3 negative smoke tests (73 lines) |
| `00-Plan/roadmap/active_task_report.md` | Updated — P14 report block prepended |

---

### 6. Test User / Token Bootstrap Decision

**Decision: register two dedicated e2e users on first run (idempotent)**

| User | Email | Password | Strategy |
|---|---|---|---|
| User A | `e2e-user-a@example.com` | `E2eTestA1!` | `POST /api/v1/auth/register` (400 = already exists → ok) then `POST /api/v1/auth/login` |
| User B | `e2e-user-b@example.com` | `E2eTestB1!` | Same |

Both users were pre-verified against the running backend before writing the fixture. PersonProfile creation is also idempotent — returns existing profile if one already exists.

---

### 7. Single-File Playwright Result

```
Running 3 tests using 1 worker
  3 passed (5.7s)
```

| Test | Status |
|---|---|
| user A JWT cannot access user B family-health-context → 404 | ✅ PASS |
| request without Authorization header → 401 | ✅ PASS |
| user A JWT cannot access user B family-recommendations → 404 | ✅ PASS |

**Scope note**: browser-context/API smoke (not full UI smoke). All HTTP calls use Playwright's `request` fixture (APIRequestContext) directly to the backend. The frontend UI login flow is not exercised — multi-user `storageState` fixture remains an open gap.

---

### 8. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 9. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `8af3262` | `test(e2e): add real-auth Playwright fixture for browser auth smoke` |
| C2 | `78afae7` | `test(e2e): add cross-user browser-context auth negative smoke` |
| C3 | (this commit) | `docs(report): P14 browser auth fixture foundation report` |

---

### 10. Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Limitation** | Tests use `request` (APIRequestContext), not `page` — no browser UI rendering, no JS navigation, no DOM assertion. Full UI smoke requires storageState + login UI fixture (P15 candidate). |
| **Limitation** | `playwright.config.ts` `webServer` starts Next.js production server (`next start`) before any test run. Tests pass because a production build exists in `.next/`. If the build is stale, `next start` may fail. |
| **Limitation** | Test user credentials (`e2e-user-a@example.com`, `e2e-user-b@example.com`) are now seeded in the running SQLite DB. They persist across restarts. |
| **Inferred** | `reuseExistingServer: false` in playwright config means Playwright always starts a fresh Next.js process on port 3010. If port 3010 is occupied, tests will fail with server-start error. |
| **Unknown** | Whether CI will have a running backend at `localhost:8000`. Backend must be started before Playwright tests in any CI pipeline. |
| **Open gap** | `storageState` multi-user login fixture for full UI smoke — not implemented in this task. |

---

### Final Classification

**`P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

- Real auth fixture implemented (`frontend/tests/e2e/fixtures/auth.ts`)
- Cross-user negative smoke: 3/3 PASS (5.7s)
- TypeScript: 0 errors
- Boundary verified: `get_target_person()` ownership filter enforced end-to-end

---

---

## APPENDIX: P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

## P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

**Final Classification: `P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `.gitignore` M, `Makefile` M, 5 roadmap docs M, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`, `?? backend/tests/test_auth_negative_smoke.py`, `?? backend/tests/test_real_token_auth_negative.py` — all P13 expected artifacts, no scope conflict |
| Staged diff at start | 3 deletions (`git diff --cached --stat`) — all confirmed `git rm --cached` (index-only) |

---

### A1 — Staging Intent Confirmation

Physical files verified present on disk before any commit:
- `frontend/tsconfig.tsbuildinfo` — 126,055 bytes, mtime 2026-05-23 ✅
- `runtime/launchd/pids/backend.pid` — 5 bytes, mtime 2026-05-22 ✅
- `runtime/launchd/pids/frontend.pid` — 5 bytes, mtime 2026-05-22 ✅

**Verdict: `git rm --cached` (index-only removal). Physical files intact. Safe to proceed.**

---

### A2 — P13 Test File Authenticity Confirmation

| File | Docstring confirmation |
|---|---|
| `test_real_token_auth_negative.py` | "P13 Real-Token Auth Negative Smoke" — uses real `jwt.decode`, real `create_access_token`, production `get_target_person`. 7 tests. ✅ |
| `test_auth_negative_smoke.py` | "P12 Auth Negative Smoke — cross-user family context isolation" — override-style via `app.dependency_overrides`. 5 tests. ✅ |

**Verdict: Both files confirmed P13 auth tests. Content matches task description.**

---

### A3 — Commit List

| Commit | Hash | Files | Message |
|---|---|---|---|
| C1 | `0a73f1a` | 2 | `feat(auth): P13 real-token JWT negative smoke + override smoke` |
| C2 | `eeadbf7` | 5 | `chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment` |
| C3 | `b484c56` | 5 | `docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report` |

C2 includes: `Makefile`, `.gitignore`, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`

---

### A Acceptance Check

```
git log --oneline -5:
  b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
  eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
  0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
  de78305 docs: update active_task_report — P12 production trust closure (713 PASS)
  d41d13c fix(orchestrator): _open_db respects ORCHESTRATOR_PROFILE_PATH env var

git status --short: (empty) ✅

Physical files post-commit:
  frontend/tsconfig.tsbuildinfo — present ✅
  runtime/launchd/pids/backend.pid — present ✅
  runtime/launchd/pids/frontend.pid — present ✅
```

**Sub-acceptance A: PASS**

---

### B1 — Playwright Fixture Probe

```
frontend/tests/
  e2e/
    family-health-card.spec.ts
    health-platform.spec.ts
    platform-app.spec.ts
```

Grep results for `test.use|login|authenticate|storageState|access_token` — **0 matches**

Playwright config (`playwright.config.ts`):
- `testDir: ./tests/e2e`
- `baseURL: http://127.0.0.1:3010`
- No `globalSetup`, no `storageState`, no auth bootstrap

All existing specs use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API interception
- No real login flow, no real credential exchange

---

### B2 — Branch Decision: `BROWSER_AUTH_E2E_NOT_IMPLEMENTED`

#### Missing Fixtures (precise gap list)

| Missing Component | Description |
|---|---|
| **Login helper / auth fixture** | No function that navigates to login page, submits real credentials, and captures a token or `storageState` snapshot |
| **Token bootstrap** | No mechanism to call `/api/v1/auth/token` or `/api/v1/auth/login` with test user credentials and store the JWT for subsequent requests |
| **`storageState` setup** | No `playwright/.auth/user.json` or equivalent; no `test.use({ storageState: ... })` in any spec |
| **Multi-user isolation fixture** | No fixture that creates two distinct authenticated sessions (user A session vs. user B session) |

#### Next.js Routes Involved

| Route | Path |
|---|---|
| Login page | `/platform/login` (App Router: `frontend/app/platform/login/`) and `pages/login.tsx` |
| Family context page | `/platform/settings/family` (App Router: `frontend/app/platform/settings/family/`) |
| Family context API | `GET /api/v1/family-health-context?person_id=<pid>` and `GET /api/v1/family-recommendations?person_id=<pid>` |

#### Recommended Test Assertion Points (when implemented)

1. **Setup**: Create two real users (user A, user B) via API; obtain real JWT for user A via `POST /api/v1/auth/token`
2. **Browser action**: Navigate to `/platform/settings/family?profile=<userB_person_id>` while authenticated as user A
3. **Assertion options** (any of):
   - Response status 404 from backend API call (user B's person not found for user A)
   - Redirect to `/platform/login` or error page
   - DOM assertion: user B's `display_name` / health data NOT present in page content
4. **Negative confirmation**: Page must not render any user B health data (blood pressure, symptoms, risk alerts)

#### Implementation Prerequisites (for future P14)

```typescript
// Required: tests/e2e/fixtures/auth.ts
import { test as base, Page } from '@playwright/test'

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // 1. POST /api/v1/auth/token with test credentials
    // 2. localStorage.setItem('token', realJWT)
    // 3. yield page to test
    await use(page)
  }
})
```

**No new npm packages required** — Playwright's built-in `page.request.post()` is sufficient for token acquisition.

---

### Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Inferred** | All existing Playwright specs use mock tokens — real auth flow has never been E2E tested at browser level |
| **Unknown** | Whether the `/platform/login` App Router page (`frontend/app/platform/login/`) is the active login route vs. `pages/login.tsx` (Pages Router) |
| **Known limitation** | Backend test suite (723 PASS) validates auth isolation at HTTP level; browser-level isolation gap is purely at the Playwright fixture layer |
| **Known limitation** | `webServer` in playwright.config.ts uses `next start` (production build) — any auth fixture must work with the built app, not dev mode |

---

### Final Classification

**`P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

- Sub-acceptance A: **PASS** — 3 commits (C1/C2/C3) above `de78305`, clean working tree, all 3 physical files intact
- Sub-acceptance B: **`BROWSER_AUTH_E2E_NOT_IMPLEMENTED`** with complete gap detail (missing fixtures, routes, assertion points, implementation guide)

---

---

## APPENDIX: P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

## P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

**Final Classification: `P13_AUTH_E2E_ENTRYPOINT_HARDENED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | Known P12 artifacts only (`.gitignore` M, plan files M, 3 artifact D entries from P12 `git rm --cached`, `test_auth_negative_smoke.py` ??). No scope conflict. |

---

### 1. Auth Token Fixture Probe

| Item | Finding |
|---|---|
| `create_access_token` | **Exists** — `backend/app/core/security.py:18` |
| `get_current_user` | Decodes JWT via `jose.jwt.decode` using `settings.jwt_secret_key` / `settings.jwt_algorithm` |
| Existing tests with real JWT | **None** — all prior tests used `dependency_overrides[get_current_user]` |
| Auth fixture available? | **YES** — `create_access_token` is importable; real tokens can be minted in tests |

---

### 2. Real-Token Auth Negative Smoke — PASS

**New file:** `backend/tests/test_real_token_auth_negative.py`

**Approach:** Only `get_db` is overridden (in-memory SQLite). `get_target_person` runs as production code. `get_current_user` uses a SQLite-compatible shim that calls the same `jwt.decode` with the same keys/algorithm, then coerces `sub` string → `uuid.UUID` before the DB query (required for SQLite `UUID(as_uuid=True)`; a no-op in production PostgreSQL).

**Token issuance:** `create_access_token(str(user_id))` — identical to production login endpoint.

| Test | Status |
|---|---|
| User A real token + user B `person_id` → `/family-health-context` → 404, no data leak | ✅ PASS |
| User A real token + user B `person_id` → `/family-recommendations` → 404, no data leak | ✅ PASS |
| No `Authorization` header → 401 | ✅ PASS |
| Expired JWT (exp in past) → 401 | ✅ PASS |
| Garbage non-JWT string → 401 | ✅ PASS |
| User A real token + own `person_id` → 200 (sanity) | ✅ PASS |
| User A real token + no `person_id` → 200 default person (sanity) | ✅ PASS |

**Result:** `7 passed in 1.72s`

**SQLite UUID limitation note:** The production `get_current_user` passes the JWT `sub` string directly to `UUID(as_uuid=True)` column. PostgreSQL's psycopg2 handles implicit casting; SQLite does not. The test shim adds `uuid.UUID(user_id_str)` coercion. This is a test-infra gap, not a security gap — `get_target_person` ownership enforcement runs unshimmed in both test environments.

---

### 3. Test Entrypoint Hardening — PASS

**Problem:** `pytest -q` without `.venv` activation → 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`).

**Changes:**

| File | Change |
|---|---|
| `backend/README.md` | Replaced bare `pytest -q` with canonical `.venv/bin/python -m pytest -q`; added warning box; documented `make backend-test` as CI equivalent |
| `Makefile` (root) | Added `backend-smoke` target: runs only auth negative tests (`test_auth_negative_smoke.py` + `test_real_token_auth_negative.py`) without full DB setup |

**Canonical test command (hardened):**
```bash
# From repo root
make backend-test
# or directly
cd backend && .venv/bin/python -m pytest -q
# auth smoke only
make backend-smoke
```

---

### 4. Full Validation Run

| Check | Command | Result |
|---|---|---|
| Backend pytest | `backend/.venv/bin/python -m pytest -q` | **723 passed, 0 failed** (716 prior + 7 new real-token tests) |
| Frontend TypeScript | `cd frontend && npx tsc --noEmit` | **Exit 0, 0 errors** |
| Frontend Next Build | `cd frontend && npx next build` | **Success** — 20 static routes, First Load JS 95.3 kB |

---

### 5. Files Changed This Sprint

| File | Action |
|---|---|
| `backend/tests/test_real_token_auth_negative.py` | **NEW** — 7 real-token auth negative tests |
| `backend/README.md` | Updated Tests section with hardened entrypoint instructions |
| `Makefile` | Added `backend-smoke` target; updated `.PHONY` |
| `00-Plan/roadmap/active_task_report.md` | This block prepended |

---

### 6. Known Limitations

1. **SQLite UUID coercion in `get_current_user`:** Production code (`deps.py`) passes JWT `sub` as string to `UUID(as_uuid=True)` column; works in PostgreSQL, fails in SQLite. Fixed by test shim. Application code not changed (out of scope).
2. **Playwright E2E still NOT_RUN:** Real-browser login → token → cross-user probe flow. Out of scope for this sprint.
3. **FastAPI `on_event` deprecation:** 4 warnings per run, pre-existing, not introduced here.
4. **`backend-test` Makefile re-creates venv on every run:** `python3 -m venv .venv` is idempotent but slow. No change made (out of scope).

---

--- # Appendix: P12 Report ---

## P12-POST-CLOSURE-VERIFICATION (2026-05-21)

**Final Classification: `P12_POST_CLOSURE_VERIFIED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `M 00-Plan/roadmap/CEO-Decision.md`, `M 00-Plan/roadmap/CTO-Analysis.md`, `M 00-Plan/roadmap/active_task.md`, `M 00-Plan/roadmap/roadmap.md`, `M frontend/tsconfig.tsbuildinfo`, `M runtime/launchd/pids/backend.pid`, `M runtime/launchd/pids/frontend.pid` — all known artifacts, no scope conflict |

---

### A. Backend Regression Rerun — PASS

**Command:** `cd backend && source .venv/bin/activate && pytest -q`

| Metric | Result |
|---|---|
| Total tests | 716 (713 prior + 3 new auth negative smoke) |
| PASS | 716 |
| FAIL | 0 |
| Skipped | 0 |
| Warnings | 4 (FastAPI `on_event` deprecation — pre-existing) |

**Summary line:** `716 passed, 4 warnings in 5.82s`

> Note: Running pytest without `.venv` activation produces 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`). The canonical invocation requires `.venv` activation — this is the same environment that produced the claimed 713 PASS.

---

### B. Frontend TypeScript — PASS

**Command:** `cd frontend && npx tsc --noEmit`

**Result:** Exit code 0, zero errors.

---

### C. Frontend Next Build — PASS

**Node version:** v20.19.5  
**npm version:** 10.8.2  
**Command:** `cd frontend && npx next build`

Build succeeded. Route table (all static):

| Route | Size | First Load JS |
|---|---|---|
| / | 358 B | 81.4 kB |
| /dashboard | 325 B | 81.4 kB |
| /health-insights | 2.4 kB | 105 kB |
| /login | 2.98 kB | 84.1 kB |
| /register | 2.84 kB | 83.9 kB |
| … (20 routes total, all ○ Static) | | |

First Load JS shared: 95.2 kB.

---

### D. Minimal API Auth Negative Smoke — PASS

**Auth fixture probe:**
- `TestClient`: present in multiple test files ✅
- `Authorization` / `access_token` / `create_access_token` / `auth_headers`: **NOT present** in test suite
- Existing tests use `app.dependency_overrides[get_current_user]` pattern (no raw JWT in tests)

**Decision:** Auth fixture exists (via dependency_overrides pattern). New negative smoke test written.

**Test file:** `backend/tests/test_auth_negative_smoke.py`

**Access control mechanism verified:**
`get_target_person` in `backend/app/core/deps.py` enforces:
```python
.filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
```
If no match → HTTP 404. This is the isolation boundary tested.

**Tests written (3):**
1. `test_cross_user_family_context_returns_404` — User A token + user B's `person_id` → `/family-health-context` → 404, no data leak ✅
2. `test_cross_user_family_recommendations_returns_404` — Same for `/family-recommendations` → 404, no data leak ✅
3. `test_own_person_id_still_accessible` — Sanity: user A's own `person_id` → 200 ✅

**Result:** `3 passed in 1.50s`

**Full regression after adding test:** `716 passed, 4 warnings in 5.82s` (0 regressions)

---

### E. Artifact Hygiene + Report Integrity — PASS

**E1. Artifact Hygiene:**

| File | Action Taken |
|---|---|
| `frontend/tsconfig.tsbuildinfo` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/backend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/frontend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |

Physical files confirmed intact after `git rm --cached`. No runtime state was deleted.

**E2. Report Integrity:** This block inserted at top of `active_task_report.md`. Prior content preserved below appendix separator.

---

### Known Limitations / Unknown / Inferred

1. **venv invocation**: `pytest -q` without `.venv` activation fails with 46 collection errors. The 713 PASS claim and this session's 716 PASS both require explicit venv. CI/CD should pin to `.venv/bin/pytest` or equivalent.
2. **Token-based E2E**: No real JWT token is issued or verified in tests — auth isolation is tested via `dependency_overrides`. A Playwright-level E2E with a real token flow (login → get JWT → cross-user probe) remains unverified.
3. **Playwright E2E**: Written (spec exists) but not run. Browser E2E status unchanged from P11 handoff.
4. **FastAPI `on_event` deprecation**: 4 warnings in all test runs. Pre-existing, not P12-introduced.

---

--- # Appendix: Prior Sprint Reports ---

# Active Task Report — P12_PRODUCTION_TRUST_CLOSURE_READY

Generated: 2026-05-22  
Classification: **`P12_PRODUCTION_TRUST_CLOSURE_READY`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P10 Family UI evidence transparency verified | ✅ PASS (static smoke + tsc) |
| Task 2 — Minimal static / browser smoke | ✅ Static PASS · Playwright spec written · Browser E2E NOT RUN |
| Task 3 — P11 Production Trust Readiness checklist | ✅ THIS DOCUMENT |
| Task 4 — Regression validation | ✅ 617 PASS (see breakdown below) |

---

## Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files | `M frontend/tsconfig.tsbuildinfo` (build artifact, not blocking) ✅ |

---

## Task 1 — P10 Family UI Evidence Transparency Verification

### Static smoke checks (all PASS)

| Check | Result |
|---|---|
| `EvidenceSourceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `AudienceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `source_type` consumed in render | ✅ 1 occurrence |
| Non-diagnosis disclaimer `非醫療診斷` | ✅ 1 occurrence |
| Limitations section rendered | ✅ present |
| Source origin label `健康觀察資料` | ✅ 2 occurrences (child + caregiver sections) |
| Diagnosis word `診斷` only in disclaimer | ✅ 1 total (confirmed to be in disclaimer text only) |
| Profile UUID `profile_id` in user-facing text | ✅ 0 leakage (only in internal logic / type references) |
| Badge labels: 兒童健康, 照護提醒, 共同風險, 行動建議 | ✅ all present in EvidenceSourceBadge config |

### TypeScript shape validation

- `FamilyRecommendation` type includes `source_type: string` ✅
- `npx tsc --noEmit` → 0 errors ✅
- `npx next build` → CLEAN ✅

---

## Task 2 — Smoke Test Status

| Method | Status |
|---|---|
| Static grep checks | ✅ PASS |
| TypeScript compilation | ✅ PASS |
| Next.js build | ✅ PASS |
| Playwright spec written | ✅ `frontend/tests/e2e/family-health-card.spec.ts` (6 tests) |
| Playwright browser E2E executed | ❌ NOT RUN — requires live dev server |

> Note: Playwright spec covers: section visibility, disclaimer text, source badges (兒童健康, 行動建議), audience badge (照護者), source origin label. Tests are written with mocked API routes.

---

## Task 4 — Regression Validation

### Backend test results

| Test file | Tests | Result |
|---|---|---|
| test_family_health_context.py | 46 | ✅ PASS |
| test_family_context_data_population.py | 18 | ✅ PASS |
| test_family_relationships.py | 17 | ✅ PASS |
| test_narrative_reasoning.py | — | ✅ PASS |
| test_narrative_memory_service.py | — | ✅ PASS |
| test_api_narrative_memory.py | — | ✅ PASS |
| test_engagement_analytics.py | — | ✅ PASS |
| test_personalization_profile.py | — | ✅ PASS |
| test_adaptive_recommendation_scoring.py | — | ✅ PASS |
| test_notification_history_service.py | — | ✅ PASS |
| test_api_notification_status.py | — | ✅ PASS |
| test_notification_intelligence.py | — | ✅ PASS |
| test_api_notification_intelligence.py | — | ✅ PASS |
| test_lab_intelligence.py | — | ✅ PASS |
| test_api_lab_smoke.py | — | ✅ PASS |
| test_api_symptom_smoke.py | — | ✅ PASS |
| test_symptom_intelligence.py | — | ✅ PASS |
| test_device_signal_escalation.py | — | ✅ PASS |
| test_device_signal_detection.py | — | ✅ PASS |
| test_api_escalation_smoke.py | — | ✅ PASS |
| test_health_assistant_service.py | — | ✅ PASS |
| test_daily_summary_service.py | — | ✅ PASS |
| test_recommendation_trust_service.py | — | ✅ PASS |
| test_outcome_feedback_service.py | — | ✅ PASS |
| **Batch 1 total** | **320** | ✅ PASS |
| **Batch 2 total** | **297** | ✅ PASS |
| test_dual_agent_orchestrator.py | 10 failed | ⚠️ PRE-EXISTING — excluded |

**Total (mandated suites): 617 PASS, 0 new failures**

---

## P11 — Production Trust Readiness Checklist

> This checklist tracks readiness for trustworthy production deployment, not feature completeness.  
> Unit tests ≠ production validation. Each item is tagged DONE / GAP / NOT RUN.

### 1. Privacy & Cross-Profile Isolation

| Item | Status | Notes |
|---|---|---|
| Profile UUID not exposed in user-facing text | ✅ DONE | `test_load_errors_limitation_does_not_expose_profile_id` asserts this |
| Cross-profile evidence mixing prevention | ✅ DONE | `build_family_health_context` only uses profiles in `relationships` list |
| Unrelated profile data not surfaced | ✅ DONE | Enforced by `related_pids` filter in service |
| API auth guards (token required) | ⚠️ GAP | Backend endpoints require `Authorization` header but E2E auth validation not tested |
| Family relationship permission enforcement | ⚠️ GAP | `permission_level` stored but not enforced at query level in DB layer |

### 2. Medical Disclaimer Coverage

| Item | Status | Notes |
|---|---|---|
| No-diagnosis disclaimer in FamilyHealthCard | ✅ DONE | "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。" |
| Diagnosis wording absent from static copy | ✅ DONE | Only 1 occurrence of `診斷` in component, confirmed in disclaimer context |
| Hallucination guardrail policy documented | ✅ DONE | `ai/prompts/hallucination_guardrail_policy.md` exists |
| Disclaimer on other health display pages | ⚠️ GAP | Disclaimer only confirmed in FamilyHealthCard; other dashboards not audited |
| AI summary output review | ⚠️ GAP | `health_summary_system_prompt.md` exists but output review not automated |

### 3. Source Traceability

| Item | Status | Notes |
|---|---|---|
| `evidence_source` field in recommendations | ✅ DONE | Since P8 |
| `source_type` field in recommendations | ✅ DONE | Added P10 (child_health/caregiver_health/shared_risk/action) |
| Source badge visible in UI | ✅ DONE | `EvidenceSourceBadge` in FamilyHealthCard |
| Audience badge visible in UI | ✅ DONE | `AudienceBadge` in FamilyHealthCard |
| Lab/symptom/device granularity per item | ⚠️ GAP | `childAttentionItems` + `caregiverAlerts` are mixed-source strings; per-item source type not tracked |
| Narrative source traceability | ⚠️ GAP | Narrative memories referenced but not surfaced as evidence badges in UI |

### 4. Confidence & Limitations Coverage

| Item | Status | Notes |
|---|---|---|
| `confidence` field in FamilyHealthContext | ✅ DONE | Scales with profile count + evidence density |
| `limitations` field in FamilyHealthContext | ✅ DONE | Explains data gaps to user |
| Load failure visibility in limitations | ✅ DONE | P9: `load_errors_by_profile` adds limitation text |
| Limitations displayed in FamilyHealthCard | ✅ DONE | Styled with Info icon (P10) |
| ConfidenceBadge shows score | ✅ DONE | `可信度 X%` with color thresholds |
| Confidence calibration validated | ⚠️ GAP | No test asserts confidence formula accuracy vs real data |

### 5. Notification Spam Guard

| Item | Status | Notes |
|---|---|---|
| Max recommendations per member capped | ✅ DONE | `_MAX_SUGGESTIONS_PER_MEMBER = 3` constant enforced in `generate_family_recommendations` |
| Dedup against active actions | ✅ DONE | P9: `active_actions_by_profile` dedup |
| Dedup case-insensitive edge cases | ✅ DONE | P9 `TestFamilyDedupHardening` (6 tests) |
| Notification frequency limits in production | ⚠️ GAP | Unit-level only; no integration test for notification rate limits |

### 6. Data Persistence Boundaries

| Item | Status | Notes |
|---|---|---|
| Family relationships stored in DB | ✅ DONE | `FamilyRelationship` model, `family_relationships` table |
| Evidence data loaded from live DB per request | ✅ DONE | `load_family_evidence_data()` queries DB each call |
| No sensitive data in memory cache | ✅ DONE | No Redis/memory cache layer in current architecture |
| SQLite in tests, real DB in production | ✅ DONE | pytest uses in-memory SQLite via test fixtures |
| Database migration scripts present | ✅ DONE | `database/migrations/` directory exists |
| Migration tested against production schema | ⚠️ GAP | Migration scripts not run in CI |

### 7. E2E Coverage Gaps

| Item | Status | Notes |
|---|---|---|
| Platform dashboard loads | ✅ Written | `platform-app.spec.ts` (NOT RUN in this sprint) |
| FamilyHealthCard section visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| No-diagnosis disclaimer visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Source badge text visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Auth flows (login/token refresh) | ❌ NOT WRITTEN | No Playwright test for auth |
| Error state handling (API 500) | ❌ NOT WRITTEN | FamilyHealthCard error state not E2E tested |
| Empty state (no relationships) | ❌ NOT WRITTEN | `EmptyState` component not E2E tested |
| Cross-browser rendering | ❌ NOT RUN | Playwright config not verified for multi-browser |

### 8. Orchestrator Pre-existing Failures

| Item | Status | Notes |
|---|---|---|
| `test_dual_agent_orchestrator.py` | ⚠️ 10 FAILED | Pre-existing failures — not caused by P8–P10 changes |
| Orchestrator failures affect production | ❌ UNVERIFIED | Dual-agent orchestrator feature scope unclear |
| Fix plan | ⚠️ GAP | Failures not investigated; excluded from mandatory suites |

### 9. Deployment Smoke Gaps

| Item | Status | Notes |
|---|---|---|
| Docker Compose local config present | ✅ DONE | `docker-compose.local.yml` exists |
| Docker Compose prod config present | ✅ DONE | `docker-compose.prod.yml` exists |
| `smoke_check.py` script present | ✅ DONE | Root-level `smoke_check.py` exists |
| Smoke check actually run | ❌ NOT RUN | Not run in this sprint |
| Backend startup health check | ⚠️ GAP | `/health` or `/ping` endpoint not confirmed present |
| Frontend startup health check | ⚠️ GAP | Next.js deployment smoke not automated |
| Secrets / env config validated | ❌ NOT RUN | `.env` variable audit not done |

### P11 Summary

| Category | DONE | GAP | NOT RUN |
|---|---|---|---|
| Privacy & cross-profile | 3 | 2 | 0 |
| Medical disclaimer | 3 | 2 | 0 |
| Source traceability | 4 | 2 | 0 |
| Confidence & limitations | 4 | 1 | 0 |
| Notification spam guard | 4 | 1 | 0 |
| Data persistence | 5 | 1 | 0 |
| E2E coverage | 4 written | 3 not written | 4 not run |
| Orchestrator failures | 0 | 1 | 1 |
| Deployment smoke | 3 | 2 | 2 |

> **P11 overall**: Foundation is solid for a health tracking app at personal/beta scale. Key gaps before broader production trust: permission enforcement at DB layer, per-item source type granularity, auth E2E tests, deployment smoke execution, and orchestrator failure resolution.

---

## Prior Sprint Reference

| Sprint | Commit | Classification |
|---|---|---|
| P8 | `cc4312b` | P8_FAMILY_HEALTH_ASSISTANT_VERIFIED |
| P9 | `5e8528f` | P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED |
| P10a | `92b9707` | P10_FAMILY_CONTEXT_UI_EVIDENCE_READY |
| P10b | this commit | P10_FAMILY_UI_VERIFIED_AND_P11_TRUST_CHECKLIST_READY |

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy except designated disclaimer ✅
- Existing API shape unchanged (additive only) ✅
- All mandated test suites PASS ✅
- No new branches created ✅

---

## P10 Sprint Context

Previous sprint: **P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED** (commit `5e8528f`)

Prior sprint delivered:
- `load_errors_by_profile` visibility in limitations
- Family dedup edge-case hardening (6 tests)
- Load error visibility tests (4 tests)
- 672 backend PASS

This sprint: UI evidence transparency — make Family Health UI trustworthy and transparent without major backend changes.

---

## Changes Delivered

### Backend (`family_health_context_service.py`)
- Added `source_type: str` field to `FamilyRecommendation` TypedDict docstring
- `generate_family_recommendations()` now emits `source_type` alongside `evidence_source`:
  - `child_attention_item` → `"child_health"`
  - `caregiver_alert` → `"caregiver_health"`
  - `shared_risk` → `"shared_risk"`
  - `family_suggestion` → `"action"`
- Fully additive — no existing fields changed

### Frontend Types (`lib/api.ts`)
- Added `source_type: string` to `FamilyRecommendation` type

### Frontend Component (`family-health-card.tsx`)
- New `EvidenceSourceBadge({ sourceType })` — maps source_type → label + color badge
- New `AudienceBadge({ audience })` — shows recommendation target (照護者/成員/全家)
- Recommendations section: shows urgency badge + evidence source badge + audience badge before text
- `childAttentionItems` section: added source origin label "來源：健康觀察資料"
- `caregiverAlerts` section: added source origin label "來源：健康觀察資料"
- Limitations section: upgraded from plain bullets to `Info` icon + styled container
- Added no-diagnosis disclaimer at card bottom: "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。"
- Added `Info` icon from lucide-react

### Tests (`test_family_health_context.py`)
- New class `TestFamilyRecommendationAPIShape` (6 tests):
  - `test_all_recommendations_have_source_type`
  - `test_child_attention_item_source_type_is_child_health`
  - `test_caregiver_alert_source_type_is_caregiver_health`
  - `test_shared_risk_source_type_is_shared_risk`
  - `test_family_suggestion_source_type_is_action`
  - `test_context_has_confidence_and_limitations_fields`

---

## Validation Results

```
Backend: 678 PASS (ignoring 10 pre-existing failures in test_dual_agent_orchestrator)
Frontend: tsc 0 errors
Frontend: next build CLEAN
```

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy ✅  
- Existing API shape unchanged (additive only) ✅
- All 40 pre-existing family tests continue to pass ✅

---

## P9 Sprint Context

Previous sprint: **P8_FAMILY_HEALTH_ASSISTANT_VERIFIED** (commit `cc4312b`)

Prior sprint delivered:
- `extract_family_evidence_from_bundle()` pure helper
- `load_family_evidence_data()` DB helper
- `GET /family-health-context` uses real per-profile evidence
- `GET /family-recommendations` uses real `active_actions_by_profile` for dedup

This sprint: verification, failure visibility, dedup edge-case hardening.

---

## Commits

| Commit | Tag | Description |
|---|---|---|
| `cc4312b` | `P9_FAMILY_CONTEXT_DATA_POPULATED` | P9 — populate 6 per-profile dicts with real evidence data |
| (current) | `P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED` | Failure visibility + dedup hardening |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/family_health_context_service.py` | `load_family_evidence_data()` now tracks errors in `load_errors_by_profile`; `build_family_health_context()` accepts `load_errors_by_profile` and adds limitation text |
| `backend/app/api/health_assistant.py` | Both family endpoints pass `load_errors_by_profile` from evidence to `build_family_health_context` |
| `backend/tests/test_family_health_context.py` | Added `TestFamilyDedupHardening` (6 tests) and `TestLoadErrorVisibility` (4 tests) |

---

## P9 Data Flow Confirmation

```
FamilyRelationship DB rows
    → load_family_relationships(db, owner_user_id, subject_profile_id)
    → load_family_evidence_data(db, owner_user_id, relationships)
        → unique related_profile_ids iterated
        → build_evidence_bundle(db, uid, pid) per profile
        → on failure: load_errors_by_profile[pid] = "evidence_unavailable" (skip, no crash)
        → returns {
              lab_abnormalities_by_profile,
              symptom_patterns_by_profile,
              escalations_by_profile,
              active_actions_by_profile,
              recommendations_by_profile,
              load_errors_by_profile
          }
    → build_family_health_context(relationships, **evidence, load_errors_by_profile=...)
        → limitations += "部分成員資料載入失敗（N 位）..." when errors present
        → profile IDs never exposed in user-facing limitation text
    → generate_family_recommendations(context, active_actions_by_profile)
        → dedup via flat union all_active set (lowercase strip)
    → GET /family-health-context → frontend FamilyHealthCard
    → GET /family-recommendations → FamilyHealthCard recommendations section
```

---

## Failure Visibility Implementation

| Behaviour | Result |
|---|---|
| Evidence load error for one profile → stored in `load_errors_by_profile` | ✅ |
| Failed profile does not crash endpoint | ✅ |
| Error count surfaced in `limitations` field | ✅ |
| Profile UUID not exposed in `limitations` text | ✅ CONFIRMED by test |
| No errors → no failure limitation added | ✅ |

---

## Family Dedup Hardening — Edge Cases

| Case | Test | Result |
|---|---|---|
| Active child action suppresses matching child recommendation | `test_active_child_action_suppresses_matching_child_recommendation` | ✅ |
| Active parent action does NOT suppress unrelated child recommendation | `test_active_parent_action_does_not_suppress_unrelated_child_recommendation` | ✅ |
| Caregiver alert + child attention item with different text → both in output | `test_caregiver_alert_and_child_attention_item_both_survive_when_different` | ✅ |
| Same risk across two profiles → one shared family suggestion (not two) | `test_same_risk_in_two_profiles_creates_one_shared_suggestion` | ✅ |
| Repeated profile_id in relationships → no duplicate recommendations | `test_repeated_profile_in_relationships_no_duplicate_recommendations` | ✅ |
| Same-case active action text → dedup triggered | `test_case_insensitive_dedup_against_active_actions` | ✅ |

---

## Test Results — Required Validation Suite

| Suite | Count | Result |
|---|---|---|
| `test_family_health_context.py` | 40 | **PASS** (+10 new: 6 dedup + 4 error visibility) |
| `test_family_context_data_population.py` | 18 | **PASS** |
| `test_family_relationships.py` | 17 | **PASS** |
| `test_narrative_reasoning.py` | (included) | **PASS** |
| `test_narrative_memory_service.py` | (included) | **PASS** |
| `test_api_narrative_memory.py` | (included) | **PASS** |
| `test_engagement_analytics.py` | (included) | **PASS** |
| `test_personalization_profile.py` | (included) | **PASS** |
| `test_adaptive_recommendation_scoring.py` | (included) | **PASS** |
| `test_notification_history_service.py` | (included) | **PASS** |
| `test_api_notification_status.py` | (included) | **PASS** |
| `test_notification_intelligence.py` | (included) | **PASS** |
| `test_api_notification_intelligence.py` | (included) | **PASS** |
| `test_lab_intelligence.py` | (included) | **PASS** |
| `test_api_lab_smoke.py` | (included) | **PASS** |
| `test_api_symptom_smoke.py` | (included) | **PASS** |
| `test_symptom_intelligence.py` | (included) | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | (included) | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Full backend suite (excl. dual_agent)** | **672** | **672/672 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures** |
| E2E / Playwright | — | **NOT RUN** |

---

## Cross-Profile Isolation Verification

| Check | Result |
|---|---|
| Evidence loading scoped to `owner_user_id` | ✅ |
| `load_errors_by_profile` keyed by `related_profile_id` only (not user ID) | ✅ |
| User-facing limitation text contains no profile UUIDs | ✅ CONFIRMED by test |
| Evidence load failure for profile A does not affect profile B's data | ✅ |

---

## Frontend Build Verification

| Check | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ CLEAN — all pages static/SSR, no errors |

---

## Known Limitations

- **E2E / Playwright**: NOT RUN. All tests are unit / API integration.
- **Real family data**: Tests use in-memory SQLite with synthetic profiles.
- **Evidence load error granularity**: `load_errors_by_profile` stores `"evidence_unavailable"` for all errors. Detailed error types not exposed to frontend (by design — privacy + simplicity).
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded. Unrelated to P9.

---

## Git

- Branch: `main`
- P8 foundation commit: `1c1717e` — `P8_FAMILY_HEALTH_ASSISTANT_FOUNDATION_READY`
- P8 verification commit: pending

---

---

# Previous Sprint Report — P4-REPORT-TO-ACTION-VERIFIED

Generated: 2026-05-20  
Classification: **`P4_REPORT_TO_ACTION_VERIFIED`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P4 data flow end-to-end verification | ✅ CONFIRMED |
| Task 2 — API smoke / regression confirmation | ✅ 16/16 PASS (↑1 stale confidence test added) |
| Task 3 — Dashboard LabInsightCard verification | ✅ CONFIRMED — stale indicator added, disclaimer present |
| Task 4 — Update active task report | ✅ THIS DOCUMENT |
| Task 5 — P5 Notification Intelligence planning | ✅ PLANNED (see below, NOT IMPLEMENTED) |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/health_assistant_service.py` | Bug fix: `recency` now computed from `report.report_date` (not `created_at`); added `date` import |
| `backend/tests/test_api_lab_smoke.py` | Added `test_stale_report_confidence_lower_than_recent`; fixed sequential client ordering |
| `frontend/app/components/platform/lab-insight-card.tsx` | Added `StaleBadge` component (visible even when collapsed); added `Clock` icon import |

---

## Test Results — Full Battery

| Suite | Count | Result |
|---|---|---|
| `test_lab_intelligence.py` | 82 | **PASS** |
| `test_api_lab_smoke.py` | 16 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **297** | **297/297 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures, unrelated to P4** |
| E2E / Playwright | — | **NOT RUN** |

---

## P4 Data Flow Confirmation

```
LabReportItem rows (DB, abnormal_flag IS NOT NULL)
    → health_assistant_service.py: build_evidence_bundle()
        → lab_report_items list (recency now computed from report_date ✅)
    → lab_intelligence_service.py: detect_lab_abnormalities()
        → groups by item_name
        → computes severity (flag → recurrence → alert corroboration)
        → classifies abnormality_type (lipid / glucose / uric_acid / fatty_liver_marker / kidney_stone_related_marker / …)
        → stale penalty: recency=older → confidence -0.10
        → stale warning appended to whyDetected text
        → returns list[LabAbnormality]
    → evidence bundle: lab_abnormalities key always present
    → get_action_recommendations()
        → high-severity lab abnormalities enter candidate pool at priority 75
        → trust layer applied
        → completed actions (status=done, completed_at ≤ 30d) deduped by rule_id
    → /recommendations response: lab_abnormalities key present
    → Dashboard LabInsightCard renders:
        → severity badge (red/amber/blue)
        → recurrence pill (if count > 1)
        → stale badge (if any evidenceSource.recency === 'older') ← NEW THIS SPRINT
        → suggested action (always visible)
        → whyDetected + evidence sources (expanded)
        → medical disclaimer
```

---

## Supported Lab Abnormality Types

| Type code | Markers covered |
|---|---|
| `lipid_abnormality` | LDL, HDL, TC, TG, 三酸甘油酯, Cholesterol, Triglyceride |
| `glucose_abnormality` | Blood Sugar, HbA1c, Glucose, 血糖, 糖化血色素 |
| `kidney_function` | Creatinine, eGFR, BUN, 肌酸酐, 腎功能 |
| `liver_function` | ALT, AST, GGT, ALP, Bilirubin, 肝功能 |
| `fatty_liver_marker` | 脂肪肝, Fatty Liver |
| `uric_acid` | 尿酸, Uric Acid |
| `kidney_stone_related_marker` | Oxalate, Calcium, 草酸, 膀胱石, Phosphate |
| `anemia_marker` | Hemoglobin, RBC, Hematocrit, 血色素 |
| `inflammation_marker` | CRP, ESR, WBC, 白血球 |
| `thyroid_function` | TSH, T3, T4, 甲狀腺 |
| `blood_pressure` | BP, Systolic, Diastolic, 血壓 |
| `lab_abnormality` | All other out-of-range markers (generic fallback) |

---

## Dashboard LabInsightCard Verification

| Check | Result |
|---|---|
| Component exists | ✅ `frontend/app/components/platform/lab-insight-card.tsx` |
| Imported in `health-assistant-panel.tsx` | ✅ line 9 |
| `LabInsightCard` rendered in panel | ✅ line 306: `<LabInsightCard abnormalities={data.lab_abnormalities ?? []} />` |
| Uses backend `LabAbnormality` type (not mock data) | ✅ `import type { LabAbnormality } from '../../../lib/api'` |
| `lab_abnormalities` key in frontend `HealthAssistantData` | ✅ `lab_abnormalities?: LabAbnormality[]` |
| Empty state rendered when no abnormalities | ✅ "目前無異常健檢指標" |
| Stale report warning displayed (new) | ✅ `StaleBadge` chip shown in collapsed card header when evidenceSource.recency === 'older' |
| Medical disclaimer | ✅ "以上分析由 AI 自動產生，僅供健康追蹤參考，不構成醫療診斷建議" |
| No diagnosis wording | ✅ (see Known Limitations) |
| `npx tsc --noEmit` | ✅ CLEAN |
| `npx next build` | ✅ SUCCESS |

---

## Known Limitations

- **No diagnosis wording**: `suggestedAction` copy uses action-oriented language ("建議諮詢醫師" not "診斷為X"); copy review against `docs/UI_FEEDBACK_STANDARDS.md` was not re-run this sprint — spot-checked only.
- **Recency uses `report_date`**: Fixed this sprint. Previous implementation used `created_at` (DB insert time), causing all reports to appear fresh in integration tests. Production behaviour was unaffected (reports imported from parsing use `report_date` which was already set correctly), but the test relied on the bug being absent.
- **Stale warning in body text only (before this sprint)**: Was embedded in `whyDetected`, only visible on expand. Now also shown as a collapsed-state chip badge.
- **Single-occurrence reports**: If a lab report has only 1 abnormal occurrence, severity cap = "medium" regardless of flag value (unless flag is "HH"/"LL"). This is intentional conservatism.
- **No trend charts**: Lab marker trends over time are not yet visualised. Planned for P5+.
- **E2E / Playwright tests**: NOT RUN. Smoke tests cover route-level behaviour only.
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded (`--ignore`).

---

## Git

- Branch: `main`
- P4 base commit: `d2eedc9` — `P4_REPORT_TO_ACTION_BRIDGE_READY`
- This sprint commit: pending (P4_REPORT_TO_ACTION_VERIFIED)

---

# P5 Notification Intelligence — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P5).  
> **Scope**: Proactive notification layer bridging daily health insights to user-facing alerts.  
> **No notification code added this sprint.**

### Problem Statement

The recommendation pipeline (`health_assistant_service.py`) currently produces prioritised recommendations on-demand (user opens dashboard). There is no mechanism to:
- Proactively alert the user when a new high-severity finding appears
- Respect quiet hours or notification fatigue thresholds
- Escalate unacknowledged critical alerts
- Learn from snooze/dismiss behaviour to adjust timing

### Required Behaviours

| # | Requirement | Priority |
|---|---|---|
| N1 | High-severity lab/device/symptom finding → push notification | P0 |
| N2 | Notification deduplication — same rule_id not re-notified within cooldown window | P0 |
| N3 | User-configurable quiet hours | P1 |
| N4 | Snooze → re-surface after snooze_duration | P1 |
| N5 | Persistent dismiss → suppress for 30 days | P1 |
| N6 | Escalation → higher-priority notification channel | P1 |
| N7 | Alert fatigue guard: max N notifications per day per person | P1 |
| N8 | Learn from ignore patterns: ignored N times → reduce channel priority | P2 |
| N9 | Notification history in DB for audit/compliance | P2 |

### Proposed Architecture

```
Daily assistant run / cron / real-time trigger
    ↓
notification_intelligence_service.py  (NEW)
    filter_notifiable_findings(evidence_bundle, prefs, notification_log)
        → only findings that exceed priority threshold
        → dedup against NotificationLog within cooldown
        → respect quiet_hours and daily_cap
        ↓
    rank_notifications(candidates)
        → sort by: severity DESC, source_priority DESC, last_seen ASC
        ↓
    build_notification_payload(ranked)
        → title, body, action_url, priority_level, rule_id
        ↓
NotificationLog DB row (status: pending → sent → acked/snoozed/dismissed)
    ↓
delivery_adapter (abstraction)
    → web push (Phase 1)
    → LINE / email (Phase 2)
    → in-app bell (already exists via notification-bell.tsx)
```

### New DB Tables Required

```sql
CREATE TABLE notification_log (
    id              UUID PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    person_id       INTEGER REFERENCES person_profiles(id),
    rule_id         VARCHAR(80),
    channel         VARCHAR(20),   -- 'web_push' | 'email' | 'in_app'
    priority_level  VARCHAR(10),   -- 'critical' | 'high' | 'medium' | 'low'
    title           TEXT,
    body            TEXT,
    action_url      TEXT,
    status          VARCHAR(20),   -- 'pending' | 'sent' | 'acked' | 'snoozed' | 'dismissed'
    snooze_until    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    acked_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notification_preferences (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id),
    quiet_start     TIME,          -- e.g. 22:00
    quiet_end       TIME,          -- e.g. 08:00
    daily_cap       INTEGER DEFAULT 5,
    min_priority    VARCHAR(10) DEFAULT 'medium',
    channels        JSONB          -- {"web_push": true, "email": false, "in_app": true}
);
```

### Priority Scoring

| Source type | Base priority | Escalation modifier |
|---|---|---|
| `device_escalation` (critical) | critical | +2 |
| `lab_abnormality` (high severity) | high | +1 if recurrence ≥ 3 |
| `symptom_pattern` (high severity) | high | +1 if worsening trend |
| `lab_abnormality` (medium) | medium | — |
| `symptom_pattern` (medium) | medium | — |
| All others | low | — |

### Cooldown Windows

| Priority | Cooldown | Dismiss suppress |
|---|---|---|
| critical | 6 hours | 7 days |
| high | 24 hours | 30 days |
| medium | 72 hours | 30 days |
| low | 7 days | 90 days |

### Alert Fatigue Guard

- Per-person daily cap (default: 5 notifications/day across all channels)
- Per-rule_id dedup: same rule not re-surfaced until cooldown expires
- Snooze learning: if snoozed ≥ 3 times → auto-downgrade channel priority for that rule

### Out of Scope for P5

- AI-generated notification copy (P6)
- Multi-language notification content (P6)
- SMS delivery (P6)
- Apple Watch / wearable push (future)

### Next Sprint Prompt (P5 kickoff)

```
PersonalHealthOS P5 — Notification Intelligence

Context:
  P4_REPORT_TO_ACTION_VERIFIED complete (297/297 tests pass).
  Evidence bundle: lab_abnormalities, symptom_patterns, device_escalation all wired.
  Daily assistant: get_action_recommendations() produces prioritised top-3.

Goal:
  Implement notification_intelligence_service.py and NotificationLog DB table.
  Wire into daily assistant and /recommendations endpoint.
  Add notification preference model.
  Expose /api/v1/notifications/ CRUD endpoints.
  No frontend push integration yet — in-app bell only (notification-bell.tsx already exists).

Must deliver:
  - notification_intelligence_service.py with filter/rank/build functions
  - NotificationLog SQLAlchemy model + migration
  - NotificationPreferences model
  - test_notification_intelligence.py: 20+ pure-function tests
  - test_api_notification_smoke.py: 8+ route tests
  - Full regression: all 297 existing tests still pass
  - npx tsc --noEmit CLEAN
  - npx next build PASS
  - Commit: P5_NOTIFICATION_INTELLIGENCE_READY

P5 NOT IMPLEMENTED as of this commit.
```

---


|---|---|
| Task 1 — Symptom data flow integrity (code review) | ✅ CONFIRMED |
| Task 2 — API smoke tests for symptom intelligence | ✅ 14/14 PASS |
| Task 3 — `npx tsc --noEmit` + `npx next build` | ✅ CLEAN / BUILD OK |
| Task 4 — Report-to-Action Bridge planning spec | ✅ DOCUMENTED (NOT IMPLEMENTED) |

### Test results — full battery

| Suite | Tests | Result |
|---|---|---|
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **199** | **199/199 PASS** |

### Data flow confirmation

- `SymptomLog` DB rows → `build_evidence_bundle()` reads last 90 days of symptoms  
- `build_symptom_timeline()` groups rows → produces `symptom_timeline` list in bundle  
- `detect_symptom_patterns()` analyses timeline → produces `symptom_patterns` list in bundle  
- `/evidence-bundle` response always includes `symptom_timeline` + `symptom_patterns` keys  
- High-severity patterns enter `get_action_recommendations()` candidate pool (priority 65)  
- `/recommendations` response always includes `symptom_patterns` key  
- `SymptomInsightCard` renders patterns in `health-assistant-panel.tsx`

### Frontend build

- `npx tsc --noEmit`: **CLEAN** (0 errors)  
- `npx next build`: **SUCCESS** — all pages compiled, static output generated

### Known limitations (carried forward)

- Symptom intelligence computed request-time only; no historical pattern DB table  
- E2E / Playwright tests: NOT RUN  
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, always excluded  
- Report-to-Action Bridge: NOT IMPLEMENTED (see spec below)

### Git

- Branch: `main`  
- This sprint: `test_api_symptom_smoke.py` (14 tests) + this report  

---

## Report-to-Action Bridge — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P4).  
> **Scope**: Bridge between parsed lab report items and the recommendation / decision pipeline.

### Problem statement

Lab reports are parsed and stored as `LabReportItem` rows.  Currently they
inform the `evidence_bundle` but do **not** automatically produce prioritised
action items.  The clinician's intent is: _an abnormal lab result → patient
knows what to do next_.

### Required behaviours

| # | Requirement | Priority |
|---|---|---|
| 1 | Lab abnormality → decision item in `recommendations` | P0 |
| 2 | Lab abnormality → a specific recommended next action | P0 |
| 3 | Repeated abnormal result for same marker → higher recommendation priority | P1 |
| 4 | Completed or active action for same marker → deduplicate (no double-surfacing) | P1 |
| 5 | Each recommendation includes full evidence source traceability | P1 |
| 6 | No medical diagnosis wording — all copy reviewed against `ui-feedback-standards.md` | P0 |

### Proposed architecture

```
LabReportItem rows (DB)
    ↓
build_lab_evidence()          ← new function in lab_intelligence_service.py
    ↓
detect_lab_abnormalities()    ← new function; returns list[LabAbnormality]
    ├─ compares value vs reference_range
    ├─ checks historical recurrence (count of same marker out-of-range)
    └─ deduplicates against existing ActionItem DB rows
    ↓
get_action_recommendations()  ← existing; add "lab_abnormality" source type
    priority score: 75 (above device_signal=70)
    rule_id: "lab_abnormality_{marker_name}"
    ↓
/recommendations response      ← new key: "lab_abnormalities"
    ↓
LabInsightCard (new component) ← renders in health-assistant-panel.tsx
```

### Concrete next-sprint tasks

1. **`lab_intelligence_service.py`** — implement `build_lab_evidence()` and `detect_lab_abnormalities()`:
   - Input: `LabReportItem` list from DB query
   - Output: `list[LabAbnormality]` — each with `markerName`, `value`, `unit`, `referenceRange`, `severity` (low/medium/high), `recurrenceCount`, `suggestedAction`, `evidenceSources`
   - Severity mapping: ≥2× out-of-range = high, 1× = medium, borderline = low
   - No hallucination: only markers actually present in `LabReportItem` inputs

2. **`health_assistant_service.py`** — integrate `detect_lab_abnormalities()` into `build_evidence_bundle()`:
   - Add `"lab_abnormalities"` key to bundle return
   - Add `"lab_abnormality"` to `_SOURCE_PRIORITY` at 75
   - Add `elif src_type == "lab_abnormality":` case in `_build_recommendation_from_candidate()`

3. **Deduplication** — before returning recommendations, check `ActionItem` DB for existing active items with matching `rule_id`; skip if found within 7 days

4. **`LabInsightCard` component** — `frontend/app/components/platform/lab-insight-card.tsx`:
   - Renders each abnormality with severity badge, recurrence count, suggested action
   - Links to source lab report
   - Identical medical-disclaimer footer as `SymptomInsightCard`
   - Loading skeleton + empty state

5. **Tests** (`test_lab_intelligence.py` — 20 pure-function tests + `test_api_lab_smoke.py` — 8 route tests):
   - No abnormalities → empty list (anti-hallucination)
   - Single out-of-range → medium severity
   - Repeated out-of-range → high severity + recurrenceCount
   - Existing ActionItem → deduplication suppresses recommendation
   - All required schema keys present
   - No medical diagnosis wording (keyword blacklist check)

6. **Copy review** — audit all `suggestedAction` and `label` strings against `docs/UI_FEEDBACK_STANDARDS.md` blacklist before merge

### Out of scope for P4

- Trend charts for lab markers (P5)
- Integration with external reference range APIs (P5)
- GP/clinician report generation (future)

---

# Previous Report — P3-SYMPTOM-INTELLIGENCE-READY

Generated: 2026-05-21  
Classification: **`P3_SYMPTOM_INTELLIGENCE_READY`**

---

## Summary

P3 Symptom Intelligence layer is complete and production-merged on `main`.

### What was built

| Component | File | Status |
|---|---|---|
| `build_symptom_timeline()` | `backend/app/services/symptom_intelligence_service.py` | ✅ |
| `detect_symptom_patterns()` | same | ✅ |
| Wire into recommendation pipeline | `backend/app/services/health_assistant_service.py` | ✅ |
| `SymptomInsightCard` | `frontend/app/components/platform/symptom-insight-card.tsx` | ✅ |
| `SymptomPattern` type | `frontend/lib/api.ts` | ✅ |
| `health-assistant-panel.tsx` update | `frontend/app/components/platform/health-assistant-panel.tsx` | ✅ |
| 24 pure-function tests | `backend/tests/test_symptom_intelligence.py` | ✅ 24/24 |

### Validation results

| Suite | Result |
|---|---|
| `test_symptom_intelligence.py` | **24/24 PASS** |
| Full backend (excl. dual_agent) | **246/246 PASS** |
| `npx tsc --noEmit` | **CLEAN** |

### Architecture

- **`build_symptom_timeline`** — groups SymptomLog dicts by symptom name, computes firstSeenAt/lastSeenAt/recurrenceCount, severityTrend (oldest-half avg vs newest-half avg, ±1.5 threshold), relatedDeviceSignals and relatedLabItems via predefined keyword correlation maps (no hallucination guarantee — only returns items actually present in inputs).
- **`detect_symptom_patterns`** — emits up to 5 pattern types per symptom: `recurring_symptom` (≥3 occurrences), `worsening_symptom` (trend==worsening), `symptom_with_device_signal`, `symptom_with_lab_risk`, `unresolved_high_severity_symptom` (severity ≥ 8). Confidence bounded [0.20, 0.90]. No pattern without supporting data.
- **Recommendation bridge** — high-severity patterns enter the `get_action_recommendations()` candidate pool at priority score 65 (between `device_signal=70` and `insight=60`). Rule IDs: `symptom_pattern_{patternType}_{symptomType}`.
- **`SymptomInsightCard`** — shows severity-coded pattern cards with confidence bar, related signal/lab tag chips, suggested action, and medical disclaimer.

### Known limitations
- Symptom timeline computed from current 90-day evidence bundle only (no separate historical DB table).
- E2E / Playwright tests not run.
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, excluded.

### Git
- Branch: `main`
- Commit: `42fc0f9` — `feat: P3_SYMPTOM_INTELLIGENCE_READY`

---

# Previous Report — P2-DEVICE-ESCALATION-VERIFIED-AND-SAFEGUARDED

Generated: 2026-05-20  
Classification: **`P2_DEVICE_ESCALATION_VERIFIED_AND_SAFEGUARDED`**

---

## Summary

This sprint verified and safeguarded the P2 Device Escalation Layer completed in
the prior session.  No new features were added.  Focus was on git safety, data
flow verification, automated smoke testing, and honest limitation documentation.

---

## Task 1 — Git Safety

| Item | Result |
|---|---|
| `git status` before init | `fatal: not a git repository` |
| `.gitignore` created | ✅ Excludes `.venv/`, `node_modules/`, `.next/`, `.env`, `runtime/snapshots/`, runtime locks |
| `git init` | ✅ |
| `git add .` — excluded files verified | ✅ No `.env`, `.venv`, `node_modules`, `.next`, `snapshots` committed |
| Initial commit | ✅ `ab977a6 chore: initial commit — P2_DEVICE_ESCALATION_LAYER_READY` |
| Runtime orchestrator locks untracked | ✅ `git rm --cached` + .gitignore update |
| Final `git status` | ✅ `nothing to commit, working tree clean` |
| `git log --oneline` | `0df1cb5 chore: untrack runtime lock files from index` → `2c5d36e` → `ab977a6` |

---

## Task 2 — Device Escalation Data Flow Verification

Verified end-to-end by code inspection + automated smoke tests:

```
external_metrics (HealthMetric rows, source != 'manual')
  → detect_device_signals()            ← device_signals in bundle ✅
  → build_device_signal_history()      ← device_signal_history in bundle ✅
  → evaluate_signal_escalation()       ← device_escalation in bundle ✅
  → build_evidence_bundle()
  → get_action_recommendations()       ← device_escalation in return ✅
  → generate_daily_health_summary()    ← escalation key injected when level != none ✅
  → frontend DeviceSignalCard          ← escalation prop consumed ✅
```

| Check | Result |
|---|---|
| `bundle["device_signals"]` present | ✅ |
| `bundle["device_signal_history"]` present | ✅ computed, NOT persisted to DB |
| `bundle["device_escalation"]` present | ✅ |
| `get_action_recommendations()` returns `device_escalation` | ✅ |
| `generate_daily_health_summary()` uses escalation for topRisk / todayAction | ✅ |
| `EscalationDecision` type in `frontend/lib/api.ts` | ✅ |
| `DeviceSignalCard` receives and renders `escalation` prop | ✅ |
| Medical disclaimer shown when signals or escalation present | ✅ |
| Stale-all cap at "watch" | ✅ |

---

## Task 3 — API Smoke Tests

**New file:** `backend/tests/test_api_escalation_smoke.py` — 12 tests

| Class | Tests | Result |
|---|---|---|
| `TestDeviceSignalsEndpoint` | schema keys, empty=no signals, elevated HR→signal, signal key shapes | **4/4 PASS** |
| `TestEvidenceBundleEndpoint` | device_escalation key, schema, no-signal=none, elevated HR raises level, device_signal_history present | **5/5 PASS** |
| `TestDailySummaryEndpoint` | base keys, no-signal=no escalation key, elevated HR may inject escalation | **3/3 PASS** |

Note: Tests use in-memory SQLite with real FastAPI TestClient.  An `autouse`
fixture clears `app.dependency_overrides` after each test to prevent cross-test
contamination.

---

## Required Validation — Full Results

| Test file | Count | Result |
|---|---|---|
| `test_device_signal_escalation.py` | 24 | **24 PASS** |
| `test_device_signal_detection.py` | 21 | **21 PASS** |
| `test_health_assistant_service.py` | ~40 | **PASS** |
| `test_daily_summary_service.py` | ~20 | **PASS** |
| `test_recommendation_trust_service.py` | ~20 | **PASS** |
| `test_outcome_feedback_service.py` | ~20 | **PASS** |
| **Full backend (excl. orchestrator)** | **222** | **222 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **PRE-EXISTING FAILURES — excluded** |
| `npx tsc --noEmit` | — | **PASS** |
| `npx next build` | — | **PASS** |
| E2E / Playwright browser smoke | — | **NOT RUN** |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `.gitignore` | Created — excludes secrets, venv, node_modules, runtime locks |
| `backend/tests/test_api_escalation_smoke.py` | Created — 12 API smoke tests |

(All P2 escalation service + UI files were created in the prior session.)

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **DB persistence NOT implemented** | `device_signal_history` is computed deterministically from `HealthMetric` rows at request time.  There is NO separate history table, no trend DB, no long-term memory store.  "Trend memory" means recurrence is inferred across time-bucketed rows from the same table. |
| **E2E not run** | No Playwright / browser smoke tests executed.  Frontend verified by `tsc --noEmit` + `next build` only. |
| **Orchestrator failures pre-existing** | `test_dual_agent_orchestrator.py` — 10 PLANNER_SKIP_SAFE_RUN failures exist before this sprint and are not caused by escalation changes. |
| **No remote git** | Repo is local only.  No remote configured, no CI/CD triggered. |
| **Escalation is session-scoped** | Each API call recomputes escalation from available metrics.  There is no cross-session escalation state. |

---

## Previous Report — P2-DEVICE-SIGNAL-INTELLIGENCE

# Active Task Report — P2-DEVICE-SIGNAL-INTELLIGENCE

Generated: 2026-05-20  
Classification: **`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`**

---

## Pre-step Results

| Step | Result |
|---|---|
| Snapshot path | `runtime/snapshots/backend.app.20260520-HHMM.tgz` (created before any change) |
| `HealthMetric.source` field confirmed | ✅ String(40), default='manual' |
| `HealthMetric.spo2` column exists | ❌ Not present — handled gracefully (no hallucination) |

---

## Modified / Created Files

| File | Action |
|---|---|
| `backend/app/services/device_signal_detection_service.py` | **CREATED** — pure-function detection: elevated HR, pulse trend, low sleep, reduced activity, SpO₂ placeholder |
| `backend/app/services/health_assistant_service.py` | **MODIFIED** — import + enrich external_metrics with raw values + `detect_device_signals` call + `device_signals` in bundle + `_SOURCE_PRIORITY["device_signal"]=70` + candidate generation + recommendation builder handler + return `device_signals` |
| `backend/app/api/health_assistant.py` | **MODIFIED** — import + new `GET /health-assistant/device-signals` endpoint |
| `backend/tests/test_device_signal_detection.py` | **CREATED** — 21 tests covering all 9 spec scenarios |
| `frontend/lib/api.ts` | **MODIFIED** — `DeviceSignal` type + `getDeviceSignals()` |
| `frontend/app/components/platform/device-signal-card.tsx` | **CREATED** — severity badges, freshness, confidence %, empty state |
| `frontend/app/components/platform/health-assistant-panel.tsx` | **MODIFIED** — import + `device_signals?` in HealthAssistantData + render section |

---

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `detect_device_signals([])` returns `[]` | [Confirmed] |
| elevated_resting_heart_rate detected (HR ≥ 90) | [Confirmed] |
| abnormal_pulse_trend detected (≥ 3 ascending readings) | [Confirmed] |
| low_sleep_duration detected (< 7 h) | [Confirmed] |
| reduced_activity detected (< 5000 steps) | [Confirmed] |
| unstable_spo2 — no hallucination (no column) | [Confirmed] |
| Stale → confidence × 0.70 | [Confirmed] |
| ≥ 3 repeated abnormal → severity escalates to high | [Confirmed] |
| Device signal surfaces in Top-3 recommendations | [Confirmed] |
| `/health-assistant/device-signals` endpoint | [Confirmed] |
| `DeviceSignal` TS type + `getDeviceSignals()` API | [Confirmed] |
| `DeviceSignalCard` + empty state rendered in panel | [Confirmed] |
| `npx tsc --noEmit` PASS | [Confirmed] |
| `npx next build` PASS | [Confirmed] |

---

## Test Results

```
test_device_signal_detection.py  — 21 passed
Full backend regression           — 186 passed, 4 warnings
frontend tsc --noEmit             — PASS
frontend next build               — PASS
```

---

## Risks / Next Steps

| Item | Note |
|---|---|
| SpO₂ signal | No `spo2` column yet. Placeholder comment in service. Implement when schema column added. |
| Pulse trend / elevated HR co-signal | Trend only emits when HR < 90 to avoid double-counting. |
| Frontend empty state | Does NOT claim any device is connected — neutral guidance only. |

---

## Final Classification

`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`

---

# Previous Report — P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS

Generated: 2026-05-20

---

## 前置步驟結果

### Step 1 — Snapshot

```
runtime/snapshots/backend.app.20260520-1218.tgz  (180K)
```
Status: **DONE** [Confirmed]

### Step 2 — source 欄位確認

```
backend/app/models/entities.py:93
class HealthMetric:
    source = Column(String(40), default='manual')
```
Status: **CONFIRMED** — `HealthMetric.source` 欄位存在，型別 `String(40)`，預設值 `'manual'`。

### Step 3 — 原始 external_metrics 邏輯

```python
# 原始 (修改前)
"external_metrics": [],  # populated by external_metrics_service if needed
```
原因：hardcoded 空陣列，從未被填入任何資料。

---

## 修改檔案清單

| 檔案 | 修改內容 |
|---|---|
| `backend/app/services/health_assistant_service.py` | 新增 `_freshness_label()` 函式、`_EXTERNAL_RELIABILITY` 對照表、`_DEFAULT_EXTERNAL_RELIABILITY`；在 `build_evidence_bundle` 的 health_metrics 迴圈後新增 external_metrics 抽取邏輯；將 `"external_metrics": []` 替換為 `"external_metrics": external_metrics` |
| `backend/tests/test_health_assistant_service.py` | 新增 `_make_external_metric()` helper、`test_external_metrics_happy_path`、`test_external_metrics_empty_when_all_manual`、`test_external_metrics_stale_freshness` 三個新測試 |
| `runtime/snapshots/backend.app.20260520-1218.tgz` | 新增 snapshot（唯讀備份） |

**未修改任何其他檔案。** frontend、models、API endpoint 簽名均未動。

---

## 驗收標準逐項對應

| 驗收標準 | 結果 |
|---|---|
| 1. 含 source-tagged metrics 的使用者，`external_metrics` 為非空陣列 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 2. 每筆含 `source`, `timestamp`, `freshness`, `reliability`, `summary` | **[Confirmed]** — `test_external_metrics_happy_path` 驗證所有欄位 |
| 3. 無 source-tagged metrics 時，`external_metrics` 保持 `[]` 且不報錯 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4a. happy path 測試 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 4b. empty path 測試 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4c. stale freshness 測試 | **[Confirmed]** — `test_external_metrics_stale_freshness` PASS |
| 5. 既有 backend tests 全綠（無回歸） | **[Confirmed]** — 165 passed (excluding pre-existing orchestrator failures) |
| 6. `npx tsc --noEmit` PASS | **[Confirmed]** — exit code 0 |

---

## 測試輸出摘要

### test_health_assistant_service.py (18 tests)
```
18 passed in 0.43s
```
新增測試：
- `test_external_metrics_happy_path`        PASS
- `test_external_metrics_empty_when_all_manual`  PASS
- `test_external_metrics_stale_freshness`   PASS

### 全 backend suite（不含 orchestrator）
```
165 passed, 4 warnings in 2.23s
```

### Orchestrator pre-existing failures（與本任務無關）
```
10 failed in test_dual_agent_orchestrator.py
原因: PLANNER_SKIP_SAFE_RUN vs CREATED — 環境問題，非本任務造成
```

### Frontend tsc
```
npx tsc --noEmit → exit 0
```

---

## 實作細節

### `_freshness_label(dt)` 邏輯
- `None` → `"unknown"`
- 距今 ≤ 86400 秒（24 h）→ `"fresh"`
- 距今 > 86400 秒 → `"stale"`

### `_EXTERNAL_RELIABILITY` 對照表
| source | reliability |
|---|---|
| apple_health | 0.90 |
| google_fit | 0.88 |
| omron | 0.88 |
| wearable / fitbit / garmin / samsung / withings | 0.85 |
| 未知來源 | 0.80 (fallback) |

### external_metrics 抽取邏輯
- 從現有 `metric_rows`（30 天查詢）中篩選 `source != 'manual'`
- 不新增額外 DB query
- 每筆回傳：`source`, `timestamp` (ISO8601), `freshness`, `reliability`, `summary`
- `summary` 格式：`[{source}] 血壓 130/85、血糖 95.0、體重 70.5kg、...`

---

## 風險 / Unknown / 後續建議

| 項目 | 說明 |
|---|---|
| 真實資料庫中的 source 值多樣性 | 目前 source 欄位為 free-text String(40)，沒有 ENUM 約束。若真實資料中出現非預期 source 值（如 `"Withings"` 大寫），會走 fallback reliability 0.80。建議未來在資料入口統一 lowercase normalize。 |
| external_metrics 未加入 `missing_data` 提示 | 設計決定：external metrics 是補充資料，非必填，不適合觸發 missing_data 警告。 |
| freshness 邊界 24h | 目前 "fresh" = 24h 內。若 wearable 每小時同步，這個邊界合理。但若使用場景改為「當天」概念，建議改為 calendar day boundary。 |
| orchestrator 10 tests 失敗 | 與本任務完全無關，為 `PLANNER_SKIP_SAFE_RUN` 環境設定問題，不在本任務修改範圍。 |
| E2E / API integration test | 未執行 live API call 驗證，unit tests 覆蓋邏輯層，但真實 DB 回傳的 source 值尚未在 staging 驗證。 |

---

## Final Classification

**`P0_EVIDENCE_EXTERNAL_METRICS_DONE`**
