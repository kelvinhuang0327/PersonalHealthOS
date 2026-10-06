from __future__ import annotations

from typing import Any


def stratify_risk_level(
    metrics: list[Any],
    lab_items: list[Any],
    long_term_symptom_count: int,
    active_alert_count: int,
) -> dict[str, Any]:
    score = 0
    latest = metrics[0] if metrics else None
    if latest and getattr(latest, 'systolic_bp', 0) and float(latest.systolic_bp) >= 140:
        score += 2
    if latest and getattr(latest, 'weight_kg', None) is not None:
        bmi = float(latest.weight_kg) / (1.65 * 1.65)
        if bmi >= 30:
            score += 2
        elif bmi >= 27:
            score += 1
    if _alt_high(lab_items):
        score += 1
    if _uric_high(lab_items):
        score += 1
    if long_term_symptom_count > 0:
        score += 1
    score += min(3, active_alert_count)
    level = 'low'
    if score >= 6:
        level = 'high'
    elif score >= 3:
        level = 'moderate'
    return {
        'risk_level': level,
        'rule_id': 'risk_stratification_v4',
        'category': 'risk',
        'priority': 10,
        'confidence': 0.82,
        'evidence_level': 'B',
        'guideline_source': 'Composite Clinical Rules',
        'guideline_version': 'v1',
    }


def _alt_high(lab_items: list[Any]) -> bool:
    for item in lab_items:
        if getattr(item, 'item_name', None) == 'ALT' and getattr(item, 'value_num', None) is not None:
            ref = float(item.ref_high) if getattr(item, 'ref_high', None) is not None else 40.0
            return float(item.value_num) > ref
    return False


def _uric_high(lab_items: list[Any]) -> bool:
    for item in lab_items:
        if getattr(item, 'item_name', None) in {'Uric Acid', 'UricAcid'} and getattr(item, 'value_num', None) is not None:
            ref = float(item.ref_high) if getattr(item, 'ref_high', None) is not None else 7.0
            return float(item.value_num) > ref
    return False
