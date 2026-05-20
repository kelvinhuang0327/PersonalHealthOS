from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.health_ai_engine.insight_engine import generate_health_narrative_v2


def test_health_narrative_v2_outputs_delta_and_tracking_fields():
    now = datetime.now(timezone.utc)
    previous_narrative = {
        'summary': '上週你的健康風險偏中度。',
        'created_at': (now - timedelta(days=5)).isoformat(),
        'overall_score': 60,
    }

    narrative = generate_health_narrative_v2(
        {
            'health_score': {'overall_score': 66, 'components': {'cardiovascular': 61}},
            'risk_level': 'moderate',
            'alerts': [SimpleNamespace(title='血壓偏高', description='近期血壓仍偏高', severity='warning')],
            'insights': [SimpleNamespace(title='血壓趨勢上升')],
            'trends': {
                'systolic_bp': [
                    {'recorded_at': (now - timedelta(days=14)).isoformat(), 'value': 126},
                    {'recorded_at': now.isoformat(), 'value': 138},
                ],
                'weight_kg': [
                    {'recorded_at': (now - timedelta(days=14)).isoformat(), 'value': 72.0},
                    {'recorded_at': now.isoformat(), 'value': 70.8},
                ],
                'sleep_hours': [
                    {'recorded_at': (now - timedelta(days=14)).isoformat(), 'value': 7.2},
                    {'recorded_at': now.isoformat(), 'value': 6.1},
                ],
            },
            'symptoms': [
                SimpleNamespace(symptom='腰痠', note='腰痠10年', estimated_duration_days=3650, severity=4),
            ],
            'labs': [
                SimpleNamespace(item_name='尿酸', abnormal_flag='H'),
            ],
            'metrics': [
                SimpleNamespace(recorded_at=now, sleep_hours=6.1),
            ],
            'actions': [
                SimpleNamespace(title='每日量血壓', status='done', streak=3),
                SimpleNamespace(title='每晚提早睡', status='in_progress', streak=2),
                SimpleNamespace(title='週末散步', status='todo', streak=0),
            ],
        },
        previous_narrative,
    )

    assert narrative['delta_summary']
    assert narrative['improvements']
    assert narrative['deteriorations']
    assert narrative['adherence']
    assert narrative['missed_risks']
    joined_text = ' '.join(
        [
            narrative['delta_summary'],
            *narrative['improvements'],
            *narrative['deteriorations'],
            *narrative['adherence'],
            *narrative['missed_risks'],
        ]
    )
    assert '上週' in joined_text or '過去 7 天' in joined_text or '7天' in joined_text
    assert '10年' in joined_text or '10 年' in joined_text
