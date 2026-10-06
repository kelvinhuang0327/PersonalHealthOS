from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import AISummary, HealthMetric, PersonProfile, RiskAlert, User
from app.schemas.ai_summary import AISummaryGenerateRequest, AISummaryResponse
from app.services.ai_service import generate_health_summary

router = APIRouter(prefix='/ai-summary', tags=['ai-summary'])


@router.post('/generate', response_model=AISummaryResponse)
def generate_summary(
    payload: AISummaryGenerateRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    period_end = payload.period_end or date.today()
    period_start = payload.period_start or (period_end - timedelta(days=30))

    metric_filter = HealthMetric.subject_profile_id == target_person.id
    alert_filter = RiskAlert.subject_profile_id == target_person.id
    if target_person.is_default:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(20)
        .all()
    )
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == current_user.id, alert_filter)
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
        .all()
    )

    data = generate_health_summary(
        profile={
            'full_name': target_person.display_name,
            'gender': target_person.gender,
            'height_cm': float(target_person.height_cm) if target_person.height_cm else None,
            'weight_kg': float(target_person.weight_kg) if target_person.weight_kg else None,
        },
        metrics=[
            {
                'recorded_at': m.recorded_at.isoformat(),
                'systolic_bp': m.systolic_bp,
                'diastolic_bp': m.diastolic_bp,
                'blood_glucose': float(m.blood_glucose) if m.blood_glucose is not None else None,
                'weight_kg': float(m.weight_kg) if m.weight_kg is not None else None,
            }
            for m in metrics
        ],
        alerts=[
            {
                'severity': a.severity,
                'title': a.title,
                'message': a.message,
                'created_at': a.created_at.isoformat(),
            }
            for a in alerts
        ],
        period_start=period_start,
        period_end=period_end,
    )

    row = AISummary(user_id=current_user.id, subject_profile_id=target_person.id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get('', response_model=list[AISummaryResponse])
def list_summary(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary_filter = AISummary.subject_profile_id == target_person.id
    if target_person.is_default:
        summary_filter = or_(summary_filter, AISummary.subject_profile_id.is_(None))
    return (
        db.query(AISummary)
        .filter(AISummary.user_id == current_user.id, summary_filter)
        .order_by(AISummary.created_at.desc())
        .limit(20)
        .all()
    )
