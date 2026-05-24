"""P42 — Rate Limit Production Policy Tests.

Verifies get_runtime_security_warnings() correctly surfaces rate-limit
production risks without blocking startup.

Coverage map
------------
TestSettingsParsing
  test_rate_limit_enabled_parses_true       → RATE_LIMIT_ENABLED=true accepted
  test_rate_limit_enabled_default_false     → default is False (opt-in)
  test_rate_limit_requests_default          → default threshold 120 req
  test_rate_limit_window_default            → default window 60 s

TestRuntimeSecurityWarnings_DevEnv
  test_no_warnings_in_dev_disabled          → dev + disabled → no warnings
  test_no_warnings_in_dev_enabled           → dev + enabled  → no warnings
  test_no_warnings_in_staging              → non-prod env    → no warnings

TestRuntimeSecurityWarnings_Production_Disabled
  test_disabled_in_production_warns         → production + disabled → 1 warning
  test_warning_mentions_rate_limit_key      → warning text identifies the field
  test_warning_mentions_env_var_remediation → warning names RATE_LIMIT_ENABLED
  test_prod_alias_warns                     → 'prod' alias also triggers warning

TestRuntimeSecurityWarnings_Production_Enabled
  test_enabled_in_production_warns_process_local  → enabled → process-local warning
  test_process_local_warning_names_middleware     → warning text identifies risk
  test_process_local_warning_recommends_gateway   → mentions gateway / Redis

TestRuntimeSecurityWarnings_ReturnType
  test_returns_list                         → always returns a list
  test_no_exception_in_any_config           → never raises; only warns
"""
from __future__ import annotations

import pytest

from app.core.config import Settings, get_runtime_security_warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(**kwargs) -> Settings:
    """Build Settings with explicit overrides, isolated from .env files."""
    return Settings(**kwargs)


_REAL_SECRET = 'f3a8c2d1e94b607a5b2e0d8c4f1a3e6b9d2c5f8a1e4b7d0c3f6a9e2b5d8f1a4'


# ---------------------------------------------------------------------------
# Settings field parsing
# ---------------------------------------------------------------------------

class TestSettingsParsing:
    def test_rate_limit_enabled_parses_true(self, monkeypatch: pytest.MonkeyPatch):
        """RATE_LIMIT_ENABLED=true env var must be accepted."""
        monkeypatch.setenv('RATE_LIMIT_ENABLED', 'true')
        s = Settings()
        assert s.rate_limit_enabled is True

    def test_rate_limit_enabled_default_false(self):
        """rate_limit_enabled defaults to False (opt-in)."""
        s = _settings()
        assert s.rate_limit_enabled is False

    def test_rate_limit_requests_default(self):
        """Default request threshold is 120."""
        s = _settings()
        assert s.rate_limit_requests == 120

    def test_rate_limit_window_default(self):
        """Default window is 60 seconds."""
        s = _settings()
        assert s.rate_limit_window_seconds == 60


# ---------------------------------------------------------------------------
# Non-production environments — no warnings expected
# ---------------------------------------------------------------------------

class TestRuntimeSecurityWarnings_DevEnv:
    def test_no_warnings_in_dev_disabled(self):
        """dev env + rate_limit_enabled=False must produce no warnings."""
        s = _settings(app_env='dev', rate_limit_enabled=False)
        assert get_runtime_security_warnings(s) == []

    def test_no_warnings_in_dev_enabled(self):
        """dev env + rate_limit_enabled=True must produce no warnings."""
        s = _settings(app_env='dev', rate_limit_enabled=True)
        assert get_runtime_security_warnings(s) == []

    def test_no_warnings_in_staging(self):
        """staging env must produce no warnings (not a production alias)."""
        s = _settings(app_env='staging', rate_limit_enabled=False)
        assert get_runtime_security_warnings(s) == []

    def test_no_warnings_in_local(self):
        """local env must produce no warnings."""
        s = _settings(app_env='local', rate_limit_enabled=False)
        assert get_runtime_security_warnings(s) == []


# ---------------------------------------------------------------------------
# Production + rate limit disabled
# ---------------------------------------------------------------------------

class TestRuntimeSecurityWarnings_Production_Disabled:
    def test_disabled_in_production_warns(self):
        """production + rate_limit_enabled=False must return exactly 1 warning."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=False)
        w = get_runtime_security_warnings(s)
        assert len(w) == 1

    def test_warning_mentions_rate_limit_key(self):
        """Warning must mention rate_limit_enabled so operators know the field."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=False)
        w = get_runtime_security_warnings(s)
        assert any('rate_limit_enabled' in msg for msg in w)

    def test_warning_mentions_env_var_remediation(self):
        """Warning must name RATE_LIMIT_ENABLED so operators know the env var."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=False)
        w = get_runtime_security_warnings(s)
        assert any('RATE_LIMIT_ENABLED' in msg for msg in w)

    def test_prod_alias_warns(self):
        """'prod' alias must also trigger the disabled-in-production warning."""
        s = _settings(app_env='prod', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=False)
        w = get_runtime_security_warnings(s)
        assert len(w) == 1
        assert any('RATE_LIMIT' in msg for msg in w)


# ---------------------------------------------------------------------------
# Production + rate limit enabled (in-memory / process-local risk)
# ---------------------------------------------------------------------------

class TestRuntimeSecurityWarnings_Production_Enabled:
    def test_enabled_in_production_warns_process_local(self):
        """production + rate_limit_enabled=True must return the process-local warning."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=True)
        w = get_runtime_security_warnings(s)
        assert len(w) == 1

    def test_process_local_warning_names_middleware(self):
        """Warning must mention InMemoryRateLimitMiddleware or in-memory."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=True)
        w = get_runtime_security_warnings(s)
        combined = ' '.join(w).lower()
        assert 'memory' in combined or 'process' in combined

    def test_process_local_warning_recommends_gateway(self):
        """Warning must recommend a gateway or Redis-backed alternative."""
        s = _settings(app_env='production', jwt_secret_key=_REAL_SECRET,
                      rate_limit_enabled=True)
        w = get_runtime_security_warnings(s)
        combined = ' '.join(w).lower()
        assert 'gateway' in combined or 'redis' in combined


# ---------------------------------------------------------------------------
# Return-type / safety invariants
# ---------------------------------------------------------------------------

class TestRuntimeSecurityWarnings_ReturnType:
    def test_returns_list(self):
        """get_runtime_security_warnings must always return a list."""
        for env in ('dev', 'staging', 'production', 'prod'):
            for enabled in (True, False):
                s = _settings(app_env=env, jwt_secret_key=_REAL_SECRET,
                               rate_limit_enabled=enabled)
                result = get_runtime_security_warnings(s)
                assert isinstance(result, list), \
                    f"Expected list for env={env!r} enabled={enabled}, got {type(result)}"

    def test_no_exception_in_any_config(self):
        """get_runtime_security_warnings must never raise — only warn."""
        configs = [
            dict(app_env='dev', rate_limit_enabled=False),
            dict(app_env='dev', rate_limit_enabled=True),
            dict(app_env='production', jwt_secret_key=_REAL_SECRET, rate_limit_enabled=False),
            dict(app_env='production', jwt_secret_key=_REAL_SECRET, rate_limit_enabled=True),
            dict(app_env='prod', jwt_secret_key=_REAL_SECRET, rate_limit_enabled=False),
        ]
        for cfg in configs:
            s = _settings(**cfg)
            # must not raise
            get_runtime_security_warnings(s)
