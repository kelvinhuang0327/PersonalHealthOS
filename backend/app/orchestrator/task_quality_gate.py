from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


BANNED_PATTERNS: list[str] = [
    'SIGNAL_EXHAUSTED',
    'NO_SIGNAL',
    '停止建議',
    '目前沒有方向',
]
# Internal alias kept for any direct internal use
_BANNED_PATTERNS = BANNED_PATTERNS

_PHASE_RE = re.compile(r'^\s*(?:Phase|階段|Step)\s*(\d+)\s*[:：-]\s*(.+?)\s*$', re.IGNORECASE)
_TASK_START_RE = re.compile(r'^\s*[-*]\s*\[\s\]\s*(.+?)\s*$')
_TASK_STOP_RE = re.compile(r'^\s*(?:[-*]\s*\[[ xX]\]|#{1,6}\s+)')
_FOCUS_KEYS_RE = re.compile(r'^\s*focus[_\-]?keys?\s*[:：]\s*(.+?)\s*$', re.IGNORECASE)
_EXPECTED_DURATION_RE = re.compile(
    r'^\s*expected[_\-]?duration(?:[_\-]?minutes?)?\s*[:：]\s*(.+?)\s*$', re.IGNORECASE
)
_ACCEPTANCE_RE = re.compile(
    r'acceptance.{0,25}criteria|驗收條件|acceptance.{0,25}check|✓ passes|完成條件|completed when|done when',
    re.IGNORECASE,
)
_SCOPE_RE = re.compile(
    r'scope[:：]|files?_or_modules?|target.{0,20}module|inspect[:：]|範圍[:：]|作用範圍',
    re.IGNORECASE,
)

# Minimum content depth for a genuine 8-hour task
_MIN_DRAFT_CHARS = 200
_MIN_CONTENT_LINES = 3  # phases / scope / acceptance lines


@dataclass(frozen=True)
class TaskDraft:
    title: str
    draft_markdown: str
    focus_keys: tuple[str, ...] = ()
    expected_duration_minutes: int | None = None
    category: str | None = None
    duplicate_signature: str | None = None


@dataclass(frozen=True)
class QualityGateResult:
    quality_status: str
    reasons: list[str]

    @property
    def passed(self) -> bool:
        return self.quality_status == 'PASS'


def extract_task_drafts(backlog_content: str) -> list[TaskDraft]:
    drafts: list[TaskDraft] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in backlog_content.splitlines():
        start_match = _TASK_START_RE.match(raw_line)
        if start_match:
            _flush_current_draft(drafts, current_title, current_lines)
            current_title = start_match.group(1).strip()
            current_lines = [current_title]
            continue

        if current_title is None:
            continue

        if _TASK_STOP_RE.match(raw_line):
            _flush_current_draft(drafts, current_title, current_lines)
            current_title = None
            current_lines = []
            continue

        if _is_continuation_line(raw_line):
            _append_continuation_line(current_lines, raw_line)
            continue

        _flush_current_draft(drafts, current_title, current_lines)
        current_title = None
        current_lines = []

    _flush_current_draft(drafts, current_title, current_lines)

    return drafts


def _flush_current_draft(drafts: list[TaskDraft], title: str | None, lines: list[str]) -> None:
    if title is None:
        return
    draft_markdown = '\n'.join(lines).strip()
    drafts.append(TaskDraft(
        title=title,
        draft_markdown=draft_markdown,
        focus_keys=tuple(_parse_focus_keys(draft_markdown)),
        expected_duration_minutes=_parse_expected_duration_minutes(draft_markdown),
    ))


def _is_continuation_line(raw_line: str) -> bool:
    return raw_line.startswith('  ') or raw_line.startswith('\t') or not raw_line.strip()


def _append_continuation_line(current_lines: list[str], raw_line: str) -> None:
    stripped = raw_line.strip()
    if stripped or current_lines[-1] != '':
        current_lines.append(stripped)


def _parse_focus_keys(text: str) -> list[str]:
    for line in text.splitlines():
        m = _FOCUS_KEYS_RE.match(line)
        if m:
            return [k.strip() for k in m.group(1).split(',') if k.strip()]
    return []


def _parse_expected_duration_minutes(text: str) -> int | None:
    for line in text.splitlines():
        m = _EXPECTED_DURATION_RE.match(line)
        if not m:
            continue
        value = m.group(1).strip()
        range_match = re.match(r'^(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*h$', value, re.IGNORECASE)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            return int((low + high) / 2 * 60)
        single_match = re.match(r'^(\d+(?:\.\d+)?)\s*h$', value, re.IGNORECASE)
        if single_match:
            return int(float(single_match.group(1)) * 60)
        int_match = re.match(r'^(\d+)$', value)
        if int_match:
            return int(int_match.group(1))
    return None


def evaluate_task_draft(draft: TaskDraft, recent_tasks: list[dict[str, Any]]) -> QualityGateResult:
    """Quality gate for Personal Health OS 8-hour improvement tasks.

    Checks:
    - No banned tokens
    - Minimum content depth (not a stub / one-liner)
    - Acceptance criteria present
    - No duplicate active task with same objective or signature
    """
    reasons: list[str] = []
    text = draft.draft_markdown

    # ── 1. Banned content ────────────────────────────────────────────────────
    banned_found = [token for token in _BANNED_PATTERNS if token.lower() in text.lower()]
    if banned_found:
        reasons.append(f"BANNED_CONTENT: contains forbidden tokens {', '.join(banned_found)}.")

    # ── 2. Content depth ─────────────────────────────────────────────────────
    char_count = len(text.strip())
    content_line_count = _count_content_lines(text)
    if char_count < _MIN_DRAFT_CHARS or content_line_count < _MIN_CONTENT_LINES:
        reasons.append(
            f'CONTENT_TOO_SHALLOW: draft has {char_count} chars and {content_line_count} content '
            f'lines (need ≥{_MIN_DRAFT_CHARS} chars and ≥{_MIN_CONTENT_LINES} phases/scope/acceptance lines). '
            'A genuine 8-hour task requires detailed objective, phased steps, scope, and acceptance criteria.'
        )

    # ── 3. Acceptance criteria ───────────────────────────────────────────────
    if not _ACCEPTANCE_RE.search(text):
        reasons.append(
            'MISSING_ACCEPTANCE_CRITERIA: task must include acceptance criteria '
            '(e.g., "Acceptance Criteria:", "驗收條件:", or checkable completion conditions).'
        )

    # ── 4. Duplicate check (active tasks only) ───────────────────────────────
    duplicate_reason = _check_duplicate(draft, recent_tasks)
    if duplicate_reason:
        reasons.append(duplicate_reason)

    return QualityGateResult(quality_status='PASS' if not reasons else 'REJECT', reasons=reasons)


def _count_content_lines(text: str) -> int:
    """Count meaningful content lines: phases, scope, acceptance, objectives."""
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_phase = bool(_PHASE_RE.match(line))
        is_scope = bool(_SCOPE_RE.search(stripped))
        is_acceptance = bool(_ACCEPTANCE_RE.search(stripped))
        is_objective = stripped.lower().startswith(('objective', 'goal', '目標', 'deliverable'))
        is_recommended = stripped.lower().startswith(('recommended', 'command', 'files', 'inspect'))
        if is_phase or is_scope or is_acceptance or is_objective or is_recommended:
            count += 1
    return count


def _extract_phases(text: str) -> dict[int, str]:
    phases: dict[int, str] = {}
    for line in text.splitlines():
        match = _PHASE_RE.match(line)
        if not match:
            continue
        phase_no = int(match.group(1))
        description = match.group(2).strip()
        if description:
            phases[phase_no] = description
    return phases


def _has_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _check_duplicate(draft: TaskDraft, recent_tasks: list[dict[str, Any]]) -> str | None:
    """Block tasks whose signature or objective is already ACTIVE (QUEUED/RUNNING/REPLAN_REQUIRED).

    Cooldown rotation for completed tasks is handled by pick_next_category — the gate
    should never block based on completion history alone, because that causes deadlocks
    when all pool signatures have been completed recently.
    Title-based deduplication only applies to ACTIVE tasks (titles vary between sprints).
    """
    _ACTIVE_STATUSES = {'QUEUED', 'RUNNING', 'REPLAN_REQUIRED'}

    new_title = _normalize_text(draft.title)
    new_sig = (draft.duplicate_signature or '').strip()

    for task in recent_tasks:
        task_status = str(task.get('status') or '')
        task_id = task.get('id', '?')
        task_sig = str(task.get('duplicate_signature') or '').strip()

        if task_status in _ACTIVE_STATUSES:
            # Block immediately — same signature already queued/running
            if new_sig and task_sig and task_sig == new_sig:
                return (
                    f'DUPLICATE_TASK: 任務 #{task_id}（{task_status}）已有相同識別碼 '
                    f'"{new_sig}"，不可重複建立。'
                )
            objective = _normalize_text(str(task.get('objective') or task.get('title') or ''))
            if objective and objective == new_title:
                return (
                    f'DUPLICATE_TASK: 任務 #{task_id}（{task_status}）目標相同，'
                    '請換一個類別或模組。'
                )

    return None


def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())


def _jaccard_tokens(left: str, right: str) -> float:
    left_tokens = {token for token in re.split(r'[^\w\u4e00-\u9fff]+', left) if len(token) >= 2}
    right_tokens = {token for token in re.split(r'[^\w\u4e00-\u9fff]+', right) if len(token) >= 2}
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union if union else 0.0