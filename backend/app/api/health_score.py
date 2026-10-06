from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.core.cache import cache_get, cache_invalidate, cache_set
from app.models.entities import HealthScore, PersonProfile, User
from app.schemas.health_score import HealthScoreCalculateRequest, HealthScoreResponse
from app.services.health_score_service import calculate_health_score

router = APIRouter(prefix='/health-score', tags=['health-score'])


@router.post('/calculate', response_model=HealthScoreResponse)
def calculate(
    payload: HealthScoreCalculateRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    score_payload = calculate_health_score(
        db,
        str(current_user.id),
        person_id=str(target_person.id),
        profile=target_person,
        include_legacy=target_person.is_default,
        days=payload.days,
    )
    row = HealthScore(user_id=current_user.id, subject_profile_id=target_person.id, **score_payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    cache_invalidate(f'score:{target_person.id}')
    return row


@router.get('/latest', response_model=Optional[HealthScoreResponse])
def latest(
    response: Response,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache_key = f'score:{target_person.id}'
    cached = cache_get(cache_key)
    if cached is not None:
      response.headers['X-Cache'] = 'HIT'
      return cached
    person_filter = HealthScore.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, HealthScore.subject_profile_id.is_(None))
    row = (
        db.query(HealthScore)
        .filter(HealthScore.user_id == current_user.id, person_filter)
        .order_by(HealthScore.calculated_at.desc())
        .first()
    )
    response.headers['X-Cache'] = 'MISS'
    if row is not None:
        cache_set(cache_key, row, ttl_seconds=300)
    return row


@router.get('/history', response_model=list[HealthScoreResponse])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person_filter = HealthScore.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, HealthScore.subject_profile_id.is_(None))
    return (
        db.query(HealthScore)
        .filter(HealthScore.user_id == current_user.id, person_filter)
        .order_by(HealthScore.calculated_at.desc())
        .limit(limit)
        .all()
    )
