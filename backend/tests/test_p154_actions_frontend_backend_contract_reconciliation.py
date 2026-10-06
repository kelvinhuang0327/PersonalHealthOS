"""P154 — Actions Frontend/Backend Contract Reconciliation

Verify that backend Action API endpoints returned payloads contain the precise
fields, statuses, and types expected and consumed by the frontend (as verified
in P150 Playwright E2E tests, action-context.tsx, and lib/api.ts).

Specifically:
- Check GET /api/v1/actions
- Check GET /api/v1/actions/prioritized
- Check POST /api/v1/actions
- Check PATCH /api/v1/actions/{id}
- Check GET /api/v1/actions/{id}/outcomes
- Check GET /api/v1/health-assistant/outcome-feedback

And ensure:
- All required frontend-consumed fields are present with correct types.
- No sensitive leakage.
- No prohibited medical overclaims or doctor replacement copying.
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
# Safety and Leakage Constants (aligned with P150/P151/P152/P153)
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


def _assert_iso_datetime_or_none(val: Any) -> None:
    if val is None:
        return
    assert isinstance(val, str)
    # Must be parseable datetime
    try:
        # FastAPI responses use 'Z' or offset. ISO parser handles it.
        datetime.fromisoformat(val.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"Value '{val}' is not a valid ISO-8601 datetime string")


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
        email='p154test@example.com',
        password_hash='hashed_password_xyz',
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name='P154 Tester Person',
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


# ---------------------------------------------------------------------------
# Helper Assertions
# ---------------------------------------------------------------------------

def _assert_health_action_shape(action: dict[str, Any]) -> None:
    """Assert the dictionary matches the fields/types consumed by action-context.tsx."""
    # Required keys and type expectations
    assert 'id' in action
    assert isinstance(action['id'], str)
    try:
        uuid.UUID(action['id'])
    except ValueError:
        pytest.fail(f"action['id'] '{action['id']}' is not a valid UUID string")

    assert 'person_id' in action
    assert isinstance(action['person_id'], str)
    try:
        uuid.UUID(action['person_id'])
    except ValueError:
        pytest.fail(f"action['person_id'] '{action['person_id']}' is not a valid UUID string")

    assert 'source_type' in action
    assert isinstance(action['source_type'], str)

    assert 'source_id' in action
    assert action['source_id'] is None or isinstance(action['source_id'], str)

    assert 'title' in action
    assert isinstance(action['title'], str)

    assert 'description' in action
    assert action['description'] is None or isinstance(action['description'], str)

    assert 'action_type' in action
    assert isinstance(action['action_type'], str)

    assert 'priority' in action
    assert isinstance(action['priority'], str)

    assert 'status' in action
    assert isinstance(action['status'], str)
    assert action['status'] in ('todo', 'in_progress', 'done', 'snoozed', 'not_useful', 'not_applicable')

    assert 'due_date' in action
    _assert_iso_datetime_or_none(action['due_date'])

    assert 'frequency' in action
    assert action['frequency'] is None or isinstance(action['frequency'], str)

    assert 'streak_count' in action
    assert isinstance(action['streak_count'], int)

    assert 'last_completed_at' in action
    _assert_iso_datetime_or_none(action['last_completed_at'])

    assert 'completed_at' in action
    _assert_iso_datetime_or_none(action['completed_at'])

    assert 'impact_status' in action
    assert action['impact_status'] is None or isinstance(action['impact_status'], str)

    assert 'reminder_status' in action
    assert action['reminder_status'] is None or isinstance(action['reminder_status'], str)

    assert 'snoozed_until' in action
    _assert_iso_datetime_or_none(action['snoozed_until'])

    assert 'snoozed_at' in action
    _assert_iso_datetime_or_none(action['snoozed_at'])

    assert 'snooze_reason' in action
    assert action['snooze_reason'] is None or isinstance(action['snooze_reason'], str)

    assert 'resurface_count' in action
    assert isinstance(action['resurface_count'], int)

    assert 'confidence' in action
    assert action['confidence'] is None or isinstance(action['confidence'], (int, float))

    assert 'evidence_level' in action
    assert action['evidence_level'] is None or isinstance(action['evidence_level'], str)

    assert 'guideline_source' in action
    assert action['guideline_source'] is None or isinstance(action['guideline_source'], str)

    assert 'rule_id' in action
    assert action['rule_id'] is None or isinstance(action['rule_id'], str)

    assert 'category' in action
    assert action['category'] is None or isinstance(action['category'], str)

    assert 'created_at' in action
    _assert_iso_datetime_or_none(action['created_at'])

    assert 'updated_at' in action
    _assert_iso_datetime_or_none(action['updated_at'])

    assert 'outcomes' in action
    assert isinstance(action['outcomes'], list)


def _assert_outcome_shape(outcome: dict[str, Any]) -> None:
    """Assert shape matches the Outcomes consumed by action-feedback-card / action-outcome-card."""
    assert 'metric_type' in outcome
    assert isinstance(outcome['metric_type'], str)

    assert 'before_value' in outcome
    assert outcome['before_value'] is None or isinstance(outcome['before_value'], (int, float))

    assert 'after_value' in outcome
    assert outcome['after_value'] is None or isinstance(outcome['after_value'], (int, float))

    assert 'delta' in outcome
    assert outcome['delta'] is None or isinstance(outcome['delta'], (int, float))

    assert 'delta_pct' in outcome
    assert outcome['delta_pct'] is None or isinstance(outcome['delta_pct'], (int, float))

    assert 'time_window_days' in outcome
    assert isinstance(outcome['time_window_days'], int)

    assert 'outcome_label' in outcome
    assert isinstance(outcome['outcome_label'], str)
    assert outcome['outcome_label'] in ('improved', 'no_change', 'worse')

    assert 'computed_at' in outcome
    _assert_iso_datetime_or_none(outcome['computed_at'])


# ===========================================================================
# Contract Tests
# ===========================================================================

class TestActionsContractReconciliation:
    """Validates that actions API shapes reconcile with frontend expectations."""

    def test_list_actions_shape(self):
        """Seed diverse actions → GET /api/v1/actions → check shapes & values."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        # Seed multiple actions representing various stages
        a1 = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Action One',
            status='todo', priority='high', action_type='lifestyle',
            due_date=now + timedelta(days=2), category='bp',
        )
        a2 = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='manual', title='P154 Action Two',
            status='done', priority='medium', action_type='lifestyle',
            completed_at=now - timedelta(days=1), streak_count=3,
        )
        db.add_all([a1, a2])
        db.commit()

        resp = client.get('/api/v1/actions', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        actions = resp.json()
        assert len(actions) == 2

        for a in actions:
            _assert_health_action_shape(a)
            _find_sensitive_key(a) is None
            _assert_no_medical_overclaim(a)

    def test_prioritized_actions_shape(self):
        """Seed actions → GET /api/v1/actions/prioritized → check active filtering & shape."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        active = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Active',
            status='todo', priority='high', action_type='lifestyle',
        )
        done = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Done',
            status='done', priority='medium', action_type='lifestyle',
        )
        snoozed_future = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Snoozed Future',
            status='snoozed', priority='medium', action_type='lifestyle',
            snoozed_until=now + timedelta(days=3),
        )
        db.add_all([active, done, snoozed_future])
        db.commit()

        resp = client.get('/api/v1/actions/prioritized', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        actions = resp.json()
        # Only 'active' should remain (done and future snoozed are filtered out)
        assert len(actions) == 1
        a = actions[0]
        assert a['title'] == 'P154 Active'
        _assert_health_action_shape(a)
        _assert_no_medical_overclaim(a)

    def test_create_and_patch_action_shapes(self):
        """POST to create, PATCH to update/feedback/snooze → check status & shape transitions."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        # 1. Create via POST
        post_payload = {
            'title': 'P154 New Action',
            'source_type': 'recommendation',
            'source_id': 'rule-glucose-p154',
            'status': 'todo',
            'priority': 'medium',
            'action_type': 'lifestyle',
        }
        resp_post = client.post('/api/v1/actions', json=post_payload, params={'person_id': str(person.id)})
        assert resp_post.status_code == 201
        created = resp_post.json()
        _assert_health_action_shape(created)
        action_id = created['id']

        # 2. PATCH status to 'not_useful' (Feedback contract)
        resp_patch1 = client.patch(f'/api/v1/actions/{action_id}', json={'status': 'not_useful'})
        assert resp_patch1.status_code == 200
        patched1 = resp_patch1.json()
        assert patched1['status'] == 'not_useful'
        _assert_health_action_shape(patched1)

        # 3. PATCH status to 'snoozed' (Snooze contract)
        snoozed_until = (now + timedelta(days=3)).isoformat()
        resp_patch2 = client.patch(
            f'/api/v1/actions/{action_id}',
            json={'status': 'snoozed', 'snoozed_until': snoozed_until, 'snooze_reason': 'Busy this week'}
        )
        assert resp_patch2.status_code == 200
        patched2 = resp_patch2.json()
        assert patched2['status'] == 'snoozed'
        assert patched2['snoozed_until'] is not None
        assert patched2['snooze_reason'] == 'Busy this week'
        _assert_health_action_shape(patched2)
        _assert_no_medical_overclaim(patched2)

    def test_action_outcomes_shape(self):
        """Seed ActionOutcome → GET /actions/{id}/outcomes → check outcomes shape."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        action = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Done Action',
            status='done', priority='medium', action_type='lifestyle',
            completed_at=now - timedelta(days=2),
        )
        db.add(action)
        db.flush()

        outcome = ActionOutcome(
            id=uuid.uuid4(), action_id=action.id, user_id=user.id, person_id=person.id,
            metric_type='steps', before_value=5000.0, after_value=8000.0,
            delta=3000.0, delta_pct=60.0, time_window_days=7,
            outcome_label='improved', computed_at=now,
        )
        db.add(outcome)
        db.commit()

        resp = client.get(f'/api/v1/actions/{action.id}/outcomes')
        assert resp.status_code == 200
        outcomes = resp.json()
        assert len(outcomes) == 1
        o = outcomes[0]
        _assert_outcome_shape(o)
        _assert_no_medical_overclaim(o)

    def test_outcome_feedback_shape(self):
        """Seed multiple actions and outcome rows → GET /health-assistant/outcome-feedback → check shape."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        a_done = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Done',
            status='done', category='bp', completed_at=now - timedelta(days=3),
        )
        a_todo = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Todo',
            status='todo', category='glucose',
        )
        a_snoozed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Snoozed',
            status='snoozed', category='weight', snoozed_until=now + timedelta(days=2),
        )
        a_dismissed = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Dismissed',
            status='not_useful', category='sleep',
        )
        db.add_all([a_done, a_todo, a_snoozed, a_dismissed])
        db.flush()

        outcome = ActionOutcome(
            id=uuid.uuid4(), action_id=a_done.id, user_id=user.id, person_id=person.id,
            metric_type='systolic_bp', before_value=145.0, after_value=135.0,
            delta=-10.0, delta_pct=-6.9, time_window_days=7,
            outcome_label='improved', computed_at=now,
        )
        db.add(outcome)
        db.commit()

        resp = client.get('/api/v1/health-assistant/outcome-feedback', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        data = resp.json()

        # Check top-level OutcomeFeedback shape
        assert 'person_id' in data
        assert data['person_id'] == str(person.id)
        assert 'generated_at' in data
        _assert_iso_datetime_or_none(data['generated_at'])
        assert 'window_days' in data
        assert isinstance(data['window_days'], int)

        assert 'outcomes' in data
        assert isinstance(data['outcomes'], list)
        assert len(data['outcomes']) == 4

        # Validate summary
        assert 'summary' in data
        summary = data['summary']
        assert isinstance(summary, dict)
        for key in ('improved_count', 'unchanged_count', 'deteriorated_count',
                    'insufficient_data_count', 'tracking_count', 'not_useful_count',
                    'not_applicable_count', 'snoozed_count', 'total_count'):
            assert key in summary
            assert isinstance(summary[key], int)

        # Validate each OutcomeFeedbackItem shape
        for item in data['outcomes']:
            assert 'action_id' in item
            assert isinstance(item['action_id'], str)
            uuid.UUID(item['action_id'])

            assert 'action_title' in item
            assert isinstance(item['action_title'], str)

            assert 'status' in item
            assert isinstance(item['status'], str)
            assert item['status'] in ('completed', 'tracking', 'not_useful', 'not_applicable', 'snoozed')

            assert 'completed_at' in item
            _assert_iso_datetime_or_none(item['completed_at'])

            assert 'expected_health_impact' in item
            assert isinstance(item['expected_health_impact'], str)

            assert 'outcome_status' in item
            assert isinstance(item['outcome_status'], str)

            assert 'actual_metric_change' in item
            amc = item['actual_metric_change']
            if amc is not None:
                assert isinstance(amc, dict)
                assert 'metric_type' in amc
                assert isinstance(amc['metric_type'], str)
                assert 'before_value' in amc
                assert amc['before_value'] is None or isinstance(amc['before_value'], (int, float))
                assert 'after_value' in amc
                assert amc['after_value'] is None or isinstance(amc['after_value'], (int, float))
                assert 'delta' in amc
                assert amc['delta'] is None or isinstance(amc['delta'], (int, float))
                assert 'direction' in amc
                assert amc['direction'] is None or isinstance(amc['direction'], str)

            assert 'adherence_status' in item
            assert isinstance(item['adherence_status'], str)

            assert 'evidence_sources' in item
            assert isinstance(item['evidence_sources'], list)
            for es in item['evidence_sources']:
                assert isinstance(es, str)

            assert 'confidence' in item
            assert isinstance(item['confidence'], (int, float))

            assert 'explanation' in item
            assert isinstance(item['explanation'], str)

            assert 'next_check_in' in item
            if item['next_check_in'] is not None:
                assert isinstance(item['next_check_in'], str)
                # Should be parseable as ISO date or ISO datetime
                try:
                    datetime.fromisoformat(item['next_check_in'].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        from datetime import date
                        date.fromisoformat(item['next_check_in'])
                    except ValueError:
                        pytest.fail(f"next_check_in '{item['next_check_in']}' is neither a valid ISO date nor a valid ISO datetime")

            _assert_no_medical_overclaim(item)

    def test_no_sensitive_leakage(self):
        """Scan endpoint payloads recursively for any sensitive credentials or primary database user keys."""
        db, user, person, client = _setup_isolated_env()
        now = datetime.now(timezone.utc)

        a = HealthAction(
            id=uuid.uuid4(), user_id=user.id, person_id=person.id,
            source_type='recommendation', title='P154 Leakage Test',
            status='todo', priority='high', action_type='lifestyle',
        )
        db.add(a)
        db.commit()

        # Check list endpoint
        resp = client.get('/api/v1/actions', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json())
        assert found is None, f"Sensitive leakage found in actions list at: {found}"

        # Check prioritized
        resp = client.get('/api/v1/actions/prioritized', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json())
        assert found is None, f"Sensitive leakage found in prioritized at: {found}"

        # Check outcome-feedback
        resp = client.get('/api/v1/health-assistant/outcome-feedback', params={'person_id': str(person.id)})
        assert resp.status_code == 200
        found = _find_sensitive_key(resp.json())
        assert found is None, f"Sensitive leakage found in outcome-feedback at: {found}"
