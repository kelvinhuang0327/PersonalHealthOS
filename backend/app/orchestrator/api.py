from __future__ import annotations

import json
import threading
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.orchestrator.common import (
    WORKER_COPILOT_MODEL_PRESETS,
    copilot_daemon_status,
    planner_provider_options,
    provider_available,
    provider_label,
    iso_utc_now,
    load_project_profile,
    read_text_if_exists,
    utc_now,
    validate_copilot_model,
    worker_provider_options,
)
from app.orchestrator.cto_review_tick import run_cto_review_tick
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.execution_policy import LLM_MODE_HARD_OFF, LLM_MODE_SAFE_RUN, get_llm_control_state
from app.orchestrator.planner_tick import run_planner_tick
from app.orchestrator.scheduler import force_scheduler_run_at_once, scheduler_running, start_scheduler, stop_scheduler
from app.orchestrator.task_pool import CATEGORIES as POOL_CATEGORIES, get_task_pool_info
from app.orchestrator.worker_tick import run_worker_tick

router = APIRouter(
    prefix='/orchestrator',
    tags=['agent-orchestrator'],
    dependencies=[Depends(get_current_user)],
)

# ── Request models ────────────────────────────────────────────────────────────


class RunNowRequest(BaseModel):
    runner: Optional[Literal['planner', 'worker']] = None
    role: Optional[Literal['planner', 'worker']] = None  # backward compat alias
    simulate_invalid_delivery: bool = False


class SchedulerUpdateRequest(BaseModel):
    enabled: bool
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)


class ProviderUpdateRequest(BaseModel):
    planner_provider: Optional[Literal['codex', 'claude']] = None
    worker_provider: Optional[Literal['codex', 'claude', 'copilot', 'copilot-daemon']] = None
    worker_copilot_model: Optional[str] = None


class CtoRunNowRequest(BaseModel):
    force: bool = False
    run_intent: Optional[Literal['retry', 'compare', 'override']] = None
    parent_run_id: Optional[str] = None


class CtoSchedulerRequest(BaseModel):
    enabled: bool


class LlmControlRequest(BaseModel):
    mode: Literal['safe-run', 'hard-off']


class CtoProviderRequest(BaseModel):
    planner_provider: Optional[str] = None
    planner_model: Optional[str] = None


class BacklogItemRequest(BaseModel):
    cto_run_id: str
    task_id: Optional[int] = None
    category: Optional[str] = 'quality'
    severity: Optional[str] = 'MEDIUM'
    impact_score: Optional[int] = 50
    urgency: Optional[str] = 'normal'
    suggested_action: Optional[str] = ''
    finding_id: Optional[str] = None


class BatchBacklogRequest(BaseModel):
    cto_run_id: str
    min_severity: str = 'HIGH'
    min_impact: int = 60


class ExecutionPolicyRequest(BaseModel):
    mode: Literal['balanced', 'strict_priority', 'fairness']


# ── Provider constants ────────────────────────────────────────────────────────

_PLANNER_OPTIONS = [
    {'value': 'claude', 'label': 'Claude CLI'},
    {'value': 'codex', 'label': 'Codex CLI'},
]
_COPILOT_MODEL_PRESETS = ['claude-sonnet-4-5', 'gpt-4o', 'o1-mini', 'o3-mini']

_CATEGORY_LABELS: dict[str, str] = {
    'behavior_loop_optimization': '行為改變循環',
    'ux_flow_redesign': 'UX 流程優化',
    'action_system_enhancement': '行動建議系統',
    'decision_engine_improvement': '決策引擎',
    'health_narrative_deepening': '健康敘事',
    'user_journey_analysis': '用戶旅程',
    'retention_habit_loop': '習慣留存',
    'notifications_lifecycle': '通知生命週期',
    'reports_product_value': '報告價值',
    'timeline_history_value': '歷史時間軸',
    'growth_analytics': '成長分析',
    'cross_page_consistency': '跨頁一致性',
}


def _db_for_profile(profile_path: Optional[str] = None) -> tuple[Any, OrchestratorDB]:
    loaded = load_project_profile(profile_path=profile_path)
    profile = loaded.profile
    db = OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )
    return loaded, db


def _run_to_api(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise a runs-table row to match SOURCE API shape for UI compatibility."""
    return {
        'id': row.get('id'),
        'runner': row.get('role'),
        'tick_at': row.get('started_at'),
        'outcome': row.get('outcome') or row.get('status') or '—',
        'request_id': row.get('request_id'),
        'task_id': row.get('task_id'),
        'message': row.get('message', ''),
        'run_type': row.get('run_type'),
        'started_at': row.get('started_at'),
        'finished_at': row.get('finished_at'),
    }



@router.get('/summary')
def get_orchestrator_summary(profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()
    latest_task = db.get_latest_task()
    task_counts = db.get_task_counts()
    total_today = sum(task_counts.values())
    running = task_counts.get('RUNNING', 0)
    completed = task_counts.get('COMPLETED', 0)

    # Get next tick estimates from recent runs
    # Compute fresh estimate: if the stored timestamp is in the past, show now+interval
    # so the UI never shows a stale "2 days ago" value after a backend restart.
    from datetime import datetime, timedelta, timezone as _tz

    def _fresh_estimate(stored_iso: str | None, interval_minutes: int) -> str | None:
        if not stored_iso:
            return None
        try:
            parsed = datetime.fromisoformat(str(stored_iso).replace('Z', '+00:00'))
            now = datetime.now(_tz.utc)
            if parsed < now:
                # Timestamp is in the past — scheduler will fire imminently; show projected next run
                return (now + timedelta(minutes=interval_minutes)).isoformat()
            return stored_iso
        except (ValueError, AttributeError):
            return stored_iso

    next_planner_est = _fresh_estimate(state.get('next_planner_run_at'), int(state['planner_interval_minutes']))
    next_worker_est = _fresh_estimate(state.get('next_worker_run_at'), int(state['worker_interval_minutes']))

    # Copilot daemon status
    daemon = copilot_daemon_status(repo_root=loaded.repo_root)

    # Running task for worker_task_id
    running_tasks, _ = db.list_tasks_filtered(limit=1, offset=0, status='RUNNING')
    worker_task_id = running_tasks[0]['id'] if running_tasks else None

    planner_prov = db.get_planner_provider() or state.get('planner_provider', 'codex')
    worker_prov = db.get_worker_provider() or state.get('worker_provider', 'codex')
    combo_label = f'{provider_label(planner_prov)} Planner + {provider_label(worker_prov)} Worker'
    llm_control = get_llm_control_state(profile_path=profile_path)

    if running > 0:
        worker_state = '執行中'
    elif daemon.get('running'):
        worker_state = '待命中'
    else:
        worker_state = '閒置'

    return {
        'project_name': loaded.profile['project_name'],
        'project_slug': loaded.profile['project_slug'],
        'today': iso_utc_now()[:10].replace('-', ''),
        'scheduler': {
            'enabled': state['enabled'],
            'loop_running': scheduler_running(),
            'planner_interval_minutes': state['planner_interval_minutes'],
            'worker_interval_minutes': state['worker_interval_minutes'],
            'next_planner_run_at': state['next_planner_run_at'],
            'next_worker_run_at': state['next_worker_run_at'],
            'planner_provider': planner_prov,
            'worker_provider': worker_prov,
        },
        'scheduler_enabled': state['enabled'],
        'task_counts': task_counts,
        'total_today': total_today,
        'total_running': running,
        'total_completed': completed,
        'worker_busy': running > 0,
        'worker_pid': None,
        'worker_task_id': worker_task_id,
        'worker_state': worker_state,
        'planner_provider': planner_prov,
        'worker_provider': worker_prov,
        'combo_label': combo_label,
        'llm_control': llm_control,
        'copilot_daemon_running': daemon.get('running', False),
        'copilot_daemon_pid': daemon.get('pid'),
        'copilot_daemon_status': daemon.get('reason', '未啟動'),
        'copilot_daemon_task_id': None,
        'next_planner_tick_estimate': next_planner_est,
        'next_worker_tick_estimate': next_worker_est,
        'latest_task': latest_task,
    }


@router.get('/dashboard-summary')
def get_dashboard_summary(profile_path: Optional[str] = None):
    """Lightweight product-friendly summary for the Dashboard panel."""
    from collections import Counter
    _, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()
    task_counts = db.get_task_counts()
    latest_task = db.get_latest_task()

    # Derive category completion counts from recent COMPLETED tasks
    completed_tasks, _ = db.list_tasks_filtered(limit=30, offset=0, status='COMPLETED')
    category_counter: Counter[str] = Counter()
    for t in completed_tasks:
        cat = t.get('category') or ''
        if cat:
            category_counter[cat] += 1

    top_categories = [
        {
            'category': cat,
            'label': _CATEGORY_LABELS.get(cat, cat),
            'completed_count': count,
        }
        for cat, count in category_counter.most_common(3)
    ]

    latest = None
    if latest_task:
        cat = latest_task.get('category') or ''
        latest = {
            'id': latest_task.get('id'),
            'title': latest_task.get('title', ''),
            'category': cat,
            'category_label': _CATEGORY_LABELS.get(cat, cat) if cat else '',
            'status': latest_task.get('status', ''),
            'gate_verdict': latest_task.get('gate_verdict'),
        }

    recent_completed = [
        {
            'id': t.get('id'),
            'title': t.get('title', ''),
            'category': t.get('category') or '',
            'category_label': _CATEGORY_LABELS.get(t.get('category') or '', t.get('category') or ''),
            'gate_verdict': t.get('gate_verdict'),
            'finished_at': t.get('finished_at'),
        }
        for t in completed_tasks[:3]
    ]

    return {
        'scheduler_active': state['enabled'],
        'today_total': sum(task_counts.values()),
        'today_completed': task_counts.get('COMPLETED', 0),
        'today_running': task_counts.get('RUNNING', 0),
        'today_failed': task_counts.get('FAILED', 0) + task_counts.get('FAILED_RATE_LIMIT', 0),
        'today_replan': task_counts.get('REPLAN_REQUIRED', 0),
        'latest_task': latest,
        'top_categories': top_categories,
        'recent_completed': recent_completed,
    }


@router.get('/providers')
def get_providers(profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    planner = db.get_planner_provider()
    worker = db.get_worker_provider()
    worker_copilot_model = db.get_worker_copilot_model()
    return _provider_payload(
        planner_provider=planner,
        worker_provider=worker,
        worker_copilot_model=worker_copilot_model,
        repo_root=loaded.repo_root,
    )


@router.get('/tasks')
def list_orchestrator_tasks(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    # Support both limit/offset and page/page_size styles
    effective_limit = page_size if page_size != 20 else limit
    effective_offset = (page - 1) * effective_limit if page > 1 else offset
    tasks, total = db.list_tasks_filtered(
        limit=effective_limit,
        offset=effective_offset,
        status=status,
        date_folder=date,
    )
    total_pages = max(1, (total + effective_limit - 1) // effective_limit)
    return {
        'items': tasks,
        'tasks': tasks,
        'count': len(tasks),
        'limit': effective_limit,
        'offset': effective_offset,
        'total': total,
        'page': page,
        'page_size': effective_limit,
        'total_pages': total_pages,
    }


@router.get('/tasks/{task_id}')
def get_orchestrator_task_detail(task_id: int, profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f'Task #{task_id} not found')

    prompt_text = read_text_if_exists(loaded.repo_root / task['prompt_path'])
    completed_text = read_text_if_exists(loaded.repo_root / task['completed_path']) if task.get('completed_path') else None
    contract_text = read_text_if_exists(loaded.repo_root / task['contract_path'])
    result_text = read_text_if_exists(loaded.repo_root / task['result_path']) if task.get('result_path') else None
    worker_log_tail = _tail_text_file(loaded.repo_root / task['worker_log_path'], line_limit=50)

    contract_json = _parse_json_or_none(contract_text)
    result_json = _parse_json_or_none(result_text)

    return {
        'task': task,
        'prompt_markdown': prompt_text,
        'completed_markdown': completed_text,
        'contract_json': contract_json,
        'result_json': result_json,
        'worker_log_tail': worker_log_tail,
    }


@router.get('/runs')
def list_orchestrator_runs(
    limit: int = Query(default=20, ge=1, le=500),
    runner: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    rows = db.list_runs_by_role(role=runner, limit=limit, since=since, request_id=request_id)
    runs = [_run_to_api(r) for r in rows]
    return {'items': runs, 'runs': runs, 'count': len(runs), 'limit': limit}


@router.get('/run-status')
def get_run_status(
    request_id: str = Query(...),
    runner: Optional[str] = Query(default=None),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    row = db.get_run_by_request_id(request_id)
    if row is None:
        return {'status': 'PENDING', 'run': None, 'final': False}
    outcome = row.get('outcome') or row.get('status') or 'PENDING'
    finished = row.get('finished_at') is not None
    planner_terminal = {
        'PLANNER_PRODUCED', 'PLANNER_INVALID_CONTRACT',
        'PLANNER_SKIP_DISABLED', 'PLANNER_SKIP_NO_POOL', 'PLANNER_SKIP_ALL_ACTIVE',
        'PLANNER_SKIP_DUPLICATE', 'PLANNER_SKIP_RATE_LIMIT', 'PLANNER_SKIP_HARD_OFF',
        'PLANNER_SKIP_SAFE_RUN',
    }
    worker_terminal = {
        'WORKER_FINALIZED', 'WORKER_SKIP_DISABLED', 'WORKER_SKIP_NO_TASK',
        'WORKER_SKIP_BUSY', 'WORKER_SKIP_RATE_LIMIT', 'WORKER_SKIP_HARD_OFF',
        'WORKER_SKIP_SAFE_RUN',
    }
    legacy_terminal = {
        'COMPLETED', 'SKIPPED', 'FAILED', 'FAILED_RATE_LIMIT', 'REJECTED',
        'FINALIZED_STALE_TASK', 'NO_QUEUED_TASK', 'PENDING_REVIEW',
    }
    terminal_outcomes = planner_terminal | worker_terminal | legacy_terminal
    is_final = finished or outcome in terminal_outcomes
    return {
        'status': outcome,
        'run': _run_to_api(row),
        'final': is_final,
    }


@router.post('/run-now')
def run_orchestrator_now(
    payload: RunNowRequest,
    background_tasks: BackgroundTasks,
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    runner = payload.runner or payload.role or 'planner'
    run_db_id, request_id = db.create_run_with_request_id(runner, 'manual')

    def _do_run() -> None:
        try:
            if runner == 'planner':
                result = run_planner_tick(profile_path=profile_path, run_type='manual')
            else:
                result = run_worker_tick(
                    profile_path=profile_path,
                    run_type='manual',
                    simulate_invalid_delivery=payload.simulate_invalid_delivery,
                )
            outcome = result.get('status', 'COMPLETED')
            task_id = result.get('task_id')
            db.finish_run_with_outcome(run_db_id, 'COMPLETED', str(result), outcome, task_id)
        except Exception as exc:
            db.finish_run_with_outcome(run_db_id, 'FAILED', str(exc), 'FAILED')

    background_tasks.add_task(_do_run)
    return {
        'ok': True,
        'runner': runner,
        'pid': 0,
        'mode': 'spawned',
        'triggered_at': iso_utc_now(),
        'request_id': request_id,
        # backward compat
        'status': 'triggered',
        'role': runner,
    }


@router.post('/scheduler')
def update_scheduler(payload: SchedulerUpdateRequest, profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()

    planner_interval = payload.interval_minutes or state['planner_interval_minutes']
    worker_interval = payload.interval_minutes or state['worker_interval_minutes']
    now = utc_now()
    fields: dict[str, Any] = {
        'enabled': payload.enabled,
        'planner_interval_minutes': planner_interval,
        'worker_interval_minutes': worker_interval,
    }

    if payload.enabled:
        fields['next_planner_run_at'] = (now + timedelta(minutes=planner_interval)).isoformat()
        fields['next_worker_run_at'] = (now + timedelta(minutes=worker_interval)).isoformat()

    updated_state = db.update_scheduler_state(**fields)
    if payload.enabled:
        start_scheduler(profile_path=loaded.profile_path)
    else:
        stop_scheduler()
    return {'scheduler': updated_state, 'enabled': payload.enabled, 'profile': str(loaded.profile_path)}


@router.get('/llm-control')
def get_llm_control(profile_path: Optional[str] = None):
    state = get_llm_control_state(profile_path=profile_path)
    return {
        'mode': state['mode'],
        'scheduler_enabled': state['scheduler_enabled'],
        'effective_background_run_allowed': state['effective_background_run_allowed'],
        'safe_run': state['mode'] == LLM_MODE_SAFE_RUN,
        'hard_off': state['mode'] == LLM_MODE_HARD_OFF,
        'last_decision_at': state['last_decision_at'],
        'last_source': state['last_source'],
        'last_decision_code': state['last_decision_code'],
        'last_allowed': state['last_allowed'],
        'last_blocked_at': state['last_blocked_at'],
        'blocked_count': state['blocked_count'],
        'last_call_at': state['last_call_at'],
        'call_count': state['call_count'],
        'last_provider': state['last_provider'],
        'last_model': state['last_model'],
        'last_call_source': state['last_call_source'],
    }


@router.post('/llm-control')
def update_llm_control(payload: LlmControlRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    db.set_setting('llm_control_mode', payload.mode)
    if payload.mode == LLM_MODE_HARD_OFF:
        db.update_scheduler_state(enabled=False)
    state = get_llm_control_state(profile_path=profile_path)
    return {
        'mode': state['mode'],
        'scheduler_enabled': state['scheduler_enabled'],
        'effective_background_run_allowed': state['effective_background_run_allowed'],
        'safe_run': state['mode'] == LLM_MODE_SAFE_RUN,
        'hard_off': state['mode'] == LLM_MODE_HARD_OFF,
        'last_decision_at': state['last_decision_at'],
        'last_source': state['last_source'],
        'last_decision_code': state['last_decision_code'],
        'last_allowed': state['last_allowed'],
        'last_blocked_at': state['last_blocked_at'],
        'blocked_count': state['blocked_count'],
        'last_call_at': state['last_call_at'],
        'call_count': state['call_count'],
        'last_provider': state['last_provider'],
        'last_model': state['last_model'],
        'last_call_source': state['last_call_source'],
    }


@router.post('/providers')
def update_providers(payload: ProviderUpdateRequest, profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    planner_provider = payload.planner_provider or db.get_planner_provider()
    worker_provider = payload.worker_provider or db.get_worker_provider()

    planner_check = provider_available(planner_provider, repo_root=loaded.repo_root)
    if not planner_check.get('available'):
        raise HTTPException(status_code=400, detail=planner_check.get('reason', 'Planner provider unavailable'))

    worker_check = provider_available(worker_provider, repo_root=loaded.repo_root)
    if not worker_check.get('available'):
        raise HTTPException(status_code=400, detail=worker_check.get('reason', 'Worker provider unavailable'))

    try:
        worker_copilot_model = validate_copilot_model(
            payload.worker_copilot_model if payload.worker_copilot_model is not None else db.get_worker_copilot_model()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.set_planner_provider(planner_provider)
    db.set_worker_provider(worker_provider)
    db.set_worker_copilot_model(worker_copilot_model)
    db.update_scheduler_state(planner_provider=planner_provider, worker_provider=worker_provider)

    return _provider_payload(
        planner_provider=planner_provider,
        worker_provider=worker_provider,
        worker_copilot_model=worker_copilot_model,
        repo_root=loaded.repo_root,
    )


@router.post('/scheduler/run-at-once')
def run_scheduler_at_once(profile_path: Optional[str] = None):
    return force_scheduler_run_at_once(profile_path=profile_path)


@router.get('/backlog')
def get_orchestrator_backlog(profile_path: Optional[str] = None):
    """Return the full content of backlog.md."""
    loaded, _ = _db_for_profile(profile_path=profile_path)
    backlog_path = loaded.repo_root / loaded.profile['backlog_path']
    content = read_text_if_exists(backlog_path) or ''
    return {'content': content, 'path': str(loaded.profile['backlog_path'])}


# ── Task Pool Routes ──────────────────────────────────────────────────────────


@router.get('/task-pool')
def get_task_pool_status(profile_path: Optional[str] = None):
    """Return the 10-category task pool with active/available status for each."""
    _, db = _db_for_profile(profile_path=profile_path)
    recent = db.list_tasks(limit=30)
    active_sigs: set[str] = {
        str(t.get('duplicate_signature') or '')
        for t in recent
        if str(t.get('status') or '') in {'QUEUED', 'RUNNING', 'REPLAN_REQUIRED'}
    }
    active_categories: set[str] = {
        str(t.get('category') or '')
        for t in recent
        if str(t.get('status') or '') in {'QUEUED', 'RUNNING', 'REPLAN_REQUIRED'} and t.get('category')
    }
    pool_info = get_task_pool_info()
    for item in pool_info:
        sig = str(item.get('duplicate_signature') or '')
        item['is_active'] = sig in active_sigs or item['category'] in active_categories
    return {
        'categories': POOL_CATEGORIES,
        'pool': pool_info,
        'active_count': len(active_sigs),
        'available_count': sum(1 for item in pool_info if not item['is_active']),
    }


@router.get('/planner-candidates')
def get_planner_candidates(
    limit: int = Query(default=5, ge=1, le=20),
    profile_path: Optional[str] = None,
):
    """Return the most recent planner runs with rejection/fallback info."""
    _, db = _db_for_profile(profile_path=profile_path)
    runs = db.list_runs_by_role(role='planner', limit=limit)
    return {'items': runs}


# ── CTO Routes ────────────────────────────────────────────────────────────────


@router.get('/cto/summary')
def get_cto_summary(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    stats = db.get_cto_summary_stats()
    state = db.get_scheduler_state()
    latest_run = db.get_latest_cto_review_run()
    stats['scheduler_enabled'] = state['enabled']
    stats['planner_provider'] = state.get('planner_provider', 'codex')
    stats['planner_model'] = None
    stats['latest_run'] = latest_run
    stats['next_run_estimate'] = stats.pop('next_run_at', None)
    return stats


@router.get('/cto/pending')
def get_cto_pending(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    return {'items': db.list_pending_task_reviews(limit=limit, offset=offset)}


@router.get('/cto/runs')
def list_cto_runs(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    date: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    runs = db.list_cto_review_runs(limit=limit, offset=offset, date_str=date, status=status)
    return {'items': runs, 'runs': runs, 'count': len(runs)}


@router.get('/cto/runs/{run_id}')
def get_cto_run_detail(run_id: str, profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    run = db.get_cto_review_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f'CTO run {run_id} not found')
    reviews = db.list_task_reviews_for_run(run_id)

    # Load intelligence JSON if available
    intelligence: dict[str, Any] = {}
    if run.get('report_json_path'):
        report_path = loaded.repo_root / run['report_json_path']
        content = read_text_if_exists(report_path)
        if content:
            try:
                intelligence = json.loads(content)
            except Exception:
                pass

    return {
        'run': run,
        'reviews': reviews,
        'intelligence': intelligence,
    }


@router.get('/cto/reports/{run_id}')
def get_cto_report(run_id: str, profile_path: Optional[str] = None):
    loaded, db = _db_for_profile(profile_path=profile_path)
    run = db.get_cto_review_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f'CTO run {run_id} not found')
    if not run.get('report_json_path'):
        return {'markdown': None, 'json': None}
    report_path = loaded.repo_root / run['report_json_path']
    content = read_text_if_exists(report_path)
    report_json: Optional[dict[str, Any]] = None
    if content:
        try:
            report_json = json.loads(content)
        except Exception:
            pass
    markdown = _render_report_markdown(run, report_json)
    return {'markdown': markdown, 'json': report_json}


@router.get('/cto/backlog')
def list_cto_backlog(
    cto_run_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    return {'items': db.list_backlog_items(status=status, limit=limit, cto_run_id=cto_run_id)}


@router.get('/cto/backlog/prioritized')
def get_prioritized_backlog(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    return db.get_prioritized_backlog()


@router.get('/cto/backlog/policy')
def get_backlog_policy(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    return db.get_execution_policy()


@router.post('/cto/backlog/policy')
def update_backlog_policy(payload: ExecutionPolicyRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    return db.update_execution_policy(mode=payload.mode)


@router.post('/cto/backlog')
def add_backlog_item(payload: BacklogItemRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    item = db.add_backlog_item(payload.model_dump())
    return {'item': item, 'finding_id': item.get('finding_id')}


@router.post('/cto/backlog/batch')
def batch_add_backlog(payload: BatchBacklogRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    added = db.add_batch_backlog_items(
        cto_run_id=payload.cto_run_id,
        min_severity=payload.min_severity,
        min_impact=payload.min_impact,
    )
    return {'added': added, 'cto_run_id': payload.cto_run_id}


@router.post('/cto/backlog/rescore')
def rescore_backlog(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    updated = db.rescore_backlog_items()
    return {'updated': updated}


@router.post('/cto/backlog/aging')
def apply_aging(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    updated = db.apply_aging_to_backlog()
    return {'updated': updated}


@router.get('/cto/adaptive-policy')
def get_adaptive_policy(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    return db.get_cto_adaptive_policy()


@router.post('/cto/adaptive-policy/refresh')
def refresh_adaptive_policy(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    return db.get_cto_adaptive_policy()


@router.get('/cto/providers')
def get_cto_providers(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()
    planner = state['planner_provider']
    return {
        'planner_provider': planner,
        'planner_provider_label': _label(planner),
        'planner_model': None,
        'planner_options': _PLANNER_OPTIONS,
        'planner_model_presets': _COPILOT_MODEL_PRESETS,
    }


@router.post('/cto/providers')
def update_cto_providers(payload: CtoProviderRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()
    planner = payload.planner_provider or state['planner_provider']
    db.update_scheduler_state(planner_provider=planner)
    return {
        'planner_provider': planner,
        'planner_provider_label': _label(planner),
        'planner_model': payload.planner_model,
    }


@router.get('/cto/scheduler')
def get_cto_scheduler(profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    state = db.get_scheduler_state()
    planner = state.get('planner_provider', 'codex')
    return {
        'enabled': state['enabled'],
        'planner_provider': planner,
        'planner_provider_label': _label(planner),
        'planner_model': None,
        'planner_options': _PLANNER_OPTIONS,
    }


@router.post('/cto/scheduler')
def update_cto_scheduler(payload: CtoSchedulerRequest, profile_path: Optional[str] = None):
    _, db = _db_for_profile(profile_path=profile_path)
    # CTO scheduler uses the same enabled flag for now; can be split later
    db.update_scheduler_state(enabled=payload.enabled)
    return {'enabled': payload.enabled}


@router.post('/cto/run-now')
def cto_run_now(
    payload: CtoRunNowRequest,
    background_tasks: BackgroundTasks,
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    request_id = str(uuid.uuid4())
    triggered_at = iso_utc_now()

    # Persist a pending run record so /cto/run-status can poll it
    with db._connect() as conn:
        conn.execute(
            'INSERT INTO runs (role, run_type, status, message, started_at, request_id, outcome) VALUES (?,?,?,?,?,?,?)',
            ('cto_planner', 'manual', 'RUNNING', 'CTO run triggered', triggered_at, request_id, 'CTO_REVIEW_RUNNING'),
        )
        conn.commit()

    def _do_cto_run() -> None:
        try:
            run_cto_review_tick(
                profile_path=profile_path,
                run_type='manual',
                is_force=payload.force,
                run_intent=payload.run_intent,
                parent_run_id=payload.parent_run_id,
                request_id=request_id,
            )
        except Exception as exc:
            with db._connect() as conn:
                conn.execute(
                    'UPDATE runs SET status=?, message=?, finished_at=?, outcome=? WHERE request_id=?',
                    ('FAILED', str(exc), iso_utc_now(), 'CTO_REVIEW_ERROR', request_id),
                )
                conn.commit()

    background_tasks.add_task(_do_cto_run)
    return {
        'status': 'triggered',
        'request_id': request_id,
        'triggered_at': triggered_at,
    }


@router.get('/cto/run-status')
def get_cto_run_status(
    request_id: str = Query(...),
    profile_path: Optional[str] = None,
):
    _, db = _db_for_profile(profile_path=profile_path)
    row = db.get_run_by_request_id(request_id)
    if row is None:
        return {'status': 'pending', 'run': None, 'final': False}
    outcome = row.get('outcome') or row.get('status') or 'pending'
    finished = row.get('finished_at') is not None
    cto_terminal = {
        'CTO_REVIEW_COMPLETED',
        'CTO_REVIEW_SKIP_DISABLED',
        'CTO_REVIEW_SKIP_HARD_OFF',
        'CTO_REVIEW_SKIP_SAFE_RUN',
        'CTO_REVIEW_SKIP_FREQUENCY',
        'CTO_REVIEW_NO_CANDIDATES',
        'CTO_REVIEW_ERROR',
        'CTO_REVIEW_SKIP_DUPLICATE_RUNNING',
        'CTO_REVIEW_SKIP_DUPLICATE_RECENT',
    }
    is_final = finished or outcome in cto_terminal
    return {
        'status': outcome,
        'run': _run_to_api(row),
        'final': is_final,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _label(provider: Optional[str]) -> str:
    return provider_label(provider)


def _provider_payload(
    planner_provider: str,
    worker_provider: str,
    worker_copilot_model: str,
    repo_root: Path,
) -> dict[str, Any]:
    return {
        'planner_provider': planner_provider,
        'planner_provider_label': provider_label(planner_provider),
        'worker_provider': worker_provider,
        'worker_provider_label': provider_label(worker_provider),
        'combo_label': f'{provider_label(planner_provider)} Planner + {provider_label(worker_provider)} Worker',
        'planner_options': planner_provider_options(),
        'worker_options': worker_provider_options(repo_root=repo_root),
        'worker_copilot_model': worker_copilot_model,
        'worker_copilot_model_presets': WORKER_COPILOT_MODEL_PRESETS,
    }


def _tail_text_file(path: Path, line_limit: int = 50) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8').splitlines()
    return lines[-line_limit:]


def _parse_json_or_none(content: Optional[str]) -> Optional[dict[str, Any]]:
    if not content:
        return None
    try:
        return json.loads(content)
    except Exception:
        return None


def _render_report_markdown(run: dict[str, Any], report: Optional[dict[str, Any]]) -> str:
    if not report:
        return f'# CTO Review {run["run_id"]}\n\n_No report data available._\n'
    health = report.get('health_score', '?')
    verdict = report.get('verdict', '?')
    summary = report.get('summary', '')
    reviews = report.get('reviews', [])
    lines = [
        f'# CTO Review `{run["run_id"][:8]}`',
        '',
        f'**Verdict**: {verdict} | **Health Score**: {health}/100',
        '',
        f'**Summary**: {summary}',
        '',
        '## Decision Timeline',
        '',
    ]
    for rev in reviews:
        lines.append(f'- **Task #{rev["task_id"]}** — `{rev["decision"]}` ({rev.get("severity","?")}): {rev.get("reason","")}')
    return '\n'.join(lines) + '\n'

