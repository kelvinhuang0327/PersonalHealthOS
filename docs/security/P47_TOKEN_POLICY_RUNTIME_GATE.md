# P47 — Report Download Token Policy Tests: Runtime Smoke Gate

**Stage**: P47  
**Classification**: P47_TOKEN_POLICY_RUNTIME_GATE_READY  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `8fde52f` (P46 closure)  
**Date**: 2026-05-24  

---

## 1. Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean ✅ |
| HEAD | `8fde52f` (P46 closure) ✅ |

---

## 2. Gap Being Closed

P46 documented that `test_report_download_token_policy.py` (12 tests: 5 P44 + 7 P45) was **not included in `runtime-smoke`**. It ran only in the full backend suite. This meant a regression in the P44/P45 download token contract would not be caught by the standard smoke gate.

P47 closes this gap with a single Makefile change.

---

## 3. Makefile Change

**Target**: `backend-auth-audit`

**Before**:
```makefile
# Full P13-P20 auth/security regression (no DB required — in-memory SQLite)
# Covers: API auth, real JWT, person_id audit, report owner hardening
backend-auth-audit:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v \
		tests/test_auth_negative_smoke.py \
		tests/test_real_token_auth_negative.py \
		tests/test_person_id_authorization_audit.py \
		tests/test_report_authorization_hardening.py
```

**After**:
```makefile
# Full P13-P20 + P44/P45 auth/security regression (no DB required — in-memory SQLite)
# Covers: API auth, real JWT, person_id audit, report owner hardening, download token policy
backend-auth-audit:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v \
		tests/test_auth_negative_smoke.py \
		tests/test_real_token_auth_negative.py \
		tests/test_person_id_authorization_audit.py \
		tests/test_report_authorization_hardening.py \
		tests/test_report_download_token_policy.py
```

**Propagation**: `backend-auth-audit` → `security-smoke` → `runtime-smoke` (stage 2)

---

## 4. Test File Added

**File**: `backend/tests/test_report_download_token_policy.py`  
**Tests**: 12 total

| Class | Origin | Tests | Coverage |
|-------|--------|-------|----------|
| `TestDownloadTokenRequiresJWT` | P44 | 5 | No-JWT→401, cross-user→404, token expiry, wrong token→403, missing token→422 |
| `TestDownloadTokenBodyDoesNotLeakToken` | P44 | — | Schema assertions (no `token` field in response) |
| `TestHeaderTokenDownload` | P45 | 7 | Header→200, query→200, header-preferred, no-fallback, no-token→403, cross-user→404, no-JWT→401 |

---

## 5. runtime-smoke Before / After

| | Before P47 | After P47 |
|-|------------|-----------|
| Stage 1 (health) | 3 passed | 3 passed |
| Stage 2 (security-smoke) | 29 passed, 2 skipped | **41 passed, 2 skipped** (+12) |
| Stage 3 (config-smoke) | 29 passed | 29 passed |
| Stage 4 (validation-smoke) | 57 passed | 57 passed |
| **Total** | **118 passed, 2 skipped** | **130 passed, 2 skipped** |

---

## 6. Targeted Test Result

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_report_download_token_policy.py
```

**Result**: 12 passed, 4 warnings ✅

---

## 7. Files Changed

| File | Change |
|------|--------|
| `Makefile` | Added `tests/test_report_download_token_policy.py` to `backend-auth-audit`; updated comment |
| `docs/security/P47_TOKEN_POLICY_RUNTIME_GATE.md` | Created (this file) |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Gap status updated → CLOSED by P47; table cells updated; P47 recommendation marked COMPLETE |
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage 2 count 29→41; total 118→130; Section 13 P47 row added; gap note closed |
| `00-Plan/roadmap/active_task_report.md` | P47 block prepended |

---

## 8. Residual Limitations

| Item | Status |
|------|--------|
| `download_url` status response still contains `?token=` | Accepted — owner-JWT-gated; frontend strips before fetch |
| Query token backward compat still accepted | Intentional — no active consumer after P45 |
| PostgreSQL parity untested | All tests SQLite in-memory |
| R1 in-memory rate limiter | OPEN — single-worker only |
| R2 rate limit opt-in | OPEN — code review guard |
| R3 AI prompt injection | OPEN — no untrusted traffic |
| R6 Playwright E2E requires live backend | OPEN — `backend-auth-audit` covers same logic |

---

## 9. Final Classification

```
P47_TOKEN_POLICY_RUNTIME_GATE_READY

- test_report_download_token_policy.py added to backend-auth-audit ✅
- runtime-smoke: 130 passed, 2 skipped (was 118) ✅
- targeted test: 12/12 passed ✅
- all token policy scenarios now gated on make runtime-smoke ✅
- Starting HEAD: 8fde52f
```
