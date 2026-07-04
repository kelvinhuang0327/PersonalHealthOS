from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import HealthAction, ActionOutcome, PersonProfile, User

# Prohibited phrases from P150 contract
PROHIBITED_PHRASES = [
    '診斷',
    '確診',
    '治療',
    '治癒',
    '一定',
    '絕對',
    '保證',
    '100%',
    '取代醫師',
    '正常代表沒問題',
    'diagnose',
    'guarantee',
    'cure',
]

def assert_no_medical_overclaim(data: Any):
    """Recursively scan deserialized JSON data for prohibited phrases."""
    text = str(data)
    for phrase in PROHIBITED_PHRASES:
        assert phrase not in text, f"Response contains prohibited phrase: {phrase}"

@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()

def _setup_db_user_client() -> tuple[Session, User, PersonProfile, TestClient]:
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
        email="p151test@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P151 Tester",
        relationship="self",
        is_default=True,
    )
    db.add(person)
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person

    client = TestClient(app, raise_server_exceptions=False)
    return db, user, person, client


def test_actions_feedback_status_contract():
    db, user, person, client = _setup_db_user_client()

    # 1. Test POST dismissal / feedback creation
    payload_not_useful = {
        "title": "建議進行肝臟健康管理",
        "source_type": "recommendation",
        "source_id": "rule-ast-high-p150",
        "status": "not_useful",
        "priority": "medium",
        "action_type": "lifestyle",
    }
    resp = client.post("/api/v1/actions", json=payload_not_useful, params={"person_id": str(person.id)})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "not_useful"
    assert data["source_id"] == "rule-ast-high-p150"
    assert "user_id" not in data
    assert_no_medical_overclaim(data)

    # 2. Test PATCH update status to not_applicable
    payload_todo = {
        "title": "建議追蹤血糖趨勢",
        "source_type": "recommendation",
        "source_id": "rule-glucose-insufficient-p150",
        "status": "todo",
        "priority": "low",
        "action_type": "lifestyle",
    }
    resp_todo = client.post("/api/v1/actions", json=payload_todo, params={"person_id": str(person.id)})
    assert resp_todo.status_code == 201
    action_id = resp_todo.json()["id"]

    resp_patch = client.patch(f"/api/v1/actions/{action_id}", json={"status": "not_applicable"})
    assert resp_patch.status_code == 200, resp_patch.text
    data_patch = resp_patch.json()
    assert data_patch["status"] == "not_applicable"
    assert "user_id" not in data_patch
    assert_no_medical_overclaim(data_patch)


def test_actions_snooze_status_contract():
    db, user, person, client = _setup_db_user_client()

    # Create a todo action
    payload = {
        "title": "每日步行三十分鐘",
        "source_type": "recommendation",
        "source_id": "rec-ast-p150",
        "status": "todo",
        "priority": "medium",
    }
    resp = client.post("/api/v1/actions", json=payload, params={"person_id": str(person.id)})
    assert resp.status_code == 201
    action_id = resp.json()["id"]

    # Update to snoozed with snoozed_until via PATCH
    snoozed_until_val = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    resp_patch = client.patch(
        f"/api/v1/actions/{action_id}",
        json={"status": "snoozed", "snoozed_until": snoozed_until_val}
    )
    assert resp_patch.status_code == 200, resp_patch.text
    data = resp_patch.json()
    assert data["status"] == "snoozed"
    assert data["snoozed_until"] is not None
    
    # Check that in DB it is saved
    action_in_db = db.query(HealthAction).filter(HealthAction.id == uuid.UUID(action_id)).first()
    assert action_in_db is not None
    assert action_in_db.status == "snoozed"
    assert action_in_db.snoozed_at is not None
    assert action_in_db.snoozed_until is not None

    # Test creating a snoozed action via POST with snoozed_until included in payload
    # It should not crash (extra fields are ignored or handled gracefully)
    payload_snoozed_post = {
        "title": "每日步行三十分鐘",
        "source_type": "recommendation",
        "source_id": "rec-ast-p150",
        "status": "snoozed",
        "priority": "medium",
        "snoozed_until": snoozed_until_val,
    }
    resp_post = client.post("/api/v1/actions", json=payload_snoozed_post, params={"person_id": str(person.id)})
    assert resp_post.status_code == 201, resp_post.text

    assert_no_medical_overclaim(data)


def test_outcome_feedback_retrieval_contract():
    db, user, person, client = _setup_db_user_client()
    now = datetime.now(timezone.utc)

    # 1. Seed completed action (no metrics/outcomes) -> insufficient_data
    act_completed = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Completed Action with No Metrics",
        status="done",
        completed_at=now - timedelta(days=2),
    )
    # 2. Seed completed action (with ActionOutcome) -> improved
    act_completed_with_outcome = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Completed Action with Metric Outcome",
        status="done",
        completed_at=now - timedelta(days=3),
    )
    # 3. Seed dismissed action (not_useful) -> not_useful
    act_dismissed_not_useful = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Dismissed Not Useful",
        status="not_useful",
    )
    # 4. Seed dismissed action (not_applicable) -> not_applicable
    act_dismissed_not_applicable = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Dismissed Not Applicable",
        status="not_applicable",
    )
    # 5. Seed snoozed action -> snoozed
    snoozed_until_val = now + timedelta(days=3)
    act_snoozed = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Snoozed Action",
        status="snoozed",
        snoozed_until=snoozed_until_val,
    )
    # 6. Seed active action -> tracking
    act_active = HealthAction(
        id=uuid.uuid4(),
        user_id=user.id,
        person_id=person.id,
        source_type="recommendation",
        title="Active Action",
        status="todo",
    )

    db.add_all([
        act_completed,
        act_completed_with_outcome,
        act_dismissed_not_useful,
        act_dismissed_not_applicable,
        act_snoozed,
        act_active
    ])
    db.flush()

    # Seed ActionOutcome for act_completed_with_outcome
    outcome = ActionOutcome(
        id=uuid.uuid4(),
        action_id=act_completed_with_outcome.id,
        user_id=user.id,
        person_id=person.id,
        metric_type="steps",
        before_value=4000.0,
        after_value=8000.0,
        delta=4000.0,
        delta_pct=100.0,
        time_window_days=7,
        outcome_label="improved",
        computed_at=now,
    )
    db.add(outcome)
    db.commit()

    resp = client.get("/api/v1/health-assistant/outcome-feedback", params={"window_days": 7, "person_id": str(person.id)})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["person_id"] == str(person.id)
    assert_no_medical_overclaim(data)

    outcomes = data["outcomes"]
    assert len(outcomes) == 6

    # Verify each mapped outcome feedback status and structure
    # completed with no metrics -> insufficient_data
    out_comp = next(o for o in outcomes if o["action_id"] == str(act_completed.id))
    assert out_comp["status"] == "completed"
    assert out_comp["outcome_status"] == "insufficient_data"
    assert out_comp["actual_metric_change"] is None

    # completed with outcome -> improved
    out_comp_out = next(o for o in outcomes if o["action_id"] == str(act_completed_with_outcome.id))
    assert out_comp_out["status"] == "completed"
    assert out_comp_out["outcome_status"] == "improved"
    assert out_comp_out["actual_metric_change"] is not None
    assert out_comp_out["actual_metric_change"]["metric_type"] == "steps"
    assert out_comp_out["actual_metric_change"]["before_value"] == 4000.0
    assert out_comp_out["actual_metric_change"]["after_value"] == 8000.0

    # dismissed not_useful -> not_useful
    out_not_useful = next(o for o in outcomes if o["action_id"] == str(act_dismissed_not_useful.id))
    assert out_not_useful["status"] == "not_useful"
    assert out_not_useful["outcome_status"] == "not_useful"
    assert out_not_useful["confidence"] == 0.0

    # dismissed not_applicable -> not_applicable
    out_not_applicable = next(o for o in outcomes if o["action_id"] == str(act_dismissed_not_applicable.id))
    assert out_not_applicable["status"] == "not_applicable"
    assert out_not_applicable["outcome_status"] == "not_applicable"
    assert out_not_applicable["confidence"] == 0.0

    # snoozed -> snoozed
    out_snoozed = next(o for o in outcomes if o["action_id"] == str(act_snoozed.id))
    assert out_snoozed["status"] == "snoozed"
    assert out_snoozed["outcome_status"] == "snoozed"
    assert out_snoozed["confidence"] == 0.0
    assert out_snoozed["next_check_in"] is not None

    # active -> tracking
    out_active = next(o for o in outcomes if o["action_id"] == str(act_active.id))
    assert out_active["status"] == "tracking"
    assert out_active["outcome_status"] == "tracking"
    assert out_active["confidence"] == 0.0

    # Verify summary counts
    summary = data["summary"]
    assert summary["improved_count"] == 1
    assert summary["insufficient_data_count"] == 1
    assert summary["not_useful_count"] == 1
    assert summary["not_applicable_count"] == 1
    assert summary["snoozed_count"] == 1
    assert summary["tracking_count"] == 1


def test_invalid_input_and_failure_safe_contract():
    db, user, person, client = _setup_db_user_client()

    # 1. Title exceeding max_length of 240
    long_title = "A" * 241
    payload_invalid = {
        "title": long_title,
        "source_type": "recommendation",
        "status": "todo",
    }
    resp = client.post("/api/v1/actions", json=payload_invalid, params={"person_id": str(person.id)})
    assert resp.status_code == 422, "Expected validation error (422) for over-length title"

    # 2. Patching non-existent action
    random_id = str(uuid.uuid4())
    resp_patch = client.patch(f"/api/v1/actions/{random_id}", json={"status": "not_useful"})
    assert resp_patch.status_code == 404, "Expected 404 for non-existent action ID"

    # 3. Querying outcome-feedback with non-7/14/30 value but within ge=7, le=30 range (clamped to 7)
    resp_clamp = client.get("/api/v1/health-assistant/outcome-feedback", params={"window_days": 10, "person_id": str(person.id)})
    assert resp_clamp.status_code == 200
    assert resp_clamp.json()["window_days"] == 7  # Clamped to 7
