"""API tests — P59 Outcome Feedback Visibility (GET /health-assistant/outcome-feedback)
========================================================================================
Verifies that the route exposes P58 safe outcomes for feedback statuses:

  GET /api/v1/health-assistant/outcome-feedback?window_days=7

Coverage
--------
  - not_useful action appears in outcomes
  - not_applicable action appears in outcomes
  - snoozed action appears in outcomes
  - confidence == 0.0 for all feedback-status actions
  - actual_metric_change == null for dismissed actions
  - explanation contains safe Chinese copy; no overclaiming phrases
  - summary includes not_useful_count / not_applicable_count / snoozed_count
  - no medical effectiveness language in any explanation field
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import HealthAction, PersonProfile, User

# ---------------------------------------------------------------------------
# Override cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_app_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_UNSAFE_PHRASES = [
    "improved your health",
    "recommendation worked",
    "treatment is effective",
    "改善健康",
    "建議有效",
    "已證明有效",
    "治療有效",
]


def _build_client(
    seed_actions: list[dict] | None = None,
) -> tuple[TestClient, PersonProfile, User]:
    """Build TestClient with in-memory SQLite, optionally seeding HealthAction rows."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    user = User(
        email=f"outcome_p59_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    person = PersonProfile(
        owner_user_id=user.id,
        display_name="P59 Tester",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    if seed_actions:
        for spec in seed_actions:
            action = HealthAction(
                user_id=user.id,
                person_id=person.id,
                title=spec.get("title", "健康行動"),
                status=spec["status"],
                action_type=spec.get("action_type", "lifestyle"),
                snoozed_until=spec.get("snoozed_until"),
            )
            db.add(action)
        db.commit()

    def override_db():
        yield db

    def override_user():
        return user

    def override_person():
        return person

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_target_person] = override_person

    return TestClient(app), person, user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_outcome_feedback(client: TestClient, window_days: int = 7) -> dict:
    resp = client.get(
        f"/api/v1/health-assistant/outcome-feedback?window_days={window_days}"
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _outcome_ids(data: dict) -> set[str]:
    return {o["action_id"] for o in data["outcomes"]}


# ---------------------------------------------------------------------------
# Presence tests
# ---------------------------------------------------------------------------


def test_not_useful_action_visible_via_route():
    client, person, _ = _build_client(
        seed_actions=[{"title": "沒有用行動", "status": "not_useful"}]
    )
    data = _get_outcome_feedback(client)
    statuses = {o["outcome_status"] for o in data["outcomes"]}
    assert "not_useful" in statuses


def test_not_applicable_action_visible_via_route():
    client, person, _ = _build_client(
        seed_actions=[{"title": "不適合行動", "status": "not_applicable"}]
    )
    data = _get_outcome_feedback(client)
    statuses = {o["outcome_status"] for o in data["outcomes"]}
    assert "not_applicable" in statuses


def test_snoozed_action_visible_via_route():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, person, _ = _build_client(
        seed_actions=[{"title": "延後行動", "status": "snoozed", "snoozed_until": future}]
    )
    data = _get_outcome_feedback(client)
    statuses = {o["outcome_status"] for o in data["outcomes"]}
    assert "snoozed" in statuses


# ---------------------------------------------------------------------------
# Confidence / metric safety tests
# ---------------------------------------------------------------------------


def test_not_useful_confidence_is_zero_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_useful"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_useful":
            assert o["confidence"] == 0.0


def test_not_applicable_confidence_is_zero_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_applicable"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_applicable":
            assert o["confidence"] == 0.0


def test_snoozed_confidence_is_zero_via_route():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "snoozed", "snoozed_until": future}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "snoozed":
            assert o["confidence"] == 0.0


def test_not_useful_actual_metric_change_is_null_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_useful"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_useful":
            assert o["actual_metric_change"] is None


def test_not_applicable_actual_metric_change_is_null_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_applicable"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_applicable":
            assert o["actual_metric_change"] is None


# ---------------------------------------------------------------------------
# No-overclaiming language tests
# ---------------------------------------------------------------------------


def test_not_useful_explanation_safe_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_useful"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_useful":
            assert "回饋已記錄" in o["explanation"]
            for phrase in _UNSAFE_PHRASES:
                assert phrase not in o["explanation"], f"unsafe phrase: {phrase!r}"


def test_not_applicable_explanation_safe_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "not_applicable"}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "not_applicable":
            assert "回饋已記錄" in o["explanation"]
            for phrase in _UNSAFE_PHRASES:
                assert phrase not in o["explanation"], f"unsafe phrase: {phrase!r}"


def test_snoozed_explanation_safe_via_route():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, _, _ = _build_client(
        seed_actions=[{"title": "test action", "status": "snoozed", "snoozed_until": future}]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        if o["outcome_status"] == "snoozed":
            assert "延後" in o["explanation"]
            for phrase in _UNSAFE_PHRASES:
                assert phrase not in o["explanation"], f"unsafe phrase: {phrase!r}"


# ---------------------------------------------------------------------------
# Summary count tests
# ---------------------------------------------------------------------------


def test_summary_not_useful_count_via_route():
    client, _, _ = _build_client(
        seed_actions=[
            {"title": "行動1", "status": "not_useful"},
            {"title": "行動2", "status": "not_useful"},
        ]
    )
    data = _get_outcome_feedback(client)
    assert data["summary"]["not_useful_count"] == 2


def test_summary_not_applicable_count_via_route():
    client, _, _ = _build_client(
        seed_actions=[{"title": "行動1", "status": "not_applicable"}]
    )
    data = _get_outcome_feedback(client)
    assert data["summary"]["not_applicable_count"] == 1


def test_summary_snoozed_count_via_route():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, _, _ = _build_client(
        seed_actions=[
            {"title": "行動1", "status": "snoozed", "snoozed_until": future},
            {"title": "行動2", "status": "snoozed", "snoozed_until": future},
        ]
    )
    data = _get_outcome_feedback(client)
    assert data["summary"]["snoozed_count"] == 2


def test_summary_total_includes_feedback_statuses_via_route():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, _, _ = _build_client(
        seed_actions=[
            {"title": "行動1", "status": "not_useful"},
            {"title": "行動2", "status": "not_applicable"},
            {"title": "行動3", "status": "snoozed", "snoozed_until": future},
        ]
    )
    data = _get_outcome_feedback(client)
    assert data["summary"]["total_count"] == 3


# ---------------------------------------------------------------------------
# No unsafe phrases anywhere in full response
# ---------------------------------------------------------------------------


def test_no_unsafe_phrases_anywhere_via_route():
    """No outcome explanation in any response should contain overclaiming language."""
    future = datetime.now(timezone.utc) + timedelta(days=3)
    client, _, _ = _build_client(
        seed_actions=[
            {"title": "行動1", "status": "not_useful"},
            {"title": "行動2", "status": "not_applicable"},
            {"title": "行動3", "status": "snoozed", "snoozed_until": future},
        ]
    )
    data = _get_outcome_feedback(client)
    for o in data["outcomes"]:
        expl = o.get("explanation", "")
        for phrase in _UNSAFE_PHRASES:
            assert phrase not in expl, (
                f"Unsafe phrase {phrase!r} found in outcome for {o['outcome_status']!r}"
            )


# ---------------------------------------------------------------------------
# Window clamping
# ---------------------------------------------------------------------------


def test_invalid_window_days_clamped_to_7():
    client, _, _ = _build_client(
        seed_actions=[{"title": "行動1", "status": "not_useful"}]
    )
    # window_days=5 is outside [7,30] — FastAPI rejects with 422
    resp = client.get("/api/v1/health-assistant/outcome-feedback?window_days=5")
    assert resp.status_code == 422


def test_valid_window_days_14():
    client, _, _ = _build_client(
        seed_actions=[{"title": "行動1", "status": "not_useful"}]
    )
    data = _get_outcome_feedback(client, window_days=14)
    assert data["window_days"] == 14
    assert "not_useful" in {o["outcome_status"] for o in data["outcomes"]}
