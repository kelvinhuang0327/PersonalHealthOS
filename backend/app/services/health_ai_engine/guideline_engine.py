from __future__ import annotations

from typing import Any

from app.services.health_ai_engine.guideline_registry import resolve_guideline


def derive_clinical_labels(metrics: list[Any], lab_items: list[Any]) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    latest = metrics[0] if metrics else None
    if latest and getattr(latest, 'systolic_bp', None) is not None and getattr(latest, 'diastolic_bp', None) is not None:
        sbp = float(latest.systolic_bp)
        dbp = float(latest.diastolic_bp)
        if sbp < 120 and dbp < 80:
            level = 'normal'
        elif sbp < 140 and dbp < 90:
            level = 'elevated'
        else:
            level = 'hypertension'
        labels.append(
            {
                'label': f'BP:{level}',
                'value': f'{int(sbp)}/{int(dbp)}',
                'rule_id': 'guideline_bp_acc_aha',
                'category': 'cardiovascular',
                'priority': 10,
                'confidence': 0.9,
                'evidence_level': 'A',
                **resolve_guideline('ACC/AHA'),
            }
        )
    if latest and getattr(latest, 'weight_kg', None) is not None:
        bmi = _estimate_bmi(float(latest.weight_kg))
        if bmi < 18.5:
            cls = 'underweight'
        elif bmi < 25:
            cls = 'normal'
        elif bmi < 30:
            cls = 'overweight'
        else:
            cls = 'obese'
        labels.append(
            {
                'label': f'BMI:{cls}',
                'value': round(bmi, 2),
                'rule_id': 'guideline_bmi_who',
                'category': 'metabolic',
                'priority': 8,
                'confidence': 0.85,
                'evidence_level': 'A',
                **resolve_guideline('WHO'),
            }
        )
    glucose = _latest_lab_value(lab_items, {'Glucose', 'Fasting Glucose'})
    if glucose is not None:
        risk = 'high' if glucose >= 126 else 'moderate' if glucose >= 100 else 'low'
        labels.append(
            {
                'label': f'DM-risk:{risk}',
                'value': glucose,
                'rule_id': 'guideline_dm_ada',
                'category': 'metabolic',
                'priority': 9,
                'confidence': 0.82,
                'evidence_level': 'A',
                **resolve_guideline('ADA'),
            }
        )
    uric = _latest_lab_value(lab_items, {'Uric Acid', 'UricAcid'})
    if uric is not None and uric >= 7.0:
        labels.append(
            {
                'label': 'UricAcid:high',
                'value': uric,
                'rule_id': 'guideline_uric_acid',
                'category': 'gout',
                'priority': 7,
                'confidence': 0.8,
                'evidence_level': 'B',
                **resolve_guideline('Hyperuricemia Standard'),
            }
        )
    labels.sort(key=lambda x: x['priority'], reverse=True)
    return labels


def _latest_lab_value(lab_items: list[Any], names: set[str]) -> float | None:
    for item in lab_items:
        if getattr(item, 'item_name', None) in names and getattr(item, 'value_num', None) is not None:
            return float(item.value_num)
    return None


def _estimate_bmi(weight_kg: float) -> float:
    return weight_kg / (1.65 * 1.65)
