from app.services import ai_service
from app.core.constants import MEDICAL_DISCLAIMER
from app.orchestrator.execution_policy import ExecutionPolicyDecision


def test_ai_summary_fallback_contains_disclaimer(monkeypatch):
    monkeypatch.setattr(ai_service.settings, 'openai_api_key', '')

    result = ai_service.generate_health_summary(
        profile={'full_name': 'Test'},
        metrics=[{'blood_glucose': 110}],
        alerts=[{'title': 'alert'}],
        period_start=None,
        period_end=None,
    )

    assert result['disclaimer'] == MEDICAL_DISCLAIMER
    assert '免責聲明' in result['summary_text']
    assert result['model_name'] == 'rule-based-fallback'


def test_ai_summary_policy_fallback_does_not_call_openai(monkeypatch):
    monkeypatch.setattr(ai_service.settings, 'openai_api_key', 'test-key')
    monkeypatch.setattr(
        ai_service,
        'evaluate_llm_execution',
        lambda source: ExecutionPolicyDecision(
            allowed=False,
            code='SAFE_RUN_NON_SCHEDULER_SOURCE',
            message='blocked',
            mode='safe-run',
            scheduler_enabled=False,
        ),
    )

    class FailingOpenAI:
        def __init__(self, *args, **kwargs):
            raise AssertionError('OpenAI should not be constructed when policy blocks execution')

    monkeypatch.setattr(ai_service, 'OpenAI', FailingOpenAI)

    result = ai_service.generate_health_summary(
        profile={'full_name': 'Test'},
        metrics=[{'blood_glucose': 110}],
        alerts=[{'title': 'alert'}],
        period_start=None,
        period_end=None,
    )

    assert result['model_name'] == 'policy-fallback:safe_run_non_scheduler_source'
