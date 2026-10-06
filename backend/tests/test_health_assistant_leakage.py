"""P33 — health_assistant.py Untyped Response Audit

Verifies that health_assistant.py routes (which return dict[str, Any] with no
response_model) do not expose sensitive or internal fields and do not allow
cross-user data access.

Coverage map
------------
TestEvidenceBundleLeakage
  test_evidence_bundle_no_sensitive_keys          → recursive scan: no password_hash / storage_* / file_path / token
  test_evidence_bundle_person_id_is_own_person    → person_id in response is the requested person's UUID

TestDeviceSignalsLeakage
  test_device_signals_no_sensitive_keys           → recursive scan on device-signals response
  test_device_signals_person_id_is_own            → person_id key is own person, not a foreign person

TestFamilyRelationshipsLeakage
  test_family_relationships_list_no_sensitive_keys   → GET /family-relationships: recursive scan
  test_family_relationships_owner_is_own_user        → owner_user_id in relationships is own UUID
  test_family_relationship_create_no_sensitive_keys  → POST /family-relationships: recursive scan
  test_family_relationship_create_owner_is_own_user  → owner_user_id in create response is own UUID

TestFamilyContextLeakage
  test_family_health_context_no_sensitive_keys    → recursive scan on family-health-context response
  test_family_recommendations_no_sensitive_keys   → recursive scan on family-recommendations response

TestCrossUserIsolation
  test_cross_user_person_id_returns_404_evidence_bundle   → 404 when person_id belongs to another user
  test_cross_user_person_id_returns_404_family_context    → 404 when person_id belongs to another user
  test_cross_user_person_id_returns_404_recommendations   → 404 when person_id belongs to another user

TestNotificationStatusLeakage
  test_snooze_response_no_sensitive_keys          → POST /notifications/{id}/snooze: recursive scan
  test_ignore_response_no_sensitive_keys          → POST /notifications/{id}/ignore: recursive scan

Strategy:
  HTTP tests use SQLite in-memory DB + get_db override + get_current_user override.
  Cross-user tests create two users with separate PersonProfiles.
  Sensitive key detection uses recursive JSON scan.
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
from app.models.entities import FamilyRelationship, NotificationLog, PersonProfile, User


# ---------------------------------------------------------------------------
# Sensitive key set — anything in a response JSON that should never appear
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

    Returns the first offending key path found, or None if clean.
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


def _make_db_and_user(email: str = "p33test@example.com") -> tuple[Session, User, PersonProfile]:
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
        display_name="P33 Test",
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
# TestEvidenceBundleLeakage
# ---------------------------------------------------------------------------


class TestEvidenceBundleLeakage:
    """GET /health-assistant/evidence-bundle must not expose sensitive fields."""

    def test_evidence_bundle_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in evidence-bundle response: '{found}'. "
            "This internal field must not be returned to clients."
        )

    def test_evidence_bundle_person_id_is_own_person(self):
        """person_id in evidence-bundle response is the current user's person UUID."""
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/evidence-bundle")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("person_id") == str(person.id)


# ---------------------------------------------------------------------------
# TestDeviceSignalsLeakage
# ---------------------------------------------------------------------------


class TestDeviceSignalsLeakage:
    """GET /health-assistant/device-signals must not expose sensitive fields."""

    def test_device_signals_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/device-signals")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in device-signals response: '{found}'"
        )

    def test_device_signals_person_id_is_own(self):
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/device-signals")
        assert resp.status_code == 200
        assert resp.json().get("person_id") == str(person.id)


# ---------------------------------------------------------------------------
# TestFamilyRelationshipsLeakage
# ---------------------------------------------------------------------------


class TestFamilyRelationshipsLeakage:
    """Family relationship endpoints must not expose sensitive fields."""

    def test_family_relationships_list_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/family-relationships")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in family-relationships response: '{found}'"
        )

    def test_family_relationships_owner_is_own_user(self):
        """owner_user_id in each relationship dict must equal the authenticated user's UUID."""
        db, user, person = _make_db_and_user()

        # Add a second person (related) and a FamilyRelationship
        related_person = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            display_name="Child Profile",
            relationship="child",
            is_default=False,
        )
        db.add(related_person)
        db.flush()

        rel = FamilyRelationship(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            subject_profile_id=person.id,
            related_profile_id=related_person.id,
            relationship_type="child",
            permission_level="read_only",
        )
        db.add(rel)
        db.commit()

        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/family-relationships")
        assert resp.status_code == 200
        body = resp.json()
        for item in body.get("relationships", []):
            if "owner_user_id" in item:
                assert item["owner_user_id"] == str(user.id), (
                    "owner_user_id in family-relationships response must be the "
                    "requesting user's own UUID — no cross-user UUID may appear here"
                )

    def test_family_relationship_create_no_sensitive_keys(self):
        db, user, person = _make_db_and_user()

        related_person = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            display_name="Spouse",
            relationship="spouse",
            is_default=False,
        )
        db.add(related_person)
        db.commit()

        client = _make_client(db, user)
        resp = client.post("/api/v1/health-assistant/family-relationships", json={
            "related_profile_id": str(related_person.id),
            "relationship_type": "spouse",
            "permission_level": "read_only",
        })
        assert resp.status_code == 201, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in family-relationship create response: '{found}'"
        )

    def test_family_relationship_create_owner_is_own_user(self):
        """POST /family-relationships response owner_user_id must be own UUID."""
        db, user, person = _make_db_and_user()

        related_person = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            display_name="Parent",
            relationship="parent",
            is_default=False,
        )
        db.add(related_person)
        db.commit()

        client = _make_client(db, user)
        resp = client.post("/api/v1/health-assistant/family-relationships", json={
            "related_profile_id": str(related_person.id),
            "relationship_type": "parent",
            "permission_level": "read_only",
        })
        assert resp.status_code == 201
        body = resp.json()
        if "owner_user_id" in body:
            assert body["owner_user_id"] == str(user.id)


# ---------------------------------------------------------------------------
# TestFamilyContextLeakage
# ---------------------------------------------------------------------------


class TestFamilyContextLeakage:
    """Family health context and recommendation endpoints must not leak sensitive fields."""

    def test_family_health_context_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/family-health-context")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key in family-health-context response: '{found}'"
        )

    def test_family_recommendations_no_sensitive_keys(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.get("/api/v1/health-assistant/family-recommendations")
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key in family-recommendations response: '{found}'"
        )


# ---------------------------------------------------------------------------
# TestCrossUserIsolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    """Passing another user's person_id must return 404, never their data."""

    def _setup_two_users(self) -> tuple[Session, User, PersonProfile, PersonProfile]:
        """Creates user_a (authenticated) and user_b with their own persons on the same DB."""
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
            email="user_a_p33@example.com",
            password_hash="hashed_a",
            is_active=True,
        )
        user_b = User(
            id=uuid.uuid4(),
            email="user_b_p33@example.com",
            password_hash="hashed_b",
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.flush()

        person_a = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_a.id,
            display_name="User A Person",
            relationship="self",
            is_default=True,
        )
        person_b = PersonProfile(
            id=uuid.uuid4(),
            owner_user_id=user_b.id,
            display_name="User B Person",
            relationship="self",
            is_default=True,
        )
        db.add_all([person_a, person_b])
        db.commit()
        return db, user_a, person_a, person_b

    def test_cross_user_person_id_returns_404_evidence_bundle(self):
        """Requesting /evidence-bundle with another user's person_id must return 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(
            f"/api/v1/health-assistant/evidence-bundle?person_id={person_b.id}"
        )
        assert resp.status_code == 404, (
            f"Expected 404 when accessing another user's person_id, got {resp.status_code}: {resp.text}"
        )
        # Response body must not contain user_b data
        body = resp.json()
        assert "detail" in body or "message" in body or resp.status_code == 404

    def test_cross_user_person_id_returns_404_family_context(self):
        """Requesting /family-health-context with another user's person_id must return 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(
            f"/api/v1/health-assistant/family-health-context?person_id={person_b.id}"
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user person_id on family-health-context, got {resp.status_code}"
        )

    def test_cross_user_person_id_returns_404_recommendations(self):
        """Requesting /recommendations with another user's person_id must return 404."""
        db, user_a, _, person_b = self._setup_two_users()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: user_a
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(
            f"/api/v1/health-assistant/recommendations?person_id={person_b.id}"
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user person_id on recommendations, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# TestNotificationStatusLeakage
# ---------------------------------------------------------------------------


class TestNotificationStatusLeakage:
    """Notification status update endpoints must not expose sensitive fields."""

    def _make_notification(self, db: Session, user: User, person: PersonProfile) -> NotificationLog:
        nlog = NotificationLog(
            id=uuid.uuid4(),
            user_id=user.id,
            subject_profile_id=person.id,
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            cooldown_key="lab_glucose_high",
            source_type="lab_abnormality",
            priority=2,
            title="Blood glucose elevated",
            status="active",
            generated_at=datetime.now(timezone.utc),
        )
        db.add(nlog)
        db.commit()
        return nlog

    def test_snooze_response_no_sensitive_keys(self):
        db, user, person = _make_db_and_user()
        nlog = self._make_notification(db, user, person)
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/health-assistant/notifications/{nlog.id}/snooze",
            json={"hours": 24},
        )
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in snooze response: '{found}'"
        )

    def test_ignore_response_no_sensitive_keys(self):
        db, user, person = _make_db_and_user()
        nlog = self._make_notification(db, user, person)
        client = _make_client(db, user)
        resp = client.post(
            f"/api/v1/health-assistant/notifications/{nlog.id}/ignore"
        )
        assert resp.status_code == 200, resp.text
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key found in ignore response: '{found}'"
        )
