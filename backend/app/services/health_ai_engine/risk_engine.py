from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import AISummary, HealthMetric, LabReport, LabReportItem, RiskAlert, SymptomLog
from app.services.health_ai_engine.guideline_registry import enrich_explainability
from app.services.health_ai_engine.rule_engine import evaluate_rules, load_rules


def generate_risk_alerts(db: Session, user_id: str, person_id: str, include_legacy: bool) -> list[RiskAlert]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    metric_filter = HealthMetric.subject_profile_id == person_key
    symptom_filter = SymptomLog.subject_profile_id == person_key
    report_filter = LabReport.subject_profile_id == person_key
    alert_filter = RiskAlert.subject_profile_id == person_key
    ai_filter = AISummary.subject_profile_id == person_key
    if include_legacy:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
        ai_filter = or_(ai_filter, AISummary.subject_profile_id.is_(None))

    alerts: list[RiskAlert] = []
    alerts.extend(_rules_from_blood_pressure(db, user_key, person_key, metric_filter))
    alerts.extend(_rules_from_bmi(db, user_key, person_key, metric_filter))
    alerts.extend(_rules_from_alt(db, user_key, person_key, report_filter))
    alerts.extend(_rules_from_chronic_symptom(db, user_key, person_key, symptom_filter))
    alerts.extend(_ai_high_risk_keyword_rule(db, user_key, person_key, ai_filter))
    alerts.extend(_external_metric_rule(db, user_key, person_key, metric_filter))

    alerts.sort(key=lambda a: getattr(a, 'priority', 0), reverse=True)
    existing = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == user_key, alert_filter, RiskAlert.status == 'active')
        .all()
    )
    existing_keys = {(a.risk_type, a.description) for a in existing}
    return [a for a in alerts if (a.risk_type, a.description) not in existing_keys]


def list_active_risk_alerts(db: Session, user_id: str, person_id: str, include_legacy: bool, limit: int = 10) -> list[RiskAlert]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    alert_filter = RiskAlert.subject_profile_id == person_key
    if include_legacy:
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
    return (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == user_key, RiskAlert.status == 'active', alert_filter)
        .order_by(RiskAlert.created_at.desc())
        .limit(limit)
        .all()
    )


def _rules_from_blood_pressure(db: Session, user_id, person_id, metric_filter) -> list[RiskAlert]:
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == user_id, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .limit(3)
        .all()
    )
    bp_high_count = sum(1 for m in metrics if (m.systolic_bp or 0) > 140 and (m.diastolic_bp or 0) > 90)
    rule_set = load_rules('blood_pressure_rules.yaml') + load_rules('cardiovascular_rules.yaml')
    matched = evaluate_rules(rule_set, {'bp_high_count': bp_high_count})
    return [_alert_from_rule(rule, user_id, person_id) for rule in matched]


def _rules_from_bmi(db: Session, user_id, person_id, metric_filter) -> list[RiskAlert]:
    latest = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == user_id, metric_filter, HealthMetric.weight_kg.isnot(None))
        .order_by(HealthMetric.recorded_at.desc())
        .first()
    )
    if not latest:
        return []
    bmi = float(latest.weight_kg) / (1.65 * 1.65) if latest.weight_kg else None
    if bmi is None:
        return []
    rule_set = load_rules('bmi_rules.yaml') + load_rules('metabolic_syndrome_rules.yaml')
    matched = evaluate_rules(rule_set, {'bmi': bmi})
    return [_alert_from_rule(rule, user_id, person_id, overrides={'description': f"BMI 約 {bmi:.1f}"}) for rule in matched]


def _rules_from_alt(db: Session, user_id, person_id, report_filter) -> list[RiskAlert]:
    start = datetime.now(timezone.utc) - timedelta(days=365)
    alt_item = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(
            LabReport.user_id == user_id,
            report_filter,
            LabReport.created_at >= start,
            LabReportItem.item_name == 'ALT',
            LabReportItem.value_num.isnot(None),
        )
        .order_by(LabReportItem.captured_at.desc())
        .first()
    )
    if not alt_item:
        return []
    value = float(alt_item.value_num)
    ref_high = float(alt_item.ref_high) if alt_item.ref_high is not None else 40.0
    uric_item = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(
            LabReport.user_id == user_id,
            report_filter,
            LabReport.created_at >= start,
            LabReportItem.item_name.in_(['Uric Acid', 'UricAcid']),
            LabReportItem.value_num.isnot(None),
        )
        .order_by(LabReportItem.captured_at.desc())
        .first()
    )
    uric_value = float(uric_item.value_num) if uric_item and uric_item.value_num is not None else None
    uric_ref = float(uric_item.ref_high) if uric_item and uric_item.ref_high is not None else 7.0
    rule_set = load_rules('metabolic_rules.yaml') + load_rules('liver_function_rules.yaml') + load_rules('uric_acid_gout_rules.yaml')
    matched = evaluate_rules(rule_set, {'alt_above_ref': value > ref_high, 'uric_acid_above_ref': bool(uric_value and uric_value > uric_ref)})
    result: list[RiskAlert] = []
    for rule in matched:
        output = rule.get('output', {})
        if output.get('risk_type') == 'uric_acid_high':
            result.append(_alert_from_rule(rule, user_id, person_id, overrides={'description': f'尿酸 {uric_value:.1f} 高於上限 {uric_ref:.1f}'}))
        else:
            result.append(_alert_from_rule(rule, user_id, person_id, overrides={'description': f'ALT {value:.1f} 高於上限 {ref_high:.1f}'}))
    return result


def _rules_from_chronic_symptom(db: Session, user_id, person_id, symptom_filter) -> list[RiskAlert]:
    max_days = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == user_id, symptom_filter, SymptomLog.estimated_duration_days.isnot(None))
        .order_by(SymptomLog.estimated_duration_days.desc())
        .first()
    )
    max_estimated_duration_days = int(max_days.estimated_duration_days) if max_days and max_days.estimated_duration_days else 0
    matched = evaluate_rules(load_rules('chronic_symptom_rules.yaml'), {'max_estimated_duration_days': max_estimated_duration_days})
    return [_alert_from_rule(rule, user_id, person_id, overrides={'description': f'症狀持續約 {max_estimated_duration_days} 天'}) for rule in matched]


def _ai_high_risk_keyword_rule(db: Session, user_id, person_id, ai_filter) -> list[RiskAlert]:
    latest: Optional[AISummary] = (
        db.query(AISummary)
        .filter(AISummary.user_id == user_id, ai_filter)
        .order_by(AISummary.created_at.desc())
        .first()
    )
    if not latest:
        return []
    text = (latest.summary_text or '') + ' ' + (latest.abnormal_explanation or '')
    if '高風險' not in text and '持續異常' not in text:
        return []
    return [
        _alert(
            user_id,
            person_id,
            'ai_summary_high_risk',
            'warning',
            'AI 摘要提示風險',
            'AI 健康摘要顯示高風險或持續異常關鍵訊號',
            '建議儘速與專業醫療人員討論',
        )
    ]


def _external_metric_rule(db: Session, user_id, person_id, metric_filter) -> list[RiskAlert]:
    start = datetime.now(timezone.utc) - timedelta(days=14)
    count = (
        db.query(HealthMetric)
        .filter(
            HealthMetric.user_id == user_id,
            metric_filter,
            HealthMetric.source == 'external_api',
            HealthMetric.recorded_at >= start,
        )
        .count()
    )
    if count == 0:
        return []
    return [
        _alert(
            user_id,
            person_id,
            'external_metrics_active',
            'info',
            '外部指標已同步',
            f'近兩週已同步 {count} 筆外部健康指標',
            '建議持續同步以強化分析準確性',
        )
    ]


def _alert_from_rule(rule: dict, user_id, person_id, overrides: dict | None = None) -> RiskAlert:
    output = rule.get('output', {})
    overrides = overrides or {}
    alert = _alert(
        user_id=user_id,
        person_id=person_id,
        risk_type=output.get('risk_type', rule.get('id', 'rule_alert')),
        severity=output.get('severity', rule.get('severity', 'warning')),
        title=output.get('title', '健康風險'),
        description=overrides.get('description', output.get('description', '偵測到風險條件')),
        recommendation=output.get('recommendation', '建議持續追蹤並視情況就醫。'),
    )
    explain = rule.get('_explainability', {})
    explain = enrich_explainability(explain)
    alert.rule_id = explain.get('rule_id')
    alert.category = explain.get('category')
    alert.priority = explain.get('priority', 0)
    alert.confidence = explain.get('confidence', 0)
    alert.evidence_level = explain.get('evidence_level', 'B')
    alert.guideline_source = explain.get('guideline_source')
    alert.guideline_version = explain.get('guideline_version')
    return alert


def _alert(user_id, person_id, risk_type: str, severity: str, title: str, description: str, recommendation: str) -> RiskAlert:
    return RiskAlert(
        user_id=user_id,
        subject_profile_id=person_id,
        risk_type=risk_type,
        source_type='risk_monitor',
        source_id=None,
        rule_code=risk_type.upper(),
        severity=severity,
        title=title,
        message=description,
        description=description,
        recommendation=recommendation,
        status='active',
    )


def _uuid_or_raw(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        return value
