"""
CTO Review Tick — adapts SOURCE git-commit review to task-quality review.

Instead of cherry-picking git commits, this module reviews recently completed,
failed, and replan-required tasks and generates:
  - A CTO review run record (health_score, verdict, summary)
  - Per-task review decisions (PASS / NEEDS_REPLAN / DEFERRED / CLOSED)
  - Intelligence block (top_risks, top_actions, roadmap)
  - Backlog items for actionable findings
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.orchestrator.common import (
    GATE_FAILED_ACCEPTANCE,
    GATE_INVALID_DELIVERY,
    GATE_PASS,
    GATE_POLICY_VIOLATION,
    GATE_WORKER_RUNTIME_FAILED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_REPLAN_REQUIRED,
    iso_utc_now,
    load_project_profile,
    utc_now,
    write_json,
)
from app.orchestrator.db import (
    CTO_DECISION_CLOSED,
    CTO_DECISION_DEFERRED,
    CTO_DECISION_NEEDS_REPLAN,
    CTO_DECISION_PASS,
    OrchestratorDB,
)
from app.orchestrator.execution_policy import evaluate_llm_execution
from app.orchestrator.regime_classifier import classify_regime

logger = logging.getLogger(__name__)

_VERDICT_GO = 'GO'
_VERDICT_CAUTION = 'CAUTION'
_VERDICT_STOP = 'STOP'

# how many recent tasks to include as candidates per run
_CANDIDATE_WINDOW = 30


def run_cto_review_tick(
    profile_path: str | None = None,
    run_type: str = 'manual',
    is_force: bool = False,
    run_intent: str | None = None,
    parent_run_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    loaded = load_project_profile(profile_path=profile_path)
    profile = loaded.profile
    db = OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )
    policy_source = 'cto-scheduler' if run_type == 'scheduler' else run_type
    policy = evaluate_llm_execution(source=policy_source, profile_path=profile_path)
    if not policy.allowed:
        if policy.code == 'GLOBAL_LLM_HARD_OFF':
            return {'status': 'CTO_REVIEW_SKIP_HARD_OFF', 'message': policy.message, 'run_id': None}
        if policy.code == 'GLOBAL_SCHEDULER_DISABLED':
            return {'status': 'CTO_REVIEW_SKIP_DISABLED', 'message': policy.message, 'run_id': None}
        return {'status': 'CTO_REVIEW_SKIP_SAFE_RUN', 'message': policy.message, 'run_id': None}

    run_id = str(uuid.uuid4())
    started_at = iso_utc_now()

    # Log the CTO run in the runs table if request_id provided
    runs_row_id: int | None = None
    if request_id:
        with db._connect() as conn:
            cursor = conn.execute(
                'INSERT INTO runs (role, run_type, status, message, started_at, request_id, outcome) VALUES (?,?,?,?,?,?,?)',
                ('cto_planner', run_type, 'RUNNING', 'CTO review started', started_at, request_id, 'CTO_REVIEW_RUNNING'),
            )
            conn.commit()
            runs_row_id = int(cursor.lastrowid)

    # Dedupe: skip if a CTO run completed in the last 2 hours (unless forced)
    if not is_force:
        recent = db.get_latest_cto_review_run()
        if recent and recent.get('completed_at'):
            from app.orchestrator.common import parse_iso_datetime
            completed = parse_iso_datetime(recent['completed_at'])
            if completed and (utc_now() - completed) < timedelta(hours=2):
                msg = 'CTO review skipped: completed recently'
                _finish_run(db, runs_row_id, request_id, 'CTO_REVIEW_SKIP_DUPLICATE_RECENT', msg)
                return {'status': 'CTO_REVIEW_SKIP_DUPLICATE_RECENT', 'message': msg, 'run_id': None}

    # Get recent finished tasks as candidates
    all_tasks, _ = db.list_tasks_filtered(limit=_CANDIDATE_WINDOW, offset=0)
    candidates = [t for t in all_tasks if t.get('status') not in ('QUEUED', 'RUNNING')]

    if not candidates:
        msg = 'No candidate tasks available for CTO review'
        _finish_run(db, runs_row_id, request_id, 'CTO_REVIEW_NO_CANDIDATES', msg)
        return {'status': 'CTO_REVIEW_NO_CANDIDATES', 'message': msg, 'run_id': None}

    # Classify regime
    regime_info = classify_regime(all_tasks)

    # Create CTO run record
    dedupe_key = f"cto-{started_at[:10]}-{len(candidates)}"
    db.create_cto_review_run({
        'run_id': run_id,
        'frequency_mode': 'once_daily',
        'is_manual': run_type == 'manual',
        'is_force_run': is_force,
        'run_intent': run_intent,
        'parent_run_id': parent_run_id,
        'dedupe_key': dedupe_key,
        'started_at': started_at,
        'candidate_count': len(candidates),
        'checked_from': candidates[-1]['created_at'] if candidates else None,
        'checked_until': candidates[0]['created_at'] if candidates else None,
    })

    # Review each candidate task
    reviews: list[dict[str, Any]] = []
    for task in candidates:
        review = _review_task(task, cto_run_id=run_id)
        db.save_task_review(review)
        reviews.append(review)

    # Tally decisions
    pass_count = sum(1 for r in reviews if r['decision'] == CTO_DECISION_PASS)
    replan_count = sum(1 for r in reviews if r['decision'] == CTO_DECISION_NEEDS_REPLAN)
    deferred_count = sum(1 for r in reviews if r['decision'] == CTO_DECISION_DEFERRED)
    closed_count = sum(1 for r in reviews if r['decision'] == CTO_DECISION_CLOSED)

    # Build intelligence block
    health_score = _compute_health_score(reviews, regime_info)
    verdict = _compute_verdict(health_score)
    top_risks = _build_top_risks(reviews)
    top_actions = _build_top_actions(reviews, regime_info)
    roadmap = _build_roadmap(regime_info)
    summary = _build_summary(len(candidates), pass_count, replan_count, health_score, verdict, regime_info)

    # Save intelligence report JSON
    report_path = loaded.repo_root / profile['orchestrator_root'] / 'cto_reports' / f'{run_id}.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    intelligence = {
        'run_id': run_id,
        'health_score': health_score,
        'verdict': verdict,
        'regime': regime_info['regime'],
        'top_risks': top_risks,
        'top_actions': top_actions,
        'roadmap': roadmap,
        'summary': summary,
        'reviews': reviews,
    }
    write_json(report_path, intelligence)

    finished_at = iso_utc_now()
    duration = int((utc_now() - _parse_started(started_at)).total_seconds())

    # Update CTO run record
    db.update_cto_review_run(
        run_id,
        completed_at=finished_at,
        duration_seconds=duration,
        pass_count=pass_count,
        approved_count=pass_count,
        replan_count=replan_count,
        rejected_count=replan_count,
        deferred_count=deferred_count,
        health_score=health_score,
        verdict=verdict,
        summary=summary,
        report_json_path=str(report_path.relative_to(loaded.repo_root)),
    )

    # Save intent signal if intent provided
    if run_intent:
        db.save_cto_intent_signal({
            'run_id': run_id,
            'run_intent': run_intent,
            'outcome': 'completed',
            'candidate_count': len(candidates),
            'pass_count': pass_count,
            'replan_count': replan_count,
            'deferred_count': deferred_count,
            'approved_count': pass_count,
        })

    _finish_run(db, runs_row_id, request_id, 'CTO_REVIEW_COMPLETED', summary)

    return {
        'status': 'CTO_REVIEW_COMPLETED',
        'run_id': run_id,
        'candidate_count': len(candidates),
        'pass_count': pass_count,
        'replan_count': replan_count,
        'deferred_count': deferred_count,
        'health_score': health_score,
        'verdict': verdict,
        'summary': summary,
    }


# ── Task review logic ─────────────────────────────────────────────────────────


def _review_task(task: dict[str, Any], cto_run_id: str) -> dict[str, Any]:
    status = task.get('status', '')
    gate = task.get('gate_verdict') or 'NONE'

    # Determine decision
    if status == STATUS_CANCELLED:
        decision = CTO_DECISION_CLOSED
        severity = 'LOW'
        impact = 10
        urgency = 'low'
        reason = 'Task was cancelled.'
        action = 'Review if cancellation was intentional; requeue if still needed.'
        category = 'lifecycle'
    elif status == STATUS_COMPLETED and gate == GATE_PASS:
        decision = CTO_DECISION_PASS
        severity = 'LOW'
        impact = 5
        urgency = 'none'
        reason = 'Task completed successfully with PASS gate verdict.'
        action = 'No action required.'
        category = 'quality'
    elif gate in (GATE_INVALID_DELIVERY, GATE_FAILED_ACCEPTANCE):
        decision = CTO_DECISION_NEEDS_REPLAN
        severity = 'HIGH'
        impact = 75
        urgency = 'high'
        reason = f'Gate verdict: {gate}. Task delivery did not meet acceptance criteria.'
        action = 'Replan task with clearer acceptance criteria and contract scope.'
        category = 'delivery'
    elif gate == GATE_POLICY_VIOLATION:
        decision = CTO_DECISION_NEEDS_REPLAN
        severity = 'CRITICAL'
        impact = 90
        urgency = 'critical'
        reason = 'Task violated execution policy (forbidden file change or scope violation).'
        action = 'Review contract scope constraints and rebuild the task prompt.'
        category = 'policy'
    elif gate == GATE_WORKER_RUNTIME_FAILED:
        decision = CTO_DECISION_DEFERRED
        severity = 'HIGH'
        impact = 60
        urgency = 'high'
        reason = 'Worker runtime failure — task could not complete due to system error.'
        action = 'Investigate worker logs, fix runtime issue, then requeue.'
        category = 'runtime'
    elif status == STATUS_FAILED:
        decision = CTO_DECISION_NEEDS_REPLAN
        severity = 'MEDIUM'
        impact = 55
        urgency = 'normal'
        reason = 'Task reached FAILED status.'
        action = 'Review worker logs and re-create with improved prompt.'
        category = 'quality'
    elif status == STATUS_REPLAN_REQUIRED:
        decision = CTO_DECISION_NEEDS_REPLAN
        severity = 'MEDIUM'
        impact = 50
        urgency = 'normal'
        reason = 'Planner flagged task for replanning.'
        action = 'Adjust objective and regenerate task contract.'
        category = 'planning'
    else:
        decision = CTO_DECISION_DEFERRED
        severity = 'LOW'
        impact = 20
        urgency = 'low'
        reason = f'Task in state {status}/{gate} — requires manual review.'
        action = 'Manual review recommended.'
        category = 'lifecycle'

    return {
        'task_id': task['id'],
        'task_uid': task['task_uid'],
        'cto_run_id': cto_run_id,
        'decision': decision,
        'severity': severity,
        'impact_score': impact,
        'urgency': urgency,
        'reason': reason,
        'suggested_action': action,
        'category': category,
        'create_followup_task': decision == CTO_DECISION_NEEDS_REPLAN and impact >= 70,
        'changed_files': [],
    }


# ── Intelligence helpers ──────────────────────────────────────────────────────


def _compute_health_score(reviews: list[dict[str, Any]], regime: dict[str, Any]) -> int:
    if not reviews:
        return 50
    pass_count = sum(1 for r in reviews if r['decision'] == CTO_DECISION_PASS)
    base_score = int((pass_count / len(reviews)) * 100)
    # Penalize for CRITICAL findings
    critical = sum(1 for r in reviews if r.get('severity') == 'CRITICAL')
    penalty = min(critical * 10, 30)
    raw = base_score - penalty
    return max(0, min(100, raw))


def _compute_verdict(health_score: int) -> str:
    if health_score >= 75:
        return _VERDICT_GO
    if health_score >= 50:
        return _VERDICT_CAUTION
    return _VERDICT_STOP


def _build_top_risks(reviews: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    risky = [r for r in reviews if r['decision'] != CTO_DECISION_PASS]
    risky.sort(key=lambda r: r.get('impact_score', 0), reverse=True)
    risks = []
    for r in risky[:limit]:
        risks.append({
            'task_id': r['task_id'],
            'severity': r['severity'],
            'impact': r['impact_score'],
            'urgency': r['urgency'],
            'description': r['reason'],
            'category': r['category'],
        })
    return risks


def _build_top_actions(reviews: list[dict[str, Any]], regime: dict[str, Any]) -> list[dict[str, Any]]:
    actions = []
    needs_replan = [r for r in reviews if r['decision'] == CTO_DECISION_NEEDS_REPLAN]
    if needs_replan:
        actions.append({
            'priority': 'P0' if len(needs_replan) >= 3 else 'P1',
            'action': f'Replan {len(needs_replan)} task(s) with failed gate verdicts',
            'expected_benefit': 'Improve task completion rate and gate pass rate',
            'create_task': True,
        })
    deferred = [r for r in reviews if r['decision'] == CTO_DECISION_DEFERRED]
    if deferred:
        actions.append({
            'priority': 'P1',
            'action': f'Investigate {len(deferred)} deferred task(s) with runtime failures',
            'expected_benefit': 'Restore worker execution stability',
            'create_task': False,
        })
    if regime['regime'] in ('COLD', 'EXHAUSTED'):
        actions.append({
            'priority': 'P0',
            'action': 'System health critical — review orchestrator configuration and task contracts',
            'expected_benefit': 'Restore healthy task completion rate',
            'create_task': True,
        })
    return actions


def _build_roadmap(regime: dict[str, Any]) -> list[str]:
    items = []
    if regime['regime'] == 'ACTIVE':
        items = [
            'Continue current task execution cadence',
            'Monitor gate pass rate for any degradation',
            'Expand task coverage to new platform areas',
        ]
    elif regime['regime'] == 'COLD':
        items = [
            'Diagnose root cause of high failure rate',
            'Simplify task contracts to reduce complexity',
            'Add more specific acceptance criteria',
        ]
    elif regime['regime'] == 'SATURATED':
        items = [
            'Audit gate criteria — may be too strict',
            'Review task scope for over-ambitious objectives',
            'Consider splitting large tasks into smaller units',
        ]
    elif regime['regime'] == 'EXHAUSTED':
        items = [
            'URGENT: Halt new task generation',
            'Fix delivery validation pipeline',
            'Review and update forbidden-change policies',
        ]
    else:
        items = ['Queue initial tasks to establish baseline performance']
    return items


def _build_summary(
    total: int, passed: int, replanned: int, health: int, verdict: str, regime: dict[str, Any]
) -> str:
    return (
        f'CTO Review: {total} tasks reviewed. '
        f'{passed} PASS, {replanned} NEEDS_REPLAN. '
        f'Health score: {health}/100. Verdict: {verdict}. '
        f'Regime: {regime["regime"]}.'
    )


def _parse_started(iso: str):
    from app.orchestrator.common import parse_iso_datetime
    parsed = parse_iso_datetime(iso)
    return parsed if parsed else utc_now()


def _finish_run(
    db: OrchestratorDB,
    runs_row_id: int | None,
    request_id: str | None,
    outcome: str,
    message: str,
) -> None:
    if runs_row_id is None:
        return
    with db._connect() as conn:
        conn.execute(
            'UPDATE runs SET status = ?, message = ?, finished_at = ?, outcome = ? WHERE id = ?',
            ('COMPLETED', message, iso_utc_now(), outcome, runs_row_id),
        )
        conn.commit()
