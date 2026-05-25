from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.entities import ActionOutcome, HealthAction, HealthMetric


# ---------------------------------------------------------------------------
# Category → metric column mapping
# ---------------------------------------------------------------------------
CATEGORY_METRIC_MAP: dict[str, list[str]] = {
    'bp': ['systolic_bp', 'diastolic_bp'],
    'weight': ['weight_kg'],
    'uric_acid': [],          # lab metric – handled separately
    'sleep': ['sleep_hours'],
    'activity': ['steps'],
    'blood_glucose': ['blood_glucose'],
    'heart_rate': ['heart_rate'],
}

# Whether a decrease is "improvement" (True) or increase is "improvement" (False)
LOWER_IS_BETTER: dict[str, bool] = {
    'systolic_bp': True,
    'diastolic_bp': True,
    'weight_kg': True,
    'blood_glucose': True,
    'heart_rate': False,  # context-dependent; neutral default
    'sleep_hours': False,
    'steps': False,
}


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def list_actions(db: Session, user_id: str, person_id: str | None = None) -> list[HealthAction]:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    q = db.query(HealthAction).filter(HealthAction.user_id == uid)
    if person_id:
        pid = UUID(person_id) if isinstance(person_id, str) else person_id
        q = q.filter(HealthAction.person_id == pid)
    return q.order_by(desc(HealthAction.created_at)).all()


def get_action(db: Session, user_id: str, action_id: str) -> HealthAction | None:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    aid = UUID(action_id) if isinstance(action_id, str) else action_id
    return (
        db.query(HealthAction)
        .filter(HealthAction.id == aid, HealthAction.user_id == uid)
        .first()
    )


def create_action(db: Session, user_id: str, data: dict[str, Any]) -> HealthAction:
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    action = HealthAction(user_id=uid, **data)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def update_action(db: Session, action: HealthAction, patch: dict[str, Any]) -> HealthAction:
    now = datetime.now(timezone.utc)

    # Handle status transitions
    new_status = patch.get('status')
    if new_status == 'done' and action.status != 'done':
        patch.setdefault('completed_at', now)
        patch.setdefault('last_completed_at', now)
        # Increment streak if completed within expected window
        if action.last_completed_at:
            gap_hours = (now - action.last_completed_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if action.frequency == 'daily' and gap_hours <= 36:
                patch['streak_count'] = (action.streak_count or 0) + 1
            elif action.frequency == 'weekly' and gap_hours <= 192:
                patch['streak_count'] = (action.streak_count or 0) + 1
            else:
                patch['streak_count'] = 1
        else:
            patch['streak_count'] = 1

    elif new_status == 'snoozed':
        patch.setdefault('snoozed_at', now)

    for key, value in patch.items():
        if hasattr(action, key):
            setattr(action, key, value)

    action.updated_at = now
    db.commit()
    db.refresh(action)
    return action


def delete_action(db: Session, action: HealthAction) -> None:
    db.delete(action)
    db.commit()


# ---------------------------------------------------------------------------
# Outcome computation
# ---------------------------------------------------------------------------

def compute_outcomes(db: Session, action: HealthAction, time_window_days: int = 7) -> list[ActionOutcome]:
    """
    After an action is marked done, compare metric values before vs after
    the completion date to compute quantitative outcomes.
    """
    if not action.completed_at:
        return []

    completed_at = action.completed_at
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    before_start = completed_at - timedelta(days=time_window_days)
    after_end = completed_at + timedelta(days=time_window_days)
    now = datetime.now(timezone.utc)
    if after_end > now:
        return []  # not enough time has passed

    category = (action.category or '').lower()
    metric_cols = CATEGORY_METRIC_MAP.get(category, [])

    # Fallback: try all numeric metrics
    if not metric_cols:
        metric_cols = ['systolic_bp', 'diastolic_bp', 'weight_kg', 'sleep_hours', 'steps', 'blood_glucose']

    results: list[ActionOutcome] = []
    for col in metric_cols:
        col_attr = getattr(HealthMetric, col, None)
        if col_attr is None:
            continue

        before_avg = (
            db.query(func.avg(col_attr))
            .filter(
                HealthMetric.user_id == action.user_id,
                HealthMetric.recorded_at >= before_start,
                HealthMetric.recorded_at < completed_at,
                col_attr.isnot(None),
            )
            .scalar()
        )
        after_avg = (
            db.query(func.avg(col_attr))
            .filter(
                HealthMetric.user_id == action.user_id,
                HealthMetric.recorded_at > completed_at,
                HealthMetric.recorded_at <= after_end,
                col_attr.isnot(None),
            )
            .scalar()
        )

        if before_avg is None or after_avg is None:
            continue

        before_val = float(before_avg)
        after_val = float(after_avg)
        delta = after_val - before_val
        delta_pct = (delta / before_val * 100) if before_val != 0 else 0.0

        lower_better = LOWER_IS_BETTER.get(col, True)
        threshold = 0.02  # 2% change considered meaningful

        if abs(delta_pct) < threshold * 100:
            label = 'no_change'
        elif lower_better:
            label = 'improved' if delta < 0 else 'worse'
        else:
            label = 'improved' if delta > 0 else 'worse'

        # Upsert: remove old outcome for same action + metric + window
        db.query(ActionOutcome).filter(
            ActionOutcome.action_id == action.id,
            ActionOutcome.metric_type == col,
            ActionOutcome.time_window_days == time_window_days,
        ).delete()

        outcome = ActionOutcome(
            action_id=action.id,
            user_id=action.user_id,
            person_id=action.person_id,
            metric_type=col,
            before_value=round(before_val, 3),
            after_value=round(after_val, 3),
            delta=round(delta, 3),
            delta_pct=round(delta_pct, 2),
            time_window_days=time_window_days,
            outcome_label=label,
            computed_at=now,
        )
        db.add(outcome)
        results.append(outcome)

    if results:
        db.commit()
        # Update action impact_status based on outcomes
        labels = [o.outcome_label for o in results]
        if 'improved' in labels and 'worse' not in labels:
            action.impact_status = 'improved'
        elif 'worse' in labels and 'improved' not in labels:
            action.impact_status = 'worse'
        else:
            action.impact_status = 'no_change'
        db.commit()

    return results


def get_outcomes_for_action(db: Session, action_id: str) -> list[ActionOutcome]:
    return db.query(ActionOutcome).filter(ActionOutcome.action_id == action_id).all()


# ---------------------------------------------------------------------------
# Decision Engine integration: build prioritized actions list
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}
_STATUS_ORDER = {'in_progress': 0, 'todo': 1, 'snoozed': 2, 'done': 3}


_INACTIVE_STATUSES: frozenset[str] = frozenset({'done', 'not_useful', 'not_applicable'})


def get_prioritized_actions(db: Session, user_id: str, person_id: str | None = None) -> list[HealthAction]:
    """Return active (non-dismissed, non-done, non-future-snoozed) actions sorted by decision engine priority."""
    actions = list_actions(db, user_id, person_id)
    now = datetime.now(timezone.utc)

    def _is_active(a: HealthAction) -> bool:
        if a.status in _INACTIVE_STATUSES:
            return False
        if a.status == 'snoozed' and a.snoozed_until is not None and a.snoozed_until > now:
            return False
        return True

    active = [a for a in actions if _is_active(a)]

    def sort_key(a: HealthAction) -> tuple:
        status_rank = _STATUS_ORDER.get(a.status, 9)
        reminder_rank = 0 if a.reminder_status in ('overdue', 'risk_up', 'streak_break') else 1
        priority_rank = _PRIORITY_ORDER.get(a.priority, 9)
        return (reminder_rank, status_rank, priority_rank)

    active.sort(key=sort_key)
    return active
