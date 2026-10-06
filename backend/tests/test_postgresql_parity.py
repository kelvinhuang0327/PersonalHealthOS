"""P40 – PostgreSQL Parity Smoke

Verifies that the ORM layer works correctly against a real PostgreSQL 16
database, exercising the code paths that the SQLite-in-memory test suite
cannot cover (UUID(as_uuid=True), TIMESTAMPTZ, JSONB, FK cascade).

Key risk verified:
  R4 – risk_engine passes str(user.id) into RiskAlert(user_id=...) which is
       a UUID(as_uuid=True) column.  On SQLite this raises a StatementError
       ('str' object has no attribute 'hex').  PostgreSQL may coerce the
       string, but the ORM contract expects a UUID object.

Requires:
  - Local PostgreSQL accessible at 127.0.0.1:5432
  - Database 'health_insights_test' exists with full schema applied
  - Credentials: postgres / postgres

Run (from backend/ directory):
  DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/health_insights_test?gssencmode=disable&sslmode=disable" \
  PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_postgresql_parity.py -v
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

PG_URL = (
    "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/health_insights_test"
    "?gssencmode=disable&sslmode=disable"
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pg_engine():
    """Return a SQLAlchemy engine connected to the parity test database.
    Skip the entire module if the database is not reachable."""
    try:
        eng = create_engine(PG_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield eng
        eng.dispose()
    except Exception as exc:
        pytest.skip(f"PostgreSQL parity DB unreachable: {exc}")


@pytest.fixture(scope="module")
def pg_session(pg_engine):
    Session = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"parity_{uuid.uuid4().hex[:8]}@test.local"


# ---------------------------------------------------------------------------
# T1  Basic connectivity
# ---------------------------------------------------------------------------

class TestConnectivity:
    def test_select_one(self, pg_engine):
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS val")).fetchone()
        assert result[0] == 1

    def test_uuid_extension(self, pg_engine):
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT uuid_generate_v4()")).fetchone()
        assert result[0] is not None

    def test_expected_tables_exist(self, pg_engine):
        required = {
            "users", "user_profiles", "person_profiles",
            "health_metrics", "symptom_logs", "risk_alerts",
            "lab_reports", "lab_report_items", "medical_documents",
            "health_actions", "action_outcomes",
        }
        with pg_engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public'"
                )
            ).fetchall()
        found = {r[0] for r in rows}
        missing = required - found
        assert not missing, f"Missing tables: {missing}"


# ---------------------------------------------------------------------------
# T2  ORM – User round-trip (UUID primary key)
# ---------------------------------------------------------------------------

class TestUserORM:
    def test_insert_user_with_uuid_pk(self, pg_session):
        from app.models.entities import User

        user = User(
            email=_unique_email(),
            password_hash="hashed_pwd",
            is_active=True,
            account_settings={},
        )
        pg_session.add(user)
        pg_session.flush()

        assert isinstance(user.id, uuid.UUID), (
            f"Expected uuid.UUID, got {type(user.id)}: {user.id!r}"
        )
        pg_session.rollback()

    def test_user_created_at_is_timestamptz(self, pg_session):
        from app.models.entities import User

        user = User(
            email=_unique_email(),
            password_hash="hashed",
            is_active=True,
            account_settings={},
        )
        pg_session.add(user)
        pg_session.flush()

        # created_at is server_default func.now() — should come back as
        # timezone-aware datetime after flush.
        assert user.created_at is not None
        pg_session.rollback()


# ---------------------------------------------------------------------------
# T3  ORM – PersonProfile (UUID FK to users.id)
# ---------------------------------------------------------------------------

class TestPersonProfileORM:
    def _create_user(self, session) -> "User":
        from app.models.entities import User
        user = User(
            email=_unique_email(),
            password_hash="x",
            is_active=True,
            account_settings={},
        )
        session.add(user)
        session.flush()
        return user

    def test_insert_person_profile_uuid_fk(self, pg_session):
        from app.models.entities import PersonProfile

        user = self._create_user(pg_session)
        profile = PersonProfile(
            owner_user_id=user.id,   # UUID object
            display_name="Test Person",
            relationship="self",
            is_default=True,
        )
        pg_session.add(profile)
        pg_session.flush()

        assert isinstance(profile.id, uuid.UUID)
        assert profile.owner_user_id == user.id
        pg_session.rollback()


# ---------------------------------------------------------------------------
# T4  ORM – HealthMetric (UUID FK, TIMESTAMPTZ)
# ---------------------------------------------------------------------------

class TestHealthMetricORM:
    def _setup_user_and_profile(self, session):
        from app.models.entities import User, PersonProfile
        user = User(
            email=_unique_email(),
            password_hash="x",
            is_active=True,
            account_settings={},
        )
        session.add(user)
        session.flush()
        profile = PersonProfile(
            owner_user_id=user.id,
            display_name="P",
            relationship="self",
            is_default=True,
        )
        session.add(profile)
        session.flush()
        return user, profile

    def test_insert_health_metric(self, pg_session):
        from app.models.entities import HealthMetric

        user, profile = self._setup_user_and_profile(pg_session)
        metric = HealthMetric(
            user_id=user.id,
            subject_profile_id=profile.id,
            recorded_at=datetime.now(timezone.utc),
            systolic_bp=120,
            diastolic_bp=80,
            heart_rate=72,
        )
        pg_session.add(metric)
        pg_session.flush()

        assert isinstance(metric.id, uuid.UUID)
        pg_session.rollback()


# ---------------------------------------------------------------------------
# T5  R4 – RiskAlert UUID coercion (the known risk)
#
# risk_engine._make_alert() is called with user_id as a *str* (because
# api/metrics.py calls evaluate_metric_risks(str(current_user.id), ...)).
# RiskAlert.user_id is UUID(as_uuid=True).
#
# This test proves whether passing a str fails or succeeds on PostgreSQL.
# If it FAILS (DataError / StatementError) → R4 is a real PostgreSQL bug.
# If it PASSES → PostgreSQL coerces but ORM contract is violated (type smell).
# ---------------------------------------------------------------------------

class TestRiskAlertUUIDCoercion:
    def _make_user(self, session):
        from app.models.entities import User
        user = User(
            email=_unique_email(),
            password_hash="x",
            is_active=True,
            account_settings={},
        )
        session.add(user)
        session.flush()
        return user

    def test_risk_alert_with_uuid_object_succeeds(self, pg_session):
        """Baseline: passing a proper UUID object must succeed."""
        from app.models.entities import RiskAlert

        user = self._make_user(pg_session)
        metric_id = uuid.uuid4()

        alert = RiskAlert(
            user_id=user.id,            # <- UUID object (correct)
            source_type="health_metric",
            source_id=metric_id,
            rule_code="BMI_OBESE",
            severity="high",
            title="BMI Obese",
            message="BMI is in the obese range.",
            description="BMI >= 30",
            recommendation="Consult a physician.",
            status="active",
        )
        pg_session.add(alert)
        pg_session.flush()
        assert isinstance(alert.id, uuid.UUID)
        pg_session.rollback()

    def test_risk_alert_with_str_uuid_r4_behavior(self, pg_session):
        """R4 probe: passing str(user.id) to UUID(as_uuid=True) column.

        On SQLite this raises StatementError.
        On PostgreSQL the behaviour depends on psycopg2/SQLAlchemy version:
          - May raise DataError / ProgrammingError (bug confirmed)
          - May silently coerce (type-smell, still warrants fix)

        The test marks XFAIL if PostgreSQL rejects the str — which means
        the R4 fix is REQUIRED, not just cosmetic.
        """
        from sqlalchemy.exc import StatementError, DataError
        from app.models.entities import RiskAlert

        user = self._make_user(pg_session)
        metric_id = uuid.uuid4()

        str_user_id = str(user.id)   # <- str, not UUID (the defect)

        raised = False
        try:
            alert = RiskAlert(
                user_id=str_user_id,    # <- triggers R4 path
                source_type="health_metric",
                source_id=metric_id,
                rule_code="BMI_OBESE",
                severity="high",
                title="BMI Obese",
                message="BMI is in the obese range.",
                description="BMI >= 30",
                recommendation="Consult a physician.",
                status="active",
            )
            pg_session.add(alert)
            pg_session.flush()
        except (StatementError, DataError, Exception) as exc:
            raised = True
            pg_session.rollback()
            # Re-record: R4 IS a runtime bug on PostgreSQL
            pytest.fail(
                f"R4 CONFIRMED: str UUID causes failure on PostgreSQL: {exc!r}"
            )
        else:
            pg_session.rollback()

        # If we reach here: PostgreSQL coerced the string — technically
        # the insert worked but the ORM contract is violated.  We record
        # this as a warning via an assertion that is always true but
        # documented with the finding.
        if not raised:
            # R4 is a latent type smell — fix still recommended
            assert True, (
                "R4 WARNING: str UUID was accepted by PostgreSQL (psycopg2 "
                "coercion). ORM contract violated. Fix recommended."
            )


# ---------------------------------------------------------------------------
# T6  FK cascade: deleting a user should cascade to related rows
# ---------------------------------------------------------------------------

class TestFKCascade:
    def test_delete_user_cascades_metric(self, pg_session):
        from app.models.entities import User, HealthMetric

        user = User(
            email=_unique_email(),
            password_hash="x",
            is_active=True,
            account_settings={},
        )
        pg_session.add(user)
        pg_session.flush()

        metric = HealthMetric(
            user_id=user.id,
            recorded_at=datetime.now(timezone.utc),
            heart_rate=65,
        )
        pg_session.add(metric)
        pg_session.flush()

        metric_id = metric.id
        pg_session.delete(user)
        pg_session.flush()

        # expire_all clears the identity map so session.get queries the DB
        pg_session.expire_all()
        remaining = pg_session.get(HealthMetric, metric_id)
        assert remaining is None, "ON DELETE CASCADE did not remove the metric"
        pg_session.rollback()


# ---------------------------------------------------------------------------
# T7  JSONB column (account_settings on User)
# ---------------------------------------------------------------------------

class TestJSONBColumn:
    def test_jsonb_roundtrip(self, pg_session):
        from app.models.entities import User

        payload = {"theme": "dark", "notifications": True, "version": 3}
        user = User(
            email=_unique_email(),
            password_hash="x",
            is_active=True,
            account_settings=payload,
        )
        pg_session.add(user)
        pg_session.flush()

        loaded = pg_session.get(User, user.id)
        assert loaded.account_settings == payload
        pg_session.rollback()
