"""P12 Auth Negative Smoke — cross-user family context isolation.

Verifies that user A holding a valid session cannot read user B's
family health context by passing user B's profile_id as a query param.
Expected: 404 (person not found for current user).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, User


@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


def _build_two_user_client() -> tuple[TestClient, User, PersonProfile, User, PersonProfile, Session]:
    """Two distinct users, each owning one PersonProfile, sharing an in-memory DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()

    user_a = User(email=f"user_a_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    user_b = User(email=f"user_b_{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    person_a = PersonProfile(
        owner_user_id=user_a.id,
        display_name="User A Self",
        relationship="self",
        is_default=True,
    )
    person_b = PersonProfile(
        owner_user_id=user_b.id,
        display_name="User B Self",
        relationship="self",
        is_default=True,
    )
    db.add_all([person_a, person_b])
    db.commit()
    db.refresh(person_a)
    db.refresh(person_b)

    def override_db():
        yield db

    # Authenticate as user_a only; get_target_person runs real ownership check
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    client = TestClient(app)
    return client, user_a, person_a, user_b, person_b, db


class TestAuthNegativeCrossUserIsolation:
    """User A must not read User B's family context via person_id query param."""

    def test_cross_user_family_context_returns_404(self):
        client, user_a, person_a, user_b, person_b, db = _build_two_user_client()

        # user_a requests family-health-context with user_b's person_id
        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            params={"person_id": str(person_b.id)},
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user access, got {resp.status_code}. "
            f"Response: {resp.text}"
        )
        # Must not leak user_b's display_name or id in body
        body = resp.text
        assert "User B Self" not in body, "Response leaked user B display_name"
        assert str(person_b.id) not in body, "Response leaked user B person_id"

    def test_cross_user_family_recommendations_returns_404(self):
        client, user_a, person_a, user_b, person_b, db = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-recommendations",
            params={"person_id": str(person_b.id)},
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-user access, got {resp.status_code}. "
            f"Response: {resp.text}"
        )
        body = resp.text
        assert "User B Self" not in body, "Response leaked user B display_name"
        assert str(person_b.id) not in body, "Response leaked user B person_id"

    def test_own_person_id_still_accessible(self):
        """Sanity check: user_a can access their own person_a profile."""
        client, user_a, person_a, user_b, person_b, db = _build_two_user_client()

        resp = client.get(
            "/api/v1/health-assistant/family-health-context",
            params={"person_id": str(person_a.id)},
        )
        assert resp.status_code == 200, (
            f"Expected 200 for own profile, got {resp.status_code}. "
            f"Response: {resp.text}"
        )
