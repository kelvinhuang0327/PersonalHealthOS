from app.services.health_ai_engine.safety_guardrail import MEDICAL_DISCLAIMER, apply_safety_guardrail


def test_safety_guardrail_rewrites_unsafe_and_appends_disclaimer():
    raw = '你已確診高血壓，請立即服用藥物。'
    safe = apply_safety_guardrail(raw)['safe_response']
    assert '確診' not in safe
    assert MEDICAL_DISCLAIMER in safe
