from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.health_ai_engine.insight_engine import generate_health_narrative


def test_health_narrative_engine_outputs_human_readable_sections():
    now = datetime.now(timezone.utc)
    narrative = generate_health_narrative(
        {
            'health_score': {'overall_score': 68, 'components': {'cardiovascular': 62}},
            'risk_level': 'moderate',
            'alerts': [SimpleNamespace(title='血壓偏高', description='最近量測偏高', severity='warning')],
            'insights': [SimpleNamespace(title='血壓趨勢上升')],
            'trends': {
                'systolic_bp': [
                    {'recorded_at': (now - timedelta(days=14)).isoformat(), 'value': 126},
                    {'recorded_at': now.isoformat(), 'value': 138},
                ],
                'sleep_hours': [
                    {'recorded_at': (now - timedelta(days=14)).isoformat(), 'value': 7.2},
                    {'recorded_at': now.isoformat(), 'value': 5.8},
                ],
            },
            'symptoms': [
                SimpleNamespace(symptom='腰痠', note='腰痠10年', estimated_duration_days=3650),
            ],
            'labs': [
                SimpleNamespace(item_name='尿酸', abnormal_flag='H'),
            ],
            'metrics': [
                SimpleNamespace(recorded_at=now, sleep_hours=5.8),
            ],
            'actions': [
                SimpleNamespace(status='todo'),
            ],
        }
    )

    assert narrative['summary']
    assert len(narrative['actions']) >= 3
    joined_text = ' '.join(
        [narrative['summary'], *narrative['risks'], *narrative['trends'], *narrative['reasons'], *narrative['actions']]
    )
    assert '10年' in joined_text
    assert '2週' in joined_text or '2 週' in joined_text
