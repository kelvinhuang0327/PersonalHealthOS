"""P23 — Input Validation & Schema Hardening Regression

Verifies that Pydantic constraints added in P23 cause FastAPI to return
HTTP 422 (Unprocessable Entity) for invalid inputs rather than writing
garbage data to the DB or crashing with 500.

Coverage map
------------
TestAuthInputValidation
  test_login_password_too_long          → 422 (max_length=1024)

TestSymptomInputValidation
  test_create_note_too_long             → 422 (max_length=2000)
  test_update_note_too_long             → 422 (max_length=2000)
  test_create_valid_with_note           → 201 (constraint respected)

TestProfileInputValidation
  test_allergies_too_long               → 422 (max_length=2000)
  test_family_history_too_long          → 422 (max_length=2000)
  test_chronic_conditions_too_long      → 422 (max_length=2000)
  test_account_email_invalid            → 422 (EmailStr validation)
  test_profile_valid                    → 200 (constraints respected)

TestActionInputValidation
  test_create_description_too_long      → 422 (max_length=2000)
  test_create_category_too_long         → 422 (max_length=60)
  test_create_priority_too_long         → 422 (max_length=30)
  test_update_snooze_reason_too_long    → 422 (max_length=500)
  test_create_valid_action              → 201 (constraints respected)

TestDocumentParsedItemValidation
  test_update_value_too_long            → 422 (max_length=500)
  test_update_unit_too_long             → 422 (max_length=50)
  test_update_reference_range_too_long  → 422 (max_length=100)

Strategy: SQLite in-memory DB + get_db override + get_current_user override.
Tests that hit authenticated endpoints use the standard dependency override
pattern established in P18 tests.
"""
from __future__ import annotations

import io
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


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Wipe dependency overrides after every test."""
    yield
    app.dependency_overrides.clear()


def _make_db_and_user() -> tuple[Session, User, PersonProfile]:
    """Create one user + default PersonProfile in a fresh SQLite DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SLocal()

    user = User(
        email=f"p23_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="h",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="P23 Test User",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    return db, user, person


def _set_user(db: Session, user: User) -> TestClient:
    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ---------------------------------------------------------------------------
# TestAuthInputValidation
# ---------------------------------------------------------------------------


class TestAuthInputValidation:
    """Auth endpoint input validation — no DB/auth setup needed (public endpoints)."""

    def test_login_password_too_long(self):
        """Password > 1024 chars must be rejected with 422."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "x@example.com", "password": "A" * 1025},
        )
        assert resp.status_code == 422, resp.text

    def test_login_password_at_max_accepted(self):
        """Password exactly 1024 chars must pass schema validation (may fail 401 — not 422)."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nouser@example.com", "password": "A" * 1024},
        )
        # 401 = credential failure (schema OK); anything but 422 is fine here
        assert resp.status_code != 422, f"Got 422 — schema rejected a valid-length password: {resp.text}"


# ---------------------------------------------------------------------------
# TestSymptomInputValidation
# ---------------------------------------------------------------------------


class TestSymptomInputValidation:
    def test_create_note_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/symptoms",
            json={
                "severity": 3,
                "symptom": "headache",
                "note": "N" * 2001,
            },
        )
        assert resp.status_code == 422, resp.text

    def test_update_note_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        # First create a symptom
        create_resp = client.post(
            "/api/v1/symptoms",
            json={"severity": 2, "symptom": "headache"},
        )
        assert create_resp.status_code == 200, create_resp.text
        symptom_id = create_resp.json()["id"]

        # Now try to update with oversized note
        resp = client.put(
            f"/api/v1/symptoms/{symptom_id}",
            json={"note": "N" * 2001},
        )
        assert resp.status_code == 422, resp.text

    def test_create_valid_with_note(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/symptoms",
            json={
                "severity": 1,
                "symptom": "mild headache",
                "note": "A" * 200,
            },
        )
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# TestProfileInputValidation
# ---------------------------------------------------------------------------


class TestProfileInputValidation:
    def test_allergies_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.put(
            "/api/v1/profile/me",
            json={"allergies": "A" * 2001},
        )
        assert resp.status_code == 422, resp.text

    def test_family_history_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.put(
            "/api/v1/profile/me",
            json={"family_history": "F" * 2001},
        )
        assert resp.status_code == 422, resp.text

    def test_chronic_conditions_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.put(
            "/api/v1/profile/me",
            json={"chronic_conditions": "C" * 2001},
        )
        assert resp.status_code == 422, resp.text

    def test_account_email_invalid(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.put(
            "/api/v1/profile/account",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422, resp.text

    def test_profile_valid(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.put(
            "/api/v1/profile/me",
            json={
                "allergies": "Penicillin",
                "family_history": "Hypertension",
                "chronic_conditions": "None",
            },
        )
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# TestActionInputValidation
# ---------------------------------------------------------------------------


class TestActionInputValidation:
    _BASE_ACTION = {
        "title": "Exercise daily",
        "action_type": "lifestyle",
        "priority": "medium",
        "frequency": "daily",
        "status": "todo",
    }

    def test_create_description_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={**self._BASE_ACTION, "description": "D" * 2001},
        )
        assert resp.status_code == 422, resp.text

    def test_create_category_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={**self._BASE_ACTION, "category": "C" * 61},
        )
        assert resp.status_code == 422, resp.text

    def test_create_priority_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={**self._BASE_ACTION, "priority": "P" * 31},
        )
        assert resp.status_code == 422, resp.text

    def test_update_snooze_reason_too_long(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        # Create action first
        create_resp = client.post(
            "/api/v1/actions",
            json=self._BASE_ACTION,
        )
        assert create_resp.status_code == 201, create_resp.text
        action_id = create_resp.json()["id"]

        # Update with oversized snooze_reason
        resp = client.patch(
            f"/api/v1/actions/{action_id}",
            json={"snooze_reason": "R" * 501},
        )
        assert resp.status_code == 422, resp.text

    def test_create_valid_action(self):
        db, user, person = _make_db_and_user()
        client = _set_user(db, user)
        resp = client.post(
            "/api/v1/actions",
            json={
                **self._BASE_ACTION,
                "description": "Walk 30 minutes",
                "category": "fitness",
            },
        )
        assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# TestDocumentParsedItemValidation
# ---------------------------------------------------------------------------


class TestDocumentParsedItemValidation:
    """Tests against ParsedItemUpdate via PATCH /{document_id}/parsed-items/{item_id}.

    Since creating a real document requires file upload + parse pipeline we
    instead test the schema layer directly through Pydantic to confirm the
    constraints are wired (the PATCH endpoint itself requires a real
    document_id that we cannot easily stub without the full pipeline).
    """

    def test_update_value_too_long(self):
        from app.schemas.documents import ParsedItemUpdate
        import pydantic

        with pytest.raises(pydantic.ValidationError) as exc_info:
            ParsedItemUpdate(value="V" * 501)
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "value" in fields, f"Expected 'value' error, got: {errors}"

    def test_update_unit_too_long(self):
        from app.schemas.documents import ParsedItemUpdate
        import pydantic

        with pytest.raises(pydantic.ValidationError) as exc_info:
            ParsedItemUpdate(unit="U" * 51)
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "unit" in fields, f"Expected 'unit' error, got: {errors}"

    def test_update_reference_range_too_long(self):
        from app.schemas.documents import ParsedItemUpdate
        import pydantic

        with pytest.raises(pydantic.ValidationError) as exc_info:
            ParsedItemUpdate(reference_range="R" * 101)
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "reference_range" in fields, f"Expected 'reference_range' error, got: {errors}"

    def test_update_valid(self):
        from app.schemas.documents import ParsedItemUpdate

        item = ParsedItemUpdate(value="12.5", unit="mg/dL", reference_range="10-20")
        assert item.value == "12.5"
        assert item.unit == "mg/dL"
