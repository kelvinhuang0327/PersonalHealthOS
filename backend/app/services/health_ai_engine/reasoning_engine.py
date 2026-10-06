from __future__ import annotations

from typing import Any


def generate_reasoning_summary(
    timeline_events: list[dict[str, Any]],
    risk_alerts: list[Any],
    health_score: dict[str, Any],
    insights: list[Any],
    metrics: list[Any],
) -> dict[str, Any]:
    avg_sys = _avg([float(m.systolic_bp) for m in metrics if getattr(m, 'systolic_bp', None) is not None][:7])
    avg_steps = _avg([float(m.steps) for m in metrics if getattr(m, 'steps', None) is not None][:7])
    score = health_score.get('overall_score') or health_score.get('health_score')
    parts = []
    if avg_sys is not None:
        parts.append(f'過去期間平均收縮壓約 {avg_sys:.1f}')
    if avg_steps is not None:
        parts.append(f'平均步數約 {avg_steps:.0f}')
    if score is not None:
        parts.append(f'健康分數約 {score}')
    if risk_alerts:
        parts.append(f'目前有 {len(risk_alerts)} 筆風險警示')
    if insights:
        parts.append(f'已生成 {len(insights)} 筆洞察')
    summary = '，'.join(parts) if parts else '資料不足，無法產生可靠推論。'
    if timeline_events:
        summary += f'；時間序列事件共 {len(timeline_events)} 筆。'
    return {
        'summary': summary,
        'rule_id': 'reasoning_v3_multisource',
        'category': 'reasoning',
        'priority': 8,
        'confidence': 0.7,
        'evidence_level': 'B',
        'guideline_source': 'Clinical Safety Reasoning',
        'guideline_version': 'v1',
    }


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
