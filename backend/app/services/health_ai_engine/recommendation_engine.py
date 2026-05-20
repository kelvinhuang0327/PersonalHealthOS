from __future__ import annotations

from typing import Any

from app.services.health_ai_engine.confidence_engine import combine_confidence
from app.services.health_ai_engine.guideline_registry import resolve_guideline
from app.services.health_ai_engine.safety_guardrail import MEDICAL_DISCLAIMER


def generate_recommendations(
    clinical_labels: list[dict[str, Any]],
    risk_level: str,
    active_alerts: list[Any],
    calibrated_confidence: float = 0.75,
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if any(str(label.get('label', '')).startswith('BP:hypertension') for label in clinical_labels):
        recs.append(_rec('lifestyle', '減少鈉攝取並每週監測血壓至少 3 次', 10, 0.9, 'ACC/AHA', 'A', calibrated_confidence))
    if any(str(label.get('label', '')).startswith('BMI:overweight') or str(label.get('label', '')).startswith('BMI:obese') for label in clinical_labels):
        recs.append(_rec('lifestyle', '建議每週至少 150 分鐘中等強度運動並控制熱量', 8, 0.85, 'WHO', 'A', calibrated_confidence))
    if any(str(label.get('label', '')).startswith('UricAcid:high') for label in clinical_labels):
        recs.append(_rec('monitoring', '建議減少高普林飲食並追蹤尿酸', 7, 0.82, 'Hyperuricemia Standard', 'B', calibrated_confidence))
    if risk_level in {'moderate', 'high'} or active_alerts:
        recs.append(_rec('follow_up', '建議 1-3 個月內安排門診追蹤', 9, 0.88, 'Clinical Follow-up Guidance', 'A', calibrated_confidence))
    if not recs:
        recs.append(_rec('lifestyle', '維持規律作息與運動，並定期健康檢查', 5, 0.75, 'General Preventive Guidance', 'B', calibrated_confidence))
    recs.sort(key=lambda x: x['priority'], reverse=True)
    return recs


def _rec(
    kind: str,
    text: str,
    priority: int,
    confidence: float,
    guideline_source: str,
    evidence_level: str,
    calibrated_confidence: float,
) -> dict[str, Any]:
    guideline = resolve_guideline(guideline_source)
    return {
        'type': kind,
        'text': text,
        'recommendation': text,
        'rule_id': f'recommendation_{kind}',
        'category': 'recommendation',
        'priority': priority,
        'confidence': combine_confidence(calibrated_confidence, confidence),
        'evidence_level': evidence_level,
        'medical_disclaimer': MEDICAL_DISCLAIMER,
        **guideline,
    }
