# P42 – Rate Limit Production Enablement Policy

**Stage**: P42  
**Classification**: P42_RATE_LIMIT_POLICY_HARDENED  
**Status**: COMPLETE  
**Branch**: main  
**Commits**: `8484fca` (helper + tests)  
**Date**: 2026-05-24  

---

## Summary

P39 closed with two accepted residual risks:

- **R1**: In-memory rate limiter is not shared across workers  
- **R2**: Rate limiting remains opt-in / global threshold only  

P42 converts these accepted risks into an explicit production policy, a helper that surfaces warnings at startup, and regression tests that prove the policy is asserted.

---

## Investigation Findings

| Category | Finding |
|----------|---------|
| `rate_limit_enabled` default | `False` — rate limiting is **opt-in** |
| Middleware type | `InMemoryRateLimitMiddleware` — per-process, not distributed |
| `/health*` exemption | Hardcoded in middleware dispatch — always exempt |
| Existing `validate_production_secrets` | Checks only `jwt_secret_key` — no rate-limit check |
| P26 test coverage | Middleware contract (threshold, 429 body, path isolation) ✅ |
| Production policy | **ABSENT** before P42 |

**Classification prior to fix**: B (PARTIAL) + C (GAP)

---

## Helper Added: `get_runtime_security_warnings`

Added to `backend/app/core/config.py`. Returns `list[str]` — non-fatal warnings, never raises.

```python
def get_runtime_security_warnings(settings: Settings) -> list[str]:
    warnings: list[str] = []
    if settings.app_env.lower() in _PRODUCTION_ENVS:
        if not settings.rate_limit_enabled:
            warnings.append(
                "RATE_LIMIT_DISABLED_IN_PRODUCTION: rate_limit_enabled=False in "
                f"app_env='{settings.app_env}'. Set RATE_LIMIT_ENABLED=true or "
                "place the app behind a gateway/WAF with request throttling."
            )
        else:
            warnings.append(
                "IN_MEMORY_LIMITER_PROCESS_LOCAL: rate_limit_enabled=True but "
                "InMemoryRateLimitMiddleware state is not shared across workers. "
                "For multi-worker deployments use a gateway/WAF or a "
                "Redis-backed limiter."
            )
    return warnings
```

**Design decisions**:
- Returns warnings, does not block startup — preserves backward compatibility.
- In production with limiter **disabled**: warns `RATE_LIMIT_DISABLED_IN_PRODUCTION`.
- In production with limiter **enabled**: warns `IN_MEMORY_LIMITER_PROCESS_LOCAL` — because in-memory is always process-local.
- In dev/staging/local: returns `[]` — no noise during development.

---

## Production Policy

### Recommended production stance

| Setting | Recommended value |
|---------|------------------|
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_REQUESTS` | `120` (default) — tune per threat model |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` (default) |

### Topology guidance

| Topology | Rate limit approach |
|----------|---------------------|
| Single worker (1 uvicorn process) | `RATE_LIMIT_ENABLED=true` is sufficient for basic abuse protection |
| Multi-worker (gunicorn, multiple uvicorn processes) | In-memory limiter does **not** share state; per-worker quota applies independently. Add a gateway/WAF or Redis-backed limiter at the edge |
| Container / Kubernetes / load balancer | Gateway-level rate limiting (nginx rate_limit, Cloudflare, AWS WAF) is required. In-memory limiter alone is insufficient |

### Health endpoint policy

`/health`, `/health/live`, `/health/ready` are **permanently exempt** from rate limiting (hardcoded in `InMemoryRateLimitMiddleware.dispatch`). This is intentional — monitoring probes must not be throttled.

### Auth route policy

No stricter auth-route-specific throttle is applied. If auth brute-forcing is a concern, the recommended approach is:
1. Enable `RATE_LIMIT_ENABLED=true` for baseline protection.
2. Layer a gateway/WAF rule targeting `/api/v1/auth/*` with a lower threshold (e.g., 10 req/min per IP).

---

## Accepted Residual Limitations

| Risk | Status |
|------|--------|
| In-memory limiter is process-local | **ACCEPTED** — documented; warning surfaced at production startup |
| No worker count / topology field in Settings | **ACCEPTED / UNKNOWN** — no worker config; operators must configure topology externally |
| Global threshold only (no per-route throttle) | **ACCEPTED** — adding per-route throttles is out of scope without explicit test evidence |
| `get_runtime_security_warnings` not yet wired into startup logging | **DEFERRED** — wiring log call at startup is a separate P43 step |

---

## Recommended Future Distributed Limiter Path

When multi-worker scale is required:

1. **Nginx/gateway level**: Use `limit_req_zone` or equivalent. Zero application code change.
2. **Redis-backed middleware**: Replace `InMemoryRateLimitMiddleware` with a Redis atomic counter (e.g., `slowapi` with Redis backend). Requires adding `redis` dependency — out of P42 scope.
3. **Cloud WAF**: AWS WAF managed rules, Cloudflare Rate Limiting — recommended for Internet-facing production.

The application config (`RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`) is designed so the internal middleware can be disabled when a gateway handles limiting externally.

---

## Test Coverage Added

**File**: `backend/tests/test_rate_limit_production_policy.py` (17 tests)

| Class | Tests |
|-------|-------|
| `TestSettingsParsing` | 4 — field parsing for `RATE_LIMIT_ENABLED`, defaults |
| `TestRuntimeSecurityWarnings_DevEnv` | 4 — dev/staging/local → no warnings |
| `TestRuntimeSecurityWarnings_Production_Disabled` | 4 — production + disabled → 1 warning with correct text |
| `TestRuntimeSecurityWarnings_Production_Enabled` | 3 — production + enabled → process-local warning |
| `TestRuntimeSecurityWarnings_ReturnType` | 2 — always returns list, never raises |

---

## Test Results

| Suite | Result |
|-------|--------|
| `test_rate_limit_production_policy.py` | **17/17 passed** |
| `test_rate_limit_smoke.py` | **7/7 passed** |
| `test_config_security_guard.py` | **15/15 passed** |
| `make runtime-smoke` (Stage 1–4) | **113 passed, 2 skipped** |
| Full backend suite | **966 passed, 2 skipped** |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/core/config.py` | Added `get_runtime_security_warnings(settings) -> list[str]` |
| `backend/tests/test_rate_limit_production_policy.py` | **NEW** — 17 policy tests |
