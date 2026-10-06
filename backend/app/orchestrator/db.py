from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.orchestrator.common import iso_utc_now, utc_now

# ── CTO decision constants ────────────────────────────────────────────────────
CTO_DECISION_PASS = 'PASS'
CTO_DECISION_NEEDS_REPLAN = 'NEEDS_REPLAN'
CTO_DECISION_DEFERRED = 'DEFERRED'
CTO_DECISION_CLOSED = 'CLOSED'

_SEVERITY_RANK: dict[str, int] = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

DEFAULT_SETTINGS = {
    'planner_provider': 'claude',
    'worker_provider': 'codex',
    'worker_copilot_model': '',
    'llm_control_mode': 'safe-run',
}


def _new_request_id() -> str:
    return str(uuid.uuid4())


class OrchestratorDB:
    def __init__(self, db_path: Path, default_schedule_minutes: int, planner_provider: str, worker_provider: str):
        self.db_path = db_path
        self.default_schedule_minutes = default_schedule_minutes
        self.default_planner_provider = planner_provider
        self.default_worker_provider = worker_provider
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_uid TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    gate_verdict TEXT,
                    gate_reason TEXT DEFAULT '',
                    planner_provider TEXT NOT NULL,
                    worker_provider TEXT NOT NULL,
                    task_dir TEXT NOT NULL,
                    prompt_path TEXT NOT NULL,
                    contract_path TEXT NOT NULL,
                    worker_log_path TEXT NOT NULL,
                    completed_path TEXT,
                    result_path TEXT,
                    meta_path TEXT NOT NULL,
                    last_output_at TEXT,
                    latest_progress_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    task_id INTEGER,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    request_id TEXT,
                    outcome TEXT
                )
                '''
            )
            # migration: add request_id + outcome to existing runs table
            existing_run_cols = {
                row['name']
                for row in conn.execute('PRAGMA table_info(runs)').fetchall()
            }
            for col_def in [('request_id', 'TEXT'), ('outcome', 'TEXT')]:
                if col_def[0] not in existing_run_cols:
                    conn.execute(f'ALTER TABLE runs ADD COLUMN {col_def[0]} {col_def[1]}')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runs_request_id ON runs(request_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runs_role ON runs(role)')

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS scheduler_state (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    planner_interval_minutes INTEGER NOT NULL,
                    worker_interval_minutes INTEGER NOT NULL,
                    next_planner_run_at TEXT,
                    next_worker_run_at TEXT,
                    planner_provider TEXT NOT NULL,
                    worker_provider TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS orchestrator_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            existing = conn.execute('SELECT singleton_id FROM scheduler_state WHERE singleton_id = 1').fetchone()
            if existing is None:
                now = utc_now()
                next_run = (now + timedelta(minutes=self.default_schedule_minutes)).isoformat()
                conn.execute(
                    '''
                    INSERT INTO scheduler_state (
                        singleton_id,
                        enabled,
                        planner_interval_minutes,
                        worker_interval_minutes,
                        next_planner_run_at,
                        next_worker_run_at,
                        planner_provider,
                        worker_provider,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        1,
                        0,
                        self.default_schedule_minutes,
                        self.default_schedule_minutes,
                        next_run,
                        next_run,
                        self.default_planner_provider,
                        self.default_worker_provider,
                        iso_utc_now(),
                    ),
                )
            for key, value in DEFAULT_SETTINGS.items():
                existing_setting = conn.execute(
                    'SELECT key FROM orchestrator_settings WHERE key = ?',
                    (key,),
                ).fetchone()
                if existing_setting is None:
                    conn.execute(
                        'INSERT INTO orchestrator_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, value, iso_utc_now()),
                    )

            # ── CTO / review tables ────────────────────────────────────────────
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS task_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    task_uid TEXT NOT NULL,
                    cto_run_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    severity TEXT,
                    impact_score INTEGER DEFAULT 0,
                    urgency TEXT,
                    category TEXT,
                    reason TEXT,
                    suggested_action TEXT,
                    create_followup_task INTEGER DEFAULT 0,
                    changed_files_json TEXT,
                    created_at TEXT NOT NULL
                )
                '''
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tr_task_id ON task_reviews(task_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tr_cto_run_id ON task_reviews(cto_run_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tr_decision ON task_reviews(decision)')

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS cto_review_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE NOT NULL,
                    frequency_mode TEXT NOT NULL DEFAULT 'once_daily',
                    is_manual INTEGER NOT NULL DEFAULT 0,
                    is_force_run INTEGER NOT NULL DEFAULT 0,
                    run_intent TEXT,
                    parent_run_id TEXT,
                    dedupe_key TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds INTEGER,
                    checked_from TEXT,
                    checked_until TEXT,
                    candidate_count INTEGER DEFAULT 0,
                    pass_count INTEGER DEFAULT 0,
                    approved_count INTEGER DEFAULT 0,
                    merged_count INTEGER DEFAULT 0,
                    replan_count INTEGER DEFAULT 0,
                    rejected_count INTEGER DEFAULT 0,
                    deferred_count INTEGER DEFAULT 0,
                    superseded_count INTEGER DEFAULT 0,
                    duplicate_count INTEGER DEFAULT 0,
                    health_score INTEGER,
                    verdict TEXT,
                    merge_branch TEXT,
                    report_json_path TEXT,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cto_runs_started ON cto_review_runs(started_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cto_runs_run_id ON cto_review_runs(run_id)')

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS cto_intent_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    run_intent TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    candidate_count INTEGER DEFAULT 0,
                    pass_count INTEGER DEFAULT 0,
                    replan_count INTEGER DEFAULT 0,
                    deferred_count INTEGER DEFAULT 0,
                    approved_count INTEGER DEFAULT 0,
                    is_compare_only INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                '''
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cis_intent ON cto_intent_signals(run_intent)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cis_created ON cto_intent_signals(created_at)')

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS cto_backlog_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finding_id TEXT UNIQUE NOT NULL,
                    cto_run_id TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'cto_review',
                    task_id INTEGER,
                    category TEXT,
                    severity TEXT,
                    impact_score INTEGER DEFAULT 0,
                    urgency TEXT,
                    suggested_action TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority_score REAL NOT NULL DEFAULT 0,
                    priority_level TEXT NOT NULL DEFAULT 'P3',
                    rank INTEGER,
                    selection_count INTEGER NOT NULL DEFAULT 0,
                    aging_bonus REAL NOT NULL DEFAULT 0,
                    last_selected_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cbi_finding_id ON cto_backlog_items(finding_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cbi_status ON cto_backlog_items(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cbi_cto_run_id ON cto_backlog_items(cto_run_id)')

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS execution_policy_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    mode TEXT NOT NULL DEFAULT 'balanced',
                    consecutive_high INTEGER NOT NULL DEFAULT 0,
                    consecutive_category TEXT,
                    consecutive_category_count INTEGER NOT NULL DEFAULT 0,
                    recent_selections TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                '''
            )
            policy_exists = conn.execute('SELECT id FROM execution_policy_state WHERE id = 1').fetchone()
            if policy_exists is None:
                conn.execute(
                    "INSERT INTO execution_policy_state (id, mode, updated_at) VALUES (1, 'balanced', ?)",
                    (iso_utc_now(),),
                )

            # migration: add new columns to tasks table
            existing_task_cols = {
                row['name']
                for row in conn.execute('PRAGMA table_info(tasks)').fetchall()
            }
            for col_def in [
                ('focus_keys', 'TEXT'),
                ('expected_duration_minutes', 'INTEGER'),
                ('current_phase', 'TEXT'),
                ('phase_completed_at', 'TEXT'),
                ('duplicate_signature', 'TEXT'),
                ('category', 'TEXT'),
                ('commit_branch', 'TEXT'),
                ('auto_committed', 'INTEGER DEFAULT 0'),
            ]:
                if col_def[0] not in existing_task_cols:
                    conn.execute(f'ALTER TABLE tasks ADD COLUMN {col_def[0]} {col_def[1]}')

            conn.commit()

    def create_run(self, role: str, run_type: str) -> int:
        now = iso_utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO runs (role, run_type, status, message, started_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (role, run_type, 'RUNNING', '', now),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, message: str, task_id: int | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                UPDATE runs
                SET status = ?, message = ?, task_id = ?, finished_at = ?
                WHERE id = ?
                ''',
                (status, message, task_id, iso_utc_now(), run_id),
            )
            conn.commit()

    def list_recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT *
                FROM runs
                ORDER BY id DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_task(self, payload: dict[str, Any]) -> int:
        now = iso_utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO tasks (
                    task_uid,
                    title,
                    objective,
                    status,
                    gate_verdict,
                    gate_reason,
                    planner_provider,
                    worker_provider,
                    task_dir,
                    prompt_path,
                    contract_path,
                    worker_log_path,
                    completed_path,
                    result_path,
                    meta_path,
                    last_output_at,
                    latest_progress_summary,
                    created_at,
                    updated_at,
                    started_at,
                    finished_at,
                    focus_keys,
                    expected_duration_minutes,
                    duplicate_signature,
                    category
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    payload['task_uid'],
                    payload['title'],
                    payload['objective'],
                    payload['status'],
                    payload.get('gate_verdict'),
                    payload.get('gate_reason', ''),
                    payload['planner_provider'],
                    payload['worker_provider'],
                    payload['task_dir'],
                    payload['prompt_path'],
                    payload['contract_path'],
                    payload['worker_log_path'],
                    payload.get('completed_path'),
                    payload.get('result_path'),
                    payload['meta_path'],
                    payload.get('last_output_at'),
                    payload.get('latest_progress_summary'),
                    payload.get('created_at', now),
                    payload.get('updated_at', now),
                    payload.get('started_at'),
                    payload.get('finished_at'),
                    payload.get('focus_keys'),
                    payload.get('expected_duration_minutes'),
                    payload.get('duplicate_signature'),
                    payload.get('category'),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_latest_task(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 1').fetchone()
        return dict(row) if row else None

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT *
                FROM tasks
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                ''',
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active_task(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT *
                FROM tasks
                WHERE status = 'RUNNING'
                ORDER BY id DESC
                LIMIT 1
                '''
            ).fetchone()
        return dict(row) if row else None

    def claim_next_queued_task(self) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            queued = conn.execute(
                '''
                SELECT id
                FROM tasks
                WHERE status = 'QUEUED'
                ORDER BY id ASC
                LIMIT 1
                '''
            ).fetchone()
            if queued is None:
                conn.commit()
                return None
            now = iso_utc_now()
            conn.execute(
                '''
                UPDATE tasks
                SET status = 'RUNNING', started_at = ?, updated_at = ?
                WHERE id = ?
                ''',
                (now, now, queued['id']),
            )
            conn.commit()
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (queued['id'],)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_task(self, task_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields['updated_at'] = fields.get('updated_at', iso_utc_now())
        assignments = ', '.join(f'{key} = ?' for key in fields.keys())
        values = list(fields.values()) + [task_id]
        with self._connect() as conn:
            conn.execute(f'UPDATE tasks SET {assignments} WHERE id = ?', values)
            conn.commit()

    def update_task_progress(self, task_id: int, summary: str) -> None:
        now = iso_utc_now()
        self.update_task(task_id, latest_progress_summary=summary, last_output_at=now, updated_at=now)

    def get_task_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute('SELECT status, COUNT(*) AS count FROM tasks GROUP BY status').fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            counts[row['status']] = int(row['count'])
        return counts

    def get_scheduler_state(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM scheduler_state WHERE singleton_id = 1').fetchone()
        if row is None:
            raise RuntimeError('scheduler_state row is missing')
        data = dict(row)
        data['enabled'] = bool(data['enabled'])
        return data

    def get_setting(self, key: str, default: str = '') -> str:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT value FROM orchestrator_settings WHERE key = ?',
                (key,),
            ).fetchone()
        if row is None:
            return default
        return str(row['value'])

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO orchestrator_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                ''',
                (key, value, iso_utc_now()),
            )
            conn.commit()

    def set_settings(self, values: dict[str, Any]) -> None:
        if not values:
            return
        now = iso_utc_now()
        rows = [
            (key, '' if value is None else str(value), now)
            for key, value in values.items()
        ]
        with self._connect() as conn:
            conn.executemany(
                '''
                INSERT INTO orchestrator_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                ''',
                rows,
            )
            conn.commit()

    def get_int_setting(self, key: str, default: int = 0) -> int:
        raw = self.get_setting(key, str(default))
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def increment_setting(self, key: str, delta: int = 1) -> int:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT value FROM orchestrator_settings WHERE key = ?',
                (key,),
            ).fetchone()
            try:
                current = int(row['value']) if row is not None else 0
            except (TypeError, ValueError):
                current = 0
            next_value = current + delta
            now = iso_utc_now()
            conn.execute(
                '''
                INSERT INTO orchestrator_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                ''',
                (key, str(next_value), now),
            )
            conn.commit()
        return next_value

    def get_planner_provider(self) -> str:
        return self.get_setting('planner_provider', self.default_planner_provider or DEFAULT_SETTINGS['planner_provider'])

    def set_planner_provider(self, provider: str) -> None:
        self.set_setting('planner_provider', provider)

    def get_worker_provider(self) -> str:
        return self.get_setting('worker_provider', self.default_worker_provider or DEFAULT_SETTINGS['worker_provider'])

    def set_worker_provider(self, provider: str) -> None:
        self.set_setting('worker_provider', provider)

    def get_worker_copilot_model(self) -> str:
        return self.get_setting('worker_copilot_model', DEFAULT_SETTINGS['worker_copilot_model'])

    def set_worker_copilot_model(self, model: str) -> None:
        self.set_setting('worker_copilot_model', model)

    def update_scheduler_state(self, **fields: Any) -> dict[str, Any]:
        if not fields:
            return self.get_scheduler_state()
        normalized_fields = fields.copy()
        if 'enabled' in normalized_fields:
            normalized_fields['enabled'] = 1 if normalized_fields['enabled'] else 0
        normalized_fields['updated_at'] = iso_utc_now()
        assignments = ', '.join(f'{key} = ?' for key in normalized_fields.keys())
        values = list(normalized_fields.values())
        values.append(1)
        with self._connect() as conn:
            conn.execute(f'UPDATE scheduler_state SET {assignments} WHERE singleton_id = ?', values)
            conn.commit()
        return self.get_scheduler_state()

    # ── runs with request_id support ─────────────────────────────────────────

    def create_run_with_request_id(self, role: str, run_type: str) -> tuple[int, str]:
        """Create a run record with a tracking request_id. Returns (run_id, request_id)."""
        now = iso_utc_now()
        request_id = _new_request_id()
        with self._connect() as conn:
            cursor = conn.execute(
                'INSERT INTO runs (role, run_type, status, message, started_at, request_id, outcome) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (role, run_type, 'RUNNING', '', now, request_id, 'PENDING'),
            )
            conn.commit()
        return int(cursor.lastrowid), request_id

    def finish_run_with_outcome(
        self, run_id: int, status: str, message: str, outcome: str, task_id: int | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE runs SET status = ?, message = ?, task_id = ?, finished_at = ?, outcome = ? WHERE id = ?',
                (status, message, task_id, iso_utc_now(), outcome, run_id),
            )
            conn.commit()

    def get_run_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM runs WHERE request_id = ? ORDER BY id DESC LIMIT 1',
                (request_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_runs_by_role(
        self,
        role: str | None = None,
        limit: int = 500,
        since: str | None = None,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if role:
            filters.append('role = ?')
            params.append(role)
        if since:
            filters.append('started_at >= ?')
            params.append(since)
        if request_id:
            filters.append('request_id = ?')
            params.append(request_id)
        where = f'WHERE {" AND ".join(filters)}' if filters else ''
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT * FROM runs {where} ORDER BY id DESC LIMIT ?', params + [limit]
            ).fetchall()
        return [dict(row) for row in rows]

    def list_tasks_filtered(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        date_folder: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Returns (tasks, total)."""
        filters: list[str] = []
        params: list[Any] = []
        if status and status != 'ALL':
            filters.append('status = ?')
            params.append(status)
        if date_folder:
            # date_folder is YYYYMMDD; task_uid starts with that prefix
            filters.append("task_uid LIKE ?")
            params.append(f'{date_folder}%')
        where = f'WHERE {" AND ".join(filters)}' if filters else ''
        with self._connect() as conn:
            total_row = conn.execute(f'SELECT COUNT(*) as cnt FROM tasks {where}', params).fetchone()
            total = int(total_row['cnt']) if total_row else 0
            rows = conn.execute(
                f'SELECT * FROM tasks {where} ORDER BY id DESC LIMIT ? OFFSET ?',
                params + [limit, offset],
            ).fetchall()
        return [dict(row) for row in rows], total

    # ── CTO scheduler state (re-uses scheduler_state table columns) ───────────

    def get_cto_scheduler_state(self) -> dict[str, Any]:
        """Returns a simplified CTO scheduler view from scheduler_state."""
        state = self.get_scheduler_state()
        return {
            'enabled': state['enabled'],
            'frequency_mode': 'once_daily',
            'next_run_at': None,
        }

    # ── CTO Review Runs ───────────────────────────────────────────────────────

    def create_cto_review_run(self, payload: dict[str, Any]) -> str:
        run_id = payload.get('run_id') or str(uuid.uuid4())
        now = iso_utc_now()
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO cto_review_runs (
                    run_id, frequency_mode, is_manual, is_force_run, run_intent,
                    parent_run_id, dedupe_key, started_at, completed_at, duration_seconds,
                    checked_from, checked_until, candidate_count, pass_count, approved_count,
                    merged_count, replan_count, rejected_count, deferred_count,
                    superseded_count, duplicate_count, health_score, verdict, merge_branch,
                    report_json_path, summary, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''',
                (
                    run_id,
                    payload.get('frequency_mode', 'once_daily'),
                    1 if payload.get('is_manual') else 0,
                    1 if payload.get('is_force_run') else 0,
                    payload.get('run_intent'),
                    payload.get('parent_run_id'),
                    payload.get('dedupe_key'),
                    payload.get('started_at', now),
                    payload.get('completed_at'),
                    payload.get('duration_seconds'),
                    payload.get('checked_from'),
                    payload.get('checked_until'),
                    payload.get('candidate_count', 0),
                    payload.get('pass_count', 0),
                    payload.get('approved_count', 0),
                    payload.get('merged_count', 0),
                    payload.get('replan_count', 0),
                    payload.get('rejected_count', 0),
                    payload.get('deferred_count', 0),
                    payload.get('superseded_count', 0),
                    payload.get('duplicate_count', 0),
                    payload.get('health_score'),
                    payload.get('verdict'),
                    payload.get('merge_branch'),
                    payload.get('report_json_path'),
                    payload.get('summary'),
                    now,
                    now,
                ),
            )
            conn.commit()
        return run_id

    def update_cto_review_run(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields['updated_at'] = iso_utc_now()
        assignments = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [run_id]
        with self._connect() as conn:
            conn.execute(f'UPDATE cto_review_runs SET {assignments} WHERE run_id = ?', values)
            conn.commit()

    def get_cto_review_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM cto_review_runs WHERE run_id = ?', (run_id,)).fetchone()
        return dict(row) if row else None

    def list_cto_review_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        date_str: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if date_str and len(date_str) == 8:
            prefix = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
            filters.append('started_at LIKE ?')
            params.append(f'{prefix}%')
        if status:
            filters.append('status = ?')
            params.append(status)
        where = f'WHERE {" AND ".join(filters)}' if filters else ''
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT * FROM cto_review_runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?',
                params + [limit, offset],
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['is_manual'] = bool(d['is_manual'])
            d['is_force_run'] = bool(d['is_force_run'])
            result.append(d)
        return result

    def get_latest_cto_review_run(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM cto_review_runs ORDER BY started_at DESC LIMIT 1'
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d['is_manual'] = bool(d['is_manual'])
        d['is_force_run'] = bool(d['is_force_run'])
        return d

    def get_cto_summary_stats(self) -> dict[str, Any]:
        latest = self.get_latest_cto_review_run()
        with self._connect() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) as cnt FROM task_reviews WHERE decision = 'NEEDS_REPLAN'"
            ).fetchone()
            pass_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM task_reviews WHERE decision = 'PASS'"
            ).fetchone()
            deferred = conn.execute(
                "SELECT COUNT(*) as cnt FROM task_reviews WHERE decision = 'DEFERRED'"
            ).fetchone()
            closed = conn.execute(
                "SELECT COUNT(*) as cnt FROM task_reviews WHERE decision = 'CLOSED'"
            ).fetchone()
        return {
            'frequency_mode': 'once_daily',
            'latest_run_at': latest['started_at'] if latest else None,
            'next_run_at': None,
            'pending_count': int(pending['cnt']) if pending else 0,
            'approved_count': int(pass_count['cnt']) if pass_count else 0,
            'merged_count': 0,
            'rejected_count': int(deferred['cnt']) if deferred else 0,
            'deferred_count': int(deferred['cnt']) if deferred else 0,
            'superseded_count': 0,
            'duplicate_count': 0,
            'total_reviews': int((pass_count['cnt'] if pass_count else 0) +
                                 (pending['cnt'] if pending else 0) +
                                 (deferred['cnt'] if deferred else 0) +
                                 (closed['cnt'] if closed else 0)),
            'health_score': latest['health_score'] if latest else None,
            'verdict': latest['verdict'] if latest else None,
            'summary': latest['summary'] if latest else None,
        }

    # ── Task Reviews ──────────────────────────────────────────────────────────

    def save_task_review(self, payload: dict[str, Any]) -> int:
        now = iso_utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO task_reviews (
                    task_id, task_uid, cto_run_id, decision, severity,
                    impact_score, urgency, category, reason, suggested_action,
                    create_followup_task, changed_files_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''',
                (
                    payload['task_id'],
                    payload['task_uid'],
                    payload['cto_run_id'],
                    payload['decision'],
                    payload.get('severity', 'MEDIUM'),
                    payload.get('impact_score', 50),
                    payload.get('urgency', 'normal'),
                    payload.get('category', 'quality'),
                    payload.get('reason', ''),
                    payload.get('suggested_action', ''),
                    1 if payload.get('create_followup_task') else 0,
                    json.dumps(payload.get('changed_files', [])),
                    now,
                ),
            )
            conn.commit()
        return int(cursor.lastrowid)

    def list_task_reviews_for_run(self, cto_run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM task_reviews WHERE cto_run_id = ? ORDER BY id ASC',
                (cto_run_id,),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['create_followup_task'] = bool(d['create_followup_task'])
            try:
                d['changed_files'] = json.loads(d.get('changed_files_json') or '[]')
            except Exception:
                d['changed_files'] = []
            result.append(d)
        return result

    def list_pending_task_reviews(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Tasks that need attention (NEEDS_REPLAN decision without a followup yet)."""
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT tr.*, t.title as task_title
                FROM task_reviews tr
                LEFT JOIN tasks t ON t.id = tr.task_id
                WHERE tr.decision = 'NEEDS_REPLAN'
                ORDER BY tr.created_at DESC
                LIMIT ? OFFSET ?
                ''',
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    # ── CTO Intent Signals ────────────────────────────────────────────────────

    def save_cto_intent_signal(self, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO cto_intent_signals (
                    run_id, run_intent, outcome, candidate_count, pass_count,
                    replan_count, deferred_count, approved_count, is_compare_only, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                ''',
                (
                    payload['run_id'],
                    payload['run_intent'],
                    payload.get('outcome', 'completed'),
                    payload.get('candidate_count', 0),
                    payload.get('pass_count', 0),
                    payload.get('replan_count', 0),
                    payload.get('deferred_count', 0),
                    payload.get('approved_count', 0),
                    1 if payload.get('is_compare_only') else 0,
                    iso_utc_now(),
                ),
            )
            conn.commit()

    def get_cto_adaptive_policy(self) -> dict[str, Any]:
        """Derive adaptive policy from intent signal history."""
        with self._connect() as conn:
            signals = conn.execute(
                'SELECT * FROM cto_intent_signals ORDER BY created_at DESC LIMIT 100'
            ).fetchall()
        merge_rates: dict[str, dict[str, Any]] = {
            'retry': {'total': 0, 'pass': 0},
            'compare': {'total': 0, 'pass': 0},
            'override': {'total': 0, 'pass': 0},
        }
        for sig in signals:
            intent = sig['run_intent']
            if intent in merge_rates:
                merge_rates[intent]['total'] += sig['candidate_count'] or 0
                merge_rates[intent]['pass'] += sig['pass_count'] or 0
        intent_merge_rates: dict[str, float] = {}
        for intent, counts in merge_rates.items():
            total = counts['total']
            intent_merge_rates[intent] = round(counts['pass'] / total, 2) if total else 0.0
        return {
            'intent_merge_rates': intent_merge_rates,
            'policy_adjustments': {
                'retry_coverage_limit': 3,
                'category_priority_boosts': {},
            },
            'suggestions': [],
        }

    # ── CTO Backlog Items ─────────────────────────────────────────────────────

    def add_backlog_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = iso_utc_now()
        finding_id = payload.get('finding_id') or f"bl-{str(uuid.uuid4())[:8]}"
        # upsert: ignore if duplicate finding_id
        score = self._compute_priority_score(
            impact=payload.get('impact_score', 0),
            aging_bonus=payload.get('aging_bonus', 0),
            selection_count=0,
            severity=payload.get('severity', 'MEDIUM'),
        )
        level = self._score_to_level(score)
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT OR IGNORE INTO cto_backlog_items (
                    finding_id, cto_run_id, source, task_id, category, severity,
                    impact_score, urgency, suggested_action, status, priority_score,
                    priority_level, selection_count, aging_bonus, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''',
                (
                    finding_id,
                    payload.get('cto_run_id', ''),
                    payload.get('source', 'cto_review'),
                    payload.get('task_id'),
                    payload.get('category', 'quality'),
                    payload.get('severity', 'MEDIUM'),
                    payload.get('impact_score', 50),
                    payload.get('urgency', 'normal'),
                    payload.get('suggested_action', ''),
                    payload.get('status', 'pending'),
                    score,
                    level,
                    0,
                    0.0,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                'SELECT * FROM cto_backlog_items WHERE finding_id = ?', (finding_id,)
            ).fetchone()
        return dict(row) if row else {}

    def list_backlog_items(
        self,
        status: str | None = None,
        limit: int = 200,
        cto_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if status:
            filters.append('status = ?')
            params.append(status)
        if cto_run_id:
            filters.append('cto_run_id = ?')
            params.append(cto_run_id)
        where = f'WHERE {" AND ".join(filters)}' if filters else ''
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT * FROM cto_backlog_items {where} ORDER BY priority_score DESC LIMIT ?',
                params + [limit],
            ).fetchall()
        return [dict(row) for row in rows]

    def get_prioritized_backlog(self) -> dict[str, Any]:
        items = self.list_backlog_items(status='pending')
        levels: dict[str, list[dict[str, Any]]] = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
        for item in items:
            lvl = item.get('priority_level', 'P3')
            levels.setdefault(lvl, []).append(item)
        return {
            'items': items,
            'by_level': levels,
            'counts': {lvl: len(lst) for lvl, lst in levels.items()},
            'total': len(items),
        }

    def add_batch_backlog_items(self, cto_run_id: str, min_severity: str = 'HIGH', min_impact: int = 60) -> int:
        reviews = self.list_task_reviews_for_run(cto_run_id)
        rank_required = _SEVERITY_RANK.get(min_severity, 3)
        added = 0
        for rev in reviews:
            if rev['decision'] == CTO_DECISION_PASS:
                continue
            sev = rev.get('severity', 'MEDIUM')
            impact = rev.get('impact_score', 0)
            if _SEVERITY_RANK.get(sev, 0) >= rank_required and impact >= min_impact:
                self.add_backlog_item({
                    'finding_id': f"batch-{cto_run_id[:8]}-{rev['id']}",
                    'cto_run_id': cto_run_id,
                    'task_id': rev['task_id'],
                    'category': rev.get('category', 'quality'),
                    'severity': sev,
                    'impact_score': impact,
                    'urgency': rev.get('urgency', 'normal'),
                    'suggested_action': rev.get('suggested_action', ''),
                })
                added += 1
        return added

    def rescore_backlog_items(self) -> int:
        items = self.list_backlog_items()
        now = iso_utc_now()
        updated = 0
        with self._connect() as conn:
            for item in items:
                aging = item.get('aging_bonus', 0) + 2
                score = self._compute_priority_score(
                    impact=item.get('impact_score', 0),
                    aging_bonus=aging,
                    selection_count=item.get('selection_count', 0),
                    severity=item.get('severity', 'MEDIUM'),
                )
                level = self._score_to_level(score)
                conn.execute(
                    'UPDATE cto_backlog_items SET priority_score=?, priority_level=?, aging_bonus=?, updated_at=? WHERE id=?',
                    (score, level, aging, now, item['id']),
                )
                updated += 1
            conn.commit()
        return updated

    def apply_aging_to_backlog(self) -> int:
        return self.rescore_backlog_items()

    def get_execution_policy(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM execution_policy_state WHERE id = 1').fetchone()
        if row is None:
            return {'mode': 'balanced', 'recent_selections': [], 'consecutive_high': 0}
        d = dict(row)
        try:
            d['recent_selections'] = json.loads(d.get('recent_selections') or '[]')
        except Exception:
            d['recent_selections'] = []
        return d

    def update_execution_policy(self, **fields: Any) -> dict[str, Any]:
        if not fields:
            return self.get_execution_policy()
        fields['updated_at'] = iso_utc_now()
        assignments = ', '.join(f'{k} = ?' for k in fields)
        values = list(fields.values()) + [1]
        with self._connect() as conn:
            conn.execute(f'UPDATE execution_policy_state SET {assignments} WHERE id = ?', values)
            conn.commit()
        return self.get_execution_policy()

    @staticmethod
    def _compute_priority_score(impact: int, aging_bonus: float, selection_count: int, severity: str) -> float:
        sev_bonus = {'CRITICAL': 40, 'HIGH': 25, 'MEDIUM': 10, 'LOW': 0}.get(severity, 10)
        selection_penalty = min(selection_count * 5, 30)
        return round(impact + sev_bonus + aging_bonus - selection_penalty, 2)

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score >= 90:
            return 'P0'
        if score >= 70:
            return 'P1'
        if score >= 40:
            return 'P2'
        return 'P3'
