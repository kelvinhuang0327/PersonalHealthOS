# P48 — CI Runtime Smoke Alignment

**Stage**: P48  
**Classification**: P48_CI_RUNTIME_SMOKE_ALIGNED  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `a6a64c9` (P47 closure)  
**Date**: 2026-05-24  

---

## 1. Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean ✅ |
| HEAD | `a6a64c9` (P47 closure) ✅ |

---

## 2. Investigation: CI Command Inventory

### CI Frontend Job (`.github/workflows/ci-cd.yml`)
| Step | Command | Type |
|------|---------|------|
| Install | `npm ci` | deps |
| ~~TypeScript~~ | ~~none~~ | ~~gap (pre-P48)~~ |
| Lint | `npm run lint` | ESLint only |
| Build | `npm run build` | Next.js build (`ignoreBuildErrors: true` → no tsc gate) |
| Playwright install | `npx playwright install --with-deps chromium` | browsers |
| E2E | `npm run e2e:ci` | 3 mocked specs (no backend) |

### CI Backend Job (`.github/workflows/ci-cd.yml`)
| Step | Command | Type |
|------|---------|------|
| Install | `pip install -r requirements-dev.txt` | deps |
| Tests | `PYTHONPATH=. python -m pytest -q` | **full suite — 983 passed, 2 skipped** |

---

## 3. runtime-smoke Stage Coverage Comparison (Pre-P48)

| runtime-smoke Stage | Local Gate | CI Coverage (pre-P48) |
|---------------------|------------|------------------------|
| Stage 1: health (`test_runtime_smoke.py`, 3 tests) | ✅ `make runtime-smoke` | ✅ CI full suite (superset) |
| Stage 2a: `backend-auth-audit` (41 tests, 2 skip) | ✅ `make security-smoke` | ✅ CI full suite (superset) |
| Stage 2b: `frontend-tsc` (`npx tsc --noEmit`) | ✅ `make security-smoke` | ❌ `ignoreBuildErrors: true` — tsc not enforced |
| Stage 3: config-smoke (29 tests) | ✅ `make config-smoke` | ✅ CI full suite (superset) |
| Stage 4: validation-smoke (57 tests) | ✅ `make validation-smoke` | ✅ CI full suite (superset) |
| **P47 token policy tests** (12 tests in stage 2a) | ✅ `backend-auth-audit` | ✅ CI full suite (superset) |

**Pre-P48 summary**: CI backend was SUPERSET (983 ⊇ 130 backend tests). CI frontend-tsc was MISSING — `next.config.mjs` sets `typescript: { ignoreBuildErrors: true }`, silently suppressing TypeScript errors in `npm run build`.

---

## 4. Root Cause of tsc Gap

**File**: `frontend/next.config.mjs`  
```js
typescript: { ignoreBuildErrors: true },
eslint: { ignoreDuringBuilds: true },
```

`npm run build` (`next build`) would normally run TypeScript type-checking, but `ignoreBuildErrors: true` suppresses all TS errors and allows the build to succeed regardless. CI's `npm run lint` is ESLint only — does not check types.

Result: before P48, no CI gate caught TypeScript regressions. Only `make frontend-tsc` (local) enforced this.

---

## 5. Selected Option: A — Align CI Frontend with `frontend-tsc`

Added `npx tsc --noEmit` as an explicit step in the CI frontend job, after `npm ci` and before lint/build. This is:
- **Safe**: `npm ci` already installs `typescript`; tsc passes locally with exit 0
- **Minimal**: single step, no new deps, no services
- **Equivalent to `make frontend-tsc`**: same command, same scope

### Change Applied

**`.github/workflows/ci-cd.yml`** — frontend job:

**Before**:
```yaml
      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint
```

**After**:
```yaml
      - name: Install dependencies
        run: npm ci

      - name: TypeScript typecheck
        run: npx tsc --noEmit

      - name: Lint
        run: npm run lint
```

---

## 6. runtime-smoke After P48

Local validation (`make runtime-smoke`):

| Stage | Tests | Result |
|-------|-------|--------|
| Stage 1 (health) | 3 | ✅ 3 passed |
| Stage 2 (security-smoke) | 41 + tsc | ✅ 41 passed, 2 skipped + tsc exit 0 |
| Stage 3 (config-smoke) | 29 | ✅ 29 passed |
| Stage 4 (validation-smoke) | 57 | ✅ 57 passed |
| **Total** | **130** | **✅ 130 passed, 2 skipped** |

`npx tsc --noEmit` (CI equivalent): exit 0 ✅

---

## 7. CI vs runtime-smoke: Post-P48 Alignment Matrix

| Coverage Area | runtime-smoke (local) | CI (post-P48) | Status |
|---------------|----------------------|----------------|--------|
| Health contracts (`test_runtime_smoke.py`) | ✅ Stage 1 | ✅ Full backend suite | ALIGNED |
| Auth/security regression (41 tests incl. P47) | ✅ Stage 2a | ✅ Full backend suite | ALIGNED |
| Frontend TypeScript | ✅ Stage 2b (`tsc --noEmit`) | ✅ `npx tsc --noEmit` (P48) | **ALIGNED (P48)** |
| Config/startup guard (29 tests) | ✅ Stage 3 | ✅ Full backend suite | ALIGNED |
| Input validation/injection (57 tests) | ✅ Stage 4 | ✅ Full backend suite | ALIGNED |
| P47 token policy (12 tests) | ✅ Stage 2a | ✅ Full backend suite | ALIGNED |
| Frontend E2E (mocked) | local only | ✅ `npm run e2e:ci` | CI-only |
| Frontend auth E2E (live backend) | `make frontend-auth-smoke` | ❌ local only | ACCEPTED |
| PostgreSQL parity | not in runtime-smoke | not in CI | OPEN (R4) |

---

## 8. Files Changed

| File | Change |
|------|--------|
| `.github/workflows/ci-cd.yml` | Added `npx tsc --noEmit` step to frontend job |
| `docs/security/P48_CI_RUNTIME_SMOKE_ALIGNMENT.md` | Created (this file) |
| `00-Plan/roadmap/active_task_report.md` | P48 block prepended |

---

## 9. Residual Limitations / Known Gaps

| Item | Status | Notes |
|------|--------|-------|
| `ignoreBuildErrors: true` in `next.config.mjs` | ACCEPTED | Intentional — allows build while tsc gate is explicit step |
| Frontend auth E2E (live backend) | OPEN | Runs locally via `make frontend-auth-smoke` only |
| PostgreSQL compatibility | OPEN | All tests SQLite in-memory; R4 from P39 |
| R1 in-memory rate limiter | OPEN | Single-worker only; multi-worker untested |
| CI `e2e:ci` subset only | ACCEPTED | Mocked specs; no live backend dependency |
| CI backend job uses `python -m pytest -q` not `make` | ACCEPTED | Equivalent or broader coverage; avoids venv dependency in CI |

---

## 10. Final Classification

```
P48_CI_RUNTIME_SMOKE_ALIGNED

- CI backend: python -m pytest -q = 983 tests ⊇ all 130 runtime-smoke backend stages ✅
- CI frontend: npx tsc --noEmit added (P48) ≡ make frontend-tsc ✅
- P47 token policy tests (12): in CI backend full suite ✅
- runtime-smoke post-P48: 130 passed, 2 skipped ✅
- tsc --noEmit: exit 0 ✅
- Starting HEAD: a6a64c9
```
