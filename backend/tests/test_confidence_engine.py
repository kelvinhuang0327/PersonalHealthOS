from app.services.health_ai_engine.confidence_engine import calibrate_confidence, combine_confidence


def test_confidence_engine_calibrates_with_data_completeness():
    low = calibrate_confidence(metrics_count=1, labs_count=0, timeline_length=2, rule_coverage=0.2)
    high = calibrate_confidence(metrics_count=10, labs_count=8, timeline_length=60, rule_coverage=0.9)
    assert low >= 0.5
    assert high <= 0.95
    assert high > low


def test_confidence_combination():
    combined = combine_confidence(0.8, 0.9)
    assert 0.5 <= combined <= 0.95
