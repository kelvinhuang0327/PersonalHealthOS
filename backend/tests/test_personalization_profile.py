"""Tests for PersonalizationProfile model + personalization_service (P6).

Uses in-memory SQLite — no Docker required.
Covers:
  - model creation / default fallback
  - get_or_create_profile (idempotent)
  - sync_profile_from_history (engagement scoring, category aggregation)
  - profile_to_dict serialization
  - no-history fallback
  - profile update persists correctly
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.entities import Base, PersonalizationProfile, PersonProfile, User
from app.services.personalization_service import (
    _DEFAULT_PROFILE,
    get_or_create_profile,
    profile_to_dict,
    sync_profile_from_history,
)

# ---------------------------------------------------------------------------
# Shared engine + fixtures
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
    u = User(email=f"pers_{uuid.uuid4().hex[:6]}@test.com", password_hash="hashed")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def person(db, user):
    p = PersonProfile(
        owner_user_id=user.id,
        display_name="Pers Tester",
        relationship="self",
        is_default=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _hist(cooldown_key: str, status: str = "generated",
          ignore_count: int = 0, snooze_count: int = 0,
          source_type: str | None = None) -> dict:
    return {
        "cooldown_key": cooldown_key,
        "source_type": source_type,
        "status": status,
        "priority": "medium",
        "snooze_count": snooze_count,
        "ignore_count": ignore_count,
        "sent_at": None,
        "snoozed_until": None,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetOrCreateProfile:
    def test_creates_default_profile(self, db, user, person):
        profile = get_or_create_profile(db, str(user.id), str(person.id))
        assert profile is not None
        assert profile.user_id == user.id
        assert profile.subject_profile_id == person.id
        # Default engagement = 0.5
        assert float(profile.engagement_score) == pytest.approx(0.5)
        assert profile.response_style == "balanced"

    def test_idempotent_second_call(self, db, user, person):
        p1 = get_or_create_profile(db, str(user.id), str(person.id))
        p2 = get_or_create_profile(db, str(user.id), str(person.id))
        assert p1.id == p2.id

    def test_profile_stored_in_db(self, db, user, person):
        get_or_create_profile(db, str(user.id), str(person.id))
        count = (
            db.query(PersonalizationProfile)
            .filter_by(user_id=user.id, subject_profile_id=person.id)
            .count()
        )
        assert count == 1


class TestSyncProfileFromHistory:
    def test_empty_history_resets_to_defaults(self, db, user, person):
        profile = sync_profile_from_history(db, str(user.id), str(person.id), [])
        assert profile.acted_categories == {}
        assert profile.ignored_categories == {}
        assert profile.high_response_categories == []
        # Engagement should be 0.5 (neutral) when no data
        assert float(profile.engagement_score) == pytest.approx(0.5)

    def test_acted_category_tracked(self, db, user, person):
        history = [
            _hist("lab_abnormality_ldl", status="acted", source_type="lab_abnormality"),
            _hist("lab_abnormality_glucose", status="acted", source_type="lab_abnormality"),
            _hist("device_escalation_warning", status="acted", source_type="device_escalation"),
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert profile.acted_categories.get("lab_abnormality") == 2
        assert profile.acted_categories.get("device_escalation") == 1

    def test_ignored_category_tracked(self, db, user, person):
        history = [
            _hist("symptom_pattern_headache", ignore_count=3, source_type="symptom_pattern"),
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert profile.ignored_categories.get("symptom_pattern") == 3

    def test_high_response_categories_computed(self, db, user, person):
        """Categories with act_count >= 2 appear in high_response_categories."""
        history = [
            _hist("lab_a", status="acted", source_type="lab_abnormality"),
            _hist("lab_b", status="acted", source_type="lab_abnormality"),
            _hist("device_a", status="acted", source_type="device_escalation"),
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert "lab_abnormality" in profile.high_response_categories
        assert "device_escalation" not in profile.high_response_categories  # only 1 act

    def test_engagement_score_rises_with_acted(self, db, user, person):
        history = [
            _hist(f"lab_{i}", status="acted", source_type="lab_abnormality")
            for i in range(5)
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert float(profile.engagement_score) > 0.5

    def test_engagement_score_falls_with_ignored(self, db, user, person):
        history = [
            _hist(f"lab_{i}", ignore_count=2, source_type="lab_abnormality")
            for i in range(5)
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert float(profile.engagement_score) < 0.5

    def test_response_style_proactive(self, db, user, person):
        # Many acted signals → proactive style
        history = [
            _hist(f"lab_{i}", status="acted", source_type="lab_abnormality")
            for i in range(10)
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert profile.response_style == "proactive"

    def test_response_style_minimal(self, db, user, person):
        # Many ignored signals → minimal style
        history = [
            _hist(f"lab_{i}", ignore_count=3, source_type="lab_abnormality")
            for i in range(10)
        ]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        assert profile.response_style == "minimal"

    def test_profile_update_persists_correctly(self, db, user, person):
        # Create initial
        sync_profile_from_history(db, str(user.id), str(person.id), [])
        # Update with acted history
        history = [_hist("lab_a", status="acted", source_type="lab_abnormality")]
        profile = sync_profile_from_history(db, str(user.id), str(person.id), history)
        # Reload from DB
        reloaded = (
            db.query(PersonalizationProfile)
            .filter_by(user_id=user.id, subject_profile_id=person.id)
            .first()
        )
        assert reloaded is not None
        assert reloaded.acted_categories.get("lab_abnormality") == 1


class TestProfileToDict:
    def test_returns_dict(self, db, user, person):
        profile = get_or_create_profile(db, str(user.id), str(person.id))
        d = profile_to_dict(profile)
        assert isinstance(d, dict)
        assert "engagement_score" in d
        assert "response_style" in d
        assert "acted_categories" in d
        assert "ignored_categories" in d
        assert "high_response_categories" in d

    def test_none_returns_default_fallback(self):
        d = profile_to_dict(None)
        assert d == _DEFAULT_PROFILE

    def test_engagement_score_is_float(self, db, user, person):
        profile = get_or_create_profile(db, str(user.id), str(person.id))
        d = profile_to_dict(profile)
        assert isinstance(d["engagement_score"], float)
