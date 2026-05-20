from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.orchestrator.common import (
    GATE_RATE_LIMIT,
    STATUS_FAILED_RATE_LIMIT,
    STATUS_QUEUED,
    STATUS_REPLAN_REQUIRED,
    STATUS_RUNNING,
    build_rate_limit_result,
    detect_rate_limit_details,
    build_task_paths,
    iso_utc_now,
    load_project_profile,
    make_task_uid,
    parse_iso_datetime,
    read_json,
    read_text_if_exists,
    slugify,
    summarize_progress_line,
    utc_now,
    write_json,
)
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.execution_policy import evaluate_llm_execution
from app.orchestrator.regime_classifier import classify_regime
from app.orchestrator.problem_signal import (
    detect_product_issues,
    build_problem_task_draft_markdown,
    get_recently_completed_signatures,
    SIGNATURE_COOLDOWN_DAYS,
)
from app.orchestrator.task_pool import (
    CATEGORIES as POOL_CATEGORIES,
    build_task_draft as build_pool_draft,
    get_task_pool_info,
    pick_next_category,
)
from app.orchestrator.task_quality_gate import BANNED_PATTERNS, TaskDraft, evaluate_task_draft, extract_task_drafts
from app.orchestrator.task_result_quality_gate import extract_draft_dimension

# Maximum number of fallback attempts through the pool when the primary draft is rejected
_MAX_FALLBACK_ATTEMPTS = len(POOL_CATEGORIES)


def run_planner_tick(
    profile_path: str | None = None,
    run_type: str = 'manual',
    product_signals: dict[str, Any] | None = None,
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
            return {'status': 'PLANNER_SKIP_HARD_OFF', 'reason': policy.message, 'policy_code': policy.code}
        if policy.code == 'GLOBAL_SCHEDULER_DISABLED':
            return {'status': 'PLANNER_SKIP_DISABLED', 'reason': policy.message, 'policy_code': policy.code}
        return {'status': 'PLANNER_SKIP_SAFE_RUN', 'reason': policy.message, 'policy_code': policy.code}

    planner_provider = db.get_planner_provider()
    worker_provider = db.get_worker_provider()

    run_id = db.create_run(role='planner', run_type=run_type)
    task_id: int | None = None
    try:
        latest_task = db.get_latest_task()
        if latest_task is not None:
            latest_task = _finalize_rate_limited_task_if_needed(db, loaded.repo_root, latest_task)
        if latest_task and latest_task['status'] == STATUS_RUNNING and profile['planner_rules']['skip_if_latest_running']:
            message = f"跳過：任務 #{latest_task['id']} 仍在執行中（RUNNING），本次跳過規劃。"
            db.finish_run(run_id=run_id, status='SKIPPED', message=message, task_id=latest_task['id'])
            return {'status': 'SKIPPED', 'reason': message}

        previous_result = _load_previous_result_if_required(
            loaded.repo_root,
            latest_task,
            must_read=profile['planner_rules']['must_read_previous_result'],
        )

        recent_tasks = db.list_tasks(limit=50)
        regime_info = classify_regime(recent_tasks)

        # ── Try primary draft, then fall back through the pool ────────────────
        task_draft, quality, fallback_info = _choose_passing_draft(
            profile=profile,
            repo_root=loaded.repo_root,
            latest_task=latest_task,
            previous_result=previous_result,
            recent_tasks=recent_tasks,
            product_signals=product_signals,
        )

        if not quality.passed:
            message = '; '.join(quality.reasons)
            db.finish_run(run_id=run_id, status='REJECTED', message=message, task_id=None)
            return {
                'status': 'REJECTED',
                'quality_status': quality.quality_status,
                'reasons': quality.reasons,
                'objective': task_draft.title,
                'fallback_tried': fallback_info.get('fallback_tried', False),
                'fallback_category': fallback_info.get('fallback_category'),
                'next_candidate_category': fallback_info.get('next_candidate_category'),
            }

        objective = task_draft.title
        slug = slugify(objective)
        task_uid = make_task_uid()
        task_paths = build_task_paths(loaded=loaded, task_uid=task_uid, slug=slug)
        prompt_content = _build_prompt_markdown(profile, task_draft, previous_result, latest_task, regime_info)
        contract = _build_contract(profile, task_draft, latest_task, previous_result)
        meta = {
            'task_uid': task_uid,
            'objective': objective,
            'task_draft_markdown': task_draft.draft_markdown,
            'quality_status': quality.quality_status,
            'planner_provider': planner_provider,
            'worker_provider': worker_provider,
            'created_at': iso_utc_now(),
            'run_type': run_type,
            'previous_task_id': latest_task['id'] if latest_task else None,
            'previous_task_status': latest_task['status'] if latest_task else None,
            'task_category': task_draft.category,
            'duplicate_signature': task_draft.duplicate_signature,
            'fallback_info': fallback_info,
        }

        prompt_path = loaded.repo_root / task_paths['prompt_path']
        contract_path = loaded.repo_root / task_paths['contract_path']
        meta_path = loaded.repo_root / task_paths['meta_path']
        worker_log_path = loaded.repo_root / task_paths['worker_log_path']

        prompt_path.write_text(prompt_content, encoding='utf-8')
        write_json(contract_path, contract)
        write_json(meta_path, meta)
        worker_log_path.parent.mkdir(parents=True, exist_ok=True)
        worker_log_path.touch(exist_ok=True)

        task_id = db.create_task(
            {
                'task_uid': task_uid,
                'title': objective,
                'objective': objective,
                'status': STATUS_QUEUED,
                'gate_verdict': None,
                'gate_reason': '',
                'planner_provider': planner_provider,
                'worker_provider': worker_provider,
                'task_dir': task_paths['task_dir'],
                'prompt_path': task_paths['prompt_path'],
                'contract_path': task_paths['contract_path'],
                'worker_log_path': task_paths['worker_log_path'],
                'completed_path': task_paths['completed_path'],
                'result_path': task_paths['result_path'],
                'meta_path': task_paths['meta_path'],
                'latest_progress_summary': '已由規劃器排入佇列。',
                'last_output_at': iso_utc_now(),
                'focus_keys': json.dumps(list(task_draft.focus_keys)) if task_draft.focus_keys else None,
                'expected_duration_minutes': task_draft.expected_duration_minutes,
                'duplicate_signature': task_draft.duplicate_signature,
                'category': task_draft.category,
            }
        )
        meta['task_id'] = task_id
        write_json(meta_path, meta)

        db.finish_run(
            run_id=run_id,
            status='COMPLETED',
            message=f'已建立任務 #{task_id}：{objective}',
            task_id=task_id,
        )
        return {
            'status': 'CREATED',
            'task_id': task_id,
            'objective': objective,
            'category': task_draft.category,
            'duplicate_signature': task_draft.duplicate_signature,
            'fallback_info': fallback_info,
        }
    except Exception as exc:
        db.finish_run(run_id=run_id, status='FAILED', message=str(exc), task_id=task_id)
        return {'status': 'FAILED', 'error': str(exc), 'task_id': task_id}


def _finalize_rate_limited_task_if_needed(
    db: OrchestratorDB,
    repo_root: Path,
    latest_task: dict[str, Any],
) -> dict[str, Any]:
    if latest_task['status'] == STATUS_FAILED_RATE_LIMIT:
        return latest_task

    evidence_sources = [
        latest_task.get('gate_reason') or '',
        latest_task.get('latest_progress_summary') or '',
    ]
    if latest_task.get('worker_log_path'):
        evidence_sources.append(read_text_if_exists(repo_root / latest_task['worker_log_path']) or '')
    if latest_task.get('result_path'):
        evidence_sources.append(read_text_if_exists(repo_root / latest_task['result_path']) or '')

    evidence_text = next(
        (
            text
            for text in evidence_sources
            if detect_rate_limit_details(text, provider=latest_task.get('worker_provider')) is not None
        ),
        None,
    )
    if evidence_text is None:
        return latest_task

    reference_time = (
        parse_iso_datetime(latest_task.get('started_at'))
        or parse_iso_datetime(latest_task.get('last_output_at'))
        or parse_iso_datetime(latest_task.get('updated_at'))
        or utc_now()
    )
    result_payload = build_rate_limit_result(
        task_id=latest_task['id'],
        provider=latest_task.get('worker_provider'),
        evidence_text=evidence_text,
        duration_seconds=int((utc_now() - reference_time).total_seconds()),
    )
    write_json(repo_root / latest_task['result_path'], result_payload)
    db.update_task(
        task_id=latest_task['id'],
        status=STATUS_FAILED_RATE_LIMIT,
        gate_verdict=GATE_RATE_LIMIT,
        gate_reason=result_payload['gate_reason'],
        finished_at=iso_utc_now(),
        latest_progress_summary=summarize_progress_line(result_payload['final_message']),
        last_output_at=iso_utc_now(),
        result_path=latest_task['result_path'],
    )
    return db.get_task(latest_task['id']) or latest_task


def _load_previous_result_if_required(
    repo_root: Path,
    latest_task: dict[str, Any] | None,
    must_read: bool,
) -> dict[str, Any] | None:
    if not must_read or not latest_task:
        return None
    result_path = latest_task.get('result_path')
    if not result_path:
        return None
    absolute = repo_root / result_path
    if not absolute.exists():
        return None
    try:
        return read_json(absolute)
    except json.JSONDecodeError:
        return None


def _choose_passing_draft(
    profile: dict[str, Any],
    repo_root: Path,
    latest_task: dict[str, Any] | None,
    previous_result: dict[str, Any] | None,
    recent_tasks: list[dict[str, Any]],
    product_signals: dict[str, Any] | None = None,
) -> tuple['TaskDraft', 'QualityGateResult', dict[str, Any]]:
    """Select a task draft that passes the quality gate.

    Planner order per product spec:
    1. Handle REPLAN_REQUIRED first (recovery path).
    2. High-severity product issues from real user engagement signals.
    3. Backlog candidates (stale/corrupted safety items).
    4. Fall back through the task pool (rotating category).
    Returns (draft, quality_result, fallback_info).
    """
    from app.orchestrator.task_quality_gate import QualityGateResult  # local to avoid circular

    fallback_info: dict[str, Any] = {
        'source': 'backlog',
        'fallback_tried': False,
        'fallback_category': None,
        'next_candidate_category': None,
        'rejection_reasons': [],
    }

    # ── 1. Replan takes priority ──────────────────────────────────────────────
    if (
        latest_task
        and latest_task['status'] == STATUS_REPLAN_REQUIRED
        and profile['planner_rules']['retry_replan_required_first']
    ):
        gate_reason = ''
        if previous_result:
            gate_reason = previous_result.get('gate_reason', '')
        suffix = f' (reason: {gate_reason})' if gate_reason else ''
        title = f"Replan task #{latest_task['id']}: {latest_task['objective']}{suffix}"
        draft = TaskDraft(title=title, draft_markdown=title)
        # Replan drafts skip the quality gate so we give them a synthetic PASS
        quality = QualityGateResult(quality_status='PASS', reasons=[])
        fallback_info['source'] = 'replan'
        return draft, quality, fallback_info

    # ── 2. High-severity product signal issues ────────────────────────────────
    # Real user engagement metrics take priority over static backlog items.
    # Only high-severity signals pre-empt the backlog; medium/low are handled
    # in step 2.5 after the backlog is checked.
    from app.orchestrator.task_pool import _TASK_TEMPLATES  # type: ignore[attr-defined]
    pool_sig_to_cat: dict[str, str] = {
        tmpl['duplicate_signature']: cat
        for cat, tmpl in _TASK_TEMPLATES.items()
    }
    all_issues = detect_product_issues(
        recent_tasks, all_pool_signatures=pool_sig_to_cat, product_signals=product_signals
    )
    high_severity_issues = [i for i in all_issues if i['severity'] == 'high']
    for issue in high_severity_issues:
        problem_markdown = build_problem_task_draft_markdown(issue)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        problem_sig = f'problem_{issue["issue_type"]}_{today}'
        problem_draft = TaskDraft(
            title=problem_markdown.splitlines()[0].strip(),
            draft_markdown=problem_markdown,
            duplicate_signature=problem_sig,
            category=issue.get('suggested_category') or 'problem_signal',
        )
        problem_quality = evaluate_task_draft(problem_draft, recent_tasks=recent_tasks)
        if problem_quality.passed:
            fallback_info['source'] = 'product_signal_high'
            fallback_info['fallback_tried'] = True
            fallback_info['detected_issue'] = issue['issue_type']
            fallback_info['issue_severity'] = issue['severity']
            return problem_draft, problem_quality, fallback_info

    # ── 3. Try backlog candidates (stale/corrupted safety items) ──────────────
    active_titles: set[str] = {
        _norm(str(t.get('objective') or t.get('title') or ''))
        for t in recent_tasks
        if str(t.get('status') or '') in {'QUEUED', 'RUNNING', 'REPLAN_REQUIRED'}
    }

    backlog_path = repo_root / profile['backlog_path']
    backlog_content = backlog_path.read_text(encoding='utf-8') if backlog_path.exists() else ''
    all_candidates = extract_task_drafts(backlog_content)
    # Filter out items whose title is already active in the DB
    candidates = [c for c in all_candidates if _norm(c.title) not in active_titles]

    if candidates:
        draft = candidates[0]
        quality = evaluate_task_draft(draft, recent_tasks=recent_tasks)
        if quality.passed:
            return draft, quality, fallback_info
        # Primary backlog candidate was rejected — remember why and fall through
        fallback_info['rejection_reasons'] = list(quality.reasons)

    # ── 3.5. Medium/low severity product signal issues ────────────────────
    medium_low_issues = [i for i in all_issues if i['severity'] != 'high']
    for issue in medium_low_issues:
        problem_markdown = build_problem_task_draft_markdown(issue)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        problem_sig = f'problem_{issue["issue_type"]}_{today}'
        problem_draft = TaskDraft(
            title=problem_markdown.splitlines()[0].strip(),
            draft_markdown=problem_markdown,
            duplicate_signature=problem_sig,
            category=issue.get('suggested_category') or 'problem_signal',
        )
        problem_quality = evaluate_task_draft(problem_draft, recent_tasks=recent_tasks)
        if problem_quality.passed:
            fallback_info['source'] = 'problem_signal'
            fallback_info['fallback_tried'] = True
            fallback_info['detected_issue'] = issue['issue_type']
            fallback_info['issue_severity'] = issue['severity']
            return problem_draft, problem_quality, fallback_info

    # ── 4. Fall back through task pool ───────────────────────────────────────
    fallback_info['fallback_tried'] = True
    fallback_info['source'] = 'task_pool'

    last_category = str(latest_task.get('category') or '') if latest_task else ''
    tried_categories: set[str] = set()

    for _ in range(_MAX_FALLBACK_ATTEMPTS):
        category = pick_next_category(recent_tasks, last_used_category=last_category or None)
        if category in tried_categories:
            break
        tried_categories.add(category)
        fallback_info['fallback_category'] = category

        draft = build_pool_draft(category)
        quality = evaluate_task_draft(draft, recent_tasks=recent_tasks)
        if quality.passed:
            # Indicate what the next category would be for UI display
            remaining = [c for c in POOL_CATEGORIES if c != category]
            fallback_info['next_candidate_category'] = (
                pick_next_category(recent_tasks, last_used_category=category)
                if remaining else None
            )
            return draft, quality, fallback_info

        # Rejected again — mark that category as "last used" to rotate away from it
        last_category = category

    # ── 4. All options exhausted — return the last draft with its rejection ───
    return draft, quality, fallback_info


def _norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())


def _choose_task_draft(
    profile: dict[str, Any],
    repo_root: Path,
    latest_task: dict[str, Any] | None,
    previous_result: dict[str, Any] | None,
) -> 'TaskDraft':
    """Legacy helper kept for backward compatibility with tests that call it directly."""
    if (
        latest_task
        and latest_task['status'] == STATUS_REPLAN_REQUIRED
        and profile['planner_rules']['retry_replan_required_first']
    ):
        gate_reason = ''
        if previous_result:
            gate_reason = previous_result.get('gate_reason', '')
        suffix = f' (reason: {gate_reason})' if gate_reason else ''
        title = f"Replan task #{latest_task['id']}: {latest_task['objective']}{suffix}"
        return TaskDraft(title=title, draft_markdown=title)

    backlog_path = repo_root / profile['backlog_path']
    backlog_content = backlog_path.read_text(encoding='utf-8') if backlog_path.exists() else ''
    candidates = extract_task_drafts(backlog_content)
    if candidates:
        return candidates[0]
    fallback = 'Validate orchestrator safety gate and prepare next delivery task.'
    return TaskDraft(title=fallback, draft_markdown=fallback)


def _build_prompt_markdown(
    profile: dict[str, Any],
    task_draft: TaskDraft,
    previous_result: dict[str, Any] | None,
    latest_task: dict[str, Any] | None,
    regime_info: dict[str, Any] | None = None,
) -> str:
    scope = [
        'Read backlog and project references listed in project profile.',
        'Implement only what is required to satisfy this task objective.',
        'Produce both human-readable and machine-readable delivery artifacts.',
    ]
    constraints = [
        'Do not modify protected paths from project profile.',
        'Do not leave the task in RUNNING when blocked by runtime/permission issues.',
        'Keep changes focused and production-safe.',
    ]
    acceptance = [f'Pass required check: {item}' for item in profile['required_checks']]
    acceptance.append('No forbidden path modifications.')

    previous_summary = 'None'
    if latest_task:
        previous_summary = f"Latest task #{latest_task['id']} status={latest_task['status']} objective={latest_task['objective']}"
    if previous_result:
        previous_summary += f"\nLatest gate verdict={previous_result.get('gate_verdict')} reason={previous_result.get('gate_reason', '')}"

    lines = [
        '# Planner Task Prompt',
        '',
        '## Objective',
        task_draft.title,
        '',
        '## Task Draft',
        task_draft.draft_markdown,
        '',
        '## Scope',
        *[f'- {item}' for item in scope],
        '',
        '## Constraints',
        *[f'- {item}' for item in constraints],
        '',
        '## Acceptance Criteria',
        *[f'- {item}' for item in acceptance],
        '',
        '## Handoff Notes',
        '- Record changed files in task_result.json.',
        '- Attach evidence for each acceptance check.',
        '- Keep next_action clear for the next planner tick.',
        '',
    ]

    if regime_info:
        stats = regime_info.get('stats', {})
        lines += [
            '## System State',
            '| 項目 | 値 |',
            '|------|----|',
            f"| Regime | `{regime_info.get('regime', 'UNKNOWN')}` |",
            f"| 信心度 | {regime_info.get('confidence', 0):.2f} |",
            f"| Pass Rate | {stats.get('pass_rate', 0):.0%} |",
            f"| 失敗率 | {stats.get('failure_rate', 0):.0%} |",
            f"| 近期任務數 | {stats.get('total', 0)} |",
            '',
            f"> {regime_info.get('reason', '')}",
            '',
        ]

    if task_draft.focus_keys:
        lines += [
            '## Focus Keys',
            ', '.join(task_draft.focus_keys),
            '',
        ]

    if task_draft.expected_duration_minutes:
        lines += [
            '## Expected Duration',
            f'{task_draft.expected_duration_minutes} minutes ({task_draft.expected_duration_minutes / 60:.1f}h)',
            '',
        ]

    lines += [
        '## Previous Context',
        previous_summary,
        '',
    ]
    return '\n'.join(lines)


def _build_contract(
    profile: dict[str, Any],
    task_draft: TaskDraft,
    latest_task: dict[str, Any] | None,
    previous_result: dict[str, Any] | None,
) -> dict[str, Any]:
    previous_gate = previous_result.get('gate_verdict') if previous_result else None
    previous_reason = previous_result.get('gate_reason') if previous_result else ''

    handoff_questions = [
        'What is the next highest-priority backlog item after this task?',
        'Did the worker leave any unresolved risk that needs a replan?',
    ]
    if latest_task:
        handoff_questions.append(f"How should planner handle follow-up for task #{latest_task['id']}?")

    constraints = [
        'Do not touch forbidden paths.',
        'Do not claim acceptance without evidence.',
    ]
    if BANNED_PATTERNS:
        forbidden_tokens = ', '.join(f'"{p}"' for p in BANNED_PATTERNS)
        constraints.append(
            f'禁止在任何輸出中包含以下詞句：{forbidden_tokens}。每個 Focus 必須有獨立的量化結論。'
        )
    if task_draft.focus_keys:
        constraints.append(
            f"本次 Focus 方向：{', '.join(task_draft.focus_keys)}。每個方向需獨立輸出量化結果。"
        )

    return {
        'version': '1.0',
        'objective': task_draft.title,
        'task_draft_markdown': task_draft.draft_markdown,
        'focus_keys': list(task_draft.focus_keys),
        'expected_duration_minutes': task_draft.expected_duration_minutes,
        'user_value': extract_draft_dimension(task_draft.draft_markdown, 'User Value'),
        'product_maturity_impact': extract_draft_dimension(task_draft.draft_markdown, 'Product Maturity Impact'),
        'expected_change': extract_draft_dimension(task_draft.draft_markdown, 'Expected Change'),
        'scope': [
            'Complete the smallest meaningful increment toward the objective.',
            'Leave machine-readable artifacts for orchestrator validation.',
        ],
        'constraints': constraints,
        'acceptance_tests': profile['required_checks'] + ['forbidden_paths_unchanged'],
        'required_outputs': ['completed_markdown', 'task_result_json', 'changed_files_list'],
        'optional_outputs': ['backlog_additions'],
        'forbidden_changes': profile['protected_paths'],
        'handoff_questions': handoff_questions,
        'planner_context': {
            'previous_gate_verdict': previous_gate,
            'previous_gate_reason': previous_reason,
        },
    }
