from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import HealthMetric, LabReport, LabReportItem, PersonProfile, RiskAlert, SymptomLog, User
from app.schemas.health_analysis import HealthAnalysisResponse
from app.schemas.trend_analysis import TrendsAnalysisResponse
from app.services.health_analysis_service import build_health_analysis
from app.services.trend_analysis_service import analyze_health_trends

router = APIRouter(prefix='/analytics', tags=['analytics'])


@router.get('/trends', response_model=TrendsAnalysisResponse)
def trends_analysis(
    days: int = Query(default=90, ge=7, le=365),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summaries = analyze_health_trends(
        db,
        str(current_user.id),
        person_id=str(target_person.id),
        include_legacy=target_person.is_default,
        days=days,
    )
    return TrendsAnalysisResponse(period_days=days, summaries=summaries)


@router.get('/health-analysis', response_model=HealthAnalysisResponse)
def health_analysis(
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == current_user.id, RiskAlert.subject_profile_id == target_person.id)
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
        .all()
    )
    symptoms = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == current_user.id, SymptomLog.subject_profile_id == target_person.id)
        .order_by(SymptomLog.occurred_at.desc())
        .limit(20)
        .all()
    )
    lab_items = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(LabReport.user_id == current_user.id, LabReport.subject_profile_id == target_person.id)
        .order_by(LabReportItem.captured_at.desc())
        .limit(40)
        .all()
    )
    body_metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, HealthMetric.subject_profile_id == target_person.id)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(20)
        .all()
    )
    return build_health_analysis(str(target_person.id), body_metrics, symptoms, lab_items, alerts)
