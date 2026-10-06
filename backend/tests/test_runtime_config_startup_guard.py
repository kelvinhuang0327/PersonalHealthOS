"""P29 — Runtime startup config guard smoke tests.

Validates the *integration* between env-var resolution, Settings instantiation,
validate_production_secrets(), and startup_event() — confirming the guard works
end-to-end under production-like environment combinations.

Coverage map
------------
TestEnvVarToSettingsResolution (4 tests)
  test_app_env_env_var_overrides_default
      → APP_ENV env var takes priority over .env file / field default
  test_jwt_secret_key_env_var_overrides_default
      → JWT_SECRET_KEY env var takes priority over field default
  test_production_env_with_placeholder_detected_via_env_vars
      → APP_ENV=production + JWT_SECRET_KEY=replace_me (both as env vars)
        → Settings() picks them up → guard raises RuntimeError
  test_production_env_with_real_secret_via_env_vars_accepted
      → APP_ENV=production + JWT_SECRET_KEY=<safe value> → guard does NOT raise

TestStartupEventIntegration (3 tests)
  test_startup_event_raises_with_production_placeholder
      → monkeypatch app.main.settings to production+insecure
        → direct startup_event() call raises RuntimeError
  test_startup_event_does_not_raise_with_dev_placeholder
      → monkeypatch app.main.settings to dev+insecure
        → startup_event() guard passes (dev env is allowed)
  test_startup_event_does_not_raise_with_production_real_secret
      → monkeypatch app.main.settings to production+real_secret
        → startup_event() guard passes

TestGetSettingsCacheBehavior (2 tests)
  test_cache_cleared_fresh_settings_respects_env_vars
      → cache_clear() + env vars set → get_settings() returns production env
  test_cache_does_not_retain_production_env_across_invocations
      → after cache_clear() with no env override → safe local env restored
"""
from __future__ import annotations

import logging

import pytest

from app.core.config import Settings, validate_production_secrets, get_settings

# A non-placeholder secret for tests — long enough to be clearly non-trivial.
# Not a real credential; contains no meaningful entropy source.
_SAFE_TEST_SECRET = 'a4b8c2d6e0f1a5b9c3d7e1f2a6b0c4d8e2f3a7b1c5d9e0f4a8b2c6d0e1f5a9b3'


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _settings(**kwargs) -> Settings:
    """Construct a Settings instance with explicit field overrides.

    pydantic-settings priority: __init__ kwargs > env vars > env file > defaults.
    Passing kwargs here isolates tests from whatever is in the local .env file.
    """
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# 1. Environment variable → Settings resolution
# ---------------------------------------------------------------------------

class TestEnvVarToSettingsResolution:
    """Verify that os.environ values are correctly picked up by Settings()."""

    def test_app_env_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """APP_ENV env var must override the field default ('dev')."""
        monkeypatch.setenv('APP_ENV', 'production')
        monkeypatch.setenv('JWT_SECRET_KEY', _SAFE_TEST_SECRET)
        s = Settings()
        assert s.app_env == 'production'

    def test_jwt_secret_key_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """JWT_SECRET_KEY env var must override the field default ('replace_me')."""
        monkeypatch.setenv('JWT_SECRET_KEY', _SAFE_TEST_SECRET)
        s = Settings()
        assert s.jwt_secret_key == _SAFE_TEST_SECRET

    def test_production_env_with_placeholder_detected_via_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """APP_ENV=production + JWT_SECRET_KEY=replace_me (env vars) must trigger guard.

        This is the realistic misconfiguration scenario: an operator sets APP_ENV
        in docker-compose but forgets to supply JWT_SECRET_KEY, causing Settings
        to fall back to the 'replace_me' default.
        """
        monkeypatch.setenv('APP_ENV', 'production')
        monkeypatch.setenv('JWT_SECRET_KEY', 'replace_me')
        s = Settings()
        assert s.app_env == 'production'
        assert s.jwt_secret_key == 'replace_me'
        with pytest.raises(RuntimeError, match='jwt_secret_key'):
            validate_production_secrets(s)

    def test_production_env_with_real_secret_via_env_vars_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """APP_ENV=production + JWT_SECRET_KEY=<real value> (env vars) must be accepted."""
        monkeypatch.setenv('APP_ENV', 'production')
        monkeypatch.setenv('JWT_SECRET_KEY', _SAFE_TEST_SECRET)
        s = Settings()
        validate_production_secrets(s)  # must not raise


# ---------------------------------------------------------------------------
# 2. startup_event() integration
# ---------------------------------------------------------------------------

class TestStartupEventIntegration:
    """Test that startup_event() correctly propagates the production guard error.

    startup_event() is the first thing called when the ASGI lifespan starts.
    It calls validate_production_secrets(settings) before any DB or scheduler
    code runs, so the server refuses to handle requests on bad config.

    These tests call startup_event() directly (not via TestClient) with
    monkeypatched settings, verifying the integration contract without
    spinning up the full ASGI machinery or a database connection.
    """

    def test_startup_event_raises_with_production_placeholder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """startup_event() must raise RuntimeError when settings is production+insecure.

        The guard fires before any DB table creation or scheduler code runs,
        so the test needs no database connection.
        """
        import app.main as main_module

        prod_settings = _settings(app_env='production', jwt_secret_key='replace_me')
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        with pytest.raises(RuntimeError, match='UNSAFE STARTUP'):
            main_module.startup_event()

    def test_startup_event_does_not_raise_with_dev_placeholder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """startup_event() guard must pass when app_env='dev' with placeholder secret.

        app_auto_create_tables=False ensures no database connection is attempted,
        keeping this test self-contained.
        """
        import app.main as main_module

        dev_settings = _settings(
            app_env='dev',
            jwt_secret_key='replace_me',
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', dev_settings)

        main_module.startup_event()  # must not raise

    def test_startup_event_does_not_raise_with_production_real_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """startup_event() guard must pass when production env has a real secret.

        app_auto_create_tables=False keeps this test database-independent.
        """
        import app.main as main_module

        prod_settings = _settings(
            app_env='production',
            jwt_secret_key=_SAFE_TEST_SECRET,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        main_module.startup_event()  # must not raise


# ---------------------------------------------------------------------------
# 3. get_settings() lru_cache behavior
# ---------------------------------------------------------------------------

class TestGetSettingsCacheBehavior:
    """Verify that get_settings() lru_cache doesn't mask production misconfig.

    The @lru_cache on get_settings() means that once the settings object is
    created, it is reused for the lifetime of the process.  A post-startup
    env var change won't be picked up unless the cache is cleared.

    These tests confirm:
    - After cache_clear(), env vars ARE picked up by the next get_settings() call.
    - After restoring the environment (monkeypatch teardown + cache_clear()),
      the local dev default is safe and guard-free.
    """

    def test_cache_cleared_fresh_settings_respects_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After cache_clear(), get_settings() re-reads APP_ENV and JWT_SECRET_KEY."""
        monkeypatch.setenv('APP_ENV', 'production')
        monkeypatch.setenv('JWT_SECRET_KEY', _SAFE_TEST_SECRET)
        get_settings.cache_clear()
        try:
            s = get_settings()
            assert s.app_env == 'production'
            assert s.jwt_secret_key == _SAFE_TEST_SECRET
        finally:
            get_settings.cache_clear()  # restore clean state regardless of outcome

    def test_cache_does_not_retain_production_env_across_invocations(self) -> None:
        """After cache_clear() with no production env vars, local dev env is safe.

        This verifies the cleanup pattern: other tests that clear and re-prime
        the cache must not leave a production settings object behind.
        """
        get_settings.cache_clear()
        try:
            s = get_settings()
            # .env sets APP_ENV=local; field default is 'dev'.  Either way, safe.
            assert s.app_env.lower() not in ('production', 'prod'), (
                f"Expected non-production env after cache clear, got '{s.app_env}'. "
                "A previous test may have leaked a production settings object."
            )
            validate_production_secrets(s)  # must not raise
        finally:
            get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 4. startup_event() runtime security warning logging (P43)
# ---------------------------------------------------------------------------

class TestStartupRuntimeSecurityWarnings:
    """Test that startup_event() logs non-fatal runtime security warnings.

    P42 added get_runtime_security_warnings() to config.py.
    P43 wires it into startup_event() so production rate-limit policy gaps
    are visible in structured logs without blocking startup.

    Coverage:
      test_production_disabled_rate_limit_logs_warning
          → production + rate_limit_enabled=False → RATE_LIMIT_DISABLED_IN_PRODUCTION logged
      test_production_enabled_rate_limit_logs_process_local_warning
          → production + rate_limit_enabled=True  → IN_MEMORY_LIMITER_PROCESS_LOCAL logged
      test_dev_env_no_runtime_security_warning
          → dev + any rate_limit value → no runtime_security_warning logged
      test_warning_does_not_include_jwt_secret
          → log payload must never contain the JWT secret value
      test_warnings_are_non_fatal
          → warnings must not raise; startup completes normally
    """

    _REAL_SECRET = 'f3a8c2d1e94b607a5b2e0d8c4f1a3e6b9d2c5f8a1e4b7d0c3f6a9e2b5d8f1a4'

    def test_production_disabled_rate_limit_logs_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """production + rate_limit_enabled=False → RATE_LIMIT_DISABLED_IN_PRODUCTION logged."""
        import app.main as main_module

        prod_settings = _settings(
            app_env='production',
            jwt_secret_key=self._REAL_SECRET,
            rate_limit_enabled=False,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        with caplog.at_level(logging.WARNING):
            main_module.startup_event()

        messages = ' '.join(r.getMessage() for r in caplog.records)
        assert 'RATE_LIMIT_DISABLED_IN_PRODUCTION' in messages

    def test_production_enabled_rate_limit_logs_process_local_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """production + rate_limit_enabled=True → IN_MEMORY_LIMITER_PROCESS_LOCAL logged."""
        import app.main as main_module

        prod_settings = _settings(
            app_env='production',
            jwt_secret_key=self._REAL_SECRET,
            rate_limit_enabled=True,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        with caplog.at_level(logging.WARNING):
            main_module.startup_event()

        messages = ' '.join(r.getMessage() for r in caplog.records)
        assert 'IN_MEMORY_LIMITER_PROCESS_LOCAL' in messages

    def test_dev_env_no_runtime_security_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """dev env must not log any runtime_security_warning records."""
        import app.main as main_module

        dev_settings = _settings(
            app_env='dev',
            jwt_secret_key='replace_me',
            rate_limit_enabled=False,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', dev_settings)

        with caplog.at_level(logging.WARNING):
            main_module.startup_event()

        messages = ' '.join(r.getMessage() for r in caplog.records)
        assert 'runtime_security_warning' not in messages

    def test_warning_does_not_include_jwt_secret(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Runtime security warning log records must not leak the JWT secret value."""
        import app.main as main_module

        prod_settings = _settings(
            app_env='production',
            jwt_secret_key=self._REAL_SECRET,
            rate_limit_enabled=False,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        with caplog.at_level(logging.WARNING):
            main_module.startup_event()

        for record in caplog.records:
            assert self._REAL_SECRET not in record.getMessage(), \
                "JWT secret must not appear in any startup log record"

    def test_warnings_are_non_fatal(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Runtime security warnings must not raise; startup must complete normally."""
        import app.main as main_module

        prod_settings = _settings(
            app_env='production',
            jwt_secret_key=self._REAL_SECRET,
            rate_limit_enabled=False,
            app_auto_create_tables=False,
        )
        monkeypatch.setattr(main_module, 'settings', prod_settings)

        # Must not raise
        main_module.startup_event()
