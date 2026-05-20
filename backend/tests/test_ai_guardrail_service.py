from app.services.ai_guardrail_service import apply_guardrails


def test_guardrail_drops_unsupported_evidence():
    output = {
        'health_risks': [
            {'title': 'A', 'level': 'high', 'reason': 'r1', 'evidence_ids': ['METRIC:1']},
            {'title': 'B', 'level': 'low', 'reason': 'r2', 'evidence_ids': ['INVALID:1']},
        ],
        'lifestyle_recommendations': [],
        'follow_up_items': [],
        'confidence': 0.8,
    }
    guarded, report = apply_guardrails('health_check_interpreter', output, {'METRIC:1'})

    assert len(guarded['health_risks']) == 1
    assert report['dropped_items'] == 1
    assert report['grounded_ratio'] == 0.5
