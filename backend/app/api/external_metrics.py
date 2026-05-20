from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import HealthMetric, PersonProfile, User
from app.schemas.external_metrics import ExternalSyncResponse, ExternalTrendPoint, ExternalTrendResponse
from app.services.external_metrics_service import mock_external_metrics

router = APIRouter(prefix='/external-metrics', tags=['external-metrics'])


@router.post('/sync', response_model=ExternalSyncResponse)
def sync_external_metrics(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = mock_external_metrics()
    for row in rows:
        db.add(
            HealthMetric(
                user_id=current_user.id,
                subject_profile_id=target_person.id,
                recorded_at=row['recorded_at'],
                systolic_bp=row.get('systolic_bp'),
                diastolic_bp=row.get('diastolic_bp'),
                heart_rate=row.get('heart_rate'),
                blood_glucose=row.get('blood_glucose'),
                sleep_hours=row.get('sleep_hours'),
                steps=row.get('steps'),
                source=row.get('source', 'external_api'),
            )
        )
    db.commit()
    return ExternalSyncResponse(synced_count=len(rows), source='external_api')


@router.get('/history')
def list_external_metrics(
    days: int = Query(default=30, ge=1, le=365),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(HealthMetric)
        .filter(
            HealthMetric.user_id == current_user.id,
            HealthMetric.subject_profile_id == target_person.id,
            HealthMetric.source == 'external_api',
            HealthMetric.recorded_at >= start,
        )
        .order_by(HealthMetric.recorded_at.desc())
        .all()
    )


@router.get('/trends', response_model=ExternalTrendResponse)
def external_trends(
    metric: str = Query(default='steps'),
    days: int = Query(default=30, ge=1, le=365),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field_map = {'steps': 'steps', 'heart_rate': 'heart_rate', 'blood_glucose': 'blood_glucose', 'sleep_hours': 'sleep_hours'}
    field = field_map.get(metric, 'steps')
    start = datetime.now(timezone.utc) - timedelta(days=days)
    metrics = (
        db.query(HealthMetric)
        .filter(
            HealthMetric.user_id == current_user.id,
            HealthMetric.subject_profile_id == target_person.id,
            HealthMetric.source == 'external_api',
            HealthMetric.recorded_at >= start,
        )
        .order_by(HealthMetric.recorded_at.asc())
        .all()
    )
    points = []
    for row in metrics:
        value = getattr(row, field)
        if value is not None:
            points.append(ExternalTrendPoint(recorded_at=row.recorded_at, value=float(value)))
    return ExternalTrendResponse(metric=field, points=points)
