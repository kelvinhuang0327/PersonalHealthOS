from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import HealthMetric, PersonProfile, RiskAlert, User
from app.schemas.risk_alerts import RiskAlertResponse
from app.services.health_risk_monitor_service import run_health_risk_monitor
from app.services.risk_engine import evaluate_metric_risks

router = APIRouter(prefix='/risk-alerts', tags=['risk-alerts'])


@router.get('', response_model=list[RiskAlertResponse])
def list_risk_alerts(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert_filter = RiskAlert.subject_profile_id == target_person.id
    if target_person.is_default:
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
    return (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == current_user.id, alert_filter)
        .order_by(RiskAlert.created_at.desc())
        .all()
    )


@router.post('/recalculate', response_model=list[RiskAlertResponse])
def recalculate(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    metric_filter = HealthMetric.subject_profile_id == target_person.id
    if target_person.is_default:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
    latest_metric = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .first()
    )
    if not latest_metric:
        return []

    alerts = evaluate_metric_risks(str(current_user.id), target_person, latest_metric)
    for alert in alerts:
        alert.subject_profile_id = target_person.id
        db.add(alert)
    db.commit()
    return alerts


@router.post('/monitor', response_model=list[RiskAlertResponse])
def run_monitor(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = run_health_risk_monitor(
        db,
        user_id=str(current_user.id),
        person_id=str(target_person.id),
        include_legacy=target_person.is_default,
    )
    for alert in alerts:
        db.add(alert)
    db.commit()
    return alerts


@router.get('/unread-count')
def get_unread_count(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns count of active (unresolved) alerts for the badge."""
    alert_filter = RiskAlert.subject_profile_id == target_person.id
    if target_person.is_default:
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
    count = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.user_id == current_user.id,
            alert_filter,
            RiskAlert.status == 'active',
        )
        .count()
    )
    return {'count': count}


@router.post('/{alert_id}/dismiss')
def dismiss_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as resolved so it no longer appears in the unread count."""
    from uuid import UUID as _UUID
    try:
        aid = _UUID(alert_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail='Invalid alert ID')
    alert = db.query(RiskAlert).filter(RiskAlert.id == aid, RiskAlert.user_id == current_user.id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='Alert not found')
    alert.status = 'resolved'
    from datetime import datetime, timezone
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {'ok': True}
