import pytest
from app.services import ai_service, ai_modules_service
from app.core.constants import MEDICAL_DISCLAIMER
from app.orchestrator.execution_policy import ExecutionPolicyDecision

def test_ai_service_graceful_recovery_on_openai_error(monkeypatch):
    monkeypatch.setattr(ai_service.settings, 'openai_api_key', 'test-key')
    monkeypatch.setattr(
        ai_service,
        'evaluate_llm_execution',
        lambda source: ExecutionPolicyDecision(
            allowed=True,
            code='ALLOWED',
            message='allowed',
            mode='normal',
            scheduler_enabled=False,
        ),
    )

    class FailingOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        @property
        def responses(self):
            class Responses:
                def create(self, *args, **kwargs):
                    raise Exception("Injected OpenAI API connection/auth failure")
            return Responses()

    monkeypatch.setattr(ai_service, 'OpenAI', FailingOpenAI)

    result = ai_service.generate_health_summary(
        profile={'full_name': 'Test'},
        metrics=[{'blood_glucose': 110}],
        alerts=[{'title': 'alert'}],
        period_start=None,
        period_end=None,
    )

    assert result['model_name'] == 'rule-based-fallback'
    assert '近期健康數據已整理完成' in result['summary_text']
    assert MEDICAL_DISCLAIMER in result['summary_text']


def test_ai_modules_service_graceful_recovery_on_openai_error(monkeypatch):
    monkeypatch.setattr(ai_modules_service.settings, 'openai_api_key', 'test-key')
    monkeypatch.setattr(
        ai_modules_service,
        'evaluate_llm_execution',
        lambda source: ExecutionPolicyDecision(
            allowed=True,
            code='ALLOWED',
            message='allowed',
            mode='normal',
            scheduler_enabled=False,
        ),
    )

    class FailingOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        @property
        def responses(self):
            class Responses:
                def create(self, *args, **kwargs):
                    raise Exception("Injected OpenAI API connection/auth failure")
            return Responses()

    monkeypatch.setattr(ai_modules_service, 'OpenAI', FailingOpenAI)

    parsed, model_name = ai_modules_service._call_model(
        module='health_check_interpreter',
        prompt='test prompt',
        context={
            'profile': {'evidence_id': 'PROFILE:test'},
            'metrics': [],
            'symptoms': [],
            'lab_items': [],
            'alerts': [],
            'evidence_ids': []
        },
        max_items=5
    )

    assert model_name == 'rule-based-fallback'
    assert isinstance(parsed, dict)
    # Checks that fallback returns a structured format
    assert 'health_risks' in parsed
