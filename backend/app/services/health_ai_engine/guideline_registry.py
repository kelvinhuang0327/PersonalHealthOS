from __future__ import annotations

from typing import Any


GUIDELINE_REGISTRY: dict[str, dict[str, str]] = {
    'ACC/AHA': {'guideline_source': 'ACC/AHA 2017 Hypertension', 'guideline_version': '2017'},
    'WHO': {'guideline_source': 'WHO BMI Classification', 'guideline_version': '2004'},
    'ADA': {'guideline_source': 'ADA Diabetes Risk', 'guideline_version': '2024'},
    'ACG': {'guideline_source': 'ACG Liver Function', 'guideline_version': '2022'},
    'Hyperuricemia Standard': {'guideline_source': 'Hyperuricemia Standard', 'guideline_version': '2023'},
    'Clinical Follow-up Guidance': {'guideline_source': 'Clinical Follow-up Guidance', 'guideline_version': '1.0'},
    'General Preventive Guidance': {'guideline_source': 'General Preventive Guidance', 'guideline_version': '1.0'},
    'Rule Library': {'guideline_source': 'Health Rule Library', 'guideline_version': 'v2'},
    'Statistical Anomaly Detection': {'guideline_source': 'Statistical Anomaly Detection', 'guideline_version': 'v1'},
    'Linear Trend Prediction': {'guideline_source': 'Linear Trend Prediction', 'guideline_version': 'v1'},
    'Rolling Risk Probability': {'guideline_source': 'Rolling Risk Probability', 'guideline_version': 'v1'},
    'Clinical Safety Reasoning': {'guideline_source': 'Clinical Safety Reasoning', 'guideline_version': 'v1'},
    'Composite Clinical Rules': {'guideline_source': 'Composite Clinical Rules', 'guideline_version': 'v1'},
    'Weighted Clinical Scoring': {'guideline_source': 'Weighted Clinical Scoring', 'guideline_version': 'v1'},
}


def resolve_guideline(guideline_source: str | None) -> dict[str, str]:
    key = guideline_source or 'Rule Library'
    return GUIDELINE_REGISTRY.get(key, {'guideline_source': key, 'guideline_version': '1.0'})


def enrich_explainability(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    meta = resolve_guideline(str(out.get('guideline_source') or 'Rule Library'))
    out.update(meta)
    out['evidence_level'] = out.get('evidence_level', 'B')
    return out
