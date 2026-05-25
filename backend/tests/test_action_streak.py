"""
Unit tests for streak_count logic in action_service.update_action.

These tests operate purely in-memory — no database connection needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.action_service import update_action


class FakeAction:
    """Minimal stand-in for HealthAction model."""

    def __init__(
        self,
        frequency: str = 'daily',
        streak_count: int = 0,
        last_completed_at: datetime | None = None,
        status: str = 'todo',
    ) -> None:
        self.id = 'fake-id'
        self.user_id = 'fake-user'
        self.frequency = frequency
        self.streak_count = streak_count
        self.last_completed_at = last_completed_at
        self.status = status
        self.completed_at = None
        self.snoozed_at = None
        self.updated_at = None


def _run(action: FakeAction, patch_data: dict, now: datetime) -> dict:
    """Call update_action with a mocked Session, freezing 'now' to *now*."""
    db = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    with patch('app.services.action_service.datetime') as mock_dt:
        # datetime.now(timezone.utc) → *now*
        mock_dt.now.return_value = now
        # Keep timedelta accessible on the module (service uses `timedelta` directly)
        update_action(db, action, patch_data)

    return patch_data


# ─── Helpers ─────────────────────────────────────────────────────────────────

NOW = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
YESTERDAY = NOW - timedelta(hours=24)
TWO_DAYS_AGO = NOW - timedelta(hours=48)


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestStreakFirstCompletion:
    """First ever completion should set streak to 1."""

    def test_first_completion_streak_is_one(self):
        action = FakeAction(frequency='daily', streak_count=0, last_completed_at=None)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert patch_data.get('streak_count') == 1

    def test_first_completion_sets_completed_at(self):
        action = FakeAction(frequency='daily', streak_count=0, last_completed_at=None)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert 'completed_at' in patch_data


class TestDailyStreak:
    """Daily actions: gap ≤ 36 h increments; gap > 36 h resets to 1."""

    def test_completed_within_36h_increments_streak(self):
        action = FakeAction(frequency='daily', streak_count=3, last_completed_at=YESTERDAY)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert patch_data.get('streak_count') == 4

    def test_completed_after_36h_resets_streak_to_one(self):
        action = FakeAction(frequency='daily', streak_count=5, last_completed_at=TWO_DAYS_AGO)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert patch_data.get('streak_count') == 1

    def test_streak_grows_correctly_over_multiple_days(self):
        """Simulate completing a daily action 4 days in a row."""
        streak = 0
        last = NOW - timedelta(hours=24 * 4)
        for i in range(4):
            now_i = last + timedelta(hours=24)
            action = FakeAction(frequency='daily', streak_count=streak, last_completed_at=last)
            patch_data: dict = {'status': 'done'}
            _run(action, patch_data, now_i)
            streak = patch_data['streak_count']
            last = now_i
        assert streak == 4


class TestWeeklyStreak:
    """Weekly actions: gap ≤ 192 h (8 days) increments; > 192 h resets."""

    def test_weekly_within_window_increments(self):
        last = NOW - timedelta(days=6)
        action = FakeAction(frequency='weekly', streak_count=2, last_completed_at=last)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert patch_data.get('streak_count') == 3

    def test_weekly_outside_window_resets(self):
        last = NOW - timedelta(days=10)
        action = FakeAction(frequency='weekly', streak_count=4, last_completed_at=last)
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        assert patch_data.get('streak_count') == 1


class TestIdempotentStatus:
    """Re-marking done (already done) should not double-increment streak."""

    def test_already_done_no_streak_increment(self):
        action = FakeAction(frequency='daily', streak_count=3, last_completed_at=YESTERDAY, status='done')
        patch_data: dict = {'status': 'done'}
        _run(action, patch_data, NOW)
        # service only increments on todo→done transition (new_status == 'done' and action.status != 'done')
        assert 'streak_count' not in patch_data


class TestNonCompletionPatch:
    """Patches that don't touch status must not modify streak_count."""

    def test_title_update_leaves_streak_unchanged(self):
        action = FakeAction(frequency='daily', streak_count=7, last_completed_at=YESTERDAY)
        patch_data: dict = {'title': 'Updated title'}
        _run(action, patch_data, NOW)
        assert 'streak_count' not in patch_data


class TestFeedbackStatusPatch:
    """
    P56: `not_useful` and `not_applicable` are feedback statuses that must be
    accepted by update_action without triggering streak computation or
    setting completed_at.  They pass through as generic attribute sets.
    """

    def test_not_useful_is_accepted_without_streak_change(self):
        action = FakeAction(frequency='daily', streak_count=3, last_completed_at=YESTERDAY)
        patch_data: dict = {'status': 'not_useful'}
        _run(action, patch_data, NOW)
        # Status is stored verbatim — streak must not be touched
        assert 'streak_count' not in patch_data

    def test_not_useful_does_not_set_completed_at(self):
        action = FakeAction(frequency='daily', streak_count=3, last_completed_at=YESTERDAY)
        patch_data: dict = {'status': 'not_useful'}
        _run(action, patch_data, NOW)
        assert 'completed_at' not in patch_data

    def test_not_applicable_is_accepted_without_streak_change(self):
        action = FakeAction(frequency='daily', streak_count=2, last_completed_at=YESTERDAY)
        patch_data: dict = {'status': 'not_applicable'}
        _run(action, patch_data, NOW)
        assert 'streak_count' not in patch_data

    def test_not_applicable_does_not_set_completed_at(self):
        action = FakeAction(frequency='daily', streak_count=2, last_completed_at=YESTERDAY)
        patch_data: dict = {'status': 'not_applicable'}
        _run(action, patch_data, NOW)
        assert 'completed_at' not in patch_data

    def test_not_useful_status_written_to_action_object(self):
        """update_action must setattr the status on the model object."""
        action = FakeAction(status='todo')
        _run(action, {'status': 'not_useful'}, NOW)
        assert action.status == 'not_useful'

    def test_not_applicable_status_written_to_action_object(self):
        action = FakeAction(status='in_progress')
        _run(action, {'status': 'not_applicable'}, NOW)
        assert action.status == 'not_applicable'


# ─── P57: get_prioritized_actions filter ─────────────────────────────────────

from unittest.mock import patch as _patch  # noqa: E402 — already imported above

from app.services.action_service import get_prioritized_actions  # noqa: E402


class FakePrioritizedAction:
    """Minimal stand-in for HealthAction used by get_prioritized_actions."""

    def __init__(
        self,
        status: str = 'todo',
        priority: str = 'medium',
        reminder_status: str = 'none',
        snoozed_until: datetime | None = None,
    ) -> None:
        self.status = status
        self.priority = priority
        self.reminder_status = reminder_status
        self.snoozed_until = snoozed_until


FUTURE = NOW + timedelta(days=3)
PAST = NOW - timedelta(days=1)


def _get_prioritized(actions_list: list) -> list:
    """Call get_prioritized_actions with a mocked list_actions and frozen now."""
    db = MagicMock()
    with (
        _patch('app.services.action_service.list_actions', return_value=actions_list),
        _patch('app.services.action_service.datetime') as mock_dt,
    ):
        mock_dt.now.return_value = NOW
        return get_prioritized_actions(db, 'fake-user', None)


class TestPrioritizedActionsFilter:
    """
    P57: get_prioritized_actions must exclude done / not_useful / not_applicable
    actions and future-snoozed actions, while keeping active and expired-snooze ones.
    """

    def test_done_action_excluded(self):
        actions = [FakePrioritizedAction(status='done'), FakePrioritizedAction(status='todo')]
        result = _get_prioritized(actions)
        assert all(a.status != 'done' for a in result)
        assert len(result) == 1

    def test_not_useful_action_excluded(self):
        actions = [FakePrioritizedAction(status='not_useful'), FakePrioritizedAction(status='todo')]
        result = _get_prioritized(actions)
        assert all(a.status != 'not_useful' for a in result)
        assert len(result) == 1

    def test_not_applicable_action_excluded(self):
        actions = [FakePrioritizedAction(status='not_applicable'), FakePrioritizedAction(status='in_progress')]
        result = _get_prioritized(actions)
        assert all(a.status != 'not_applicable' for a in result)
        assert len(result) == 1

    def test_future_snoozed_excluded(self):
        actions = [
            FakePrioritizedAction(status='snoozed', snoozed_until=FUTURE),
            FakePrioritizedAction(status='todo'),
        ]
        result = _get_prioritized(actions)
        assert len(result) == 1
        assert result[0].status == 'todo'

    def test_snoozed_with_past_expiry_included(self):
        """A snoozed action whose snoozed_until is in the past should still appear."""
        actions = [FakePrioritizedAction(status='snoozed', snoozed_until=PAST)]
        result = _get_prioritized(actions)
        assert len(result) == 1

    def test_snoozed_without_expiry_included(self):
        """A snoozed action with snoozed_until=None should still appear (no auto-hide)."""
        actions = [FakePrioritizedAction(status='snoozed', snoozed_until=None)]
        result = _get_prioritized(actions)
        assert len(result) == 1

    def test_active_actions_included(self):
        todo = FakePrioritizedAction(status='todo')
        in_progress = FakePrioritizedAction(status='in_progress')
        result = _get_prioritized([todo, in_progress])
        assert len(result) == 2

