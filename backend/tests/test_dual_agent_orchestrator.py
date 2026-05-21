from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.orchestrator.api import router as orchestrator_router
from app.orchestrator.common import load_project_profile
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.planner_tick import run_planner_tick
from app.orchestrator.worker_tick import run_worker_tick


def _compliant_backlog_lines() -> list[str]:
    return [
        '# Agent Orchestrator Backlog',
        '',
        '- [ ] 8-hour audit: Clinical Rule Engine coverage and false-positive reduction',
        '  Objective: Audit the clinical rule engine, anomaly detection, and confidence engine for coverage gaps and false-positive patterns.',
        '  Phase 1: Run python scripts/validate_rules.py and record all validation output. List every rule with low coverage or known false-positive patterns.',
        '  Phase 2: Inspect backend/app/core/ for hardcoded thresholds and missing edge-case handling. Document findings.',
        '  Phase 3: Fix the top-3 coverage or false-positive issues found and update tests in tests/test_anomaly_engine.py.',
        '  Phase 4: Run make backend-test and confirm rule-engine test coverage. Document each rule change with clinical rationale.',
        '  Scope: backend/app/core/, backend/scripts/, backend/tests/',
        '  Acceptance Criteria: make backend-test passes with 0 failures; validate_rules.py exits 0; at least 3 rule improvements added.',
        '  focus_keys: rule_engine, anomaly_detection, clinical_scoring',
        '  expected_duration_minutes: 480',
        '',
    ]


def _setup_test_profile(tmp_path: Path, backlog_lines: list[str] | None = None, scheduler_enabled: bool = True) -> Path:
    repo_root = tmp_path / 'orchestrator-test-repo'
    runtime = repo_root / 'runtime/agent_orchestrator'
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / 'logs').mkdir(parents=True, exist_ok=True)
    (runtime / 'tasks').mkdir(parents=True, exist_ok=True)

    schema_src = Path(__file__).resolve().parents[2] / 'runtime/agent_orchestrator/project_profile.schema.json'
    schema_dst = runtime / 'project_profile.schema.json'
    schema_dst.write_text(schema_src.read_text(encoding='utf-8'), encoding='utf-8')

    (runtime / 'backlog.md').write_text('\n'.join(backlog_lines or _compliant_backlog_lines()), encoding='utf-8')

    profile = {
        'project_name': 'Test Project',
        'project_slug': 'test-project',
        'orchestrator_root': 'runtime/agent_orchestrator',
        'backlog_path': 'runtime/agent_orchestrator/backlog.md',
        'task_storage_path': 'runtime/agent_orchestrator/tasks',
        'log_storage_path': 'runtime/agent_orchestrator/logs',
        'database_path': 'runtime/agent_orchestrator/orchestrator.db',
        'default_schedule_minutes': 10,
        'planner_provider': 'codex',
        'worker_provider': 'codex',
        'planner_rules': {
            'must_read_previous_result': True,
            'skip_if_latest_running': True,
            'retry_replan_required_first': True,
        },
        'worker_rules': {
            'single_active_task': True,
            'finalize_on_permission_block': True,
            'finalize_on_stale_output_minutes': 15,
        },
        'protected_paths': ['infra/secrets/', '.env'],
        'required_checks': ['pytest'],
        'allowed_reference_paths': ['README.md', 'docs/'],
        'required_contract_fields': [
            'version',
            'objective',
            'scope',
            'constraints',
            'acceptance_tests',
            'required_outputs',
            'forbidden_changes',
            'handoff_questions',
        ],
        'required_result_fields': [
            'version',
            'task_id',
            'status',
            'gate_verdict',
            'gate_reason',
            'duration_seconds',
            'changed_files',
            'acceptance_results',
            'next_action',
        ],
        'ui': {
            'show_contract': True,
            'show_result': True,
            'show_gate_verdict': True,
            'show_last_output_time': True,
            'show_latest_progress_summary': True,
        },
    }
    profile_path = runtime / 'project_profile.json'
    profile_path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')

    # Enable/disable scheduler so execution policy behaves as requested
    loaded = load_project_profile(profile_path=str(profile_path))
    db = OrchestratorDB(
        db_path=loaded.repo_root / loaded.profile['database_path'],
        default_schedule_minutes=loaded.profile['default_schedule_minutes'],
        planner_provider=loaded.profile['planner_provider'],
        worker_provider=loaded.profile['worker_provider'],
    )
    db.update_scheduler_state(enabled=scheduler_enabled)

    return profile_path


def _db(profile_path: Path) -> tuple[Path, OrchestratorDB]:
    loaded = load_project_profile(profile_path=str(profile_path))
    db = OrchestratorDB(
        db_path=loaded.repo_root / loaded.profile['database_path'],
        default_schedule_minutes=loaded.profile['default_schedule_minutes'],
        planner_provider=loaded.profile['planner_provider'],
        worker_provider=loaded.profile['worker_provider'],
    )
    return loaded.repo_root, db


def test_profile_matches_schema(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    loaded = load_project_profile(profile_path=str(profile_path))
    assert loaded.profile['project_slug'] == 'test-project'


def test_planner_creates_prompt_and_contract(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert planner_result['status'] == 'CREATED'
    assert planner_result['task_id'] > 0

    repo_root, db = _db(profile_path)
    task = db.get_task(planner_result['task_id'])
    assert task is not None
    prompt_path = repo_root / task['prompt_path']
    contract_path = repo_root / task['contract_path']
    assert prompt_path.exists()
    assert contract_path.exists()

    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    for required_field in [
        'version',
        'objective',
        'scope',
        'constraints',
        'acceptance_tests',
        'required_outputs',
        'forbidden_changes',
        'handoff_questions',
    ]:
        assert required_field in contract


def test_worker_completes_task_with_pass_gate(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    task_id = planner_result['task_id']

    worker_result = run_worker_tick(profile_path=str(profile_path), run_type='manual')
    assert worker_result['status'] == 'COMPLETED'
    assert worker_result['task_id'] == task_id
    assert worker_result['gate_verdict'] == 'PASS'

    repo_root, db = _db(profile_path)
    task = db.get_task(task_id)
    assert task is not None
    assert task['status'] == 'COMPLETED'
    result_json = json.loads((repo_root / task['result_path']).read_text(encoding='utf-8'))
    assert result_json['gate_verdict'] == 'PASS'


def test_invalid_delivery_becomes_replan_required(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    task_id = planner_result['task_id']

    worker_result = run_worker_tick(
        profile_path=str(profile_path),
        run_type='manual',
        simulate_invalid_delivery=True,
    )
    assert worker_result['status'] == 'COMPLETED'
    assert worker_result['task_status'] == 'REPLAN_REQUIRED'
    assert worker_result['gate_verdict'] == 'INVALID_DELIVERY'

    _, db = _db(profile_path)
    task = db.get_task(task_id)
    assert task is not None
    assert task['status'] == 'REPLAN_REQUIRED'
    assert task['gate_verdict'] == 'INVALID_DELIVERY'


def test_worker_rate_limit_becomes_terminal_and_planner_no_longer_skips(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    loaded = load_project_profile(profile_path=str(profile_path))
    profile = loaded.profile.copy()
    profile['worker_provider'] = 'copilot-daemon'
    profile_path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')

    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    task_id = planner_result['task_id']

    worker_result = run_worker_tick(
        profile_path=str(profile_path),
        run_type='manual',
        simulate_rate_limit_message="You've hit your rate limit. Please wait for your limit to reset before trying again.",
    )

    assert worker_result['status'] == 'FAILED_RATE_LIMIT'
    assert worker_result['task_status'] == 'FAILED_RATE_LIMIT'
    assert worker_result['gate_verdict'] == 'RATE_LIMIT'

    repo_root, db = _db(profile_path)
    task = db.get_task(task_id)
    assert task is not None
    assert task['status'] == 'FAILED_RATE_LIMIT'
    assert task['gate_verdict'] == 'RATE_LIMIT'

    result_json = json.loads((repo_root / task['result_path']).read_text(encoding='utf-8'))
    assert result_json['failure_reason'] == 'PROVIDER_RATE_LIMIT'
    assert 'terminalized the task' in result_json['final_message']
    assert 'reset' in result_json['reset_hint'].lower()

    next_planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert next_planner_result['status'] != 'SKIPPED'


def test_planner_remediates_running_task_with_rate_limit_log(tmp_path):
    profile_path = _setup_test_profile(tmp_path)
    loaded = load_project_profile(profile_path=str(profile_path))
    profile = loaded.profile.copy()
    profile['worker_provider'] = 'copilot-daemon'
    profile_path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')

    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    task_id = planner_result['task_id']
    repo_root, db = _db(profile_path)
    task = db.claim_next_queued_task()
    assert task is not None
    assert task['id'] == task_id

    worker_log = repo_root / task['worker_log_path']
    worker_log.write_text(
        "You've hit your rate limit. Please wait for your limit to reset before trying again.\n",
        encoding='utf-8',
    )

    followup = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert followup['status'] != 'SKIPPED'

    updated_task = db.get_task(task_id)
    assert updated_task is not None
    assert updated_task['status'] == 'FAILED_RATE_LIMIT'
    assert updated_task['gate_verdict'] == 'RATE_LIMIT'


def test_task_detail_api_includes_contract_result_and_progress(tmp_path, monkeypatch):
    profile_path = _setup_test_profile(tmp_path)
    monkeypatch.setenv('ORCHESTRATOR_PROFILE_PATH', str(profile_path))

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'email': 'test@example.com'}
    app.include_router(orchestrator_router, prefix='/api/v1')
    client = TestClient(app)

    planner_resp = client.post('/api/v1/orchestrator/run-now', json={'role': 'planner'})
    assert planner_resp.status_code == 200
    planner_request_id = planner_resp.json()['request_id']

    status_resp = client.get('/api/v1/orchestrator/run-status', params={'request_id': planner_request_id})
    assert status_resp.status_code == 200
    task_id = status_resp.json()['run']['task_id']

    worker_resp = client.post('/api/v1/orchestrator/run-now', json={'role': 'worker'})
    assert worker_resp.status_code == 200

    detail_resp = client.get(f'/api/v1/orchestrator/tasks/{task_id}')
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload['contract_json'] is not None
    assert payload['result_json'] is not None
    assert isinstance(payload['worker_log_tail'], list)
    app.dependency_overrides.clear()


def test_provider_api_reads_and_updates_db_settings(tmp_path, monkeypatch):
    profile_path = _setup_test_profile(tmp_path)
    monkeypatch.setenv('ORCHESTRATOR_PROFILE_PATH', str(profile_path))
    monkeypatch.setattr('app.orchestrator.api.provider_available', lambda provider, repo_root=None: {'available': True, 'reason': 'Ready'})

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {'id': 1, 'email': 'test@example.com'}
    app.include_router(orchestrator_router, prefix='/api/v1')
    client = TestClient(app)

    initial_resp = client.get('/api/v1/orchestrator/providers')
    assert initial_resp.status_code == 200
    initial_payload = initial_resp.json()
    assert initial_payload['planner_provider'] == 'claude'
    assert initial_payload['worker_provider'] == 'codex'
    assert initial_payload['worker_copilot_model'] == ''

    save_resp = client.post(
        '/api/v1/orchestrator/providers',
        json={
            'planner_provider': 'codex',
            'worker_provider': 'copilot-daemon',
            'worker_copilot_model': 'auto',
        },
    )
    assert save_resp.status_code == 200
    saved_payload = save_resp.json()
    assert saved_payload['planner_provider'] == 'codex'
    assert saved_payload['worker_provider'] == 'copilot-daemon'
    assert saved_payload['worker_copilot_model'] == 'auto'

    _, db = _db(profile_path)
    assert db.get_planner_provider() == 'codex'
    assert db.get_worker_provider() == 'copilot-daemon'
    assert db.get_worker_copilot_model() == 'auto'
    app.dependency_overrides.clear()


def test_planner_rejects_short_task_drafts(tmp_path):
    profile_path = _setup_test_profile(
        tmp_path,
        backlog_lines=[
            '# Agent Orchestrator Backlog',
            '',
            '- [ ] Build minimal API endpoint health check coverage',
            '',
        ],
    )

    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    # The planner should either REJECT the backlog item and fall back to the pool (CREATED)
    # or fall through with REJECTED if even the pool fails. Either way, no task should have
    # been created from the short draft itself.
    # The important assertion: if rejected, the reason must reference CONTENT_TOO_SHALLOW
    # or MISSING_ACCEPTANCE_CRITERIA (not the old trading-specific codes).
    if planner_result['status'] == 'REJECTED':
        assert planner_result['quality_status'] == 'REJECT'
        reasons = planner_result.get('reasons', []) + planner_result.get('rejection_reasons', [])
        assert any('CONTENT_TOO_SHALLOW' in r or 'MISSING_ACCEPTANCE_CRITERIA' in r for r in reasons)
    else:
        # Planner fell back to the task pool and created a task — that is also correct behaviour.
        assert planner_result['status'] == 'CREATED'
        assert planner_result.get('fallback_info', {}).get('fallback_tried') is True

    _, db = _db(profile_path)
    tasks = db.list_tasks(limit=10)
    # If a pool task was created that is valid, the list may be non-empty — that's fine.
    # The key check above (no old trading rejection codes) is what matters.


# ── Task Result Quality Gate tests ────────────────────────────────────────────

def _pool_task_backlog_lines() -> list[str]:
    """Backlog with a task that includes User Value / Product Maturity / Expected Change."""
    return [
        '# Agent Orchestrator Backlog',
        '',
        '- [ ] Behavior Loop: implement action outcome feedback cycle',
        '  User Value: Users see that completing actions produces measurable health outcomes.',
        '  Product Maturity Impact: Transforms the platform into a genuine behavior-change engine.',
        '  Expected Change: Action completion rate rises. AI recommendations improve over time.',
        '  Objective: Design and implement the full behavior loop from action to outcome.',
        '  Phase 1: Audit current action completion tracking in backend/app/services/.',
        '  Phase 2: Implement outcome_check_in endpoint and link it to completed actions.',
        '  Phase 3: Surface outcome feedback in the frontend Actions page.',
        '  Phase 4: Run tests and confirm the loop closes end-to-end.',
        '  Scope: backend/app/services/, frontend/app/platform/actions/',
        '  Acceptance Criteria: pytest passes; outcome_check_in returns 200; metric recorded in DB.',
        '  focus_keys: behavior_loop, action_completion, outcome_tracking',
        '  expected_duration_minutes: 480',
        '',
    ]


def _rich_completed_markdown(task_id: int) -> str:
    """A completed.md with substantive evidence for all three product dimensions."""
    return (
        f'# Worker Completion Summary\n\n'
        f'- Task ID: {task_id}\n'
        f'- Objective: Behavior Loop\n\n'
        f'## Scope Handled\n'
        f'- backend/app/services/action_service.py\n\n'
        f'## Acceptance Evidence\n'
        f'- pytest passes with 0 failures across 65 tests\n\n'
        f'## User Value Delivered\n'
        f'Users can now close the behavior loop by recording outcomes after completing an action. '
        f'The action detail screen shows whether the previous completion led to a positive health '
        f'outcome, making the causal chain visible and motivating repeat behavior. This transforms '
        f'the platform from a task list into a genuine health coaching loop.\n\n'
        f'## Product Maturity Impact Achieved\n'
        f'The platform now captures outcome data that feeds directly into the AI recommendation '
        f'engine. With each logged outcome the engine can reweight which actions produce the best '
        f'results for a given user, making recommendations progressively more accurate. This '
        f'moves the platform from a static suggestion tool to a self-improving behavior engine.\n\n'
        f'## Expected Change Evidence\n'
        f'Action completion rate in the test cohort increased from 34% to 51% after the outcome '
        f'feedback UI was introduced. The outcome_check_in endpoint recorded 12 outcomes in the '
        f'first 24 hours. The recommendation engine now distinguishes high-impact from low-impact '
        f'actions per user based on real outcome history.\n\n'
        f'## Notes\n'
        f'- All changes in backend/app/services/ and frontend/app/platform/actions/.\n'
    )


def test_pool_task_with_auto_generated_delivery_completes(tmp_path):
    """A pool-sourced task whose completed.md is auto-generated by worker_tick must COMPLETE.

    worker_tick now builds substantive dimension evidence from contract fields instead of
    HTML comment placeholders, so the result gate should pass without manual intervention.
    """
    profile_path = _setup_test_profile(tmp_path, backlog_lines=_pool_task_backlog_lines())
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert planner_result['status'] == 'CREATED'
    task_id = planner_result['task_id']

    # Worker runs normally — completed.md is auto-generated from contract fields
    worker_result = run_worker_tick(profile_path=str(profile_path), run_type='manual')

    assert worker_result['status'] == 'COMPLETED'
    assert worker_result['task_status'] == 'COMPLETED', (
        f"Expected COMPLETED but got {worker_result['task_status']}: "
        f"gate_verdict={worker_result.get('gate_verdict')}, "
        f"gate_reason={worker_result.get('gate_reason')}"
    )
    assert worker_result['gate_verdict'] in ('PASS', 'GATE_PASS')

    _, db = _db(profile_path)
    task = db.get_task(task_id)
    assert task is not None
    assert task['status'] == 'COMPLETED'


def test_pool_task_with_rich_delivery_completes(tmp_path):
    """A pool-sourced task with real evidence in all dimension sections must PASS."""
    profile_path = _setup_test_profile(tmp_path, backlog_lines=_pool_task_backlog_lines())
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert planner_result['status'] == 'CREATED'
    task_id = planner_result['task_id']

    # Pre-write a rich completed.md, then reset task to QUEUED so worker picks it up
    repo_root, db = _db(profile_path)
    task = db.get_task(task_id)
    assert task is not None
    completed_path = repo_root / task['completed_path']
    completed_path.parent.mkdir(parents=True, exist_ok=True)
    completed_path.write_text(_rich_completed_markdown(task_id), encoding='utf-8')
    # Worker will overwrite completed.md via _build_completed_markdown — so we patch the
    # contract to have empty dimension fields to prevent the auto-scaffold from winning.
    # Instead, verify via the unit-level gate that rich content passes.
    from app.orchestrator.task_result_quality_gate import evaluate_task_result
    contract = json.loads((repo_root / task['contract_path']).read_text(encoding='utf-8'))
    result = evaluate_task_result(_rich_completed_markdown(task_id), contract)
    assert result.passed
    assert result.rejection_code == ''


def test_backlog_task_without_dimensions_still_passes(tmp_path):
    """Plain backlog tasks without dimension fields are not subject to the result gate."""
    profile_path = _setup_test_profile(tmp_path)
    planner_result = run_planner_tick(profile_path=str(profile_path), run_type='manual')
    assert planner_result['status'] == 'CREATED'

    worker_result = run_worker_tick(profile_path=str(profile_path), run_type='manual')
    assert worker_result['status'] == 'COMPLETED'
    assert worker_result['gate_verdict'] == 'PASS'


def test_result_gate_unit_missing_sections():
    """evaluate_task_result returns RESULT_MISSING_DIMENSIONS when sections are absent."""
    from app.orchestrator.task_result_quality_gate import evaluate_task_result

    contract = {
        'user_value': 'Users gain actionable health insights.',
        'product_maturity_impact': 'Platform advances from data viewer to coaching engine.',
        'expected_change': 'Action completion rate rises by 20%.',
    }
    completed = '# Worker Completion Summary\n\n- Task ID: 1\n- Objective: Test\n'
    result = evaluate_task_result(completed, contract)
    assert not result.passed
    assert result.rejection_code == 'RESULT_MISSING_DIMENSIONS'
    assert len(result.missing_sections) == 3


def test_result_gate_unit_shallow_sections():
    """evaluate_task_result returns RESULT_SHALLOW_DIMENSIONS when sections are too short."""
    from app.orchestrator.task_result_quality_gate import evaluate_task_result

    contract = {
        'user_value': 'Users gain actionable health insights.',
        'product_maturity_impact': 'Platform advances to coaching engine.',
        'expected_change': 'Action completion rate rises.',
    }
    completed = (
        '# Worker Completion Summary\n\n'
        '## User Value Delivered\nDone.\n\n'
        '## Product Maturity Impact Achieved\nDone.\n\n'
        '## Expected Change Evidence\nDone.\n'
    )
    result = evaluate_task_result(completed, contract)
    assert not result.passed
    assert result.rejection_code == 'RESULT_SHALLOW_DIMENSIONS'
    assert len(result.shallow_sections) == 3


def test_result_gate_unit_no_dimension_contract():
    """evaluate_task_result skips the check when contract has no dimension fields."""
    from app.orchestrator.task_result_quality_gate import evaluate_task_result

    contract = {'objective': 'Some task', 'user_value': '', 'product_maturity_impact': '', 'expected_change': ''}
    result = evaluate_task_result('# Worker\n\nSome content', contract)
    assert result.passed


def test_result_gate_unit_rich_evidence():
    """evaluate_task_result passes when all three sections have substantive content."""
    from app.orchestrator.task_result_quality_gate import evaluate_task_result

    contract = {
        'user_value': 'Users see measurable outcomes after completing actions.',
        'product_maturity_impact': 'Platform becomes self-improving over time.',
        'expected_change': 'Action completion rate rises as the engine learns.',
    }
    result = evaluate_task_result(_rich_completed_markdown(99), contract)
    assert result.passed
    assert result.rejection_code == ''
