from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final

from app.core.config import get_settings
from app.orchestrator.common import iso_utc_now, load_project_profile
from app.orchestrator.db import OrchestratorDB

LLM_MODE_SAFE_RUN: Final[str] = 'safe-run'
LLM_MODE_HARD_OFF: Final[str] = 'hard-off'

SCHEDULER_CONTROLLED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        'scheduler',
        'planner-tick',
        'worker-tick',
        'daemon',
        'worker-daemon',
        'copilot-daemon',
        'cto-scheduler',
        'manual',       # user-triggered runs are allowed when scheduler is enabled
    }
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    allowed: bool
    code: str
    message: str
    mode: str
    scheduler_enabled: bool


def _read_telemetry(db: OrchestratorDB) -> dict[str, object]:
    return {
        'last_decision_at': db.get_setting('llm_last_decision_at', '') or None,
        'last_source': db.get_setting('llm_last_source', '') or None,
        'last_decision_code': db.get_setting('llm_last_decision_code', '') or None,
        'last_allowed': db.get_setting('llm_last_allowed', '') == '1',
        'last_blocked_at': db.get_setting('llm_last_blocked_at', '') or None,
        'blocked_count': db.get_int_setting('llm_blocked_count', 0),
        'last_call_at': db.get_setting('llm_last_call_at', '') or None,
        'call_count': db.get_int_setting('llm_call_count', 0),
        'last_provider': db.get_setting('llm_last_provider', '') or None,
        'last_model': db.get_setting('llm_last_model', '') or None,
        'last_call_source': db.get_setting('llm_last_call_source', '') or None,
    }


def _record_policy_decision(db: OrchestratorDB, source: str, decision: ExecutionPolicyDecision) -> None:
    timestamp = iso_utc_now()
    updates: dict[str, Any] = {
        'llm_last_decision_at': timestamp,
        'llm_last_source': source,
        'llm_last_decision_code': decision.code,
        'llm_last_allowed': '1' if decision.allowed else '0',
    }
    if not decision.allowed:
        updates['llm_last_blocked_at'] = timestamp

    db.set_settings(updates)
    if not decision.allowed:
        db.increment_setting('llm_blocked_count', 1)


def record_llm_call(
    source: str,
    provider: str,
    model: str | None,
    profile_path: str | None = None,
) -> None:
    try:
        db = _open_db(profile_path=profile_path)
        timestamp = iso_utc_now()
        db.set_settings(
            {
                'llm_last_call_at': timestamp,
                'llm_last_provider': provider,
                'llm_last_model': model or '',
                'llm_last_call_source': source,
            }
        )
        db.increment_setting('llm_call_count', 1)
    except Exception:
        logger.exception('llm_call_telemetry_failed source=%s provider=%s', source, provider)


def _open_db(profile_path: str | None = None) -> OrchestratorDB:
    settings = get_settings()
    loaded = load_project_profile(profile_path=profile_path or settings.orchestrator_profile_path)
    profile = loaded.profile
    return OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )


def normalize_llm_control_mode(mode: str | None) -> str:
    value = (mode or '').strip().lower()
    if value == LLM_MODE_HARD_OFF:
        return LLM_MODE_HARD_OFF
    return LLM_MODE_SAFE_RUN


def get_llm_control_state(profile_path: str | None = None) -> dict[str, object]:
    db = _open_db(profile_path=profile_path)
    scheduler_state = db.get_scheduler_state()
    mode = normalize_llm_control_mode(db.get_setting('llm_control_mode', LLM_MODE_SAFE_RUN))
    return {
        'mode': mode,
        'scheduler_enabled': bool(scheduler_state.get('enabled')),
        'effective_background_run_allowed': mode != LLM_MODE_HARD_OFF and bool(scheduler_state.get('enabled')),
        **_read_telemetry(db),
    }


def evaluate_llm_execution(source: str, profile_path: str | None = None, record: bool = True) -> ExecutionPolicyDecision:
    try:
        db = _open_db(profile_path=profile_path)
        scheduler_state = db.get_scheduler_state()
        mode = normalize_llm_control_mode(db.get_setting('llm_control_mode', LLM_MODE_SAFE_RUN))
        state = {
            'mode': mode,
            'scheduler_enabled': bool(scheduler_state.get('enabled')),
        }
    except Exception as exc:
        return ExecutionPolicyDecision(
            allowed=False,
            code='POLICY_STATE_UNAVAILABLE',
            message=f'POLICY_STATE_UNAVAILABLE - {exc}',
            mode=LLM_MODE_SAFE_RUN,
            scheduler_enabled=False,
        )

    mode = str(state['mode'])
    scheduler_enabled = bool(state['scheduler_enabled'])
    normalized_source = (source or '').strip().lower()

    if mode == LLM_MODE_HARD_OFF:
        decision = ExecutionPolicyDecision(
            allowed=False,
            code='GLOBAL_LLM_HARD_OFF',
            message='GLOBAL_LLM_HARD_OFF - skip execution',
            mode=mode,
            scheduler_enabled=scheduler_enabled,
        )
        if record:
            _record_policy_decision(db, normalized_source, decision)
        return decision

    if normalized_source in SCHEDULER_CONTROLLED_SOURCES:
        if not scheduler_enabled:
            decision = ExecutionPolicyDecision(
                allowed=False,
                code='GLOBAL_SCHEDULER_DISABLED',
                message='GLOBAL_SCHEDULER_DISABLED - skip execution',
                mode=mode,
                scheduler_enabled=scheduler_enabled,
            )
            if record:
                _record_policy_decision(db, normalized_source, decision)
            return decision
        decision = ExecutionPolicyDecision(
            allowed=True,
            code='ALLOWED',
            message='ALLOWED',
            mode=mode,
            scheduler_enabled=scheduler_enabled,
        )
        if record:
            _record_policy_decision(db, normalized_source, decision)
        return decision

    decision = ExecutionPolicyDecision(
        allowed=False,
        code='SAFE_RUN_NON_SCHEDULER_SOURCE',
        message='SAFE_RUN_NON_SCHEDULER_SOURCE - forcing fallback',
        mode=mode,
        scheduler_enabled=scheduler_enabled,
    )
    if record:
        _record_policy_decision(db, normalized_source, decision)
    return decision