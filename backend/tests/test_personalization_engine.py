from types import SimpleNamespace

from app.services.health_ai_engine.personalization_engine import build_personalized_context


def test_personalized_baseline_context():
    metrics = [
        SimpleNamespace(systolic_bp=130, diastolic_bp=85, weight_kg=70, steps=6000, sleep_hours=7),
        SimpleNamespace(systolic_bp=120, diastolic_bp=80, weight_kg=69, steps=5000, sleep_hours=6.5),
    ]
    ctx = build_personalized_context(metrics)
    assert 'baseline_metrics' in ctx
    assert ctx['baseline_metrics']['avg_systolic_bp'] == 125.0
