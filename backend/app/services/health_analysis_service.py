from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.constants import MEDICAL_DISCLAIMER


def build_health_analysis(person_id: str, metrics: list[Any], symptoms: list[Any], lab_items: list[Any], alerts: list[Any]) -> dict[str, Any]:
    has_data = bool(metrics or symptoms or lab_items)
    if not has_data:
        return {
            'person_id': person_id,
            'analyzed_at': datetime.now(timezone.utc),
            'data_sufficient': False,
            'abnormal_indicators': [],
            'long_term_symptoms': [],
            'potential_risks': ['資料不足，無法提供可靠分析。'],
            'follow_up_items': ['請先補充近期症狀、健檢報告或身體指數資料。'],
            'recommendations': ['完成至少一筆症狀與一筆身體指數後再分析。'],
            'disclaimer': MEDICAL_DISCLAIMER,
        }

    abnormal_indicators = [f'{item.item_name}: {item.abnormal_flag}' for item in lab_items if item.abnormal_flag in {'H', 'L'}]
    potential_risks = [f'{alert.title} - {alert.message}' for alert in alerts[:5]]
    long_term_symptoms = [s for s in symptoms if getattr(s, 'estimated_duration_days', None) and s.estimated_duration_days >= 180]
    long_term_symptom_texts = [f"{s.symptom}（約 {s.estimated_duration_days} 天）" for s in long_term_symptoms]
    if long_term_symptoms:
        potential_risks.append('存在中長期症狀，建議結合健檢與追蹤評估。')
    if not potential_risks and abnormal_indicators:
        potential_risks = ['檢驗值出現異常旗標，需持續追蹤。']
    if not potential_risks:
        potential_risks = ['目前未偵測到明顯高風險訊號。']

    follow_up_items = [f'追蹤症狀：{symptom.symptom}' for symptom in symptoms[:3]]
    for symptom in long_term_symptoms[:3]:
        follow_up_items.append(f'長期症狀追蹤：{symptom.symptom}（約 {symptom.estimated_duration_days} 天）')

    external_metrics = [m for m in metrics if getattr(m, 'source', None) == 'external_api']
    if external_metrics:
        follow_up_items.append(f'外部指標資料 {len(external_metrics)} 筆，建議持續同步觀察趨勢。')
    if not follow_up_items:
        follow_up_items = ['每 1-2 週持續記錄血壓、心率、血糖或睡眠。']

    recommendations = [
        '維持規律作息與均衡飲食。',
        '若異常指標持續，請儘速諮詢醫療專業人員。',
    ]

    return {
        'person_id': person_id,
        'analyzed_at': datetime.now(timezone.utc),
        'data_sufficient': True,
        'abnormal_indicators': abnormal_indicators[:10],
        'long_term_symptoms': long_term_symptom_texts[:10],
        'potential_risks': potential_risks[:10],
        'follow_up_items': follow_up_items[:10],
        'recommendations': recommendations,
        'disclaimer': MEDICAL_DISCLAIMER,
    }
