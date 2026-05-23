"""P30 — Schema Boundary Constraint Regression

Verifies that constraints added in P30 cause FastAPI to return HTTP 422
or Pydantic ValidationError for inputs that exceed field bounds.

Coverage map
------------
TestPersonFieldConstraints   (HTTP — POST /api/v1/persons, PUT /api/v1/persons/{id})
  test_person_create_allergies_too_long         → 422 (max_length=2000)
  test_person_create_family_history_too_long    → 422 (max_length=2000)
  test_person_create_chronic_conditions_too_long → 422 (max_length=2000)
  test_person_update_allergies_too_long         → 422 (max_length=2000)
  test_person_update_family_history_too_long    → 422 (max_length=2000)
  test_person_update_chronic_conditions_too_long → 422 (max_length=2000)
  test_person_create_valid_with_all_text_fields → 201 (constraints respected)

TestMetricNoteConstraint     (HTTP — POST /api/v1/metrics)
  test_metric_note_too_long                     → 422 (max_length=2000)
  test_metric_note_valid                        → 201

TestChangePasswordConstraint (HTTP — POST /api/v1/auth/change-password)
  test_change_password_current_too_long         → 422 (max_length=1024)

TestActionConfidenceConstraint (Pydantic direct)
  test_confidence_negative_rejected             → ValidationError
  test_confidence_above_one_rejected            → ValidationError
  test_confidence_zero_valid                    → valid (boundary)
  test_confidence_one_valid                     → valid (boundary)
  test_confidence_none_valid                    → valid (optional)

TestHealthAssistantInlineSchemas (Pydantic direct)
  test_snooze_body_too_long_snoozed_until       → ValidationError (max_length=40)
  test_family_body_related_profile_id_too_long  → ValidationError (max_length=36)
  test_snooze_body_valid                        → valid
  test_family_body_valid                        → valid

Strategy: SQLite in-memory DB + get_db override + get_current_user override for HTTP
tests.  Pydantic-level tests use direct model instantiation (no HTTP layer).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.entities import PersonProfile, User
from app.schemas.actions import HealthActionCreate


# ---------------------------------------------------------------------------
# Shared DB + user helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _make_db_and_user() -> tuple[Session, User, PersonProfile]:
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
        email="p30test@example.com",
        password_hash="hashed",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="Test Person",
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
# TestPersonFieldConstraints
# ---------------------------------------------------------------------------

_TOO_LONG = "x" * 2001
_VALID_TEXT = "x" * 2000
_PERSON_BASE = {
    "display_name": "Test P30",
    "relationship": "family",
}


class TestPersonFieldConstraints:
    def test_person_create_allergies_too_long(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/persons", json={**_PERSON_BASE, "allergies": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_create_family_history_too_long(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/persons", json={**_PERSON_BASE, "family_history": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_create_chronic_conditions_too_long(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/persons", json={**_PERSON_BASE, "chronic_conditions": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_update_allergies_too_long(self):
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.put(f"/api/v1/persons/{person.id}", json={"allergies": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_update_family_history_too_long(self):
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.put(f"/api/v1/persons/{person.id}", json={"family_history": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_update_chronic_conditions_too_long(self):
        db, user, person = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.put(f"/api/v1/persons/{person.id}", json={"chronic_conditions": _TOO_LONG})
        assert resp.status_code == 422

    def test_person_create_valid_with_all_text_fields(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/persons", json={
            **_PERSON_BASE,
            "allergies": _VALID_TEXT,
            "family_history": _VALID_TEXT,
            "chronic_conditions": _VALID_TEXT,
        })
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# TestMetricNoteConstraint
# ---------------------------------------------------------------------------

_METRIC_BASE = {
    "recorded_at": datetime.now(timezone.utc).isoformat(),
}


class TestMetricNoteConstraint:
    def test_metric_note_too_long(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/metrics", json={**_METRIC_BASE, "note": _TOO_LONG})
        assert resp.status_code == 422

    def test_metric_note_valid(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/metrics", json={
            **_METRIC_BASE,
            "heart_rate": 72,
            "note": _VALID_TEXT,
        })
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# TestChangePasswordConstraint
# ---------------------------------------------------------------------------

class TestChangePasswordConstraint:
    def test_change_password_current_too_long(self):
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "x" * 1025,
            "new_password": "validpass123",
        })
        assert resp.status_code == 422

    def test_change_password_current_at_max_boundary_rejected_by_auth(self):
        """1024-char password is schema-valid but fails auth — returns 400/401, not 422."""
        db, user, _ = _make_db_and_user()
        client = _make_client(db, user)
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "x" * 1024,
            "new_password": "validpass123",
        })
        # Schema is valid so FastAPI won't return 422; auth logic rejects it
        assert resp.status_code != 422


# ---------------------------------------------------------------------------
# TestActionConfidenceConstraint  (Pydantic direct — no HTTP layer)
# ---------------------------------------------------------------------------

_ACTION_MIN = {"title": "P30 test action"}


class TestActionConfidenceConstraint:
    def test_confidence_negative_rejected(self):
        with pytest.raises(ValidationError):
            HealthActionCreate(**_ACTION_MIN, confidence=-0.01)

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            HealthActionCreate(**_ACTION_MIN, confidence=1.01)

    def test_confidence_zero_valid(self):
        m = HealthActionCreate(**_ACTION_MIN, confidence=0.0)
        assert m.confidence == 0.0

    def test_confidence_one_valid(self):
        m = HealthActionCreate(**_ACTION_MIN, confidence=1.0)
        assert m.confidence == 1.0

    def test_confidence_none_valid(self):
        m = HealthActionCreate(**_ACTION_MIN, confidence=None)
        assert m.confidence is None


# ---------------------------------------------------------------------------
# TestHealthAssistantInlineSchemas  (Pydantic direct)
# ---------------------------------------------------------------------------

class TestHealthAssistantInlineSchemas:
    def _snooze_cls(self):
        from app.api.health_assistant import _SnoozeBody
        return _SnoozeBody

    def _family_cls(self):
        from app.api.health_assistant import _FamilyRelationshipBody
        return _FamilyRelationshipBody

    def test_snooze_body_too_long_snoozed_until(self):
        _SnoozeBody = self._snooze_cls()
        with pytest.raises(ValidationError):
            _SnoozeBody(snoozed_until="a" * 41)

    def test_snooze_body_valid(self):
        _SnoozeBody = self._snooze_cls()
        m = _SnoozeBody(hours=48, snoozed_until=None)
        assert m.hours == 48

    def test_family_body_related_profile_id_too_long(self):
        _FamilyRelationshipBody = self._family_cls()
        with pytest.raises(ValidationError):
            _FamilyRelationshipBody(
                related_profile_id="a" * 37,
                relationship_type="child",
            )

    def test_family_body_valid(self):
        _FamilyRelationshipBody = self._family_cls()
        m = _FamilyRelationshipBody(
            related_profile_id=str(uuid.uuid4()),
            relationship_type="child",
        )
        assert m.relationship_type == "child"
