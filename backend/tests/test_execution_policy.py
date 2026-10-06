from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.orchestrator.api import router as orchestrator_router
from app.orchestrator.execution_policy import get_llm_control_state, record_llm_call, evaluate_llm_execution

from test_dual_agent_orchestrator import _setup_test_profile


def test_execution_policy_records_blocked_scheduler_attempt(tmp_path):
    profile_path = _setup_test_profile(tmp_path, scheduler_enabled=False)

    decision = evaluate_llm_execution(source='scheduler', profile_path=str(profile_path))

    assert decision.allowed is False
    assert decision.code == 'GLOBAL_SCHEDULER_DISABLED'

    state = get_llm_control_state(profile_path=str(profile_path))
    assert state['last_source'] == 'scheduler'
    assert state['last_decision_code'] == 'GLOBAL_SCHEDULER_DISABLED'
    assert state['blocked_count'] == 1
    assert state['effective_background_run_allowed'] is False


def test_record_llm_call_updates_telemetry(tmp_path):
    profile_path = _setup_test_profile(tmp_path)

    record_llm_call(
        source='api-direct',
        provider='openai',
        model='gpt-5.4',
        profile_path=str(profile_path),
    )

    state = get_llm_control_state(profile_path=str(profile_path))
    assert state['call_count'] == 1
    assert state['last_provider'] == 'openai'
    assert state['last_model'] == 'gpt-5.4'
    assert state['last_call_source'] == 'api-direct'
    assert state['last_call_at'] is not None


def test_llm_control_endpoint_and_summary_share_same_state(tmp_path, monkeypatch):
    profile_path = _setup_test_profile(tmp_path)
    monkeypatch.setenv('ORCHESTRATOR_PROFILE_PATH', str(profile_path))

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'email': 'test@example.com'}
    app.include_router(orchestrator_router, prefix='/api/v1')
    client = TestClient(app)

    update_resp = client.post(
        '/api/v1/orchestrator/llm-control',
        params={'profile_path': str(profile_path)},
        json={'mode': 'hard-off'},
    )
    assert update_resp.status_code == 200
    update_payload = update_resp.json()
    assert update_payload['hard_off'] is True
    assert update_payload['scheduler_enabled'] is False
    assert update_payload['effective_background_run_allowed'] is False

    summary_resp = client.get('/api/v1/orchestrator/summary', params={'profile_path': str(profile_path)})
    assert summary_resp.status_code == 200
    summary_payload = summary_resp.json()
    assert summary_payload['llm_control']['mode'] == 'hard-off'
    assert summary_payload['llm_control']['effective_background_run_allowed'] is False

    app.dependency_overrides.clear()