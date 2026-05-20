from __future__ import annotations

from typing import Any


def detect_anomalies(metrics: list[Any], lab_items: list[Any] | None = None) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    lab_items = lab_items or []
    anomalies.extend(_bp_spike(metrics))
    anomalies.extend(_weight_change(metrics))
    anomalies.extend(_alt_spike(lab_items))
    return anomalies


def _bp_spike(metrics: list[Any]) -> list[dict[str, Any]]:
    systolic = [float(m.systolic_bp) for m in metrics if getattr(m, 'systolic_bp', None) is not None][:7]
    if len(systolic) < 4:
        return []
    baseline = sum(systolic[1:]) / (len(systolic) - 1)
    latest = systolic[0]
    if latest <= baseline + 15:
        return []
    return [
        {
            'type': 'anomaly',
            'metric': 'systolic_bp',
            'title': '血壓短期上升異常',
            'summary': f'最新收縮壓 {latest:.1f} 明顯高於近期平均 {baseline:.1f}。',
            'rule_id': 'anomaly_bp_spike',
            'category': 'cardiovascular',
            'priority': 9,
            'confidence': 0.86,
            'evidence_level': 'B',
            'guideline_source': 'Statistical Anomaly Detection',
            'guideline_version': 'v1',
        }
    ]


def _weight_change(metrics: list[Any]) -> list[dict[str, Any]]:
    weights = [float(m.weight_kg) for m in metrics if getattr(m, 'weight_kg', None) is not None][:14]
    if len(weights) < 4:
        return []
    latest = weights[0]
    base = sum(weights[1:4]) / 3
    if abs(latest - base) < 2.0:
        return []
    return [
        {
            'type': 'anomaly',
            'metric': 'weight_kg',
            'title': '體重短期變化異常',
            'summary': f'體重短期變化 {latest - base:+.1f} kg。',
            'rule_id': 'anomaly_weight_shift',
            'category': 'metabolic',
            'priority': 7,
            'confidence': 0.8,
            'evidence_level': 'B',
            'guideline_source': 'Statistical Anomaly Detection',
            'guideline_version': 'v1',
        }
    ]


def _alt_spike(lab_items: list[Any]) -> list[dict[str, Any]]:
    alt_values = [float(i.value_num) for i in lab_items if getattr(i, 'item_name', '') == 'ALT' and getattr(i, 'value_num', None) is not None][:5]
    if len(alt_values) < 2:
        return []
    if alt_values[0] <= alt_values[1] + 10:
        return []
    return [
        {
            'type': 'anomaly',
            'metric': 'ALT',
            'title': 'ALT 異常上升',
            'summary': f'ALT 近期由 {alt_values[1]:.1f} 升至 {alt_values[0]:.1f}。',
            'rule_id': 'anomaly_alt_spike',
            'category': 'liver',
            'priority': 8,
            'confidence': 0.83,
            'evidence_level': 'B',
            'guideline_source': 'Statistical Anomaly Detection',
            'guideline_version': 'v1',
        }
    ]
