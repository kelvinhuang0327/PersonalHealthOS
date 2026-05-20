"""Tests for notification_history_service (P5 Learning Loop).

Uses in-memory SQLite — no Docker required.  All tests exercise the service
layer directly (no HTTP client), so they run fast and independently.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.entities import Base, NotificationLog, PersonProfile, User
from app.services.notification_history_service import (
    get_notification_by_id,
    load_notification_history,
    persist_notification_candidates,
    update_notification_status,
)

# ---------------------------------------------------------------------------
# Shared DB + seed helpers
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_ENGINE)
Base.metadata.create_all(bind=_ENGINE)


@pytest.fixture()
def db():
    session = _Session()
    yield session
    session.close()


@pytest.fixture()
def user(db):
    u = User(email=f"hist_{uuid.uuid4().hex[:6]}@test.com", password_hash="hashed")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def person(db, user):
    p = PersonProfile(
        owner_user_id=user.id,
        display_name="Test Person",
        relationship="self",
        is_default=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def other_person(db, user):
    p = PersonProfile(
        owner_user_id=user.id,
        display_name="Other Person",
        relationship="parent",
        is_default=False,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_candidate(
    candidate_id: str = "abc123def456",
    cooldown_key: str = "lab_abnormality_ldl",
    priority: str = "high",
    source_type: str = "lab_abnormality",
    suppress_reason: str | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "cooldown_key": cooldown_key,
        "source_type": source_type,
        "priority": priority,
        "title": f"Test: {cooldown_key}",
        "message": "Something is abnormal.",
        "why_now": "Because test.",
        "suggested_action": None,
        "confidence": 0.85,
        "evidence_sources": [{"type": "lab", "id": None, "summary": "LDL high"}],
        "suppress_reason": suppress_reason,
    }


# ---------------------------------------------------------------------------
# persist_notification_candidates
# ---------------------------------------------------------------------------

def test_persist_active_candidates_inserts_rows(db, user, person):
    candidates = [_make_candidate("aaa000aaa000")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), candidates, [])

    assert "aaa000aaa000" in id_map
    nid = id_map["aaa000aaa000"]
    record = db.query(NotificationLog).filter(NotificationLog.id == uuid.UUID(nid)).first()
    assert record is not None
    assert record.status == "generated"
    assert record.suppress_reason is None
    assert record.cooldown_key == "lab_abnormality_ldl"


def test_persist_suppressed_candidates_inserts_suppressed_rows(db, user, person):
    suppressed = [_make_candidate("bbb111bbb111", suppress_reason="冷卻中")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), [], suppressed)

    assert "bbb111bbb111" in id_map
    nid = id_map["bbb111bbb111"]
    record = db.query(NotificationLog).filter(NotificationLog.id == uuid.UUID(nid)).first()
    assert record.status == "suppressed"
    assert record.suppress_reason == "冷卻中"


def test_persist_returns_id_mapping_for_both_active_and_suppressed(db, user, person):
    active = [_make_candidate("ccc222ccc222")]
    suppressed = [_make_candidate("ddd333ddd333", suppress_reason="冷卻中")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, suppressed)

    assert "ccc222ccc222" in id_map
    assert "ddd333ddd333" in id_map
    assert len(id_map) == 2


def test_dedup_same_candidate_within_6h_not_duplicated(db, user, person):
    candidates = [_make_candidate("eee444eee444")]
    id_map_1 = persist_notification_candidates(db, str(user.id), str(person.id), candidates, [])
    id_map_2 = persist_notification_candidates(db, str(user.id), str(person.id), candidates, [])

    assert id_map_1["eee444eee444"] == id_map_2["eee444eee444"]
    count = (
        db.query(NotificationLog)
        .filter(NotificationLog.candidate_id == "eee444eee444")
        .count()
    )
    assert count == 1


def test_dedup_respects_person_scope(db, user, person, other_person):
    """Same candidate_id for two different people → two separate rows."""
    candidates = [_make_candidate("fff555fff555")]
    id_map_p1 = persist_notification_candidates(db, str(user.id), str(person.id), candidates, [])
    id_map_p2 = persist_notification_candidates(db, str(user.id), str(other_person.id), candidates, [])

    assert id_map_p1["fff555fff555"] != id_map_p2["fff555fff555"]


# ---------------------------------------------------------------------------
# load_notification_history
# ---------------------------------------------------------------------------

def test_load_history_returns_empty_for_new_person(db, user, person):
    history = load_notification_history(db, str(user.id), str(person.id))
    assert history == []


def test_load_history_returns_one_entry_per_cooldown_key(db, user, person):
    active = [
        _make_candidate("g01g01g01g01", cooldown_key="key_a"),
        _make_candidate("g02g02g02g02", cooldown_key="key_b"),
    ]
    persist_notification_candidates(db, str(user.id), str(person.id), active, [])

    history = load_notification_history(db, str(user.id), str(person.id))
    keys = {h["cooldown_key"] for h in history}
    assert "key_a" in keys
    assert "key_b" in keys


def test_load_history_ignore_count_aggregated(db, user, person):
    """After ignoring a notification 2×, ignore_count should reflect 2."""
    active = [_make_candidate("h01h01h01h01", cooldown_key="key_ignored")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["h01h01h01h01"]

    update_notification_status(db, nid, str(user.id), str(person.id), status="ignored")
    update_notification_status(db, nid, str(user.id), str(person.id), status="ignored")

    history = load_notification_history(db, str(user.id), str(person.id))
    entry = next(h for h in history if h["cooldown_key"] == "key_ignored")
    assert entry["ignore_count"] >= 2


def test_load_history_sent_at_is_set_for_generated(db, user, person):
    active = [_make_candidate("i01i01i01i01", cooldown_key="key_sent")]
    persist_notification_candidates(db, str(user.id), str(person.id), active, [])

    history = load_notification_history(db, str(user.id), str(person.id))
    entry = next(h for h in history if h["cooldown_key"] == "key_sent")
    assert entry["sent_at"] is not None


def test_load_history_suppressed_only_entry_has_no_sent_at(db, user, person):
    suppressed = [_make_candidate("j01j01j01j01", cooldown_key="key_supponly", suppress_reason="冷卻中")]
    persist_notification_candidates(db, str(user.id), str(person.id), [], suppressed)

    history = load_notification_history(db, str(user.id), str(person.id))
    entry = next((h for h in history if h["cooldown_key"] == "key_supponly"), None)
    assert entry is not None
    assert entry["sent_at"] is None


# ---------------------------------------------------------------------------
# update_notification_status
# ---------------------------------------------------------------------------

def test_update_status_snooze(db, user, person):
    active = [_make_candidate("k01k01k01k01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["k01k01k01k01"]
    snoozed_until = datetime.now(timezone.utc) + timedelta(hours=24)

    result = update_notification_status(
        db, nid, str(user.id), str(person.id),
        status="snoozed", snoozed_until=snoozed_until,
    )
    assert result is not None
    assert result["status"] == "snoozed"
    assert result["snoozed_until"] is not None
    assert result["snooze_count"] == 1


def test_update_status_ignore(db, user, person):
    active = [_make_candidate("l01l01l01l01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["l01l01l01l01"]

    result = update_notification_status(db, nid, str(user.id), str(person.id), status="ignored")
    assert result is not None
    assert result["status"] == "ignored"
    assert result["ignore_count"] == 1


def test_update_status_click(db, user, person):
    active = [_make_candidate("m01m01m01m01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["m01m01m01m01"]

    result = update_notification_status(db, nid, str(user.id), str(person.id), status="clicked")
    assert result is not None
    assert result["status"] == "clicked"
    assert result["clicked_at"] is not None


def test_update_status_acted(db, user, person):
    active = [_make_candidate("n01n01n01n01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["n01n01n01n01"]

    result = update_notification_status(db, nid, str(user.id), str(person.id), status="acted")
    assert result is not None
    assert result["status"] == "acted"
    assert result["acted_at"] is not None


def test_update_status_wrong_person_returns_none(db, user, person, other_person):
    active = [_make_candidate("o01o01o01o01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["o01o01o01o01"]

    result = update_notification_status(
        db, nid, str(user.id), str(other_person.id), status="ignored"
    )
    assert result is None


def test_update_status_invalid_id_returns_none(db, user, person):
    bogus = str(uuid.uuid4())
    result = update_notification_status(db, bogus, str(user.id), str(person.id), status="ignored")
    assert result is None


def test_update_status_bad_uuid_string_returns_none(db, user, person):
    result = update_notification_status(db, "not-a-uuid", str(user.id), str(person.id), status="ignored")
    assert result is None


# ---------------------------------------------------------------------------
# get_notification_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_returns_correct_record(db, user, person):
    active = [_make_candidate("p01p01p01p01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["p01p01p01p01"]

    record = get_notification_by_id(db, nid, str(user.id), str(person.id))
    assert record is not None
    assert record.candidate_id == "p01p01p01p01"


def test_get_by_id_wrong_person_returns_none(db, user, person, other_person):
    active = [_make_candidate("q01q01q01q01")]
    id_map = persist_notification_candidates(db, str(user.id), str(person.id), active, [])
    nid = id_map["q01q01q01q01"]

    record = get_notification_by_id(db, nid, str(user.id), str(other_person.id))
    assert record is None
