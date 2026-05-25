# P50 Frontend Auth Smoke Local Stability Diagnosis

**Date:** 2026-05-25  
**Task:** P50-FRONTEND-AUTH-SMOKE-DIAGNOSIS  
**Branch:** `main` @ HEAD `62b791f`  
**Final Classification:** `P50_FRONTEND_AUTH_SMOKE_STABILIZED`

---

## 1. Branch Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo root | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | `62b791f` — "docs(report): P49 frontend auth e2e handoff report" ✅ |
| Dirty files | `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (expected CTO/CEO outputs) ✅ |
| Unexpected dirty | None ✅ |

---

## 2. Evidence Collection (Checklist A)

### Port State (pre-diagnosis)
```
:3010  — NONE (free)
:3000  — node PID 2991 LISTEN (unrelated dev process)
:8000  — Python PID 5519 LISTEN (backend uvicorn)
```

### Build State (pre-diagnosis)
```
ls -la frontend/.next/BUILD_ID
  → BUILD_ID MISSING
```

`.next/` directory existed but was **incomplete** — no `BUILD_ID`, no `server/app/` directory. Only had pages-router artifacts from a previous incomplete/dev build (mtime: May 25 09:21).

### Playwright Config (`frontend/playwright.config.ts`)
```typescript
webServer: {
  command: 'node_modules/.bin/next start --hostname 127.0.0.1 --port 3010',
  url: 'http://127.0.0.1:3010',
  reuseExistingServer: false,
  timeout: 120000,
}
```

### Env State
- `.env.local` present: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (47 bytes)
- No `NEXT_*`, `NODE_*`, or `PLAYWRIGHT_*` env vars in shell
- Missing optional vars: `NEXT_PUBLIC_ENABLE_ANALYTICS`, `NEXT_PUBLIC_ERROR_TRACKING_DSN` (non-critical)

---

## 3. Timeout Type Classification (Checklist B)

**Classification: B2 — Server crash, Playwright can't connect**

Direct probe:
```
$ timeout 10 node_modules/.bin/next start --hostname 127.0.0.1 --port 3010
  ▲ Next.js 14.2.32
  - Local:        http://127.0.0.1:3010
  ✓ Starting...
  Error: Could not find a production build in the '.next' directory.
  Try building your app with 'next build' before starting the production server.
  https://nextjs.org/docs/messages/production-start-no-build-id
  EXIT: 1
```

`next start` exits immediately (< 1s) with exit code 1. Playwright's `webServer` spawns the process and polls the `url` until the process becomes ready, but since it crashes immediately, the URL never responds. Playwright retries polling until the 120s timeout elapses — hence "Timed out waiting 120000ms from config.webServer".

This is **NOT** a slow startup (B1) and **NOT** a hang (B3). It is a **deterministic crash on missing `BUILD_ID`**.

---

## 4. Five-Item Checklist (Checklist C)

### C1. Build State ✅ ROOT CAUSE FOUND — STOP

**Status:** `BUILD_ID` **missing** from `frontend/.next/`

**Action:** `cd frontend && npx next build`

**Build result:**
```
  ▲ Next.js 14.2.32
  - Environments: .env.local
  Creating an optimized production build ...
  ✓ Compiled successfully
  ✓ Collecting page data
  ✓ Generating static pages (37/37)
  ✓ Collecting build traces
  ✓ Finalizing page optimization

  Route (app)   — 16 routes (SSG)
  Route (pages) — 20 routes (SSG)
```

**Post-build BUILD_ID:**
```
frontend/.next/BUILD_ID  →  mmhAYpkD9M5aFIXDq1iZa
mtime: May 25 11:45
size: 21 bytes
```

Root cause locked at C1. Remaining items C2–C5 not required per checklist protocol.

### C2. Port Conflict — SKIPPED (C1 resolved)
Port `:3010` was free (confirmed). No conflict.

### C3. Manual `next start` — Confirmed AFTER FIX
```
$ node_modules/.bin/next start --hostname 127.0.0.1 --port 3010
  ▲ Next.js 14.2.32
  ✓ Starting...
  ✓ Ready in 438ms
$ curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:3010/
  200
```
Startup time: **438ms**. HTTP 200 confirmed. Well within 120s timeout.

### C4. Readiness URL — SKIPPED (C1 resolved)
`playwright.config.ts` `url: 'http://127.0.0.1:3010'` matches what `next start` binds. No mismatch.

### C5. Env — SKIPPED (C1 resolved)
`.env.local` contains `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. Missing optional analytics vars — not blocking.

---

## 5. Root Cause Summary

| Item | Finding |
|------|---------|
| Root cause | `frontend/.next/BUILD_ID` missing → `next start` exits with code 1 immediately |
| Why missing | Previous dev session ran `next dev` which does not write `BUILD_ID`; or build was never run in this checkout state |
| Playwright behavior | Polls `url` until 120s, unaware that process already died |
| Error message seen | "Timed out waiting 120000ms from config.webServer" (misleading — actually a crash, not a timeout) |
| Fix | `cd frontend && npx next build` |

---

## 6. Fix Applied

**Minimal, one-time fix:** `npx next build` run inside `frontend/` to create production build artifacts including `BUILD_ID`.

No config files were modified. No `playwright.config.ts` timeout changes needed (438ms startup is far within 120s limit).

---

## 7. Verification Results

### `make frontend-auth-smoke` (post-fix)
```
Running 6 tests using 1 worker
  6 passed (11.7s)
```

### `make runtime-smoke` (regression check)
```
3 passed, 4 warnings
41 passed, 2 skipped, 4 warnings
29 passed, 4 warnings
57 passed, 4 warnings
Total: 130 passed, 2 skipped ✅
```

---

## 8. Files Modified

| File | Change |
|------|--------|
| `docs/security/P50_FRONTEND_AUTH_SMOKE_STABILITY.md` | Created (this file) |
| `00-Plan/roadmap/active_task_report.md` | P50 block prepended |
| `frontend/.next/` | Production build artifacts created (not tracked by git) |

No `playwright.config.ts`, `Makefile`, fixture, or app code was changed.

---

## 9. Known Limitations / Unknowns

| Item | Status |
|------|--------|
| Build staleness | `.next/` is not in `.gitignore` checked; if git-ignored, dev must always run `npm run build` before smoke test |
| Why prior build was missing | Unknown — likely `next dev` was last run, or `frontend/.next/` was cleared. Not reproducible now. |
| Makefile `frontend-auth-smoke` | Has `# Frontend built: cd frontend && npm run build` comment — prerequisite documented but not enforced |
| Optional env vars | `NEXT_PUBLIC_ENABLE_ANALYTICS` and `NEXT_PUBLIC_ERROR_TRACKING_DSN` absent; no test failure observed |

---

## 10. Final Classification

**`P50_FRONTEND_AUTH_SMOKE_STABILIZED`**

- Local `make frontend-auth-smoke`: **6/6 PASS** (11.7s)
- `make runtime-smoke`: **130/2 PASS** — no regression
- Fix type: **build artifact creation** (config-only, no app code changed)
- Fix durability: Stable until `.next/` is cleared again — dev must run `npm run build` before smoke tests
