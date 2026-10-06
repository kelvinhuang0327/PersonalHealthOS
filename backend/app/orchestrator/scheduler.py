from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta

from app.orchestrator.common import iso_utc_now, load_project_profile, parse_iso_datetime, utc_now
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.planner_tick import run_planner_tick
from app.orchestrator.worker_tick import run_worker_tick

logger = logging.getLogger(__name__)


class OrchestratorScheduler:
    def __init__(self, profile_path: str | None = None, poll_seconds: int = 5):
        self.profile_path = profile_path
        self.poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name='agent-orchestrator-scheduler', daemon=True)
        self._thread.start()
        logger.info('orchestrator_scheduler_started')

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        logger.info('orchestrator_scheduler_stopped')

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                loaded = load_project_profile(profile_path=self.profile_path)
                profile = loaded.profile
                db = OrchestratorDB(
                    db_path=loaded.repo_root / profile['database_path'],
                    default_schedule_minutes=profile['default_schedule_minutes'],
                    planner_provider=profile['planner_provider'],
                    worker_provider=profile['worker_provider'],
                )
                state = db.get_scheduler_state()
                if not state['enabled']:
                    self._stop_event.wait(self.poll_seconds)
                    continue

                now = utc_now()
                ran_any = False
                planner_due = _is_due(state.get('next_planner_run_at'), now)
                worker_due = _is_due(state.get('next_worker_run_at'), now)

                if planner_due:
                    run_planner_tick(profile_path=str(loaded.profile_path), run_type='scheduler')
                    next_planner = now + timedelta(minutes=int(state['planner_interval_minutes']))
                    db.update_scheduler_state(next_planner_run_at=next_planner.isoformat())
                    ran_any = True

                if worker_due:
                    run_worker_tick(profile_path=str(loaded.profile_path), run_type='scheduler')
                    next_worker = now + timedelta(minutes=int(state['worker_interval_minutes']))
                    db.update_scheduler_state(next_worker_run_at=next_worker.isoformat())
                    ran_any = True

                if not ran_any:
                    self._stop_event.wait(self.poll_seconds)
            except Exception:  # pragma: no cover - defensive scheduler loop
                logger.exception('orchestrator_scheduler_loop_error')
                self._stop_event.wait(self.poll_seconds)


def _is_due(scheduled_iso: str | None, now) -> bool:
    parsed = parse_iso_datetime(scheduled_iso)
    if parsed is None:
        return True
    return now >= parsed


_GLOBAL_SCHEDULER: OrchestratorScheduler | None = None
_SCHEDULER_LOCK = threading.Lock()


def start_scheduler(profile_path: str | None = None) -> OrchestratorScheduler:
    global _GLOBAL_SCHEDULER
    with _SCHEDULER_LOCK:
        if _GLOBAL_SCHEDULER is None:
            _GLOBAL_SCHEDULER = OrchestratorScheduler(profile_path=profile_path)
        _GLOBAL_SCHEDULER.start()
        return _GLOBAL_SCHEDULER


def stop_scheduler() -> None:
    global _GLOBAL_SCHEDULER
    with _SCHEDULER_LOCK:
        if _GLOBAL_SCHEDULER is None:
            return
        _GLOBAL_SCHEDULER.stop()
        _GLOBAL_SCHEDULER = None


def scheduler_running() -> bool:
    with _SCHEDULER_LOCK:
        return _GLOBAL_SCHEDULER.is_running if _GLOBAL_SCHEDULER is not None else False


def force_scheduler_run_at_once(profile_path: str | None = None) -> dict[str, str]:
    loaded = load_project_profile(profile_path=profile_path)
    profile = loaded.profile
    db = OrchestratorDB(
        db_path=loaded.repo_root / profile['database_path'],
        default_schedule_minutes=profile['default_schedule_minutes'],
        planner_provider=profile['planner_provider'],
        worker_provider=profile['worker_provider'],
    )
    now = iso_utc_now()
    db.update_scheduler_state(next_planner_run_at=now, next_worker_run_at=now)
    return {'next_planner_run_at': now, 'next_worker_run_at': now}
