from __future__ import annotations

from typing import Any


def generate_predictive_insights(metrics: list[Any], alerts: list[Any]) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    predictions.extend(_bp_trend(metrics))
    predictions.extend(_weight_trend(metrics))
    predictions.extend(_risk_probability(alerts))
    predictions.sort(key=lambda p: p['priority'], reverse=True)
    return predictions


def _bp_trend(metrics: list[Any]) -> list[dict[str, Any]]:
    values = [float(m.systolic_bp) for m in metrics if getattr(m, 'systolic_bp', None) is not None][:7]
    if len(values) < 3:
        return []
    slope = values[0] - values[-1]
    direction = '上升' if slope > 0 else '下降'
    return [
        {
            'type': 'predictive',
            'title': '血壓趨勢預測',
            'summary': f'短期收縮壓呈{direction}趨勢，變化約 {abs(slope):.1f} mmHg。',
            'rule_id': 'prediction_bp_linear',
            'category': 'cardiovascular',
            'priority': 8,
            'confidence': 0.78,
            'evidence_level': 'C',
            'guideline_source': 'Linear Trend Prediction',
            'guideline_version': 'v1',
        }
    ]


def _weight_trend(metrics: list[Any]) -> list[dict[str, Any]]:
    values = [float(m.weight_kg) for m in metrics if getattr(m, 'weight_kg', None) is not None][:14]
    if len(values) < 3:
        return []
    slope = values[0] - values[-1]
    return [
        {
            'type': 'predictive',
            'title': '體重變化預測',
            'summary': f'近期體重趨勢變化約 {slope:+.1f} kg。',
            'rule_id': 'prediction_weight_linear',
            'category': 'metabolic',
            'priority': 6,
            'confidence': 0.72,
            'evidence_level': 'C',
            'guideline_source': 'Linear Trend Prediction',
            'guideline_version': 'v1',
        }
    ]


def _risk_probability(alerts: list[Any]) -> list[dict[str, Any]]:
    if not alerts:
        return []
    prob = min(0.95, 0.25 + len(alerts) * 0.08)
    return [
        {
            'type': 'predictive',
            'title': '風險上升機率預測',
            'summary': f'未來風險上升機率估計約 {prob * 100:.0f}%。',
            'rule_id': 'prediction_risk_probability',
            'category': 'risk',
            'priority': 9,
            'confidence': 0.75,
            'evidence_level': 'C',
            'guideline_source': 'Rolling Risk Probability',
            'guideline_version': 'v1',
        }
    ]
