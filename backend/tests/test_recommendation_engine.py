from app.services.health_ai_engine.recommendation_engine import generate_recommendations


def test_recommendation_engine_returns_prioritized_recommendations():
    labels = [{'label': 'BP:hypertension'}, {'label': 'BMI:obese'}, {'label': 'UricAcid:high'}]
    recs = generate_recommendations(labels, risk_level='high', active_alerts=[{'id': 'a1'}])
    assert recs
    assert all('guideline_source' in rec for rec in recs)
    assert all('guideline_version' in rec for rec in recs)
    assert all('evidence_level' in rec for rec in recs)
    priorities = [rec['priority'] for rec in recs]
    assert priorities == sorted(priorities, reverse=True)
