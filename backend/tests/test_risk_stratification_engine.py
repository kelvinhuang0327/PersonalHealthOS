from types import SimpleNamespace

from app.services.health_ai_engine.risk_stratification_engine import stratify_risk_level


def test_risk_stratification_engine_returns_high_for_multi_factor_risk():
    metrics = [SimpleNamespace(systolic_bp=152, weight_kg=92)]
    labs = [SimpleNamespace(item_name='ALT', value_num=65, ref_high=40)]
    result = stratify_risk_level(metrics, labs, long_term_symptom_count=1, active_alert_count=2)
    assert result['risk_level'] == 'high'
    assert result['rule_id'] == 'risk_stratification_v4'
