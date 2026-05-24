# P46 — Smoke Gate Refresh After P44/P45 Security Expansion

**Stage**: P46  
**Classification**: P46_SMOKE_GATE_REFRESH_READY  
**Status**: COMPLETE  
**Branch**: main  
**Starting HEAD**: `cb6f19b` (P45 closure)  
**Commits**: see section 7  
**Date**: 2026-05-24  

---

## 1. Governance Pre-flight

| Check | Result |
|-------|--------|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Status | Clean at start ✅ |
| HEAD | `cb6f19b` (P45 closure) ✅ |

```
git log --oneline -5 at P46 start:
cb6f19b docs(report): P45 report download token header handoff report
be76def docs(security): add P45 report download token header report
51a7ca8 test(security): add report download token header regression
47f0148 fix(frontend): send report download token via header
97c6096 fix(security): accept report download token from request header
```

---

## 2. Purpose

P43 added 5 tests to the config-smoke stage. P44 and P45 added 12 tests to `test_report_download_token_policy.py`. The smoke gate documentation in `P39_SECURITY_AUDIT_CLOSURE_INDEX.md` was last updated at HEAD `4c9ffb1` and showed stale counts (113 passed). R5 was listed as an accepted risk but has been mitigated by P45. P46 refreshes all stale governance docs so future agents have accurate counts, accurate risk status, and a clear inventory of what is and is not covered by `runtime-smoke`.

---

## 3. Smoke Gate Inventory (Current State)

### runtime-smoke: 4 stages

| Stage | Target | Test File(s) | Count | Status |
|-------|--------|-------------|-------|--------|
| 1 — Health | `test_runtime_smoke.py` | `/health`, `/api/v1/health` contract | **3** | ✅ |
| 2 — Security | `make security-smoke` → `make backend-auth-audit` + `frontend-tsc` | Auth audit (4 files) | **29, 2 skipped** | ✅ |
| 3 — Config | `make config-smoke` | P28 secret guard + P29/P43 startup integration | **29** | ✅ |
| 4 — Validation | `make validation-smoke` | P23/P24/P27/P30 schema/injection | **57** | ✅ |
| **Total** | | | **118 passed, 2 skipped** | ✅ |

### Stage 2 (security-smoke / backend-auth-audit) — file detail

| File | Origin | Tests |
|------|--------|-------|
| `test_auth_negative_smoke.py` | P13 | ~7 |
| `test_real_token_auth_negative.py` | P13 | ~7 |
| `test_person_id_authorization_audit.py` | P17 | 10 (2 skip) |
| `test_report_authorization_hardening.py` | P18/P20 | 12 |
| frontend `tsc --noEmit` | P22 | 0 errors ✅ (2 skip if Node unavail) |

### Stage 3 (config-smoke) — file detail

| File | Origin | Tests |
|------|--------|-------|
| `test_config_security_guard.py` | P28 | 15 |
| `test_runtime_config_startup_guard.py` | P29/P43 | 14 |
| **Subtotal** | | **29** |

*P39 baseline was 24. P43 added 5 startup-warning tests to `test_runtime_config_startup_guard.py`.*

### Count change history

| Baseline | Stage 3 | Total | Reason |
|----------|---------|-------|--------|
| P39 (HEAD `4c9ffb1`) | 24 | 113 | Pre-P43 |
| P43 (HEAD `2c38ebb`) | 29 | 118 | +5 startup warning tests |
| P46 (HEAD `cb6f19b`) | 29 | 118 | No additional runtime-smoke tests (P44/P45 tests are full-suite only) |

---

## 4. P44/P45 Test Coverage and Runtime-Smoke Gap

### What P44/P45 Added

| File | Tests Added | Origin |
|------|-------------|--------|
| `test_report_download_token_policy.py` | 5 | P44 |
| `test_report_download_token_policy.py` | 7 | P45 |
| **Total** | **12** | P44+P45 |

### Coverage Gap: CLOSED by P47

`test_report_download_token_policy.py` was not in any Makefile smoke target at P46 close. **P47 added it to `backend-auth-audit`** (2026-05-24).

- Now included in `backend-auth-audit` ✅
- Now included in `security-smoke` ✅
- Now included in `runtime-smoke` stage 2 ✅

**Full backend suite**: 983 passed, 2 skipped (as of P45 HEAD `cb6f19b`).

### Gap Significance

| Token policy scenario | Test | In runtime-smoke? |
|-----------------------|------|-------------------|
| No JWT + valid token → 401 | `TestDownloadTokenRequiresJWT` (P44) | ✅ (stage 2, added P47) |
| Cross-user JWT + token → 404 | `TestDownloadTokenRequiresJWT` (P44) | ✅ (stage 2, added P47) |
| Header token → 200 | `TestHeaderTokenDownload` (P45) | ✅ (stage 2, added P47) |
| Query token backward compat → 200 | `TestHeaderTokenDownload` (P45) | ✅ (stage 2, added P47) |
| Header preferred over query | `TestHeaderTokenDownload` (P45) | ✅ (stage 2, added P47) |
| No token → 403 | `TestHeaderTokenDownload` (P45) | ✅ (stage 2, added P47) |
| Report status owner binding | `test_report_authorization_hardening.py` (P18/P20) | ✅ (stage 2) |
| Cross-user report access → 404 | `test_report_authorization_hardening.py` | ✅ (stage 2) |

**Recommended P47 action**: Add `test_report_download_token_policy.py` to `backend-auth-audit` in the Makefile to bring P44/P45 token policy tests into the runtime-smoke gate.

---

## 5. Residual Risk Status After P45

| Risk | Status | Details |
|------|--------|---------|
| R1 — In-memory rate limiter, not multi-worker | OPEN | Accepted; single-worker deployment only |
| R2 — Rate limit opt-in per route | OPEN | Accepted; code review guard |
| R3 — AI prompt injection | OPEN | Accepted; no untrusted multi-tenant traffic yet |
| R4 — risk_engine.py UUID str coercion | CLOSED (P41) | `str(user.id)` → `user.id` fixed |
| R5 — Report download token leakable via URL | **MITIGATED (P45)** | Token no longer in fetch URL; sent via `X-Report-Download-Token` header |
| R6 — Playwright E2E tests require live backend | OPEN | Accepted; `backend-auth-audit` covers same logic |

### R5 Mitigation Detail

**Before P45**: `GET /api/v1/reports/download/{id}?token=<uuid>` — token in server access logs.  
**After P45**: `GET /api/v1/reports/download/{id}` — token in `X-Report-Download-Token` header (not standard access log field).

Token still embedded in `download_url` returned by status endpoint — but status endpoint requires owner JWT, so `download_url` is only delivered to the authenticated report owner.

---

## 6. Files Changed in P46

| File | Change |
|------|--------|
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage 3 count 24→29; total 113→118; R5 → MITIGATED; P44 recommendation → COMPLETE; Section 12 smoke count; Section 13 post-P39 supplement added |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Created (this file) |
| `Makefile` | `config-smoke` comment updated to reference P43 |
| `00-Plan/roadmap/active_task_report.md` | P46 block prepended |

---

## 7. Validation Commands and Results

```bash
# Governance pre-flight
git rev-parse --show-toplevel  # /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS ✅
git branch --show-current      # main ✅
git status --short             # clean ✅

# runtime-smoke
make runtime-smoke
# 118 passed, 2 skipped ✅

# Targeted regression tests
cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/test_report_download_token_policy.py \
  tests/test_report_authorization_hardening.py \
  tests/test_response_leakage.py
# 33 passed ✅

# Frontend typecheck
cd frontend && npx tsc --noEmit
# exit 0 (no errors) ✅
```

---

## 8. Known Limitations

| Item | Notes |
|------|-------|
| `test_report_download_token_policy.py` not in runtime-smoke | **CLOSED by P47** — added to `backend-auth-audit`; runtime-smoke now 130 passed |
| `download_url` still contains `?token=` in status response | Owner-scoped; status endpoint requires JWT; frontend strips token before fetch |
| Query token fallback still accepted by backend | Intentional backward compat; no active consumer after P45 frontend migration |
| PostgreSQL parity untested | All tests run on SQLite in-memory (R4 fix in P41 is SQLite-verified) |

---

## 9. Recommended Next Task

### P47 — Add Token Policy Tests to runtime-smoke Gate

**Priority**: MEDIUM  
**Rationale**: `test_report_download_token_policy.py` (12 tests covering P44/P45 download token contract) is not gated by `make runtime-smoke`. If a future agent regresses the download token behavior, it will not be caught until the full suite is run.  
**Scope**: Add `test_report_download_token_policy.py` to `backend-auth-audit` in the Makefile. Verify `runtime-smoke` count increases from 118 to 130. Update this doc and P46.  
**Constraints**: Makefile edit only; no backend/test code changes needed.  
**Status**: ✅ COMPLETE (P47, 2026-05-24). runtime-smoke: 130 passed, 2 skipped.

---

## 10. Final Classification

```
P46_SMOKE_GATE_REFRESH_READY

- P39 closure index refreshed:
  - Stage 3 config-smoke: 24 → 29 (+5 P43 tests)
  - Total runtime-smoke: 113 → 118
  - R5 marked MITIGATED (P44+P45)
  - P44 recommendation marked COMPLETE
  - Post-P39 supplement (P40-P45 table) added
- Makefile config-smoke comment updated (P43 reference)
- P46 smoke gate refresh doc created
- runtime-smoke: 118 passed, 2 skipped ✅
- 33/33 targeted tests passed ✅
- frontend tsc: 0 errors ✅
- Coverage gap documented at P46; CLOSED by P47 (test_report_download_token_policy.py added to backend-auth-audit)
- runtime-smoke after P47: 130 passed, 2 skipped ✅
- Starting HEAD: cb6f19b | Closing HEAD: see active_task_report
```
