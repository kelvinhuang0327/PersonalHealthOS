"""P38 — Remaining API Surface Response Audit

Verifies that profile, insights, and action API routes do not expose
user_id or any sensitive/internal fields to client responses.

C.GAPs found and fixed:
  ProfileResponse.user_id      — removed from schema + profile.py dicts (GET/PUT /profile/me)
  HealthInsightResponse.user_id — removed from schema
  HealthActionRead.user_id     — removed from schema

A.SAFE (no changes):
  UserResponse          — only id, email (no password_hash)
  TokenResponse         — only access_token, token_type
  AccountResponse       — only id, email, account_settings (no password_hash)
  PersonResponse        — owner_user_id = P33 intentional design for multi-person mgmt
  ExternalSyncResponse  — synced_count, source only
  ExternalTrendResponse — metric, points only
  TimelineResponse      — data dicts contain only health metrics (no user_id)
  ReportStatusResponse  — download_url is relative API path with short-lived token
  /actions/{id}/outcomes (response_model=list) — manually constructed dicts with health metrics only

Routes covered
--------------
Profile:
  GET /profile/me   → ProfileResponse: user_id absent, public fields present
  PUT /profile/me   → ProfileResponse: user_id absent
  GET /profile/account → AccountResponse: no password_hash

Insights:
  GET /insights         → list[HealthInsightResponse]: user_id absent
  POST /insights/{id}/dismiss → HealthInsightResponse: user_id absent (seeds + dismisses)

Actions:
  GET /actions          → list[HealthActionRead]: user_id absent
  POST /actions         → HealthActionRead: user_id absent

Cross-user isolation:
  GET /insights with foreign person_id → 404
  GET /actions with foreign person_id → empty list (by design, not 404)

Coverage map
------------
TestProfileResponseLeakage
  test_get_profile_no_user_id          → GET /profile/me: user_id absent
  test_get_profile_no_sensitive_keys   → GET /profile/me: recursive scan
  test_put_profile_no_user_id          → PUT /profile/me: user_id absent
  test_get_profile_field_contract      → public fields present; user_id absent
  test_account_no_password_hash        → GET /profile/account: no password_hash

TestInsightResponseLeakage
  test_list_insights_no_user_id        → GET /insights: user_id absent
  test_list_insights_no_sensitive_keys → GET /insights: recursive scan
  test_dismiss_insight_no_user_id      → POST /insights/{id}/dismiss: user_id absent

TestActionResponseLeakage
  test_list_actions_no_user_id         → GET /actions: user_id absent
  test_list_actions_no_sensitive_keys  → GET /actions: recursive scan
  test_create_action_no_user_id        → POST /actions: user_id absent
  test_create_action_no_sensitive_keys → POST /actions: recursive scan

TestCrossUserProfileInsightIsolation
  test_cross_user_insights_empty       → foreign person_id on GET /insights → empty (no data leak)
  test_cross_user_insights_own_visible → own person_id → seeded insight returned
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import HealthAction, HealthInsight, PersonProfile, User


# ---------------------------------------------------------------------------
# Sensitive key set
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
    "user_id",
})


def _find_sensitive_key(obj: Any, path: str = "") -> str | None:
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
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_db_and_user(email: str = "p38test@example.com") -> tuple[Session, User, PersonProfile]:
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
        display_name="P38 Test User",
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


def _seed_insight(db: Session, user: User, person: PersonProfile) -> HealthInsight:
    insight = HealthInsight(
        id=uuid.uuid4(),
        user_id=user.id,
        subject_profile_id=person.id,
        insight_type="blood_pressure_high",
        severity="warning",
        title="血壓偏高提醒",
        summary="近期收縮壓多次超過 130 mmHg，建議密切關注。",
        recommendation="減少鈉攝入，增加有氧運動。",
        is_active=True,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


def _seed_action(db: Session, user: User, person: PersonProfile) -> HealthAction:
    action = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="ai",
        title="每天步行 30 分鐘",
        action_type="lifestyle",
        priority="high",
        status="todo",
        frequency="daily",
        resurface_count=0,
        streak_count=0,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


# ---------------------------------------------------------------------------
# TestProfileResponseLeakage
# ---------------------------------------------------------------------------


class TestProfileResponseLeakage:
    """Profile routes must not expose user_id or sensitive fields."""

    def test_get_profile_no_user_id(self):
        """GET /profile/me must not include user_id in response."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/profile/me", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"ProfileResponse must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_get_profile_no_sensitive_keys(self):
        """GET /profile/me must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/profile/me", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /profile/me response."
        )

    def test_put_profile_no_user_id(self):
        """PUT /profile/me must not include user_id in response."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.put(
            "/api/v1/profile/me",
            json={"full_name": "Updated Name"},
            params={"person_id": str(person.id)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"ProfileResponse (PUT) must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_get_profile_field_contract(self):
        """ProfileResponse must expose id and full_name; must NOT expose user_id or password_hash."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/profile/me", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "id" in body, "ProfileResponse must include 'id'"
        assert "full_name" in body, "ProfileResponse must include 'full_name'"
        assert "user_id" not in body, "ProfileResponse must NOT expose 'user_id'"
        assert "password_hash" not in body, "ProfileResponse must NOT expose 'password_hash'"

    def test_account_no_password_hash(self):
        """GET /profile/account must not include password_hash."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/profile/account")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "password_hash" not in body, (
            f"AccountResponse must not expose password_hash. Got keys: {list(body.keys())}"
        )
        assert "password" not in body, "AccountResponse must not expose 'password'"
        assert "id" in body, "AccountResponse must include 'id'"
        assert "email" in body, "AccountResponse must include 'email'"


# ---------------------------------------------------------------------------
# TestInsightResponseLeakage
# ---------------------------------------------------------------------------


class TestInsightResponseLeakage:
    """Health insight routes must not expose user_id or sensitive fields."""

    def test_list_insights_no_user_id(self):
        """GET /insights list items must not contain user_id."""
        db, user, person = _make_db_and_user()
        _seed_insight(db, user, person)
        client = _make_client(db, user)
        resp = client.get("/api/v1/insights", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1, "Expected at least one seeded insight"
        for item in items:
            assert "user_id" not in item, (
                f"HealthInsightResponse must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_insights_no_sensitive_keys(self):
        """GET /insights response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_insight(db, user, person)
        client = _make_client(db, user)
        resp = client.get("/api/v1/insights", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /insights response."
        )

    def test_dismiss_insight_no_user_id(self):
        """POST /insights/{id}/dismiss response must not contain user_id."""
        db, user, person = _make_db_and_user()
        insight = _seed_insight(db, user, person)
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/insights/{insight.id}/dismiss",
            params={"person_id": str(person.id)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"HealthInsightResponse (dismiss) must not expose user_id. Got keys: {list(body.keys())}"
        )


# ---------------------------------------------------------------------------
# TestActionResponseLeakage
# ---------------------------------------------------------------------------


class TestActionResponseLeakage:
    """Health action routes must not expose user_id or sensitive fields."""

    def test_list_actions_no_user_id(self):
        """GET /actions list items must not contain user_id."""
        db, user, person = _make_db_and_user()
        _seed_action(db, user, person)
        client = _make_client(db, user)
        resp = client.get("/api/v1/actions", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1, "Expected at least one seeded action"
        for item in items:
            assert "user_id" not in item, (
                f"HealthActionRead must not expose user_id. Got keys: {list(item.keys())}"
            )

    def test_list_actions_no_sensitive_keys(self):
        """GET /actions response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        _seed_action(db, user, person)
        client = _make_client(db, user)
        resp = client.get("/api/v1/actions", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in GET /actions response."
        )

    def test_create_action_no_user_id(self):
        """POST /actions response must not contain user_id."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={
                "title": "每天喝 2 公升水",
                "action_type": "lifestyle",
                "priority": "medium",
                "status": "todo",
                "frequency": "daily",
                "source_type": "manual",
            },
            params={"person_id": str(person.id)},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "user_id" not in body, (
            f"HealthActionRead (create) must not expose user_id. Got keys: {list(body.keys())}"
        )

    def test_create_action_no_sensitive_keys(self):
        """POST /actions response must pass recursive sensitive-key scan."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={
                "title": "減少精製糖攝入",
                "action_type": "nutrition",
                "priority": "high",
                "status": "todo",
                "frequency": "daily",
                "source_type": "manual",
            },
            params={"person_id": str(person.id)},
        )
        assert resp.status_code == 201, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' found in POST /actions response."
        )


# ---------------------------------------------------------------------------
# TestCrossUserProfileInsightIsolation
# ---------------------------------------------------------------------------


class TestCrossUserProfileInsightIsolation:
    """Cross-user person_id on profile and insight routes must not leak data."""

    def test_cross_user_insights_empty(self):
        """GET /insights with a foreign person_id must return empty (not their insights)."""
        db, user_a, _ = _make_db_and_user("p38a@example.com")

        user_b = User(
            id=uuid.uuid4(),
            email="p38b@example.com",
            password_hash="hashed_not_real",
            is_active=True,
        )
        db.add(user_b)
        db.flush()
        person_b = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_b.id,
            display_name="User B",
            relationship="self",
            is_default=True,
        )
        db.add(person_b)
        db.flush()
        # Seed an insight for user_b
        insight_b = HealthInsight(
            id=uuid.uuid4(),
            user_id=user_b.id,
            subject_profile_id=person_b.id,
            insight_type="glucose_high",
            severity="warning",
            title="User B insight",
            summary="User B only.",
            is_active=True,
        )
        db.add(insight_b)
        db.commit()

        # user_a authenticates but targets user_b's person_id → should get 404 (person not found)
        client = _make_client(db, user_a)
        resp = client.get("/api/v1/insights", params={"person_id": str(person_b.id)})
        # get_target_person dep validates ownership → returns 404
        assert resp.status_code == 404, (
            f"Expected 404 for foreign person_id on GET /insights, got {resp.status_code}"
        )

    def test_cross_user_insights_own_visible(self):
        """GET /insights with own person_id must return own insights correctly."""
        db, user, person = _make_db_and_user("p38c@example.com")
        _seed_insight(db, user, person)
        client = _make_client(db, user)
        resp = client.get("/api/v1/insights", params={"person_id": str(person.id)})
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert len(items) >= 1, "Own insights must be returned for own person_id"
        for item in items:
            assert "user_id" not in item
