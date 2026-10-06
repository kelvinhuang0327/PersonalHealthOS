from __future__ import annotations

from datetime import datetime, timedelta, timezone


def mock_external_metrics() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {'recorded_at': now - timedelta(hours=8), 'systolic_bp': 122, 'diastolic_bp': 78, 'heart_rate': 72, 'source': 'external_api'},
        {'recorded_at': now - timedelta(hours=6), 'blood_glucose': 102, 'source': 'external_api'},
        {'recorded_at': now - timedelta(hours=4), 'steps': 4200, 'source': 'external_api'},
        {'recorded_at': now - timedelta(hours=2), 'sleep_hours': 7.1, 'source': 'external_api'},
    ]
