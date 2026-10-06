from types import SimpleNamespace

from app.services.health_ai_engine.clinical_score_engine import calculate_clinical_scores


def test_clinical_score_engine_weighted_scoring():
    metrics = [SimpleNamespace(systolic_bp=150, diastolic_bp=95, weight_kg=90)]
    labs = [SimpleNamespace(item_name='ALT', value_num=70), SimpleNamespace(item_name='Uric Acid', value_num=8.2)]
    result = calculate_clinical_scores(metrics, labs)
    assert 0 <= result['cardiovascular_risk_score'] <= 100
    assert 0 <= result['metabolic_risk_score'] <= 100
    assert result['metabolic_risk_score'] < 100
