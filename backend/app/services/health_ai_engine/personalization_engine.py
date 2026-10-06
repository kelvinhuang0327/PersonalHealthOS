from __future__ import annotations

from typing import Any


def build_personalized_context(metrics: list[Any]) -> dict[str, Any]:
    systolic = [float(m.systolic_bp) for m in metrics if getattr(m, 'systolic_bp', None) is not None]
    diastolic = [float(m.diastolic_bp) for m in metrics if getattr(m, 'diastolic_bp', None) is not None]
    weight = [float(m.weight_kg) for m in metrics if getattr(m, 'weight_kg', None) is not None]
    steps = [float(m.steps) for m in metrics if getattr(m, 'steps', None) is not None]
    sleep = [float(m.sleep_hours) for m in metrics if getattr(m, 'sleep_hours', None) is not None]
    return {
        'baseline_metrics': {
            'avg_systolic_bp': _avg(systolic),
            'avg_diastolic_bp': _avg(diastolic),
            'avg_weight_kg': _avg(weight),
            'avg_steps': _avg(steps),
            'avg_sleep_hours': _avg(sleep),
        }
    }


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)
