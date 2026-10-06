from __future__ import annotations

from typing import Any


def calculate_clinical_scores(metrics: list[Any], lab_items: list[Any]) -> dict[str, Any]:
    cv = 100.0
    metabolic = 100.0
    latest = metrics[0] if metrics else None
    if latest and getattr(latest, 'systolic_bp', None) is not None:
        cv -= max(0, (float(latest.systolic_bp) - 120) * 0.6)
    if latest and getattr(latest, 'diastolic_bp', None) is not None:
        cv -= max(0, (float(latest.diastolic_bp) - 80) * 0.7)
    if latest and getattr(latest, 'weight_kg', None) is not None:
        bmi = float(latest.weight_kg) / (1.65 * 1.65)
        metabolic -= max(0, (bmi - 24) * 3.0)
    alt = _latest(lab_items, 'ALT')
    if alt is not None and alt > 40:
        metabolic -= min(20, (alt - 40) * 0.4)
    uric = _latest(lab_items, 'Uric Acid') or _latest(lab_items, 'UricAcid')
    if uric is not None and uric > 7:
        metabolic -= min(15, (uric - 7) * 2.0)
    return {
        'cardiovascular_risk_score': _clamp(cv),
        'metabolic_risk_score': _clamp(metabolic),
        'rule_id': 'clinical_weighted_score_v4',
        'category': 'clinical_score',
        'priority': 9,
        'confidence': 0.8,
        'evidence_level': 'B',
        'guideline_source': 'Weighted Clinical Scoring',
        'guideline_version': 'v1',
    }


def _latest(lab_items: list[Any], item_name: str) -> float | None:
    for item in lab_items:
        if getattr(item, 'item_name', None) == item_name and getattr(item, 'value_num', None) is not None:
            return float(item.value_num)
    return None


def _clamp(v: float) -> int:
    return max(0, min(100, int(round(v))))
