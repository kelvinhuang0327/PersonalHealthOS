from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.entities import AISummary, HealthInsight, HealthMetric, LabReport, LabReportItem, RiskAlert, SymptomLog


def build_health_timeline(db: Session, user_id: str, person_id: str, include_legacy: bool, days: int = 180, limit: int = 200) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    report_filter = LabReport.subject_profile_id == person_key
    symptom_filter = SymptomLog.subject_profile_id == person_key
    metric_filter = HealthMetric.subject_profile_id == person_key
    ai_filter = AISummary.subject_profile_id == person_key
    alert_filter = RiskAlert.subject_profile_id == person_key
    insight_filter = HealthInsight.subject_profile_id == person_key
    if include_legacy:
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        ai_filter = or_(ai_filter, AISummary.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
        insight_filter = or_(insight_filter, HealthInsight.subject_profile_id.is_(None))

    reports = (
        db.query(LabReport).filter(LabReport.user_id == user_key, LabReport.created_at >= start, report_filter).order_by(LabReport.created_at.desc()).all()
    )
    report_ids = [r.id for r in reports]
    abnormal_map: dict[str, int] = {}
    if report_ids:
        rows = (
            db.query(LabReportItem.report_id, func.count(LabReportItem.id))
            .filter(LabReportItem.report_id.in_(report_ids), LabReportItem.abnormal_flag.in_(['H', 'L']))
            .group_by(LabReportItem.report_id)
            .all()
        )
        abnormal_map = {str(report_id): int(cnt) for report_id, cnt in rows}
    symptoms = (
        db.query(SymptomLog).filter(SymptomLog.user_id == user_key, SymptomLog.occurred_at >= start, symptom_filter).order_by(SymptomLog.occurred_at.desc()).all()
    )
    metrics = (
        db.query(HealthMetric).filter(HealthMetric.user_id == user_key, HealthMetric.recorded_at >= start, metric_filter).order_by(HealthMetric.recorded_at.desc()).all()
    )
    ai_summaries = (
        db.query(AISummary).filter(AISummary.user_id == user_key, ai_filter, AISummary.created_at >= start).order_by(AISummary.created_at.desc()).all()
    )
    risk_alerts = (
        db.query(RiskAlert).filter(RiskAlert.user_id == user_key, alert_filter, RiskAlert.created_at >= start).order_by(RiskAlert.created_at.desc()).all()
    )
    insights = (
        db.query(HealthInsight)
        .filter(HealthInsight.user_id == user_key, HealthInsight.is_active.is_(True), insight_filter, HealthInsight.generated_at >= start)
        .order_by(HealthInsight.generated_at.desc())
        .all()
    )
    timeline: list[dict[str, Any]] = []
    for report in reports:
        abnormal_count = abnormal_map.get(str(report.id), 0)
        timeline.append({'type': 'lab', 'event_type': 'lab_report', 'event_time': report.created_at.isoformat(), 'temporal_type': 'exact', 'start_date': report.created_at.date().isoformat(), 'end_date': report.created_at.date().isoformat(), 'label': report.report_type, 'title': '健檢報告解析完成', 'description': f'檢驗日期 {report.report_date or "未知"}，異常項目 {abnormal_count} 個。', 'data': {'report_id': str(report.id), 'report_type': report.report_type, 'abnormal_items': abnormal_count}, 'metadata': {'report_id': str(report.id)}})
    for symptom in symptoms:
        is_estimated = bool(symptom.estimated_start_date)
        start_date = symptom.estimated_start_date.isoformat() if symptom.estimated_start_date else symptom.occurred_at.date().isoformat()
        timeline.append({'type': 'symptom', 'event_type': 'symptom', 'event_time': (f'{start_date}T00:00:00+00:00' if is_estimated else symptom.occurred_at.isoformat()), 'temporal_type': 'estimated' if is_estimated else 'exact', 'start_date': start_date, 'end_date': 'present' if is_estimated else symptom.occurred_at.date().isoformat(), 'label': symptom.symptom, 'title': f'症狀：{symptom.symptom}', 'description': f'估算持續 {symptom.estimated_duration_days or 0} 天。' if is_estimated else f'嚴重度 {symptom.severity}/5。', 'data': {'symptom': symptom.symptom, 'severity': symptom.severity, 'estimated_start_date': symptom.estimated_start_date.isoformat() if symptom.estimated_start_date else None, 'estimated_duration_days': symptom.estimated_duration_days}, 'metadata': {'symptom_id': str(symptom.id)}})
    for metric in metrics:
        timeline.append({'type': 'metric', 'event_type': 'health_metric', 'event_time': metric.recorded_at.isoformat(), 'temporal_type': 'exact', 'start_date': metric.recorded_at.date().isoformat(), 'end_date': metric.recorded_at.date().isoformat(), 'label': '健康數據', 'title': '健康數據紀錄', 'description': '已新增健康數據。', 'data': {'systolic_bp': metric.systolic_bp, 'diastolic_bp': metric.diastolic_bp, 'heart_rate': metric.heart_rate, 'blood_glucose': float(metric.blood_glucose) if metric.blood_glucose is not None else None, 'weight_kg': float(metric.weight_kg) if metric.weight_kg is not None else None, 'sleep_hours': float(metric.sleep_hours) if metric.sleep_hours is not None else None, 'steps': metric.steps, 'source': metric.source}, 'metadata': {'metric_id': str(metric.id)}})
    for summary in ai_summaries:
        narrative_json = summary.narrative_json or {}
        narrative_v2 = narrative_json.get('health_narrative_v2') if isinstance(narrative_json, dict) else {}
        event_type = 'narrative_summary' if narrative_json else 'ai_summary'
        title = '健康敘事更新' if narrative_json else 'AI 健康洞察'
        description = (
            (narrative_v2.get('delta_summary') if isinstance(narrative_v2, dict) else None)
            or (narrative_v2.get('summary') if isinstance(narrative_v2, dict) else None)
            or (summary.summary_text or '')[:120]
        )
        event_time = summary.generated_at or summary.created_at
        timeline.append(
            {
                'type': 'insight',
                'event_type': event_type,
                'event_time': event_time.isoformat(),
                'temporal_type': 'exact',
                'start_date': event_time.date().isoformat(),
                'end_date': event_time.date().isoformat(),
                'label': '健康敘事' if narrative_json else 'AI健康洞察',
                'title': title,
                'description': description,
                'data': {
                    'summary_id': str(summary.id),
                    'model_name': summary.model_name,
                    'narrative_version': summary.narrative_version,
                    'summary_type': summary.summary_type,
                    'delta_summary': narrative_v2.get('delta_summary') if isinstance(narrative_v2, dict) else None,
                },
                'metadata': {'summary_id': str(summary.id)},
            }
        )
    for insight in insights:
        timeline.append({'type': 'insight', 'event_type': 'health_insight', 'event_time': insight.generated_at.isoformat(), 'temporal_type': 'exact', 'start_date': insight.generated_at.date().isoformat(), 'end_date': insight.expires_at.date().isoformat() if insight.expires_at else None, 'label': insight.title, 'title': f'健康洞察：{insight.title}', 'description': insight.summary, 'data': {'insight_type': insight.insight_type, 'severity': insight.severity, 'recommendation': insight.recommendation}, 'metadata': {'insight_id': str(insight.id)}})
    for alert in risk_alerts:
        timeline.append({'type': 'alert', 'event_type': 'risk_alert', 'event_time': alert.created_at.isoformat(), 'temporal_type': 'exact', 'start_date': alert.created_at.date().isoformat(), 'end_date': alert.resolved_at.date().isoformat() if alert.resolved_at else None, 'label': alert.title, 'title': f'風險提醒：{alert.title}', 'description': alert.description or alert.message, 'data': {'risk_type': alert.risk_type, 'severity': alert.severity, 'recommendation': alert.recommendation, 'status': alert.status}, 'metadata': {'alert_id': str(alert.id)}})
    timeline.sort(key=lambda x: x['event_time'], reverse=True)
    return timeline[:limit]


def _uuid_or_raw(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        return value
