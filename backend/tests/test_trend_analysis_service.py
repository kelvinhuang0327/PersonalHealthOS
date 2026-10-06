from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.trend_analysis_service import _summarize_series


def test_summarize_series_direction_up():
    now = datetime.now(timezone.utc)
    series = [
        (now - timedelta(days=2), 100.0),
        (now - timedelta(days=1), 110.0),
        (now, 120.0),
    ]

    result = _summarize_series('blood_glucose', series)
    assert result['direction'] == 'up'
    assert result['points'] == 3
    assert result['change_percent'] > 0
