from datetime import datetime, timedelta, timezone
import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.core.cache import cache_get, cache_set
from app.models.entities import HealthMetric, HealthScore, LabReport, LabReportItem, PersonProfile, SymptomLog, User
from app.schemas.dashboard import DashboardOverviewResponse, DashboardOverviewV2Response, DashboardTrendsResponse, TrendPoint
from app.services.health_ai_engine.anomaly_engine import detect_anomalies
from app.services.health_ai_engine.clinical_score_engine import calculate_clinical_scores
from app.services.health_ai_engine.confidence_engine import calibrate_confidence
from app.services.health_ai_engine.guideline_engine import derive_clinical_labels
from app.services.health_ai_engine.guideline_registry import enrich_explainability
from app.services.health_ai_engine.health_score_engine import calculate_health_score
from app.services.health_ai_engine.insight_engine import (
    generate_health_narrative,
    generate_health_narrative_v2,
    generate_health_narrative_v3,
    build_alert_snapshot_hash,
    get_latest_narrative,
    list_active_insights,
    persist_narrative_history,
)
from app.services.health_ai_engine.orchestrator import HealthEngineOrchestrator
from app.services.health_ai_engine.prediction_engine import generate_predictive_insights
from app.services.health_ai_engine.reasoning_engine import generate_reasoning_summary
from app.services.health_ai_engine.recommendation_engine import generate_recommendations
from app.services.health_ai_engine.risk_engine import list_active_risk_alerts
from app.services.health_ai_engine.risk_stratification_engine import stratify_risk_level
from app.services.health_ai_engine.safety_guardrail import MEDICAL_DISCLAIMER, apply_safety_guardrail
from app.services.health_ai_engine.timeline_engine import build_health_timeline
from app.services.health_score_service import _clamp_int
from app.services import action_service
from app.services.decision_engine_service import build_decision_items

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/overview', response_model=DashboardOverviewResponse)
def overview(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    metric_filter = HealthMetric.subject_profile_id == target_person.id
    alert_filter = list_active_risk_alerts
    if target_person.is_default:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
    latest = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .first()
    )
    alerts = alert_filter(db, str(current_user.id), str(target_person.id), target_person.is_default, limit=10)

    if latest:
        latest_metrics = {
            'recorded_at': latest.recorded_at.isoformat(),
            'systolic_bp': latest.systolic_bp,
            'diastolic_bp': latest.diastolic_bp,
            'heart_rate': latest.heart_rate,
            'blood_glucose': float(latest.blood_glucose) if latest.blood_glucose is not None else None,
            'weight_kg': float(latest.weight_kg) if latest.weight_kg is not None else None,
            'sleep_hours': float(latest.sleep_hours) if latest.sleep_hours is not None else None,
        }
    else:
        latest_metrics = {}

    return DashboardOverviewResponse(
        latest_metrics=latest_metrics,
        active_alerts=[
            {
                'id': str(a.id),
                'severity': a.severity,
                'title': a.title,
                'message': a.message,
                'created_at': a.created_at.isoformat(),
            }
            for a in alerts
        ],
        summary={
            'active_alert_count': len(alerts),
            'has_recent_metrics': latest is not None,
        },
    )


@router.get('/trends', response_model=DashboardTrendsResponse)
def trends(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    return _build_trends(days, target_person, current_user, db)


def _build_trends(days: int, target_person: PersonProfile, current_user: User, db: Session) -> DashboardTrendsResponse:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    metric_filter = HealthMetric.subject_profile_id == target_person.id
    if target_person.is_default:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, HealthMetric.recorded_at >= start, metric_filter)
        .order_by(HealthMetric.recorded_at.asc())
        .all()
    )

    def make_points(field: str):
        points = []
        for m in metrics:
            value = getattr(m, field)
            if value is not None:
                points.append(TrendPoint(recorded_at=m.recorded_at.isoformat(), value=float(value)))
        return points

    return DashboardTrendsResponse(
        blood_glucose=make_points('blood_glucose'),
        weight_kg=make_points('weight_kg'),
        systolic_bp=make_points('systolic_bp'),
        sleep_hours=make_points('sleep_hours'),
    )


@router.get('', response_model=DashboardOverviewV2Response)
def dashboard(
    response: Response,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    cache_key = f'dashboard:{current_user.id}:{target_person.id}'
    cached = cache_get(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        return cached
    metric_filter = HealthMetric.subject_profile_id == target_person.id
    alert_filter = None
    symptom_filter = SymptomLog.subject_profile_id == target_person.id
    report_filter = LabReport.subject_profile_id == target_person.id
    include_legacy = target_person.is_default
    if include_legacy:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))

    score = calculate_health_score(db, current_user.id, target_person.id, target_person, include_legacy, days=90)

    long_term_symptoms = (
        db.query(SymptomLog)
        .filter(
            SymptomLog.user_id == current_user.id,
            symptom_filter,
            SymptomLog.estimated_duration_days.isnot(None),
            SymptomLog.estimated_duration_days >= 180,
        )
        .count()
    )
    active_alerts = list_active_risk_alerts(db, str(current_user.id), str(target_person.id), include_legacy, limit=50)
    active_alerts_count = len(active_alerts)
    extra_penalty = min(20, long_term_symptoms * 4) + min(12, active_alerts_count * 2)
    overall_score = _clamp_int(score['overall_score'] - extra_penalty)

    alerts = active_alerts[:5]
    insights = list_active_insights(db, str(current_user.id), str(target_person.id), include_legacy, limit=5)
    recent_symptoms = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == current_user.id, symptom_filter)
        .order_by(SymptomLog.occurred_at.desc())
        .limit(5)
        .all()
    )
    recent_metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == current_user.id, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(5)
        .all()
    )
    recent_labs = (
        db.query(LabReport)
        .filter(LabReport.user_id == current_user.id, report_filter)
        .order_by(LabReport.created_at.desc())
        .limit(5)
        .all()
    )
    trends_data = _build_trends(30, target_person, current_user, db)
    timeline_events = build_health_timeline(
        db,
        user_id=str(current_user.id),
        person_id=str(target_person.id),
        include_legacy=include_legacy,
        days=90,
        limit=120,
    )
    predictive_insights = generate_predictive_insights(recent_metrics, alerts)
    anomaly_alerts = detect_anomalies(recent_metrics, [])
    reasoning = generate_reasoning_summary(
        timeline_events=timeline_events,
        risk_alerts=alerts,
        health_score=score,
        insights=insights,
        metrics=recent_metrics,
    )

    report_ids = [report.id for report in recent_labs]
    lab_items = []
    if report_ids:
        lab_items = (
            db.query(LabReportItem)
            .filter(LabReportItem.report_id.in_(report_ids))
            .order_by(LabReportItem.captured_at.desc())
            .limit(40)
            .all()
        )
    abnormal_by_report = {}
    if report_ids:
        abnormal_rows = (
            db.query(LabReportItem.report_id)
            .filter(LabReportItem.report_id.in_(report_ids), LabReportItem.abnormal_flag.in_(['H', 'L']))
            .all()
        )
        for row in abnormal_rows:
            abnormal_by_report[row.report_id] = abnormal_by_report.get(row.report_id, 0) + 1
    clinical_labels = derive_clinical_labels(recent_metrics, lab_items)
    previous_narrative = get_latest_narrative(db, str(current_user.id), str(target_person.id), include_legacy=include_legacy, summary_type='daily')
    calibrated_confidence = calibrate_confidence(
        metrics_count=len(recent_metrics),
        labs_count=len(lab_items),
        timeline_length=len(timeline_events),
        rule_coverage=min(1.0, (len(alerts) + len(insights)) / 10.0),
    )
    orchestrator = HealthEngineOrchestrator(db, target_person)
    analysis_results = asyncio.run(
        orchestrator.run_full_analysis(
            {
                'user_id': str(current_user.id),
                'person_id': str(target_person.id),
                'include_legacy': include_legacy,
                'metrics': recent_metrics,
                'baseline_metrics': [],
                'labs': lab_items,
                'alerts': alerts,
                'insights': insights,
                'clinical_labels': clinical_labels,
                'long_term_symptoms': long_term_symptoms,
                'active_alerts_count': active_alerts_count,
                'calibrated_confidence': calibrated_confidence,
                'previous_narrative': previous_narrative,
                'completed_actions': action_service.list_actions(db, str(current_user.id), str(target_person.id)),
            }
        )
    )
    risk_level = analysis_results.risk_level or stratify_risk_level(recent_metrics, lab_items, long_term_symptoms, active_alerts_count)
    recommendations = analysis_results.recommendations or generate_recommendations(clinical_labels, risk_level['risk_level'], alerts, calibrated_confidence)
    safe_reasoning = apply_safety_guardrail(reasoning['summary'])
    previous_score_row = (
        db.query(HealthScore)
        .filter(HealthScore.user_id == current_user.id, HealthScore.subject_profile_id == target_person.id)
        .order_by(HealthScore.calculated_at.desc())
        .first()
    )
    based_on_score_id = str(previous_score_row.id) if previous_score_row else None
    narrative_generated_at = datetime.now(timezone.utc)
    narrative_context = {
        'health_score': {'overall_score': overall_score, 'components': score},
        'overall_score': overall_score,
        'alerts': alerts,
        'insights': insights,
        'trends': {
            'blood_glucose': trends_data.blood_glucose,
            'weight_kg': trends_data.weight_kg,
            'systolic_bp': trends_data.systolic_bp,
            'sleep_hours': trends_data.sleep_hours,
        },
        'symptoms': recent_symptoms,
        'labs': lab_items,
        'metrics': recent_metrics,
        'actions': recommendations,
        'risk_level': risk_level['risk_level'],
        'summary_type': 'daily',
        'narrative_version': 'v2',
        'generated_at': narrative_generated_at.isoformat(),
        'based_on_score_id': based_on_score_id,
        'based_on_alert_snapshot': None,
    }
    health_narrative = generate_health_narrative(
        narrative_context
    )
    health_narrative_v2 = generate_health_narrative_v2(narrative_context, previous_narrative)

    # Narrative v3: load completed actions for causal analysis
    completed_actions = action_service.list_actions(db, str(current_user.id), str(target_person.id))
    health_narrative_v3 = analysis_results.narrative or {
        "summary": "健康大綱已整理，請參考下方細項建議。",
        "risks": [],
        "trends": [],
        "reasons": [],
        "actions": []
    }

    alert_snapshot = build_alert_snapshot_hash(alerts) if alerts else None
    narrative_payload = {
        'health_score': {'overall_score': overall_score, 'components': score},
        'overall_score': overall_score,
        'risk_level': risk_level['risk_level'],
        'summary_type': 'daily',
        'narrative_version': 'v2',
        'generated_at': narrative_generated_at.isoformat(),
        'based_on_score_id': based_on_score_id,
        'based_on_alert_snapshot': alert_snapshot,
        'health_narrative': health_narrative,
        'health_narrative_v2': health_narrative_v2,
        'health_narrative_history_source': 'dashboard',
    }
    persisted_narrative = persist_narrative_history(
        db,
        str(current_user.id),
        str(target_person.id),
        narrative_payload,
        summary_type='daily',
        based_on_score_id=based_on_score_id,
        based_on_alert_snapshot=alert_snapshot,
        include_legacy=include_legacy,
    )
    if persisted_narrative is not None:
        narrative_generated_at = persisted_narrative.generated_at or narrative_generated_at
    alerts_payload = [
        enrich_explainability(
            {
                'id': str(a.id),
                'severity': a.severity,
                'title': a.title,
                'description': a.description or a.message,
                'created_at': a.created_at.isoformat(),
                'rule_id': getattr(a, 'rule_id', a.rule_code.lower()),
                'category': getattr(a, 'category', 'risk'),
                'priority': getattr(a, 'priority', 0),
                'confidence': getattr(a, 'confidence', calibrated_confidence),
                'evidence_level': getattr(a, 'evidence_level', 'B'),
                'guideline_source': getattr(a, 'guideline_source', 'Rule Library'),
                'medical_disclaimer': MEDICAL_DISCLAIMER,
            }
        )
        for a in alerts
    ]
    insights_payload = []
    for i in insights:
        explain = enrich_explainability((i.evidence_json or {}).copy())
        insights_payload.append(
            {
                'id': str(i.id),
                'insight_type': i.insight_type,
                'severity': i.severity,
                'title': i.title,
                'summary': i.summary,
                'recommendation': i.recommendation,
                'generated_at': i.generated_at.isoformat(),
                'rule_id': explain.get('rule_id'),
                'category': explain.get('category'),
                'priority': explain.get('priority', 0),
                'confidence': explain.get('confidence', calibrated_confidence),
                'evidence_level': explain.get('evidence_level', 'B'),
                'guideline_source': explain.get('guideline_source'),
                'guideline_version': explain.get('guideline_version'),
                'medical_disclaimer': MEDICAL_DISCLAIMER,
            }
        )
    top_source = recommendations[0]['guideline_source'] if recommendations else 'Health Rule Library'
    top_evidence = recommendations[0].get('evidence_level', 'B') if recommendations else 'B'
    explainability_summary = (
        f"此分析基於 {top_source} 指引，證據等級 {top_evidence}，可信度 {calibrated_confidence:.2f}。"
    )

    # Decision Engine: backend-sorted prioritized actions
    prioritized_actions_raw = action_service.get_prioritized_actions(db, str(current_user.id), str(target_person.id))
    prioritized_actions = [
        {
            'id': str(a.id),
            'title': a.title,
            'category': a.category,
            'status': a.status,
            'priority': a.priority,
            'frequency': a.frequency,
            'impact_status': a.impact_status,
            'reminder_status': a.reminder_status,
            'streak_count': a.streak_count,
        }
        for a in prioritized_actions_raw
    ]

    # Unified Decision Items: single source of truth for all pages
    decision_items = build_decision_items(
        alerts=alerts_payload,
        insights=insights_payload,
        recommendations=recommendations,
        actions=prioritized_actions_raw,
        trends={
            'systolic_bp': [{'value': p.value, 'recorded_at': p.recorded_at} for p in trends_data.systolic_bp],
            'blood_glucose': [{'value': p.value, 'recorded_at': p.recorded_at} for p in trends_data.blood_glucose],
            'weight_kg': [{'value': p.value, 'recorded_at': p.recorded_at} for p in trends_data.weight_kg],
            'sleep_hours': [{'value': p.value, 'recorded_at': p.recorded_at} for p in trends_data.sleep_hours],
        },
        health_score={'overall_score': overall_score},
        risk_level=str(risk_level['risk_level']),
    )

    payload = DashboardOverviewV2Response(
        health_score={
            'overall_score': overall_score,
            'components': {
                'blood_pressure': score['cardiovascular_score'],
                'bmi': score['weight_score'],
                'long_term_symptoms_penalty': min(20, long_term_symptoms * 4),
                'lab_results': score['metabolic_score'],
                'risk_alerts_penalty': min(12, active_alerts_count * 2),
            },
        },
        alerts=alerts_payload,
        insights=insights_payload,
        recent_symptoms=[
            {
                'id': str(s.id),
                'symptom': s.symptom,
                'occurred_at': s.occurred_at.isoformat(),
                'note': s.note,
                'estimated_start_date': s.estimated_start_date.isoformat() if s.estimated_start_date else None,
                'estimated_duration_days': s.estimated_duration_days,
            }
            for s in recent_symptoms
        ],
        recent_metrics=[
            {
                'id': str(m.id),
                'recorded_at': m.recorded_at.isoformat(),
                'systolic_bp': m.systolic_bp,
                'diastolic_bp': m.diastolic_bp,
                'heart_rate': m.heart_rate,
                'blood_glucose': float(m.blood_glucose) if m.blood_glucose is not None else None,
                'weight_kg': float(m.weight_kg) if m.weight_kg is not None else None,
                'sleep_hours': float(m.sleep_hours) if m.sleep_hours is not None else None,
                'steps': m.steps,
            }
            for m in recent_metrics
        ],
        recent_labs=[
            {
                'id': str(r.id),
                'report_date': r.report_date.isoformat() if r.report_date else None,
                'report_type': r.report_type,
                'created_at': r.created_at.isoformat(),
                'abnormal_items': abnormal_by_report.get(r.id, 0),
            }
            for r in recent_labs
        ],
        trends={
            'blood_glucose': trends_data.blood_glucose,
            'weight_kg': trends_data.weight_kg,
            'systolic_bp': trends_data.systolic_bp,
            'sleep_hours': trends_data.sleep_hours,
        },
        reasoning_summary=safe_reasoning['safe_response'],
        predictive_insights=predictive_insights,
        anomaly_alerts=anomaly_alerts,
        clinical_labels=clinical_labels,
        risk_level=risk_level['risk_level'],
        recommendations=recommendations,
        health_narrative=health_narrative,
        health_narrative_v2=health_narrative_v2,
        health_narrative_v3=health_narrative_v3,
        prioritized_actions=prioritized_actions,
        decision_items=decision_items,
        narrative_generated_at=narrative_generated_at.isoformat(),
        explainability_summary=explainability_summary,
        medical_disclaimer=MEDICAL_DISCLAIMER,
    )
    response.headers['X-Cache'] = 'MISS'
    cache_set(cache_key, payload.model_dump(mode='json'), ttl_seconds=300)
    return payload
