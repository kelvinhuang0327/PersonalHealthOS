from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.core.cache import cache_invalidate
from app.models.entities import PersonProfile, User
from app.schemas.actions import HealthActionCreate, HealthActionRead, HealthActionUpdate
from app.services import action_service

router = APIRouter(prefix='/actions', tags=['actions'])
ACTION_NOT_FOUND = 'Action not found'


@router.get('', response_model=list[HealthActionRead])
def list_actions(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    due_within_days: Annotated[Optional[int], Query(ge=0, le=365)] = None,
):
    actions = action_service.list_actions(db, str(current_user.id), str(target_person.id))
    if due_within_days is not None:
        cutoff = datetime.now(timezone.utc) + timedelta(days=due_within_days)
        cutoff_date = cutoff.date()
        actions = [
            a for a in actions
            if a.due_date is not None and a.due_date <= cutoff_date and a.status not in {'done', 'cancelled'}
        ]
    return actions


@router.get('/prioritized', response_model=list[HealthActionRead])
def get_prioritized_actions(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Returns active actions ranked by Decision Engine priority."""
    return action_service.get_prioritized_actions(db, str(current_user.id), str(target_person.id))


@router.post('', response_model=HealthActionRead, status_code=201)
def create_action(
    payload: HealthActionCreate,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    data = payload.model_dump(exclude_none=True)
    # Force person_id to the resolved target person
    data['person_id'] = target_person.id
    return action_service.create_action(db, str(current_user.id), data)


@router.patch('/{action_id}', response_model=HealthActionRead, responses={404: {'description': ACTION_NOT_FOUND}})
def update_action(
    action_id: str,
    payload: HealthActionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    action = action_service.get_action(db, str(current_user.id), action_id)
    if not action:
        raise HTTPException(status_code=404, detail=ACTION_NOT_FOUND)
    patch = payload.model_dump(exclude_none=True)
    updated = action_service.update_action(db, action, patch)

    # After marking done, try to compute 7-day outcomes
    if payload.status == 'done':
        action_service.compute_outcomes(db, updated, time_window_days=7)
        action_service.compute_outcomes(db, updated, time_window_days=14)
        action_service.compute_outcomes(db, updated, time_window_days=30)
        db.refresh(updated)

    return updated


@router.post('/{action_id}/complete', response_model=HealthActionRead, responses={404: {'description': ACTION_NOT_FOUND}})
def complete_action(
    action_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Mark an action done and update streak. Idempotent if already done."""
    action = action_service.get_action(db, str(current_user.id), action_id)
    if not action:
        raise HTTPException(status_code=404, detail=ACTION_NOT_FOUND)
    updated = action_service.update_action(db, action, {'status': 'done'})
    action_service.compute_outcomes(db, updated, time_window_days=7)
    db.refresh(updated)
    cache_invalidate(f'dashboard:{current_user.id}:')
    return updated


@router.delete('/{action_id}', status_code=204, responses={404: {'description': ACTION_NOT_FOUND}})
def delete_action(
    action_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    action = action_service.get_action(db, str(current_user.id), action_id)
    if not action:
        raise HTTPException(status_code=404, detail=ACTION_NOT_FOUND)
    action_service.delete_action(db, action)


@router.get('/{action_id}/outcomes', response_model=list, responses={404: {'description': ACTION_NOT_FOUND}})
def get_action_outcomes(
    action_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    action = action_service.get_action(db, str(current_user.id), action_id)
    if not action:
        raise HTTPException(status_code=404, detail=ACTION_NOT_FOUND)
    outcomes = action_service.get_outcomes_for_action(db, action_id)
    return [
        {
            'metric_type': o.metric_type,
            'before_value': float(o.before_value) if o.before_value is not None else None,
            'after_value': float(o.after_value) if o.after_value is not None else None,
            'delta': float(o.delta) if o.delta is not None else None,
            'delta_pct': float(o.delta_pct) if o.delta_pct is not None else None,
            'time_window_days': o.time_window_days,
            'outcome_label': o.outcome_label,
            'computed_at': o.computed_at.isoformat(),
        }
        for o in outcomes
    ]
