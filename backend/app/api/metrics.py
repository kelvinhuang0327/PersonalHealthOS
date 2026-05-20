from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.core.cache import cache_invalidate
from app.models.entities import HealthMetric, PersonProfile, RiskAlert, User
from app.schemas.metrics import MetricCreateRequest, MetricResponse
from app.services.risk_engine import evaluate_metric_risks

router = APIRouter(prefix='/metrics', tags=['health-metrics'])


@router.post('', response_model=MetricResponse)
def create_metric(
    payload: MetricCreateRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    metric = HealthMetric(
        user_id=current_user.id,
        subject_profile_id=target_person.id,
        **payload.model_dump(),
    )
    db.add(metric)
    db.flush()

    alerts = evaluate_metric_risks(str(current_user.id), target_person, metric)
    for alert in alerts:
        alert.subject_profile_id = target_person.id
        db.add(alert)

    db.commit()
    db.refresh(metric)
    cache_invalidate(f'dashboard:{current_user.id}:')
    cache_invalidate(f'score:{target_person.id}')
    return metric


@router.get('', response_model=list[MetricResponse])
def list_metrics(
    limit: int = Query(default=50, ge=1, le=200),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person_filter = HealthMetric.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, HealthMetric.subject_profile_id.is_(None))
    return (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, person_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(limit)
        .all()
    )


@router.get('/latest', response_model=Optional[MetricResponse])
def latest_metric(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person_filter = HealthMetric.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, HealthMetric.subject_profile_id.is_(None))
    return (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, person_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .first()
    )
