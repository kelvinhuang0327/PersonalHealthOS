from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import HealthMetric, LabReport, LabReportItem, PersonProfile, RiskAlert
from app.services.health_ai_engine.health_score_engine import calculate_health_score as calculate_health_score_with_engine


def calculate_health_score(
    db: Session,
    user_id: str,
    person_id: str,
    profile: PersonProfile | None,
    include_legacy: bool,
    days: int = 30,
) -> dict[str, Any]:
    return calculate_health_score_with_engine(db, user_id, person_id, profile, include_legacy, days=days)


def _score_cardiovascular(metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0

    systolic_values = [m.systolic_bp for m in metrics if m.systolic_bp is not None]
    diastolic_values = [m.diastolic_bp for m in metrics if m.diastolic_bp is not None]
    hr_values = [m.heart_rate for m in metrics if m.heart_rate is not None]

    avg_systolic = _avg(systolic_values)
    avg_diastolic = _avg(diastolic_values)
    avg_hr = _avg(hr_values)

    penalties: list[dict[str, Any]] = []

    if avg_systolic is not None and avg_systolic > 120:
        p = min(25, (avg_systolic - 120) * 0.8)
        score -= p
        penalties.append({'factor': 'avg_systolic', 'penalty': round(p, 2), 'value': round(avg_systolic, 2)})

    if avg_diastolic is not None and avg_diastolic > 80:
        p = min(20, (avg_diastolic - 80) * 1.0)
        score -= p
        penalties.append({'factor': 'avg_diastolic', 'penalty': round(p, 2), 'value': round(avg_diastolic, 2)})

    if avg_hr is not None:
        if avg_hr > 100:
            p = min(20, (avg_hr - 100) * 0.5)
            score -= p
            penalties.append({'factor': 'avg_heart_rate_high', 'penalty': round(p, 2), 'value': round(avg_hr, 2)})
        elif avg_hr < 55:
            p = min(20, (55 - avg_hr) * 0.6)
            score -= p
            penalties.append({'factor': 'avg_heart_rate_low', 'penalty': round(p, 2), 'value': round(avg_hr, 2)})

    return {
        'score': _clamp_int(round(score)),
        'avg_systolic': round(avg_systolic, 2) if avg_systolic is not None else None,
        'avg_diastolic': round(avg_diastolic, 2) if avg_diastolic is not None else None,
        'avg_heart_rate': round(avg_hr, 2) if avg_hr is not None else None,
        'penalties': penalties,
    }


def _score_metabolic(
    db: Session,
    user_id: str,
    person_id: str,
    include_legacy: bool,
    metrics: list[HealthMetric],
    start: datetime,
) -> dict[str, Any]:
    score = 100.0
    penalties: list[dict[str, Any]] = []

    glucose_values = [float(m.blood_glucose) for m in metrics if m.blood_glucose is not None]
    avg_glucose = _avg(glucose_values)

    if avg_glucose is not None and avg_glucose > 99:
        p = min(35, (avg_glucose - 99) * 0.8)
        score -= p
        penalties.append({'factor': 'avg_glucose', 'penalty': round(p, 2), 'value': round(avg_glucose, 2)})

    latest_lipids = _latest_lab_values(
        db,
        user_id,
        person_id,
        include_legacy,
        start,
        ['Total Cholesterol', 'LDL', 'HDL', 'Triglycerides'],
    )

    tc = latest_lipids.get('Total Cholesterol')
    ldl = latest_lipids.get('LDL')
    hdl = latest_lipids.get('HDL')
    tg = latest_lipids.get('Triglycerides')

    if tc is not None and tc > 200:
        p = min(15, (tc - 200) * 0.15)
        score -= p
        penalties.append({'factor': 'total_cholesterol', 'penalty': round(p, 2), 'value': round(tc, 2)})

    if ldl is not None and ldl > 130:
        p = min(20, (ldl - 130) * 0.25)
        score -= p
        penalties.append({'factor': 'ldl', 'penalty': round(p, 2), 'value': round(ldl, 2)})

    if hdl is not None and hdl < 40:
        p = min(15, (40 - hdl) * 0.6)
        score -= p
        penalties.append({'factor': 'hdl', 'penalty': round(p, 2), 'value': round(hdl, 2)})

    if tg is not None and tg > 150:
        p = min(15, (tg - 150) * 0.12)
        score -= p
        penalties.append({'factor': 'triglycerides', 'penalty': round(p, 2), 'value': round(tg, 2)})

    return {
        'score': _clamp_int(round(score)),
        'avg_glucose': round(avg_glucose, 2) if avg_glucose is not None else None,
        'latest_lipids': latest_lipids,
        'penalties': penalties,
    }


def _score_weight(profile: PersonProfile | None, metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0
    penalties: list[dict[str, Any]] = []

    latest_weight = None
    for metric in metrics:
        if metric.weight_kg is not None:
            latest_weight = float(metric.weight_kg)
            break

    bmi = None
    if profile and profile.height_cm and latest_weight is not None:
        height_m = float(profile.height_cm) / 100
        if height_m > 0:
            bmi = latest_weight / (height_m * height_m)

    if bmi is not None:
        if bmi < 18.5:
            p = min(30, (18.5 - bmi) * 4)
            score -= p
            penalties.append({'factor': 'bmi_low', 'penalty': round(p, 2), 'value': round(bmi, 2)})
        elif bmi > 24:
            p = min(35, (bmi - 24) * 4)
            score -= p
            penalties.append({'factor': 'bmi_high', 'penalty': round(p, 2), 'value': round(bmi, 2)})

    return {
        'score': _clamp_int(round(score)),
        'latest_weight': latest_weight,
        'bmi': round(bmi, 2) if bmi is not None else None,
        'penalties': penalties,
    }


def _score_sleep(metrics: list[HealthMetric]) -> dict[str, Any]:
    score = 100.0
    penalties: list[dict[str, Any]] = []

    sleep_values = [float(m.sleep_hours) for m in metrics if m.sleep_hours is not None]
    avg_sleep = _avg(sleep_values)

    if avg_sleep is not None:
        if avg_sleep < 7:
            p = min(40, (7 - avg_sleep) * 12)
            score -= p
            penalties.append({'factor': 'sleep_short', 'penalty': round(p, 2), 'value': round(avg_sleep, 2)})
        elif avg_sleep > 9:
            p = min(20, (avg_sleep - 9) * 10)
            score -= p
            penalties.append({'factor': 'sleep_long', 'penalty': round(p, 2), 'value': round(avg_sleep, 2)})

    return {
        'score': _clamp_int(round(score)),
        'avg_sleep_hours': round(avg_sleep, 2) if avg_sleep is not None else None,
        'penalties': penalties,
    }


def _latest_lab_values(
    db: Session,
    user_id: str,
    person_id: str,
    include_legacy: bool,
    start: datetime,
    names: list[str],
) -> dict[str, float | None]:
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
    if not values:
        return None
    return sum(values) / len(values)


def _clamp_int(value: int) -> int:
    return max(0, min(100, int(value)))
