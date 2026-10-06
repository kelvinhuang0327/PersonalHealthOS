from app.services.health_ai_engine.rule_engine import evaluate_rule, evaluate_rules, load_rules


def test_load_and_evaluate_rules():
    rules = load_rules('blood_pressure_rules.yaml')
    assert rules
    matched = evaluate_rules(rules, {'bp_high_count': 3})
    assert len(matched) == 1
    assert evaluate_rule(rules[0], {'bp_high_count': 2}) is False


def test_extended_rule_library_files_exist():
    assert load_rules('cardiovascular_rules.yaml')
    assert load_rules('metabolic_syndrome_rules.yaml')
    assert load_rules('liver_function_rules.yaml')
    assert load_rules('uric_acid_gout_rules.yaml')
    assert load_rules('activity_sleep_rules.yaml')


def test_rule_metadata_fields_present():
    rules = load_rules('insight_rules.yaml')
    required = {'id', 'type', 'category', 'priority', 'severity', 'enabled', 'tags', 'version', 'confidence', 'evidence_level', 'guideline_source'}
    assert rules
    for rule in rules:
        assert required.issubset(set(rule.keys()))


def test_priority_sorting_and_explainability():
    rules = [
        {'id': 'low', 'priority': 1, 'enabled': True, 'conditions': {'field': 'v', 'gt': 0}, 'category': 'x', 'confidence': 0.5},
        {'id': 'high', 'priority': 9, 'enabled': True, 'conditions': {'field': 'v', 'gt': 0}, 'category': 'y', 'confidence': 0.9},
    ]
    matched = evaluate_rules(rules, {'v': 1})
    assert [m['id'] for m in matched] == ['high', 'low']
    assert matched[0]['_explainability']['rule_id'] == 'high'
    assert 'evidence_level' in matched[0]['_explainability']
    assert 'guideline_source' in matched[0]['_explainability']
    assert 'guideline_version' in matched[0]['_explainability']
