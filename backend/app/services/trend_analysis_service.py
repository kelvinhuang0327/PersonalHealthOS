from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import HealthMetric


TREND_FIELDS = {
    'blood_pressure_systolic': 'systolic_bp',
    'weight': 'weight_kg',
    'blood_glucose': 'blood_glucose',
}


def analyze_health_trends(db: Session, user_id: str, person_id: str, include_legacy: bool, days: int = 90) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    person_filter = HealthMetric.subject_profile_id == person_id
    if include_legacy:
        person_filter = or_(person_filter, HealthMetric.subject_profile_id.is_(None))
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.user_id == user_id, HealthMetric.recorded_at >= start, person_filter)
        .order_by(HealthMetric.recorded_at.asc())
        .all()
    )

    summaries: list[dict[str, Any]] = []
    for metric_name, field in TREND_FIELDS.items():
        series = [(m.recorded_at, float(getattr(m, field))) for m in metrics if getattr(m, field) is not None]
        summaries.append(_summarize_series(metric_name, series))

    return summaries


def _summarize_series(metric: str, series: list[tuple[datetime, float]]) -> dict[str, Any]:
    if not series:
        return {
            'metric': metric,
            'points': 0,
            'first_value': None,
            'last_value': None,
            'change_percent': None,
            'slope_per_day': None,
            'direction': 'no_data',
        }

    first_time, first_value = series[0]
    last_time, last_value = series[-1]

    change_percent = None
    if abs(first_value) > 1e-9:
        change_percent = ((last_value - first_value) / abs(first_value)) * 100

    day_span = max((last_time - first_time).total_seconds() / 86400, 1e-9)
    slope_per_day = (last_value - first_value) / day_span if len(series) > 1 else 0.0

    direction = 'stable'
    if change_percent is not None:
        if change_percent > 2:
            direction = 'up'
        elif change_percent < -2:
            direction = 'down'

    return {
        'metric': metric,
        'points': len(series),
        'first_value': round(first_value, 3),
        'last_value': round(last_value, 3),
        'change_percent': round(change_percent, 3) if change_percent is not None else None,
        'slope_per_day': round(slope_per_day, 4),
        'direction': direction,
    }
