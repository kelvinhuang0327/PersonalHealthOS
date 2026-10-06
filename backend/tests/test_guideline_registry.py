from app.services.health_ai_engine.guideline_registry import enrich_explainability, resolve_guideline


def test_guideline_registry_resolves_version():
    data = resolve_guideline('ACC/AHA')
    assert data['guideline_source'].startswith('ACC/AHA')
    assert data['guideline_version']


def test_enrich_explainability_fills_required_fields():
    enriched = enrich_explainability({'rule_id': 'r1', 'guideline_source': 'WHO'})
    assert enriched['guideline_source']
    assert enriched['guideline_version']
    assert enriched['evidence_level'] in {'A', 'B', 'C'}
