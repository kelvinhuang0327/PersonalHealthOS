"""P24 — Boundary Input Validation Regression

Verifies that boundary constraints added in P24 cause FastAPI to return
HTTP 422 (Unprocessable Entity) or Pydantic ValidationError for invalid
inputs at upload/report/query/path boundaries.

Coverage map
------------
TestReportSectionsValidation
  test_sections_too_many_rejected       → 422 (include_sections list max 20)
  test_section_item_too_long_rejected   → 422 (per-item max_length=60)
  test_person_id_too_long_rejected      → 422 (person_id max_length=36)
  test_valid_single_section_accepted    → 202 (constraint respected)

TestDocumentCategoryValidation
  test_category_too_long_rejected       → 422 (Form max_length=60)
  test_category_empty_rejected          → 422 (Form min_length=1)

TestAIModuleFocusValidation
  test_focus_too_long_rejected          → ValidationError (max_length=200)
  test_focus_valid_accepted             → schema valid
  test_focus_none_valid                 → schema valid

TestLabHistoryMetricQueryValidation
  test_metric_query_too_long_rejected   → 422 (Query max_length=120)
  test_metric_query_valid_accepted      → 200 (empty result OK)

Strategy: SQLite in-memory DB + get_db override + get_current_user override.
Pydantic-level tests (no HTTP) use direct model instantiation.
Form endpoint tests rely on FastAPI validating Form params before route
function body runs (no storage mock needed for rejection cases).
"""
from __future__ import annotations

import uuid

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
from app.schemas.ai_modules import AIModuleRequest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
        email=f"p24_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="h",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="P24 Test User",
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


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Wipe dependency overrides after every test."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TestReportSectionsValidation
# ---------------------------------------------------------------------------

class TestReportSectionsValidation:
    """ReportGenerateRequest: list[str] include_sections bound + person_id."""

    def test_sections_too_many_rejected(self):
        """25 section items exceeds max list length of 20 → 422."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        payload = {"include_sections": [f"sec{i}" for i in range(25)]}
        r = client.post("/api/v1/reports/generate", json=payload)
        assert r.status_code == 422

    def test_section_item_too_long_rejected(self):
        """Single section item > 60 chars → 422."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        payload = {"include_sections": ["x" * 61]}
        r = client.post("/api/v1/reports/generate", json=payload)
        assert r.status_code == 422

    def test_person_id_too_long_rejected(self):
        """person_id > 36 chars → 422."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        payload = {"person_id": "x" * 37}
        r = client.post("/api/v1/reports/generate", json=payload)
        assert r.status_code == 422

    def test_valid_single_section_accepted(self):
        """Single valid section → 202 (report generation queued)."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        payload = {"include_sections": ["score"]}
        r = client.post("/api/v1/reports/generate", json=payload)
        assert r.status_code == 202


# ---------------------------------------------------------------------------
# TestDocumentCategoryValidation
# ---------------------------------------------------------------------------

class TestDocumentCategoryValidation:
    """Upload endpoint Form category field: min_length=1, max_length=60."""

    def test_category_too_long_rejected(self):
        """category > 60 chars → 422 (FastAPI validates Form before route body)."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        r = client.post(
            "/api/v1/documents/upload",
            data={"category": "x" * 61},
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert r.status_code == 422

    def test_category_empty_rejected(self):
        """Empty category → 422 (min_length=1)."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        r = client.post(
            "/api/v1/documents/upload",
            data={"category": ""},
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# TestAIModuleFocusValidation
# ---------------------------------------------------------------------------

class TestAIModuleFocusValidation:
    """AIModuleRequest.focus: Optional[str] max_length=200."""

    def test_focus_too_long_rejected(self):
        """focus > 200 chars → Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            AIModuleRequest(focus="x" * 201)

    def test_focus_valid_accepted(self):
        """focus within limit → model valid."""
        req = AIModuleRequest(focus="check glucose trends over 30 days")
        assert req.focus == "check glucose trends over 30 days"

    def test_focus_none_valid(self):
        """focus=None → model valid (optional field)."""
        req = AIModuleRequest(focus=None)
        assert req.focus is None


# ---------------------------------------------------------------------------
# TestLabHistoryMetricQueryValidation
# ---------------------------------------------------------------------------

class TestLabHistoryMetricQueryValidation:
    """GET /documents/lab-history metric Query: max_length=120."""

    def test_metric_query_too_long_rejected(self):
        """metric param > 120 chars → 422."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        long_metric = "x" * 121
        r = client.get(f"/api/v1/documents/lab-history?metric={long_metric}")
        assert r.status_code == 422

    def test_metric_query_valid_accepted(self):
        """Valid short metric param → 200 (empty list from empty DB)."""
        db, user, _ = _make_db_and_user()
        client = _set_user(db, user)
        r = client.get("/api/v1/documents/lab-history?metric=glucose")
        assert r.status_code == 200
        assert r.json() == []
