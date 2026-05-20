"""GitHub Copilot Daemon — PersonalHealthOS.

Runs as a macOS LaunchAgent (user session) so it can access the system keychain
for ``gh copilot`` auth tokens.  Polls the orchestrator DB every N seconds and
dispatches the next QUEUED task via :func:`run_worker_tick` when
``worker_provider == 'copilot-daemon'``.

Usage (module form, recommended when PYTHONPATH=backend):

    python -m app.orchestrator.copilot_daemon \\
        --profile runtime/agent_orchestrator/project_profile.json \\
        --poll-seconds 10

Heartbeat file
--------------
Every iteration the daemon writes:

    runtime/agent_orchestrator/locks/copilot_daemon_state.json

with the following schema::

    {
      "pid":              <int>,
      "status":           "idle" | "busy" | "finalized",
      "started_at":       "<iso>",
      "heartbeat_at":     "<iso>",
      "current_task_id":  <int | null>,
      "worker_pid":       <int | null>,
      "worker_provider":  "copilot-daemon"
    }

:data:`~app.orchestrator.common.copilot_daemon_status` reads this file to
decide whether the daemon is alive (PID reachable + heartbeat age ≤ 45 s).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Optional

from app.orchestrator.common import (
    iso_utc_now,
    load_project_profile,
)
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.execution_policy import evaluate_llm_execution
from app.orchestrator.worker_tick import run_worker_tick

_LOG = logging.getLogger(__name__)

# Set in main() before serve_forever() starts.
_STARTED_AT: str = ''
_STOP: bool = False

# Path of the heartbeat file, relative to the repo root.
_HEARTBEAT_REL = 'runtime/agent_orchestrator/locks/copilot_daemon_state.json'


# ── signal handling ───────────────────────────────────────────────────────────


def _handle_signal(signum: int, _frame: Any) -> None:  # pragma: no cover
    global _STOP
    _STOP = True
    print(json.dumps({'event': 'signal_received', 'signal': signum}), flush=True)


# ── heartbeat helpers ─────────────────────────────────────────────────────────


def _write_heartbeat(
    repo_root: Path,
    *,
    status: str,
    current_task_id: Optional[int] = None,
    worker_pid: Optional[int] = None,
) -> None:
    """Atomically update the daemon state file so the API can report liveness."""
    state_path = repo_root / _HEARTBEAT_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        'pid': os.getpid(),
        'status': status,
        'started_at': _STARTED_AT,
        'heartbeat_at': iso_utc_now(),
        'current_task_id': current_task_id,
        'worker_pid': worker_pid,
        'worker_provider': 'copilot-daemon',
    }
    try:
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError as exc:
        _LOG.warning('heartbeat write failed: %s', exc)


def _write_finalized(repo_root: Path) -> None:
    """Mark the state file as finalized on graceful shutdown."""
    state_path = repo_root / _HEARTBEAT_REL
    try:
        existing: dict[str, Any] = (
            json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        )
    except (json.JSONDecodeError, OSError):
        existing = {}
    existing.update({
        'status': 'finalized',
        'heartbeat_at': iso_utc_now(),
        'pid': os.getpid(),
    })
    try:
        state_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError:
        pass


# ── core tick ─────────────────────────────────────────────────────────────────


def _open_db(loaded: Any) -> OrchestratorDB:
    profile = loaded.profile
    return OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile.get('planner_provider', 'claude'),
        worker_provider=profile.get('worker_provider', 'codex'),
    )


def run_once(profile_path: Optional[str] = None) -> dict[str, Any]:
    """Single poll iteration.

    1. Writes idle heartbeat.
    2. Checks ``worker_provider == 'copilot-daemon'`` in DB.
    3. Checks scheduler is enabled.
    4. Dispatches via :func:`run_worker_tick`; writes busy heartbeat.
    5. Returns the tick result dict.
    """
    # ── load profile ─────────────────────────────────────────────────────────
    try:
        loaded = load_project_profile(profile_path=profile_path)
    except Exception as exc:
        _LOG.error('profile load error: %s', exc)
        return {'status': 'profile-error', 'reason': str(exc)}

    repo_root = loaded.repo_root

    # ── update idle heartbeat ─────────────────────────────────────────────────
    _write_heartbeat(repo_root, status='idle')

    # ── open DB ───────────────────────────────────────────────────────────────
    try:
        db = _open_db(loaded)
    except Exception as exc:
        _LOG.error('db open error: %s', exc)
        return {'status': 'db-error', 'reason': str(exc)}

    # ── check provider ────────────────────────────────────────────────────────
    worker_provider = db.get_worker_provider()
    if worker_provider != 'copilot-daemon':
        return {'status': 'provider-not-selected', 'worker_provider': worker_provider}

    policy = evaluate_llm_execution(source='copilot-daemon', profile_path=profile_path)
    if not policy.allowed:
        if policy.code == 'GLOBAL_LLM_HARD_OFF':
            return {'status': 'WORKER_SKIP_HARD_OFF', 'reason': policy.message, 'policy_code': policy.code}
        if policy.code == 'GLOBAL_SCHEDULER_DISABLED':
            return {'status': 'scheduler-disabled', 'reason': policy.message, 'policy_code': policy.code}
        return {'status': 'WORKER_SKIP_SAFE_RUN', 'reason': policy.message, 'policy_code': policy.code}

    # ── dispatch ──────────────────────────────────────────────────────────────
    _write_heartbeat(repo_root, status='busy')
    _LOG.info('dispatching worker tick via copilot-daemon')

    result = run_worker_tick(profile_path=profile_path, run_type='copilot-daemon')

    # After tick: restore idle; include last completed task_id for UI
    finished_task_id: Optional[int] = result.get('task_id') if result.get('status') == 'COMPLETED' else None
    _write_heartbeat(repo_root, status='idle', current_task_id=finished_task_id)

    return result


# ── main loop ─────────────────────────────────────────────────────────────────


def serve_forever(poll_seconds: int, profile_path: Optional[str] = None) -> None:
    """Polling loop.  Runs until SIGINT / SIGTERM sets ``_STOP = True``."""
    # Load profile once to get repo_root so we can write the initial heartbeat
    # and finalized state even if later iterations fail.
    try:
        loaded = load_project_profile(profile_path=profile_path)
        repo_root = loaded.repo_root
    except Exception as exc:
        print(json.dumps({'event': 'startup_error', 'reason': str(exc)}), flush=True)
        return

    _write_heartbeat(repo_root, status='idle')
    print(
        json.dumps({'event': 'daemon_started', 'pid': os.getpid(), 'poll_seconds': poll_seconds}),
        flush=True,
    )

    try:
        while not _STOP:
            tick_started = time.monotonic()
            try:
                result = run_once(profile_path=profile_path)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            except Exception as exc:
                _LOG.exception('run_once unhandled error: %s', exc)

            # Sleep for the remaining poll interval, checking _STOP each second.
            elapsed = max(0.0, time.monotonic() - tick_started)
            wait = max(1, poll_seconds - int(elapsed))
            for _ in range(wait):
                if _STOP:
                    break
                time.sleep(1)
    finally:
        _write_finalized(repo_root)
        print(json.dumps({'event': 'daemon_stopped', 'pid': os.getpid()}), flush=True)


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> int:
    global _STARTED_AT
    _STARTED_AT = iso_utc_now()

    parser = argparse.ArgumentParser(
        description='GitHub Copilot Daemon — PersonalHealthOS orchestrator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--profile',
        default='runtime/agent_orchestrator/project_profile.json',
        help='Path to project_profile.json (relative to cwd or absolute)',
    )
    parser.add_argument(
        '--poll-seconds',
        type=int,
        default=10,
        help='DB polling interval in seconds',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stderr,
    )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    serve_forever(poll_seconds=args.poll_seconds, profile_path=args.profile)
    return 0


if __name__ == '__main__':
    sys.exit(main())
