# P43 – Startup Runtime Security Warning Logging

**Stage**: P43  
**Classification**: P43_STARTUP_SECURITY_WARNINGS_WIRED  
**Status**: COMPLETE  
**Branch**: main  
**Commits**: `5710698` (startup wiring), `f06e321` (tests)  
**Date**: 2026-05-24  

---

## Summary

P42 made production rate-limit policy computable via `get_runtime_security_warnings(settings)` but did not wire it into application startup. P43 wires the helper into `startup_event()` so rate-limit policy gaps are visible as structured WARNING logs when the application boots in a production environment — without blocking startup.

---

## Investigation Findings

| Category | Finding |
|----------|---------|
| `log_json(logger, level, event, **payload)` | Exists in `app/core/logging.py` — JSON-structured, timestamp included |
| `startup_event()` before P43 | Called `validate_production_secrets()` (fatal), then `app_started` (INFO) |
| `get_runtime_security_warnings()` | Existed in `config.py` since P42, **not imported or called** in `main.py` |
| Test pattern | `monkeypatch.setattr(main_module, 'settings', ...)` + direct `startup_event()` call |

**Classification prior to P43**: B (GAP) + C (PARTIAL)

---

## Implementation

### `backend/app/main.py` — startup integration

Added `get_runtime_security_warnings` to the `config` import and wired into `startup_event()`:

```python
from app.core.config import get_runtime_security_warnings, get_settings, validate_production_secrets

@app.on_event('startup')
def startup_event():
    validate_production_secrets(settings)          # fatal guard (unchanged)
    for _warning in get_runtime_security_warnings(settings):
        _code = _warning.split(':')[0]
        log_json(
            logger,
            logging.WARNING,
            'runtime_security_warning',
            warning_code=_code,
            app_env=settings.app_env,
        )
    if settings.app_auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.orchestrator_scheduler_autostart:
        start_scheduler(profile_path=settings.orchestrator_profile_path)
    log_json(logger, logging.INFO, 'app_started', ...)
```

### Warning codes emitted

| Condition | `warning_code` in log |
|-----------|----------------------|
| `app_env` in `{production, prod}` AND `rate_limit_enabled=False` | `RATE_LIMIT_DISABLED_IN_PRODUCTION` |
| `app_env` in `{production, prod}` AND `rate_limit_enabled=True` | `IN_MEMORY_LIMITER_PROCESS_LOCAL` |
| Any non-production env | *(no warning logged)* |

### Log payload

```json
{
  "ts": "2026-05-24T00:00:00+00:00",
  "event": "runtime_security_warning",
  "warning_code": "RATE_LIMIT_DISABLED_IN_PRODUCTION",
  "app_env": "production"
}
```

**No secrets are included in the payload** — only `warning_code` and `app_env`.

### Non-fatal behavior confirmed

- `get_runtime_security_warnings()` never raises.
- The startup loop does not raise on any warning.
- `validate_production_secrets()` still raises first (fatal) if JWT secret is insecure — this behavior is unchanged.

---

## Tests Added

**File**: `backend/tests/test_runtime_config_startup_guard.py` — new class `TestStartupRuntimeSecurityWarnings` (5 tests)

| Test | Validates |
|------|-----------|
| `test_production_disabled_rate_limit_logs_warning` | `RATE_LIMIT_DISABLED_IN_PRODUCTION` appears in caplog WARNING records |
| `test_production_enabled_rate_limit_logs_process_local_warning` | `IN_MEMORY_LIMITER_PROCESS_LOCAL` appears in caplog WARNING records |
| `test_dev_env_no_runtime_security_warning` | dev env → no `runtime_security_warning` records logged |
| `test_warning_does_not_include_jwt_secret` | JWT secret value absent from all log records |
| `test_warnings_are_non_fatal` | `startup_event()` completes without raising |

---

## Test Results

| Suite | Result |
|-------|--------|
| `test_runtime_config_startup_guard.py` | **14 existing + 5 new = 19/19 passed** |
| `test_rate_limit_production_policy.py` | **17/17 passed** |
| `make runtime-smoke` (Stage 1–4) | **118 passed, 2 skipped** (Stage 3 +5 from new tests) |
| Full backend suite | **971 passed, 2 skipped** |

---

## Known Limitations / Deferred

| Item | Status |
|------|--------|
| In-memory limiter is process-local | Documented, warned at startup — no code change needed |
| No distributed/Redis-backed limiter | Deferred — requires new dependency, out of P43 scope |
| Warning only at startup (not request-time) | Intentional — startup is the correct observability point |
| `on_event('startup')` FastAPI deprecation | Pre-existing, not introduced by P43 |

---

## Recommended Future Path

1. **P44+**: Migrate `startup_event` / `shutdown_event` from deprecated `@app.on_event` to `lifespan` context manager (FastAPI docs recommendation).
2. **Distributed rate limiting**: Replace `InMemoryRateLimitMiddleware` with Redis-backed limiter or gateway-level WAF rule when multi-worker scale is needed.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/main.py` | Added `get_runtime_security_warnings` import; wired warning loop in `startup_event()` |
| `backend/tests/test_runtime_config_startup_guard.py` | Added `import logging`; new class `TestStartupRuntimeSecurityWarnings` (5 tests) |
