from types import SimpleNamespace

from app.services.health_ai_engine.anomaly_engine import detect_anomalies


def test_anomaly_detection_flags_bp_spike():
    metrics = [
        SimpleNamespace(systolic_bp=160, weight_kg=70, steps=4000, sleep_hours=6),
        SimpleNamespace(systolic_bp=130, weight_kg=70, steps=4500, sleep_hours=6),
        SimpleNamespace(systolic_bp=128, weight_kg=70, steps=4500, sleep_hours=6),
        SimpleNamespace(systolic_bp=127, weight_kg=70, steps=4500, sleep_hours=6),
    ]
    anomalies = detect_anomalies(metrics, [])
    assert any(a['rule_id'] == 'anomaly_bp_spike' for a in anomalies)
