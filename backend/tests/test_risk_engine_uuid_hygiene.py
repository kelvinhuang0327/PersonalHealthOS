"""P41 – Risk Engine UUID Hygiene Regression

Verifies that `risk_engine.evaluate_metric_risks` and
`evaluate_lab_item_risks` correctly handle UUID type coercion — specifically
that passing `str(user.id)` does NOT crash on SQLite (StatementError) after
the R4 fix, and that created `RiskAlert` objects have properly typed
`user_id` (uuid.UUID, not str).

Prior to the P41 fix the test fixture in P35
(test_metrics_symptoms_response_leakage.py) had to mock
`evaluate_metric_risks` to avoid the SQLite `StatementError`.  After the fix
those mocks are removed and the real function is exercised.

All tests use SQLite in-memory (StaticPool) — no Docker required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import (
    HealthMetric,
    LabReport,
    LabReportItem,
    PersonProfile,
    RiskAlert,
    User,
)
from app.services.risk_engine import evaluate_lab_item_risks, evaluate_metric_risks


# ---------------------------------------------------------------------------
# Shared SQLite fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def sqlite_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.rollback()
    session.close()
    engine.dispose()


def _make_user(session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"uuid_hygiene_{uuid.uuid4().hex[:6]}@test.local",
        password_hash="x",
        is_active=True,
        account_settings={},
    )
    session.add(user)
    session.flush()
    return user


def _make_profile(session, user: User) -> PersonProfile:
    profile = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="Hygiene Test",
        relationship="self",
        is_default=True,
        height_cm=Decimal("170.0"),
        weight_kg=Decimal("90.0"),  # BMI ~31.1 → obese (>= 27.0)
    )
    session.add(profile)
    session.flush()
    return profile


def _make_metric_bp_elevated(user: User, profile: PersonProfile) -> HealthMetric:
    """Blood pressure 140/90 — triggers BP_HIGH alert."""
    return HealthMetric(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=profile.id,
        recorded_at=datetime.now(timezone.utc),
        systolic_bp=140,
        diastolic_bp=90,
    )


def _make_metric_normal(user: User, profile: PersonProfile | None) -> HealthMetric:
    """Heart rate only — triggers no alerts."""
    return HealthMetric(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=profile.id if profile else None,
        recorded_at=datetime.now(timezone.utc),
        heart_rate=72,
    )


# ---------------------------------------------------------------------------
# T1  str UUID does NOT crash on SQLite (R4 fix verification)
# ---------------------------------------------------------------------------

class TestStrUUIDNoSQLiteCrash:
    """Core regression: str(user.id) passed to evaluate_metric_risks must not
    raise StatementError on SQLite after the P41 fix."""

    def test_str_uuid_bp_alert_no_crash(self, sqlite_session):
        """evaluate_metric_risks(str(user.id), ...) with BP-elevated metric
        must succeed on SQLite — no StatementError."""
        user = _make_user(sqlite_session)
        profile = _make_profile(sqlite_session, user)
        metric = _make_metric_bp_elevated(user, profile)
        sqlite_session.add(metric)
        sqlite_session.flush()

        # This is the exact call pattern from api/metrics.py — str(user.id)
        alerts = evaluate_metric_risks(str(user.id), profile, metric)
        assert len(alerts) >= 1, "Expected at least one BP_HIGH alert"

        # Persist the alerts (as the API route does) — must not crash
        for alert in alerts:
            alert.subject_profile_id = profile.id
            sqlite_session.add(alert)
        sqlite_session.flush()  # would raise StatementError before fix

    def test_uuid_object_bp_alert_no_crash(self, sqlite_session):
        """evaluate_metric_risks(user.id, ...) with UUID object works too."""
        user = _make_user(sqlite_session)
        profile = _make_profile(sqlite_session, user)
        metric = _make_metric_bp_elevated(user, profile)
        sqlite_session.add(metric)
        sqlite_session.flush()

        alerts = evaluate_metric_risks(user.id, profile, metric)
        assert len(alerts) >= 1

        for alert in alerts:
            alert.subject_profile_id = profile.id
            sqlite_session.add(alert)
        sqlite_session.flush()


# ---------------------------------------------------------------------------
# T2  Created RiskAlert has UUID-typed user_id
# ---------------------------------------------------------------------------

class TestRiskAlertUserIdType:
    """After the fix, RiskAlert.user_id must be a uuid.UUID object (not str)
    regardless of whether the caller passes str or UUID."""

    def test_alert_user_id_is_uuid_when_str_passed(self, sqlite_session):
        """When str(user.id) is passed, the alert stored in DB has UUID user_id."""
        user = _make_user(sqlite_session)
        profile = _make_profile(sqlite_session, user)
        metric = _make_metric_bp_elevated(user, profile)
        sqlite_session.add(metric)
        sqlite_session.flush()

        alerts = evaluate_metric_risks(str(user.id), profile, metric)
        assert alerts, "Need at least one alert for type check"

        for alert in alerts:
            alert.subject_profile_id = profile.id
            sqlite_session.add(alert)
        sqlite_session.flush()

        # Reload from DB and verify user_id type
        loaded = sqlite_session.get(RiskAlert, alerts[0].id)
        assert loaded is not None
        assert isinstance(loaded.user_id, uuid.UUID), (
            f"RiskAlert.user_id should be uuid.UUID after fix, got {type(loaded.user_id)}: "
            f"{loaded.user_id!r}"
        )
        assert loaded.user_id == user.id, "RiskAlert.user_id must equal the owning user's id"

    def test_alert_user_id_is_uuid_when_uuid_passed(self, sqlite_session):
        """When UUID object is passed, the alert stored in DB has UUID user_id."""
        user = _make_user(sqlite_session)
        profile = _make_profile(sqlite_session, user)
        metric = _make_metric_bp_elevated(user, profile)
        sqlite_session.add(metric)
        sqlite_session.flush()

        alerts = evaluate_metric_risks(user.id, profile, metric)  # UUID directly
        assert alerts

        for alert in alerts:
            alert.subject_profile_id = profile.id
            sqlite_session.add(alert)
        sqlite_session.flush()

        loaded = sqlite_session.get(RiskAlert, alerts[0].id)
        assert isinstance(loaded.user_id, uuid.UUID)
        assert loaded.user_id == user.id


# ---------------------------------------------------------------------------
# T3  Normal metrics produce no alerts (return value unchanged by fix)
# ---------------------------------------------------------------------------

class TestNoAlertForNormalMetrics:
    """Fix must not change the return value for non-alerting metrics."""

    def test_heart_rate_only_returns_empty(self, sqlite_session):
        """Metric with only heart_rate should produce no alerts — same as before fix."""
        user = _make_user(sqlite_session)
        profile = _make_profile(sqlite_session, user)
        metric = _make_metric_normal(user, profile)
        sqlite_session.add(metric)
        sqlite_session.flush()

        alerts = evaluate_metric_risks(str(user.id), profile, metric)
        assert alerts == [], (
            f"Expected no alerts for heart-rate-only metric, got {alerts}"
        )

    def test_none_profile_returns_no_bmi_alert(self, sqlite_session):
        """profile=None must not trigger BMI alert — no change to rule logic."""
        user = _make_user(sqlite_session)
        metric = _make_metric_normal(user, None)
        sqlite_session.add(metric)
        sqlite_session.flush()

        alerts = evaluate_metric_risks(str(user.id), None, metric)
        assert alerts == []


# ---------------------------------------------------------------------------
# T4  evaluate_lab_item_risks str UUID (same fix applied)
# ---------------------------------------------------------------------------

class TestLabItemRisksUUIDHygiene:
    """evaluate_lab_item_risks also accepts str user_id — must coerce on SQLite."""

    def _make_lab_report(self, session, user: User) -> LabReport:
        report = LabReport(
            id=uuid.uuid4(),
            user_id=user.id,
            report_date=datetime.now(timezone.utc).date(),
            report_type="health_check",
        )
        session.add(report)
        session.flush()
        return report

    def _make_alt_item(self, report: LabReport) -> LabReportItem:
        """ALT=50 (>= 40) triggers LIVER_ALT_HIGH alert."""
        return LabReportItem(
            id=uuid.uuid4(),
            report_id=report.id,
            item_name="ALT",
            value_num=Decimal("50"),
            unit="U/L",
            range_source="extracted",
        )

    def test_lab_str_uuid_no_crash(self, sqlite_session):
        """evaluate_lab_item_risks(str(user.id), item) must not crash on SQLite."""
        user = _make_user(sqlite_session)
        report = self._make_lab_report(sqlite_session, user)
        item = self._make_alt_item(report)
        sqlite_session.add(item)
        sqlite_session.flush()

        alerts = evaluate_lab_item_risks(str(user.id), item)
        assert len(alerts) >= 1, "Expected LIVER_ALT_HIGH alert"

        for alert in alerts:
            sqlite_session.add(alert)
        sqlite_session.flush()  # would raise StatementError before fix

    def test_lab_alert_user_id_is_uuid(self, sqlite_session):
        """RiskAlert from lab path must have UUID-typed user_id."""
        user = _make_user(sqlite_session)
        report = self._make_lab_report(sqlite_session, user)
        item = self._make_alt_item(report)
        sqlite_session.add(item)
        sqlite_session.flush()

        alerts = evaluate_lab_item_risks(str(user.id), item)
        assert alerts

        for alert in alerts:
            sqlite_session.add(alert)
        sqlite_session.flush()

        loaded = sqlite_session.get(RiskAlert, alerts[0].id)
        assert isinstance(loaded.user_id, uuid.UUID)
        assert loaded.user_id == user.id
