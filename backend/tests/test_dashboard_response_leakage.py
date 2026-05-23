"""P34 — Dashboard dict[str, Any] Response Audit

Verifies that dashboard API routes (all bearing typed response_model) do not
expose sensitive / internal fields through their dynamic dict[str, Any] sub-
fields and do not allow cross-user data access.

Routes covered
--------------
GET /dashboard/overview   → DashboardOverviewResponse
GET /dashboard/trends     → DashboardTrendsResponse
GET /dashboard            → DashboardOverviewV2Response  (v2 big aggregation)

Coverage map
------------
TestDashboardOverviewLeakage
  test_overview_no_sensitive_keys           → recursive scan: no password_hash / storage_* / file_path / token
  test_overview_no_user_id_field            → 'user_id' not directly in response top-level or latest_metrics
  test_overview_status_200                  → baseline — route is accessible

TestDashboardTrendsLeakage
  test_trends_no_sensitive_keys             → recursive scan
  test_trends_status_200                    → baseline

TestDashboardV2Leakage
  test_v2_no_sensitive_keys                 → recursive scan on full DashboardOverviewV2Response
  test_v2_recent_metrics_no_user_id         → recent_metrics items do not expose user_id
  test_v2_recent_labs_no_storage_fields     → recent_labs items do not expose file_path / storage_key / download_token
  test_v2_recent_symptoms_no_user_id        → recent_symptoms items do not expose user_id
  test_v2_alerts_no_sensitive_keys          → alerts list recursive scan
  test_v2_decision_items_no_sensitive_keys  → decision_items list recursive scan

TestCrossUserDashboardIsolation
  test_cross_user_person_id_overview_404    → 404 when person_id belongs to another user
  test_cross_user_person_id_trends_404      → 404 when person_id belongs to another user
  test_cross_user_person_id_v2_404          → 404 when person_id belongs to another user

Strategy:
  HTTP tests use SQLite in-memory DB + get_db override + get_current_user override.
  The dashboard v2 endpoint calls asyncio.run() internally; this is compatible
  with sync TestClient (no outer event loop).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, User


# ---------------------------------------------------------------------------
# Sensitive key set — same as P32 / P33 regression suites
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password_hash",
    "hashed_password",
    "password",
    "storage_bucket",
    "storage_key",
    "file_path",
    "download_token",
    "secret_key",
    "secret",
    "is_superuser",
    "is_staff",
})


def _find_sensitive_key(obj: Any, path: str = "") -> str | None:
    """Recursively scan a deserialized JSON object for sensitive key names.

    Returns the first offending key path, or None if clean.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _SENSITIVE_KEYS:
                return f"{path}.{k}" if path else k
            found = _find_sensitive_key(v, f"{path}.{k}" if path else k)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found = _find_sensitive_key(item, f"{path}[{i}]")
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# Shared DB + user helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_db_and_user(email: str = "p34test@example.com") -> tuple[Session, User, PersonProfile]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_not_real",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P34 Test User",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    return db, user, person


def _make_client(db: Session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# TestDashboardOverviewLeakage
# ---------------------------------------------------------------------------


class TestDashboardOverviewLeakage:
    """GET /dashboard/overview must not expose sensitive fields."""

    def test_overview_status_200(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200, resp.text

    def test_overview_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in dashboard overview response: '{found}'. "
            "No credentials or infrastructure fields must be exposed to clients."
        )

    def test_overview_no_user_id_field(self):
        """latest_metrics dict must not include user_id."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        body = resp.json()
        # user_id must not appear at the top level or inside latest_metrics
        assert "user_id" not in body
        assert "user_id" not in body.get("latest_metrics", {})


# ---------------------------------------------------------------------------
# TestDashboardTrendsLeakage
# ---------------------------------------------------------------------------


class TestDashboardTrendsLeakage:
    """GET /dashboard/trends must not expose sensitive fields."""

    def test_trends_status_200(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 200, resp.text

    def test_trends_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in dashboard trends response: '{found}'"
        )

    def test_trends_only_typed_points(self):
        """Each trend series must contain only 'recorded_at' and 'value' keys."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard/trends")
        assert resp.status_code == 200
        body = resp.json()
        for series_name in ("blood_glucose", "weight_kg", "systolic_bp", "sleep_hours"):
            for point in body.get(series_name, []):
                assert set(point.keys()) == {"recorded_at", "value"}, (
                    f"Unexpected keys in trend point for '{series_name}': "
                    f"{set(point.keys()) - {'recorded_at', 'value'}}"
                )


# ---------------------------------------------------------------------------
# TestDashboardV2Leakage
# ---------------------------------------------------------------------------


class TestDashboardV2Leakage:
    """GET /dashboard (v2) must not expose sensitive fields in any nested dict."""

    def test_v2_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in dashboard v2 response: '{found}'. "
            "None of the dynamic dict[str, Any] aggregation fields may expose "
            "credentials or internal storage fields."
        )

    def test_v2_recent_metrics_no_user_id(self):
        """recent_metrics items must not expose user_id."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        for item in resp.json().get("recent_metrics", []):
            assert "user_id" not in item, (
                "user_id must not appear in recent_metrics dashboard items"
            )

    def test_v2_recent_labs_no_storage_fields(self):
        """recent_labs items must not expose file_path, storage_key, or download_token."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        forbidden = {"file_path", "storage_key", "storage_bucket", "download_token", "user_id"}
        for item in resp.json().get("recent_labs", []):
            leaked = set(item.keys()) & forbidden
            assert not leaked, (
                f"Storage/auth fields {leaked} must not appear in recent_labs items"
            )

    def test_v2_recent_symptoms_no_user_id(self):
        """recent_symptoms items must not expose user_id."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        for item in resp.json().get("recent_symptoms", []):
            assert "user_id" not in item, (
                "user_id must not appear in recent_symptoms dashboard items"
            )

    def test_v2_alerts_no_sensitive_keys(self):
        """alerts list in v2 must be recursively clean."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json().get("alerts", []))
        assert found is None, (
            f"Sensitive key found in dashboard v2 alerts: '{found}'"
        )

    def test_v2_decision_items_no_sensitive_keys(self):
        """decision_items must not contain sensitive fields."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json().get("decision_items", []))
        assert found is None, (
            f"Sensitive key found in dashboard v2 decision_items: '{found}'"
        )

    def test_v2_health_score_components_no_sensitive_keys(self):
        """health_score.components dict must not contain sensitive fields."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        score_obj = resp.json().get("health_score", {})
        found = _find_sensitive_key(score_obj)
        assert found is None, (
            f"Sensitive key found in health_score: '{found}'"
        )


# ---------------------------------------------------------------------------
# TestCrossUserDashboardIsolation
# ---------------------------------------------------------------------------


class TestCrossUserDashboardIsolation:
    """Passing another user's person_id to dashboard endpoints must return 404."""

    def _setup_two_users(self) -> tuple[Session, User, PersonProfile, PersonProfile]:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db: Session = SLocal()

        user_a = User(
            id=uuid.uuid4(),
            email="user_a_p34@example.com",
            password_hash="hashed_a",
            is_active=True,
        )
        user_b = User(
            id=uuid.uuid4(),
            email="user_b_p34@example.com",
            password_hash="hashed_b",
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.flush()

        person_a = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_a.id,
            display_name="User A",
            relationship="self",
            is_default=True,
        )
        person_b = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_b.id,
            display_name="User B",
            relationship="self",
            is_default=True,
        )
        db.add_all([person_a, person_b])
        db.commit()
        return db, user_a, person_a, person_b

    def test_cross_user_person_id_overview_404(self):
        """GET /dashboard/overview with another user's person_id → 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/v1/dashboard/overview?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user person_id on /dashboard/overview, got {resp.status_code}"
        )

    def test_cross_user_person_id_trends_404(self):
        """GET /dashboard/trends with another user's person_id → 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/v1/dashboard/trends?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user person_id on /dashboard/trends, got {resp.status_code}"
        )

    def test_cross_user_person_id_v2_404(self):
        """GET /dashboard (v2) with another user's person_id → 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(f"/api/v1/dashboard?person_id={person_b.id}")
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user person_id on /dashboard (v2), got {resp.status_code}"
        )
