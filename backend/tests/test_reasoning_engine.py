from types import SimpleNamespace

from app.services.health_ai_engine.reasoning_engine import generate_reasoning_summary


def test_reasoning_engine_generates_summary():
    metrics = [SimpleNamespace(systolic_bp=135, steps=5000), SimpleNamespace(systolic_bp=130, steps=5500)]
    summary = generate_reasoning_summary(
        timeline_events=[{'id': 1}],
        risk_alerts=[SimpleNamespace(title='血壓偏高')],
        health_score={'overall_score': 76},
        insights=[SimpleNamespace(title='趨勢洞察')],
        metrics=metrics,
    )
    assert 'summary' in summary
    assert summary['rule_id'] == 'reasoning_v3_multisource'
