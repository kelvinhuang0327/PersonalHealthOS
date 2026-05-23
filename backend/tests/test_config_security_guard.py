"""P28 — Runtime Security Config Guard Tests.

Verifies that validate_production_secrets() raises RuntimeError when
the application is configured with an insecure JWT secret placeholder
in a production environment, and does NOT raise in any non-production
environment regardless of the jwt_secret_key value.
"""
import pytest

from app.core.config import Settings, validate_production_secrets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(**kwargs) -> Settings:
    """Construct a Settings instance with explicit field overrides.
    Constructor kwargs take priority over env-file and env-var values in
    pydantic-settings, so these tests are isolated from the local .env file.
    """
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# Production environment — insecure placeholder should RAISE
# ---------------------------------------------------------------------------

class TestProductionRejectsInsecurePlaceholders:
    def test_default_placeholder_rejected_in_production(self):
        """`replace_me` (the in-code default) must not be accepted in prod."""
        s = _settings(app_env='production', jwt_secret_key='replace_me')
        with pytest.raises(RuntimeError, match='jwt_secret_key'):
            validate_production_secrets(s)

    def test_docker_compose_placeholder_rejected_in_production(self):
        """`replace_me_in_prod` (the docker-compose dev default) must not be accepted in prod."""
        s = _settings(app_env='production', jwt_secret_key='replace_me_in_prod')
        with pytest.raises(RuntimeError, match='jwt_secret_key'):
            validate_production_secrets(s)

    def test_empty_secret_rejected_in_production(self):
        """Empty jwt_secret_key must not be accepted in prod."""
        s = _settings(app_env='production', jwt_secret_key='')
        with pytest.raises(RuntimeError, match='jwt_secret_key'):
            validate_production_secrets(s)

    def test_prod_alias_also_rejected(self):
        """`prod` is treated as a production environment alias."""
        s = _settings(app_env='prod', jwt_secret_key='replace_me')
        with pytest.raises(RuntimeError, match='jwt_secret_key'):
            validate_production_secrets(s)

    def test_error_message_names_the_env_var(self):
        """Error message must mention JWT_SECRET_KEY so operators know what to fix."""
        s = _settings(app_env='production', jwt_secret_key='replace_me')
        with pytest.raises(RuntimeError, match='JWT_SECRET_KEY'):
            validate_production_secrets(s)


# ---------------------------------------------------------------------------
# Production environment — real secret should be ACCEPTED
# ---------------------------------------------------------------------------

class TestProductionAcceptsRealSecret:
    _REAL_SECRET = 'f3a8c2d1e94b607a5b2e0d8c4f1a3e6b9d2c5f8a1e4b7d0c3f6a9e2b5d8f1a4'  # 64-char hex

    def test_real_secret_accepted_in_production(self):
        s = _settings(app_env='production', jwt_secret_key=self._REAL_SECRET)
        validate_production_secrets(s)  # must not raise

    def test_real_secret_accepted_with_prod_alias(self):
        s = _settings(app_env='prod', jwt_secret_key=self._REAL_SECRET)
        validate_production_secrets(s)  # must not raise


# ---------------------------------------------------------------------------
# Non-production environments — placeholder must be ALLOWED
# ---------------------------------------------------------------------------

class TestNonProductionAllowsPlaceholder:
    @pytest.mark.parametrize('env', ['dev', 'local', 'staging', 'test', 'development'])
    def test_placeholder_allowed_in_non_production_envs(self, env: str):
        s = _settings(app_env=env, jwt_secret_key='replace_me')
        validate_production_secrets(s)  # must not raise

    def test_default_settings_are_safe(self):
        """The default Settings() (app_env='dev') must not trigger the guard."""
        # Use explicit values to be isolated from the local .env file.
        s = _settings(app_env='dev', jwt_secret_key='replace_me')
        validate_production_secrets(s)  # must not raise


# ---------------------------------------------------------------------------
# Rate-limit settings parseable (PARTIAL B config classification)
# ---------------------------------------------------------------------------

class TestRateLimitSettingsParseable:
    def test_rate_limit_flag_enabled(self):
        """`rate_limit_enabled=True` can be constructed and read correctly."""
        s = _settings(rate_limit_enabled=True)
        assert s.rate_limit_enabled is True

    def test_rate_limit_flag_disabled_by_default(self):
        """`rate_limit_enabled` defaults to False (opt-in, not opt-out)."""
        s = _settings()
        assert s.rate_limit_enabled is False
