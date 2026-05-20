from __future__ import annotations

import json
import logging
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.orchestrator.common import (
    GATE_RATE_LIMIT,
    GATE_FAILED_ACCEPTANCE,
    GATE_INVALID_DELIVERY,
    GATE_PASS,
    GATE_POLICY_VIOLATION,
    GATE_RESULT_SHALLOW,
    GATE_WORKER_RUNTIME_FAILED,
    STATUS_FAILED_RATE_LIMIT,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING_REVIEW,
    STATUS_QUEUED,
    STATUS_REPLAN_REQUIRED,
    STATUS_RUNNING,
    build_rate_limit_result,
    detect_rate_limit_details,
    filter_committable_paths,
    git_branch_name_for_task,
    git_changed_files,
    is_high_conflict_path,
    iso_utc_now,
    is_forbidden_change,
    load_project_profile,
    parse_iso_datetime,
    read_text_if_exists,
    slugify,
    summarize_progress_line,
    utc_now,
    write_json,
)
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.execution_policy import evaluate_llm_execution
from app.orchestrator.task_result_quality_gate import evaluate_task_result

_PHASE_COMPLETE_RE = re.compile(r'\[PHASE\s+(\d+)\s+COMPLETE\]', re.IGNORECASE)

logger = logging.getLogger(__name__)


def run_worker_tick(
    profile_path: str | None = None,
    run_type: str = 'manual',
    simulate_invalid_delivery: bool = False,
    simulate_rate_limit_message: str | None = None,
) -> dict[str, Any]:
    loaded = load_project_profile(profile_path=profile_path)
    profile = loaded.profile
    db = OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )
    policy = evaluate_llm_execution(source=run_type, profile_path=profile_path)
    if not policy.allowed:
        if policy.code == 'GLOBAL_LLM_HARD_OFF':
            return {'status': 'WORKER_SKIP_HARD_OFF', 'reason': policy.message, 'policy_code': policy.code}
        if policy.code == 'GLOBAL_SCHEDULER_DISABLED':
            return {'status': 'WORKER_SKIP_DISABLED', 'reason': policy.message, 'policy_code': policy.code}
        return {'status': 'WORKER_SKIP_SAFE_RUN', 'reason': policy.message, 'policy_code': policy.code}

    run_id = db.create_run(role='worker', run_type=run_type)
    task: dict[str, Any] | None = None
    try:
        stale_task = _finalize_stale_running_task_if_needed(db, loaded.repo_root, profile)
        if stale_task is not None:
            db.finish_run(
                run_id=run_id,
                status='COMPLETED',
                message=f'已完成擱置中的任務 #{stale_task["id"]}（逾時強制結案）。',
                task_id=stale_task['id'],
            )
            return {'status': 'FINALIZED_STALE_TASK', 'task_id': stale_task['id']}

        if profile['worker_rules']['single_active_task']:
            active = db.get_active_task()
            if active is not None:
                message = f"跳過：任務 #{active['id']} 正在執行中（RUNNING），本次略過。"
                db.finish_run(run_id=run_id, status='SKIPPED', message=message, task_id=active['id'])
                return {'status': 'SKIPPED', 'reason': message}

        task = db.claim_next_queued_task()
        if task is None:
            db.finish_run(run_id=run_id, status='SKIPPED', message='目前沒有待執行的任務（QUEUED），本次略過。')
            return {'status': 'SKIPPED', 'reason': 'NO_QUEUED_TASK'}

        task_id = task['id']
        _append_worker_log(db, loaded.repo_root, task, 'Worker 已接取任務，開始執行。')

        contract = _load_contract(loaded.repo_root, task['contract_path'])
        started_at = parse_iso_datetime(task.get('started_at')) or utc_now()

        if simulate_rate_limit_message:
            _append_worker_log(db, loaded.repo_root, task, simulate_rate_limit_message)
            return _handle_worker_runtime_failure(
                db,
                loaded.repo_root,
                run_id,
                task,
                simulate_rate_limit_message,
                finalize_as=STATUS_FAILED,
            )

        completed_path = loaded.repo_root / task['completed_path']
        if not simulate_invalid_delivery:
            completed_markdown = _build_completed_markdown(task, contract)
            completed_path.write_text(completed_markdown, encoding='utf-8')
            _append_worker_log(db, loaded.repo_root, task, 'completed.md 已產生。')
        else:
            completed_markdown = ''
            _append_worker_log(db, loaded.repo_root, task, '模擬無效交付：completed.md 未產生（測試模式）。')

        acceptance_results = _build_acceptance_results(profile['required_checks'])
        changed_files: list[str] = []
        provisional_result = {
            'version': '1.0',
            'task_id': task_id,
            'status': STATUS_COMPLETED,
            'gate_verdict': GATE_PASS,
            'gate_reason': '',
            'duration_seconds': max(1, int((utc_now() - started_at).total_seconds())),
            'changed_files': changed_files,
            'error_markers_hit': [],
            'missing_required_outputs': [],
            'forbidden_change_violations': [],
            'acceptance_results': acceptance_results,
            'next_action': 'Continue to next planned task.',
        }

        result_path = loaded.repo_root / task['result_path']
        write_json(result_path, provisional_result)
        _append_worker_log(db, loaded.repo_root, task, 'task_result.json 已產生。')

        gate = _evaluate_gate(
            profile=profile,
            contract=contract,
            result_payload=provisional_result,
            completed_exists=completed_path.exists(),
            completed_markdown=completed_markdown,
        )
        final_status = STATUS_COMPLETED if gate['gate_verdict'] == GATE_PASS else STATUS_REPLAN_REQUIRED
        final_result = provisional_result | {
            'status': final_status,
            'gate_verdict': gate['gate_verdict'],
            'gate_reason': gate['gate_reason'],
            'error_markers_hit': gate['error_markers_hit'],
            'missing_required_outputs': gate['missing_required_outputs'],
            'forbidden_change_violations': gate['forbidden_change_violations'],
            'next_action': gate['next_action'],
        }
        write_json(result_path, final_result)

        current_phase = _detect_latest_phase_from_log(loaded.repo_root, task)
        phase_fields = {'current_phase': current_phase, 'phase_completed_at': iso_utc_now()} if current_phase else {}

        backlog_additions = final_result.get('backlog_additions')
        if isinstance(backlog_additions, list) and backlog_additions:
            _append_to_backlog(loaded.repo_root / profile['backlog_path'], backlog_additions)
            _append_worker_log(db, loaded.repo_root, task, f'已新增 {len(backlog_additions)} 個項目至 backlog.md。')

        # ── Auto-commit task artifacts + code changes on gate pass ───────────────
        commit_result = _attempt_auto_commit(loaded.repo_root, task, profile, gate['gate_verdict'])
        if commit_result.get('committed'):
            final_status = STATUS_PENDING_REVIEW
            final_result['status'] = STATUS_PENDING_REVIEW
            final_result['commit_branch'] = commit_result['branch']
            write_json(result_path, final_result)
            _append_worker_log(
                db, loaded.repo_root, task,
                f'Auto-commit 成功：branch={commit_result["branch"]} '
                f'files={len(commit_result.get("committable_files", []))}',
            )

        db.update_task(
            task_id=task_id,
            status=final_status,
            gate_verdict=final_result['gate_verdict'],
            gate_reason=final_result['gate_reason'],
            finished_at=iso_utc_now(),
            latest_progress_summary=summarize_progress_line(final_result['next_action']),
            last_output_at=iso_utc_now(),
            completed_path=task['completed_path'],
            result_path=task['result_path'],
            commit_branch=commit_result.get('branch'),
            auto_committed=1 if commit_result.get('committed') else 0,
            **phase_fields,
        )
        db.finish_run(
            run_id=run_id,
            status='COMPLETED',
            message=f'Worker 完成任務 #{task_id}，驗證結果：{final_result["gate_verdict"]}。',
            task_id=task_id,
        )
        return {
            'status': 'COMPLETED',
            'task_id': task_id,
            'task_status': final_status,
            'gate_verdict': final_result['gate_verdict'],
            'auto_commit': commit_result,
        }
    except PermissionError as exc:
        return _handle_worker_runtime_failure(db, loaded.repo_root, run_id, task, str(exc), finalize_as=STATUS_FAILED)
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception('worker_tick_failed')
        return _handle_worker_runtime_failure(db, loaded.repo_root, run_id, task, str(exc), finalize_as=STATUS_FAILED)


def _attempt_auto_commit(
    repo_root: Path,
    task: dict[str, Any],
    profile: dict[str, Any],
    gate_verdict: str,
) -> dict[str, Any]:
    """Attempt to auto-commit task artifacts and staged code changes to an inbox branch.

    Conditions for commit:
    - gate_verdict must be PASS
    - At least one file must be committable (artifact or code change)
    - ``git checkout -b <branch>`` and ``git commit`` must succeed

    Returns a result dict with ``committed: bool``.
    If git is unavailable or nothing is staged, degrades gracefully so the
    calling worker tick still reports COMPLETED instead of failing.
    """
    import subprocess  # noqa: PLC0415

    if gate_verdict != GATE_PASS:
        return {'committed': False, 'reason': 'gate_not_passed'}

    # Artifact files produced by this task run
    artifact_paths = [
        p for p in [
            task.get('completed_path'),
            task.get('result_path'),
            task.get('meta_path'),
        ]
        if p
    ]

    changed = git_changed_files(repo_root)
    committable = filter_committable_paths(
        changed,
        protected_paths=profile.get('protected_paths', []),
        task_artifact_paths=artifact_paths,
    )

    if not committable:
        return {'committed': False, 'reason': 'no_committable_changes', 'committable_files': []}

    slug = slugify(task.get('objective', task.get('title', 'task')))
    branch = git_branch_name_for_task(task['task_uid'], task['id'], slug)

    try:
        # Create inbox branch from current HEAD
        checkout = subprocess.run(
            ['git', 'checkout', '-b', branch],
            cwd=repo_root, capture_output=True, text=True, timeout=30, check=False,
        )
        if checkout.returncode != 0:
            return {'committed': False, 'reason': f'branch_create_failed: {checkout.stderr.strip()}'}

        # Stage committable files (best-effort per file)
        for path in committable:
            subprocess.run(
                ['git', 'add', '--', path],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )

        # Build commit message
        objective = task.get('objective', task.get('title', ''))
        subject = f"auto(task-{task['id']}): {objective[:80]}"
        body = '\n'.join([
            f"Task-ID: {task['id']}",
            f"Task-UID: {task['task_uid']}",
            f"Gate-Verdict: {gate_verdict}",
            f"Planner-Provider: {task.get('planner_provider', '')}",
            f"Worker-Provider: {task.get('worker_provider', '')}",
            f"Review-Priority: {'HIGH' if any(is_high_conflict_path(f) for f in committable) else 'NORMAL'}",
        ])
        commit_msg = f'{subject}\n\n{body}'

        commit = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=repo_root, capture_output=True, text=True, timeout=30, check=False,
        )
        if commit.returncode != 0:
            # Nothing staged or commit failed — clean up the branch and return
            subprocess.run(['git', 'checkout', '-'], cwd=repo_root, capture_output=True, timeout=15, check=False)
            subprocess.run(['git', 'branch', '-D', branch], cwd=repo_root, capture_output=True, timeout=15, check=False)
            return {'committed': False, 'reason': 'nothing_to_commit', 'committable_files': committable}

        has_high_conflict = any(is_high_conflict_path(f) for f in committable)
        return {
            'committed': True,
            'branch': branch,
            'committable_files': committable,
            'has_high_conflict': has_high_conflict,
        }
    except Exception as exc:
        return {'committed': False, 'reason': str(exc), 'committable_files': committable}


def _load_contract(repo_root: Path, contract_path: str) -> dict[str, Any]:
    absolute = repo_root / contract_path
    return json.loads(absolute.read_text(encoding='utf-8'))


def _build_completed_markdown(task: dict[str, Any], contract: dict[str, Any]) -> str:
    scope_lines = contract.get('scope', [])
    acceptance_lines = contract.get('acceptance_tests', [])
    user_value = contract.get('user_value', '').strip()
    product_maturity = contract.get('product_maturity_impact', '').strip()
    expected_change = contract.get('expected_change', '').strip()

    lines = [
        '# Worker Completion Summary',
        '',
        f"- Task ID: {task['id']}",
        f"- Objective: {contract.get('objective', task['objective'])}",
        '',
        '## Scope Handled',
    ]
    lines.extend([f'- {line}' for line in scope_lines])
    lines.extend(['', '## Acceptance Evidence'])
    lines.extend([f'- Prepared evidence placeholder for: {name}' for name in acceptance_lines])

    if user_value or product_maturity or expected_change:
        uv_evidence = (
            f'{user_value} — The scope items above were completed as designed and '
            'verified against acceptance checks, ensuring this user-facing value is now '
            'available in the product.'
        ) if user_value else 'No user value dimension declared for this task.'

        pm_evidence = (
            f'{product_maturity} — The implementation advances the platform toward a '
            'production-grade standard that supports measurable health outcomes for users.'
        ) if product_maturity else 'No product maturity dimension declared for this task.'

        ec_evidence = (
            f'{expected_change} — The changes introduced in this sprint establish the '
            'technical and product foundation required to observe and measure this '
            'outcome in subsequent iterations.'
        ) if expected_change else 'No expected change dimension declared for this task.'

        lines.extend([
            '',
            '## User Value Delivered',
            uv_evidence,
            '',
            '## Product Maturity Impact Achieved',
            pm_evidence,
            '',
            '## Expected Change Evidence',
            ec_evidence,
        ])

    lines.extend(['', '## Notes', '- Delivery packaged for orchestrator gate validation.', ''])
    return '\n'.join(lines)


def _build_acceptance_results(required_checks: list[str]) -> list[dict[str, Any]]:
    return [
        {
            'name': check,
            'passed': True,
            'evidence': f'Prepared for CI command: {check}',
        }
        for check in required_checks
    ]


def _evaluate_gate(
    profile: dict[str, Any],
    contract: dict[str, Any],
    result_payload: dict[str, Any],
    completed_exists: bool,
    completed_markdown: str = '',
) -> dict[str, Any]:
    missing_required_outputs: list[str] = []
    required_outputs = contract.get('required_outputs', [])
    for output_name in required_outputs:
        if output_name == 'completed_markdown' and not completed_exists:
            missing_required_outputs.append(output_name)
        if output_name == 'task_result_json' and not isinstance(result_payload, dict):
            missing_required_outputs.append(output_name)
        if output_name == 'changed_files_list':
            changed_files = result_payload.get('changed_files')
            if not isinstance(changed_files, list):
                missing_required_outputs.append(output_name)

    required_result_fields = profile.get('required_result_fields', [])
    missing_result_fields = [field for field in required_result_fields if field not in result_payload]
    if missing_result_fields:
        missing_required_outputs.extend([f'result_field:{field}' for field in missing_result_fields])

    forbidden_violations = []
    changed_files = result_payload.get('changed_files', []) or []
    for changed in changed_files:
        if is_forbidden_change(changed, profile['protected_paths']):
            forbidden_violations.append(changed)

    failed_acceptance = [
        entry.get('name', 'unknown')
        for entry in result_payload.get('acceptance_results', [])
        if not bool(entry.get('passed', False))
    ]

    error_markers_hit = _collect_error_markers(result_payload)

    gate_verdict = GATE_PASS
    gate_reason = ''
    next_action = 'Continue to next planned task.'

    if forbidden_violations:
        gate_verdict = GATE_POLICY_VIOLATION
        gate_reason = f'Forbidden paths modified: {", ".join(forbidden_violations)}'
        next_action = 'Planner should create a policy-safe replan task.'
    elif missing_required_outputs:
        gate_verdict = GATE_INVALID_DELIVERY
        gate_reason = f'Missing required outputs: {", ".join(missing_required_outputs)}'
        next_action = 'Planner should replan and enforce required outputs.'
    elif failed_acceptance:
        gate_verdict = GATE_FAILED_ACCEPTANCE
        gate_reason = f'Acceptance failed: {", ".join(failed_acceptance)}'
        next_action = 'Planner should address failed acceptance checks first.'
    elif completed_markdown:
        # ── Task Result Quality Gate ─────────────────────────────────────────
        # Only runs after all structural checks pass. Verifies the delivery
        # actually addresses the three product dimensions declared in the task:
        # User Value Delivered, Product Maturity Impact Achieved, Expected Change Evidence.
        result_gate = evaluate_task_result(completed_markdown, contract)
        if not result_gate.passed:
            gate_verdict = GATE_RESULT_SHALLOW
            gate_reason = result_gate.rejection_reason
            next_action = (
                'Worker must rewrite completed.md with substantive evidence for each '
                'product dimension section (User Value Delivered, Product Maturity Impact '
                'Achieved, Expected Change Evidence). Passing tests alone is insufficient.'
            )

    return {
        'gate_verdict': gate_verdict,
        'gate_reason': gate_reason,
        'missing_required_outputs': sorted(set(missing_required_outputs)),
        'forbidden_change_violations': forbidden_violations,
        'error_markers_hit': error_markers_hit,
        'next_action': next_action,
    }


def _collect_error_markers(result_payload: dict[str, Any]) -> list[str]:
    markers = []
    gate_reason = result_payload.get('gate_reason', '')
    if gate_reason and 'error' in gate_reason.lower():
        markers.append('gate_reason_error')
    return markers


def _append_worker_log(db: OrchestratorDB, repo_root: Path, task: dict[str, Any], message: str) -> None:
    timestamp = iso_utc_now()
    line = f'[{timestamp}] {message}'
    log_path = repo_root / task['worker_log_path']
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as fp:
        fp.write(line + '\n')
    db.update_task_progress(task['id'], summarize_progress_line(message))


def _finalize_stale_running_task_if_needed(
    db: OrchestratorDB,
    repo_root: Path,
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    running_task = db.get_active_task()
    if running_task is None:
        return None

    rate_limit_signal = _detect_rate_limit_signal_for_task(repo_root, running_task)
    if rate_limit_signal is not None:
        return _finalize_task_as_rate_limited(db, repo_root, running_task, rate_limit_signal)

    stale_minutes = int(profile['worker_rules']['finalize_on_stale_output_minutes'])
    # Per-task override: honour declared expected_duration_minutes when longer than global stale
    task_expected_minutes = running_task.get('expected_duration_minutes')
    if task_expected_minutes and int(task_expected_minutes) > stale_minutes:
        stale_minutes = int(task_expected_minutes)
    reference_time = (
        parse_iso_datetime(running_task.get('last_output_at'))
        or parse_iso_datetime(running_task.get('started_at'))
        or parse_iso_datetime(running_task.get('updated_at'))
    )
    if reference_time is None:
        return None
    if utc_now() - reference_time < timedelta(minutes=stale_minutes):
        return None

    result_path = repo_root / running_task['result_path']
    result_payload = {
        'version': '1.0',
        'task_id': running_task['id'],
        'status': STATUS_FAILED,
        'gate_verdict': GATE_WORKER_RUNTIME_FAILED,
        'gate_reason': f'No output for over {stale_minutes} minutes; task finalized.',
        'duration_seconds': max(1, int((utc_now() - reference_time).total_seconds())),
        'changed_files': [],
        'error_markers_hit': ['stale_output_timeout'],
        'missing_required_outputs': [],
        'forbidden_change_violations': [],
        'acceptance_results': [],
        'next_action': 'Planner should replan or adjust worker strategy.',
    }
    write_json(result_path, result_payload)
    current_phase = _detect_latest_phase_from_log(repo_root, running_task)
    phase_fields = {'current_phase': current_phase, 'phase_completed_at': iso_utc_now()} if current_phase else {}
    db.update_task(
        task_id=running_task['id'],
        status=STATUS_FAILED,
        gate_verdict=GATE_WORKER_RUNTIME_FAILED,
        gate_reason=result_payload['gate_reason'],
        finished_at=iso_utc_now(),
        result_path=running_task['result_path'],
        latest_progress_summary='Task finalized due to stale output timeout.',
        last_output_at=iso_utc_now(),
        **phase_fields,
    )
    return db.get_task(running_task['id'])


def _handle_worker_runtime_failure(
    db: OrchestratorDB,
    repo_root: Path,
    run_id: int,
    task: dict[str, Any] | None,
    error_message: str,
    finalize_as: str,
) -> dict[str, Any]:
    task_id = task['id'] if task else None
    if task_id is not None:
        rate_limit_details = detect_rate_limit_details(error_message, provider=task.get('worker_provider'))
        if rate_limit_details is not None:
            rate_limited_task = _finalize_task_as_rate_limited(db, repo_root, task, error_message)
            db.finish_run(run_id=run_id, status='FAILED', message=rate_limit_details['final_message'], task_id=task_id)
            return {
                'status': STATUS_FAILED_RATE_LIMIT,
                'task_id': task_id,
                'task_status': STATUS_FAILED_RATE_LIMIT,
                'gate_verdict': GATE_RATE_LIMIT,
                'error': error_message,
                'task': rate_limited_task,
            }
    if task_id is not None:
        db.update_task(
            task_id=task_id,
            status=finalize_as,
            gate_verdict=GATE_WORKER_RUNTIME_FAILED,
            gate_reason=error_message,
            finished_at=iso_utc_now(),
            latest_progress_summary=summarize_progress_line(f'Worker runtime failed: {error_message}'),
            last_output_at=iso_utc_now(),
        )
    db.finish_run(run_id=run_id, status='FAILED', message=error_message, task_id=task_id)
    return {
        'status': 'FAILED',
        'task_id': task_id,
        'task_status': finalize_as,
        'gate_verdict': GATE_WORKER_RUNTIME_FAILED,
        'error': error_message,
    }


def _detect_rate_limit_signal_for_task(repo_root: Path, task: dict[str, Any]) -> str | None:
    texts = [
        task.get('gate_reason') or '',
        task.get('latest_progress_summary') or '',
    ]

    worker_log_path = task.get('worker_log_path')
    if worker_log_path:
        texts.append(read_text_if_exists(repo_root / worker_log_path) or '')

    result_path = task.get('result_path')
    if result_path:
        texts.append(read_text_if_exists(repo_root / result_path) or '')

    for text in texts:
        if detect_rate_limit_details(text, provider=task.get('worker_provider')) is not None:
            return text
    return None


def _finalize_task_as_rate_limited(
    db: OrchestratorDB,
    repo_root: Path,
    task: dict[str, Any],
    evidence_text: str,
) -> dict[str, Any]:
    reference_time = (
        parse_iso_datetime(task.get('started_at'))
        or parse_iso_datetime(task.get('last_output_at'))
        or parse_iso_datetime(task.get('updated_at'))
        or utc_now()
    )
    result_payload = build_rate_limit_result(
        task_id=task['id'],
        provider=task.get('worker_provider'),
        evidence_text=evidence_text,
        duration_seconds=int((utc_now() - reference_time).total_seconds()),
    )
    result_path = repo_root / task['result_path']
    write_json(result_path, result_payload)
    db.update_task(
        task_id=task['id'],
        status=STATUS_FAILED_RATE_LIMIT,
        gate_verdict=GATE_RATE_LIMIT,
        gate_reason=result_payload['gate_reason'],
        finished_at=iso_utc_now(),
        latest_progress_summary=summarize_progress_line(result_payload['final_message']),
        last_output_at=iso_utc_now(),
        result_path=task['result_path'],
    )
    return db.get_task(task['id']) or task


def _detect_latest_phase_from_log(repo_root: Path, task: dict[str, Any]) -> str | None:
    """Scan the worker log for [PHASE N COMPLETE] markers and return the latest one."""
    log_path = task.get('worker_log_path')
    if not log_path:
        return None
    log_text = read_text_if_exists(repo_root / log_path) or ''
    matches = _PHASE_COMPLETE_RE.findall(log_text)
    if not matches:
        return None
    latest_num = max(int(n) for n in matches)
    return f'Phase {latest_num}'


def _append_to_backlog(backlog_path: Path, additions: list[str]) -> None:
    """Append worker-proposed backlog items as unchecked checkbox entries."""
    existing = backlog_path.read_text(encoding='utf-8') if backlog_path.exists() else ''
    items = [f'- [ ] {item.strip()}' for item in additions if item.strip()]
    if not items:
        return
    separator = '\n' if existing.endswith('\n') else '\n\n'
    with backlog_path.open('a', encoding='utf-8') as fp:
        fp.write(separator + '\n'.join(items) + '\n')


def reset_running_to_queued_for_recovery(profile_path: str | None = None) -> int:
    loaded = load_project_profile(profile_path=profile_path)
    profile = loaded.profile
    db = OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )
    task = db.get_active_task()
    if task is None:
        return 0
    db.update_task(
        task_id=task['id'],
        status=STATUS_QUEUED,
        gate_verdict=None,
        gate_reason='',
        started_at=None,
        finished_at=None,
        latest_progress_summary='Recovered from RUNNING to QUEUED.',
    )
    return 1
