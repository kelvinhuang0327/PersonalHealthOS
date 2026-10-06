"""P153 — Actions DateTime / UUID Readback Regression

Focused regression tests for two P152-discovered backend source defects:

1. `_is_active()` in action_service.py crashed under SQLite when comparing a
   naive `snoozed_until` datetime against an aware `datetime.now(timezone.utc)`.
   Fix: normalize naive datetimes to UTC-aware before comparison.

2. `get_outcomes_for_action()` compared a string `action_id` against a UUID
   column (`ActionOutcome.action_id`) and failed under isolated SQLite.
   Fix: convert string action_id to UUID before querying.

Coverage map
------------
TestPrioritizedSnoozedDatetime
  test_prioritized_does_not_500_with_snoozed_action
    Seed snoozed action with future snoozed_until → GET /actions/prioritized → 200
  test_future_snoozed_excluded_from_prioritized
    Seed snoozed action with future snoozed_until → not in prioritized list
  test_expired_snoozed_included_in_prioritized
    Seed snoozed action with past snoozed_until → appears in prioritized list
  test_mixed_snoozed_and_active_prioritized
    Seed active + future-snoozed + expired-snoozed → only active + expired in prioritized

TestPerActionOutcomesUUID
  test_outcomes_endpoint_returns_seeded_data
    Seed action + outcomes → GET /actions/{id}/outcomes → 200 with correct data
  test_outcomes_endpoint_nonexistent_action_returns_404
    GET /actions/{random-uuid}/outcomes → 404
  test_outcomes_endpoint_invalid_uuid_returns_422_or_404
    GET /actions/not-a-uuid/outcomes → safe error (not 500)

TestSafetyCopyAndLeakage
  test_prioritized_no_sensitive_keys
    GET /actions/prioritized with snoozed actions → no user_id / sensitive keys
  test_outcomes_no_sensitive_keys
    GET /actions/{id}/outcomes → no sensitive keys
  test_no_prohibited_medical_phrases
    All responses free of diagnosis/cure/guarantee copy

Strategy:
  - All tests use isolated in-memory SQLite + TestClient + dependency overrides
  - No production DB access
  - No dependency changes
"""
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
from app.models.entities import ActionOutcome, HealthAction, PersonProfile, User


# ---------------------------------------------------------------------------
# Safety constants (aligned with P150/P151/P152)
# ---------------------------------------------------------------------------

PROHIBITED_PHRASES = [
    '診斷', '確診', '治療', '治癒', '一定', '絕對', '保證', '100%',
    '取代醫師', '正常代表沒問題', 'diagnose', 'guarantee', 'cure',
]

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    'password_hash', 'hashed_password', 'password',
    'storage_bucket', 'storage_key', 'file_path',
    'download_token', 'secret_key', 'secret',
    'is_superuser', 'is_staff', 'user_id',
})


def _assert_no_medical_overclaim(data: Any) -> None:
    text = str(data)
    for phrase in PROHIBITED_PHRASES:
        assert phrase not in text, f"Response contains prohibited phrase: {phrase}"


def _find_sensitive_key(obj: Any, path: str = '') -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _SENSITIVE_KEYS:
                return f'{path}.{k}' if path else k
            found = _find_sensitive_key(v, f'{path}.{k}' if path else k)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found = _find_sensitive_key(item, f'{path}[{i}]')
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _setup_isolated_env() -> tuple[Session, User, PersonProfile, TestClient]:
    """Create an isolated in-memory SQLite DB with user, person, and TestClient."""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    user = User(
        id=uuid.uuid4(),
        email='p153test@example.com',
        password_hash='hashed_password',
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name='P153 Tester',
        relationship='self',
        is_default=True,
    )
    db.add(person)
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person

    client = TestClient(app, raise_server_exceptions=False)
    return db, user, person, client


# ===========================================================================
# TestPrioritizedSnoozedDatetime
# ===========================================================================


class TestPrioritizedSnoozedDatetime:
    """Regression: GET /actions/prioritized must not 500 with snoozed actions."""

    def test_prioritized_does_not_500_with_snoozed_action(self):
        """Seed snoozed action with future snoozed_until → GET /actions/prioritized → 200."""
        db, user, person, client = _setup_isolated_env()

        action = HealthAction(
            id=uuid.uuid4(),
            user_id=user.id,
            person_id=person.id,
            source_type='recommendation',
            title='P153 延後建議',
            status='snoozed',
            priority='medium',
            action_type='lifestyle',
            snoozed_until=datetime.now(timezone.utc) + timedelta(days=3),
            snoozed_at=datetime.now(timezone.utc),
        )
        db.add(action)
        db.commit()

        resp = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp.status_code == 200, (
            f'Expected 200, got {resp.status_code}: {resp.text}'
        )

    def test_future_snoozed_excluded_from_prioritized(self):
        """Snoozed action with future snoozed_until must not appear in prioritized."""
        db, user, person, client = _setup_isolated_env()

        snoozed_action = HealthAction(
            id=uuid.uuid4(),
            user_id=user.id,
            person_id=person.id,
            source_type='recommendation',
            title='P153 未來延後',
            status='snoozed',
            priority='medium',
            action_type='lifestyle',
            snoozed_until=datetime.now(timezone.utc) + timedelta(days=7),
            snoozed_at=datetime.now(timezone.utc),
        )
        db.add(snoozed_action)
        db.commit()

        resp = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp.status_code == 200
        prio_ids = [a['id'] for a in resp.json()]
        assert str(snoozed_action.id) not in prio_ids, (
            'Future-snoozed action must be excluded from prioritized list'
        )

    def test_expired_snoozed_included_in_prioritized(self):
        """Snoozed action with past snoozed_until must reappear in prioritized."""
        db, user, person, client = _setup_isolated_env()

        expired_action = HealthAction(
            id=uuid.uuid4(),
            user_id=user.id,
            person_id=person.id,
            source_type='recommendation',
            title='P153 過期延後',
            status='snoozed',
            priority='medium',
            action_type='lifestyle',
            snoozed_until=datetime.now(timezone.utc) - timedelta(hours=1),
            snoozed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(expired_action)
        db.commit()

        resp = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp.status_code == 200
        prio_ids = [a['id'] for a in resp.json()]
        assert str(expired_action.id) in prio_ids, (
            'Expired-snooze action must reappear in prioritized list'
        )

    def test_mixed_snoozed_and_active_prioritized(self):
        """Active + future-snoozed + expired-snoozed → only active + expired in prioritized."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        active = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='Active',
            status='todo', priority='high', action_type='lifestyle',
        )
        future_snoozed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='Future Snoozed',
            status='snoozed', priority='medium', action_type='lifestyle',
            snoozed_until=now + timedelta(days=5),
            snoozed_at=now,
        )
        expired_snoozed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='Expired Snoozed',
            status='snoozed', priority='low', action_type='lifestyle',
            snoozed_until=now - timedelta(hours=2),
            snoozed_at=now - timedelta(days=2),
        )
        db.add_all([active, future_snoozed, expired_snoozed])
        db.commit()

        resp = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp.status_code == 200
        prio_ids = set(a['id'] for a in resp.json())
        assert str(active.id) in prio_ids, 'Active action must be in prioritized'
        assert str(expired_snoozed.id) in prio_ids, 'Expired-snoozed must be in prioritized'
        assert str(future_snoozed.id) not in prio_ids, 'Future-snoozed must NOT be in prioritized'


# ===========================================================================
# TestPerActionOutcomesUUID
# ===========================================================================


class TestPerActionOutcomesUUID:
    """Regression: GET /actions/{id}/outcomes must handle string UUIDs correctly."""

    def test_outcomes_endpoint_returns_seeded_data(self):
        """Seed action + outcomes → GET /actions/{id}/outcomes → 200 with data."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        action = HealthAction(
            id=uuid.uuid4(),
            user_id=user.id,
            person_id=person.id,
            source_type='recommendation',
            title='P153 結果讀取',
            status='done',
            completed_at=now - timedelta(days=3),
        )
        db.add(action)
        db.flush()

        outcome = ActionOutcome(
            id=uuid.uuid4(),
            action_id=action.id,
            user_id=user.id,
            person_id=person.id,
            metric_type='systolic_bp',
            before_value=140.0,
            after_value=130.0,
            delta=-10.0,
            delta_pct=-7.14,
            time_window_days=7,
            outcome_label='improved',
            computed_at=now,
        )
        db.add(outcome)
        db.commit()

        # Use string UUID in URL (as the router receives it)
        resp = client.get(f'/api/v1/actions/{action.id}/outcomes')
        assert resp.status_code == 200, (
            f'Expected 200, got {resp.status_code}: {resp.text}'
        )
        outcomes_data = resp.json()
        assert isinstance(outcomes_data, list)
        assert len(outcomes_data) == 1
        first = outcomes_data[0]
        assert first['metric_type'] == 'systolic_bp'
        assert first['before_value'] == 140.0
        assert first['after_value'] == 130.0
        assert first['delta'] == -10.0
        assert first['outcome_label'] == 'improved'

    def test_outcomes_endpoint_nonexistent_action_returns_404(self):
        """GET /actions/{random-uuid}/outcomes → 404."""
        db, user, person, client = _setup_isolated_env()
        random_id = str(uuid.uuid4())
        resp = client.get(f'/api/v1/actions/{random_id}/outcomes')
        assert resp.status_code == 404

    def test_outcomes_endpoint_invalid_uuid_returns_safe_error(self):
        """GET /actions/not-a-uuid/outcomes → 422 or 404, not 500."""
        db, user, person, client = _setup_isolated_env()
        resp = client.get('/api/v1/actions/not-a-valid-uuid/outcomes')
        assert resp.status_code in (404, 422), (
            f'Expected 404 or 422 for invalid UUID, got {resp.status_code}'
        )


# ===========================================================================
# TestSafetyCopyAndLeakage
# ===========================================================================


class TestSafetyCopyAndLeakage:
    """Verify no sensitive leakage and no prohibited medical phrases."""

    def test_prioritized_no_sensitive_keys(self):
        """GET /actions/prioritized with snoozed actions → no sensitive keys."""
        db, user, person, client = _setup_isolated_env()

        action = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 安全測試',
            status='todo', priority='high', action_type='lifestyle',
        )
        snoozed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 延後安全測試',
            status='snoozed', priority='medium', action_type='lifestyle',
            snoozed_until=datetime.now(timezone.utc) - timedelta(hours=1),
            snoozed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add_all([action, snoozed])
        db.commit()

        resp = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp.status_code == 200
        for item in resp.json():
            found = _find_sensitive_key(item)
            assert found is None, (
                f"Sensitive key '{found}' in GET /actions/prioritized response"
            )

    def test_outcomes_no_sensitive_keys(self):
        """GET /actions/{id}/outcomes → no sensitive keys in response."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        action = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 結果安全',
            status='done', completed_at=now - timedelta(days=3),
        )
        db.add(action)
        db.flush()

        outcome = ActionOutcome(
            id=uuid.uuid4(), action_id=action.id,
            user_id=user.id, person_id=person.id,
            metric_type='steps', before_value=3000.0,
            after_value=6000.0, delta=3000.0, delta_pct=100.0,
            time_window_days=7, outcome_label='improved', computed_at=now,
        )
        db.add(outcome)
        db.commit()

        resp = client.get(f'/api/v1/actions/{action.id}/outcomes')
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json())
        assert found is None, (
            f"Sensitive key '{found}' in GET /actions/{{id}}/outcomes response"
        )

    def test_no_prohibited_medical_phrases(self):
        """All responses must be free of diagnosis/cure/guarantee copy."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        action = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 醫療用語測試',
            status='todo', priority='medium', action_type='lifestyle',
        )
        snoozed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 延後醫療測試',
            status='snoozed', priority='medium', action_type='lifestyle',
            snoozed_until=now + timedelta(days=3), snoozed_at=now,
        )
        done = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P153 完成測試',
            status='done', completed_at=now - timedelta(days=2),
        )
        db.add_all([action, snoozed, done])
        db.flush()

        outcome = ActionOutcome(
            id=uuid.uuid4(), action_id=done.id,
            user_id=user.id, person_id=person.id,
            metric_type='weight_kg', before_value=80.0,
            after_value=78.0, delta=-2.0, delta_pct=-2.5,
            time_window_days=7, outcome_label='improved', computed_at=now,
        )
        db.add(outcome)
        db.commit()

        # Check prioritized
        resp_prio = client.get(
            '/api/v1/actions/prioritized',
            params={'person_id': str(person.id)},
        )
        assert resp_prio.status_code == 200
        _assert_no_medical_overclaim(resp_prio.json())

        # Check per-action outcomes
        resp_out = client.get(f'/api/v1/actions/{done.id}/outcomes')
        assert resp_out.status_code == 200
        _assert_no_medical_overclaim(resp_out.json())
