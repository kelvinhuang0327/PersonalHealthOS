"""API tests — P7 Narrative Memory endpoints
=============================================

GET  /api/v1/health-assistant/narrative-memory
POST /api/v1/health-assistant/narrative-memory/generate

Uses in-memory SQLite + FastAPI TestClient (fresh engine per test class).

Coverage
--------
  - GET returns found=False when no memory exists yet
  - POST /generate returns 200 with correct structure
  - POST /generate response contains required keys
  - GET returns found=True after generate
  - POST /generate confidence is a float in [0, 1]
  - POST /generate with daily period_type
  - POST /generate with weekly period_type
  - POST /generate with monthly period_type
  - GET ?period_type=daily isolates to daily
  - GET ?period_type=weekly isolates to weekly
  - no hallucinated content on empty DB (limitations populated)
  - summary_text is a non-empty string
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import PersonProfile, User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _build_client() -> tuple[TestClient, User, PersonProfile, Session]:
    """Build TestClient with fresh in-memory SQLite DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SLocal()

    user = User(email="narrative_test@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="Narrative Tester",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person

    client = TestClient(app)
    return client, user, person, db


# ---------------------------------------------------------------------------
# Tests — GET /narrative-memory
# ---------------------------------------------------------------------------

class TestGetNarrativeMemory:
    def test_get_returns_200(self):
        client, *_ = _build_client()
        resp = client.get("/api/v1/health-assistant/narrative-memory")
        assert resp.status_code == 200

    def test_get_no_memory_found_false(self):
        """Before any generate call, found should be False."""
        client, *_ = _build_client()
        resp = client.get("/api/v1/health-assistant/narrative-memory")
        data = resp.json()
        assert data["found"] is False
        assert data["memory"] is None

    def test_get_response_has_person_id(self):
        client, user, person, db = _build_client()
        resp = client.get("/api/v1/health-assistant/narrative-memory")
        assert "person_id" in resp.json()

    def test_get_message_when_not_found(self):
        client, *_ = _build_client()
        resp = client.get("/api/v1/health-assistant/narrative-memory")
        data = resp.json()
        assert "message" in data

    def test_get_after_generate_returns_found_true(self):
        client, *_ = _build_client()
        client.post("/api/v1/health-assistant/narrative-memory/generate?period_type=weekly")
        resp = client.get("/api/v1/health-assistant/narrative-memory?period_type=weekly")
        data = resp.json()
        assert data["found"] is True
        assert data["memory"] is not None

    def test_get_isolates_by_period_type(self):
        """Generate daily, then GET weekly should still return found=False."""
        client, *_ = _build_client()
        client.post("/api/v1/health-assistant/narrative-memory/generate?period_type=daily")
        resp = client.get("/api/v1/health-assistant/narrative-memory?period_type=weekly")
        data = resp.json()
        assert data["found"] is False


# ---------------------------------------------------------------------------
# Tests — POST /narrative-memory/generate
# ---------------------------------------------------------------------------

class TestGenerateNarrativeMemory:
    def test_generate_returns_200(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        assert resp.status_code == 200

    def test_generate_response_has_required_keys(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        data = resp.json()
        assert "generated" in data
        assert "memory" in data
        assert "person_id" in data

    def test_generate_generated_true(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        assert resp.json()["generated"] is True

    def test_generate_memory_has_structure(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        memory = resp.json()["memory"]
        required = {
            "periodType", "periodStart", "periodEnd", "summaryText",
            "topThemes", "improvingItems", "worseningItems",
            "repeatedRisks", "effectiveActions", "ignoredItems",
            "confidence", "limitations",
        }
        assert required <= set(memory.keys())

    def test_generate_confidence_in_range(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        confidence = resp.json()["memory"]["confidence"]
        assert 0.0 <= confidence <= 1.0

    def test_generate_summary_text_non_empty(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        summary = resp.json()["memory"]["summaryText"]
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_generate_daily_period_type(self):
        client, *_ = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=daily"
        )
        assert resp.json()["memory"]["periodType"] == "daily"

    def test_generate_weekly_period_type(self):
        client, *_ = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=weekly"
        )
        assert resp.json()["memory"]["periodType"] == "weekly"

    def test_generate_monthly_period_type(self):
        client, *_ = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=monthly"
        )
        assert resp.json()["memory"]["periodType"] == "monthly"

    def test_generate_invalid_period_type_rejected(self):
        client, *_ = _build_client()
        resp = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=invalid"
        )
        # Should reject with 422 (validation error)
        assert resp.status_code == 422

    def test_generate_limitations_present_on_empty_db(self):
        """Empty DB should produce limitations (no hallucination guarantee)."""
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        limitations = resp.json()["memory"]["limitations"]
        assert isinstance(limitations, list)
        assert len(limitations) > 0

    def test_generate_period_dates_are_valid_iso(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        memory = resp.json()["memory"]
        date.fromisoformat(memory["periodStart"])  # must not raise
        date.fromisoformat(memory["periodEnd"])

    def test_generate_top_themes_is_list(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        assert isinstance(resp.json()["memory"]["topThemes"], list)

    def test_generate_repeated_risks_is_list(self):
        client, *_ = _build_client()
        resp = client.post("/api/v1/health-assistant/narrative-memory/generate")
        assert isinstance(resp.json()["memory"]["repeatedRisks"], list)

    def test_generate_twice_updates_existing_record(self):
        """Calling generate twice for the same period should update, not duplicate."""
        client, *_ = _build_client()
        resp1 = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=daily"
        )
        resp2 = client.post(
            "/api/v1/health-assistant/narrative-memory/generate?period_type=daily"
        )
        # Both should return the same period_start (same day window)
        assert resp1.json()["memory"]["periodStart"] == resp2.json()["memory"]["periodStart"]

    def test_get_invalid_period_type_rejected(self):
        client, *_ = _build_client()
        resp = client.get(
            "/api/v1/health-assistant/narrative-memory?period_type=invalid"
        )
        assert resp.status_code == 422
