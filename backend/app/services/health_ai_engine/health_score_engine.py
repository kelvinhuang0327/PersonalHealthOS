from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import HealthMetric, LabReport, LabReportItem, RiskAlert, SymptomLog
from app.services.health_ai_engine.rule_engine import evaluate_rules, load_rules


def calculate_health_score(db: Session, user_id: str, person_id: str, profile: Any | None, include_legacy: bool, days: int = 30) -> dict[str, Any]:
    user_key = _uuid_or_raw(user_id)
    person_key = _uuid_or_raw(person_id)
    start = datetime.now(timezone.utc) - timedelta(days=days)
    metric_filter = HealthMetric.subject_profile_id == person_key
    alert_filter = RiskAlert.subject_profile_id == person_key
    symptom_filter = SymptomLog.subject_profile_id == person_key
    if include_legacy:
        metric_filter = or_(metric_filter, HealthMetric.subject_profile_id.is_(None))
        alert_filter = or_(alert_filter, RiskAlert.subject_profile_id.is_(None))
        symptom_filter = or_(symptom_filter, SymptomLog.subject_profile_id.is_(None))
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == user_key, HealthMetric.recorded_at >= start, metric_filter)
        .order_by(HealthMetric.recorded_at.desc())
        .all()
    )
    cardio = _score_cardiovascular(metrics)
    metabolic = _score_metabolic(db, user_key, person_key, include_legacy, metrics, start)
    activity = _score_activity(metrics)
    weight = _score_weight(profile, metrics)
    long_term_symptom_count = (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == user_key, symptom_filter, SymptomLog.estimated_duration_days.isnot(None), SymptomLog.estimated_duration_days >= 180)
        .count()
    )
    active_alert_count = (
        db.query(RiskAlert)
        .filter(RiskAlert.user_id == user_key, RiskAlert.status == 'active', alert_filter)
        .count()
    )
    context = {
        'avg_systolic': cardio.get('avg_systolic'),
        'bmi': weight.get('bmi'),
        'alt_above_ref': metabolic.get('alt_above_ref'),
        'long_term_symptom_count': long_term_symptom_count,
        'active_alert_count': active_alert_count,
    }
    penalties, applied_rules = _apply_rule_penalties(load_rules('health_score_rules.yaml') + load_rules('activity_sleep_rules.yaml'), context | activity)
    cardio_score = _clamp_int(round(cardio['score'] - penalties.get('cardiovascular', 0)))
    metabolic_score = _clamp_int(round(metabolic['score'] - penalties.get('metabolic', 0)))
    activity_score = _clamp_int(round(activity['score'] - penalties.get('activity', 0)))
    base_overall = 0.4 * cardio_score + 0.35 * metabolic_score + 0.25 * activity_score
    overall = _clamp_int(round(base_overall - penalties.get('overall', 0)))
    return {
        'source_period_days': days,
        'overall_score': overall,
        'health_score': overall,
        'cardiovascular_score': cardio_score,
        'metabolic_score': metabolic_score,
        'weight_score': weight['score'],
        'sleep_score': activity_score,
        'activity_score': activity_score,
        'lifestyle_score': activity_score,
        'score_detail': {
            'cardiovascular': cardio,
            'metabolic': metabolic,
            'activity': activity,
            'weight': weight,
            'rule_penalties': penalties,
            'applied_rules': applied_rules,
        },
    }


def _score_cardiovascular(metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0
    systolic_values = [m.systolic_bp for m in metrics if m.systolic_bp is not None]
    diastolic_values = [m.diastolic_bp for m in metrics if m.diastolic_bp is not None]
    avg_systolic = _avg(systolic_values)
    avg_diastolic = _avg(diastolic_values)
    if avg_systolic is not None and avg_systolic > 120:
        score -= min(25, (avg_systolic - 120) * 0.8)
    if avg_diastolic is not None and avg_diastolic > 80:
        score -= min(20, (avg_diastolic - 80) * 1.0)
    return {'score': _clamp_int(round(score)), 'avg_systolic': avg_systolic, 'avg_diastolic': avg_diastolic}


def _score_metabolic(db: Session, user_id, person_id, include_legacy: bool, metrics: list[HealthMetric], start: datetime) -> dict[str, Any]:
    score = 100.0
    glucose_values = [float(m.blood_glucose) for m in metrics if m.blood_glucose is not None]
    avg_glucose = _avg(glucose_values)
    if avg_glucose is not None and avg_glucose > 99:
        score -= min(35, (avg_glucose - 99) * 0.8)
    latest_lipids = _latest_lab_values(db, user_id, person_id, include_legacy, start, ['Total Cholesterol', 'LDL', 'HDL', 'Triglycerides', 'ALT'])
    alt_value = latest_lipids.get('ALT')
    if latest_lipids.get('Total Cholesterol') and latest_lipids['Total Cholesterol'] > 200:
        score -= min(15, (latest_lipids['Total Cholesterol'] - 200) * 0.15)
    if latest_lipids.get('LDL') and latest_lipids['LDL'] > 130:
        score -= min(20, (latest_lipids['LDL'] - 130) * 0.25)
    return {'score': _clamp_int(round(score)), 'avg_glucose': avg_glucose, 'latest_lipids': latest_lipids, 'alt_above_ref': bool(alt_value and alt_value > 40)}


def _score_weight(profile: Any | None, metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0
    latest_weight = next((float(m.weight_kg) for m in metrics if m.weight_kg is not None), None)
    bmi = None
    if profile and getattr(profile, 'height_cm', None) and latest_weight is not None:
        height_m = float(profile.height_cm) / 100
        if height_m > 0:
            bmi = latest_weight / (height_m * height_m)
    if bmi is not None:
        if bmi < 18.5:
            score -= min(30, (18.5 - bmi) * 4)
        elif bmi > 24:
            score -= min(35, (bmi - 24) * 4)
    return {'score': _clamp_int(round(score)), 'latest_weight': latest_weight, 'bmi': bmi}


def _score_activity(metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0
    sleep_values = [float(m.sleep_hours) for m in metrics if m.sleep_hours is not None]
    step_values = [float(m.steps) for m in metrics if m.steps is not None]
    avg_sleep = _avg(sleep_values)
    avg_steps = _avg(step_values)
    if avg_sleep is not None and avg_sleep < 7:
        score -= min(40, (7 - avg_sleep) * 12)
    if avg_steps is not None and avg_steps < 5000:
        score -= min(20, (5000 - avg_steps) / 300)
    return {'score': _clamp_int(round(score)), 'avg_sleep_hours': avg_sleep, 'avg_steps': avg_steps}


def _apply_rule_penalties(rules: list[dict[str, Any]], context: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]]]:
    matched = evaluate_rules(rules, context)
    result = {'overall': 0.0, 'cardiovascular': 0.0, 'metabolic': 0.0, 'activity': 0.0}
    applied_rules: list[dict[str, Any]] = []
    for rule in matched:
        output = rule.get('output', {})
        target = output.get('target', 'overall')
        penalty = float(output.get('penalty', 0))
        if 'penalty_per_alert' in output:
            penalty = min(float(output.get('max_penalty', 100)), float(context.get('active_alert_count', 0)) * float(output['penalty_per_alert']))
        result[target] = result.get(target, 0.0) + penalty
        applied_rules.append(
            {
                'rule_id': rule.get('id'),
                'category': rule.get('category'),
                'priority': rule.get('priority', 0),
                'confidence': rule.get('confidence', 0),
                'target': target,
                'penalty': penalty,
            }
        )
    return result, applied_rules


def _latest_lab_values(db: Session, user_id, person_id, include_legacy: bool, start: datetime, names: list[str]) -> dict[str, float | None]:
    report_filter = LabReport.subject_profile_id == person_id
    if include_legacy:
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))
    rows = (
        db.query(LabReportItem)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .filter(
            LabReport.user_id == user_id,
            report_filter,
            LabReport.created_at >= start,
            LabReportItem.item_name.in_(names),
            LabReportItem.value_num.isnot(None),
        )
        .order_by(LabReportItem.captured_at.desc())
        .all()
    )
    result: dict[str, float | None] = {name: None for name in names}
    for row in rows:
        if result.get(row.item_name) is None:
            result[row.item_name] = float(row.value_num)
    return result


def _avg(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _clamp_int(value: int) -> int:
    return max(0, min(100, int(value)))


def _uuid_or_raw(value: str):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return value
