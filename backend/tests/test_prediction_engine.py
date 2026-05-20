from types import SimpleNamespace

from app.services.health_ai_engine.prediction_engine import generate_predictive_insights


def test_prediction_engine_outputs_sorted_predictions():
    metrics = [
        SimpleNamespace(systolic_bp=138, weight_kg=72),
        SimpleNamespace(systolic_bp=132, weight_kg=71),
        SimpleNamespace(systolic_bp=128, weight_kg=70),
    ]
    alerts = [SimpleNamespace(title='A1'), SimpleNamespace(title='A2')]
    predictions = generate_predictive_insights(metrics, alerts)
    assert predictions
    priorities = [p['priority'] for p in predictions]
    assert priorities == sorted(priorities, reverse=True)
