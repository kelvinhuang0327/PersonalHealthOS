from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_QUEUED = 'QUEUED'
STATUS_RUNNING = 'RUNNING'
STATUS_COMPLETED = 'COMPLETED'
STATUS_FAILED = 'FAILED'
STATUS_FAILED_RATE_LIMIT = 'FAILED_RATE_LIMIT'
STATUS_REPLAN_REQUIRED = 'REPLAN_REQUIRED'
STATUS_CANCELLED = 'CANCELLED'
STATUS_PENDING_REVIEW = 'PENDING_REVIEW'

GATE_PASS = 'PASS'
GATE_INVALID_DELIVERY = 'INVALID_DELIVERY'
GATE_FAILED_ACCEPTANCE = 'FAILED_ACCEPTANCE'
GATE_POLICY_VIOLATION = 'POLICY_VIOLATION'
GATE_WORKER_RUNTIME_FAILED = 'WORKER_RUNTIME_FAILED'
GATE_RATE_LIMIT = 'RATE_LIMIT'
GATE_RESULT_SHALLOW = 'RESULT_SHALLOW'

DEFAULT_REQUIRED_CONTRACT_FIELDS = [
    'version',
    'objective',
    'scope',
    'constraints',
    'acceptance_tests',
    'required_outputs',
    'forbidden_changes',
    'handoff_questions',
]

DEFAULT_REQUIRED_RESULT_FIELDS = [
    'version',
    'task_id',
    'status',
    'gate_verdict',
    'gate_reason',
    'duration_seconds',
    'changed_files',
    'acceptance_results',
    'next_action',
]

ORCHESTRATOR_PROFILE_ENV = 'ORCHESTRATOR_PROFILE_PATH'
COPILOT_DAEMON_HEARTBEAT_TTL = 45

PLANNER_PROVIDER_LABELS = {
    'claude': 'Claude CLI',
    'codex': 'Codex CLI',
}

WORKER_PROVIDER_LABELS = {
    'codex': 'Codex CLI',
    'claude': 'Claude CLI',
    'copilot': 'GitHub Copilot CLI',
    'copilot-daemon': 'GitHub Copilot Daemon',
}

WORKER_COPILOT_MODEL_PRESETS = [
    {'value': '', 'label': '預設'},
    {'value': 'auto', 'label': 'auto（建議）'},
    {'value': 'gpt-5-mini', 'label': 'gpt-5-mini'},
]


@dataclass(frozen=True)
class LoadedProfile:
    repo_root: Path
    profile_path: Path
    schema_path: Path
    profile: dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc_now() -> str:
    return utc_now().isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def repo_root_from_backend_module() -> Path:
    return Path(__file__).resolve().parents[3]


def provider_label(provider: str | None) -> str:
    labels = PLANNER_PROVIDER_LABELS | WORKER_PROVIDER_LABELS
    return labels.get(provider or '', provider or '—')


def _which(binary: str) -> str | None:
    return shutil.which(binary)


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def copilot_daemon_status(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or repo_root_from_backend_module()
    state_path = root / 'runtime/agent_orchestrator/locks/copilot_daemon_state.json'
    if not state_path.exists():
        return {'running': False, 'reason': 'Ready; start resident LaunchAgent to run Copilot in user session'}

    try:
        payload = json.loads(state_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'running': False, 'reason': 'Daemon state file unreadable'}

    pid = payload.get('pid')
    heartbeat_at = parse_iso_datetime(payload.get('heartbeat_at'))
    if not isinstance(pid, int) or heartbeat_at is None:
        return {'running': False, 'reason': 'Daemon state file incomplete'}

    age_seconds = (utc_now() - heartbeat_at).total_seconds()
    if not is_process_alive(pid) or age_seconds > COPILOT_DAEMON_HEARTBEAT_TTL:
        return {'running': False, 'reason': 'Ready; start resident LaunchAgent to run Copilot in user session'}

    return {'running': True, 'pid': pid, 'reason': f'Daemon running (PID {pid})'}


def provider_available(provider: str, repo_root: Path | None = None) -> dict[str, Any]:
    if provider == 'codex':
        available = _which('codex') is not None
        return {'available': available, 'reason': 'Ready' if available else 'Codex CLI not found'}
    if provider == 'claude':
        available = _which('claude') is not None
        return {'available': available, 'reason': 'Ready' if available else 'Claude CLI not found'}
    if provider == 'copilot':
        available = _which('gh') is not None
        return {'available': available, 'reason': 'Ready' if available else 'GitHub CLI not found'}
    if provider == 'copilot-daemon':
        gh_ready = _which('gh') is not None
        if not gh_ready:
            return {'available': False, 'reason': 'GitHub CLI not found'}
        status = copilot_daemon_status(repo_root=repo_root)
        return {'available': True, 'reason': status['reason'], **status}
    return {'available': False, 'reason': f'Unknown provider: {provider}'}


def planner_provider_options() -> list[dict[str, Any]]:
    return [
        {
            'value': value,
            'label': provider_label(value),
            **provider_available(value),
        }
        for value in ('claude', 'codex')
    ]


def worker_provider_options(repo_root: Path | None = None) -> list[dict[str, Any]]:
    return [
        {
            'value': value,
            'label': provider_label(value),
            **provider_available(value, repo_root=repo_root),
        }
        for value in ('codex', 'copilot', 'copilot-daemon', 'claude')
    ]


def validate_copilot_model(model: str | None) -> str:
    value = (model or '').strip()
    if not value:
        return ''
    if value == 'auto':
        return value
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,63}', value):
        raise ValueError('worker_copilot_model 格式不合法')
    return value


def guess_repo_root_from_profile_path(profile_path: Path) -> Path:
    if (
        profile_path.name == 'project_profile.json'
        and profile_path.parent.name == 'agent_orchestrator'
        and profile_path.parent.parent.name == 'runtime'
    ):
        return profile_path.parents[2]
    return profile_path.parent


def resolve_with_root(repo_root: Path, path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_project_profile(profile_path: str | None = None, schema_path: str | None = None) -> LoadedProfile:
    env_profile = os.environ.get(ORCHESTRATOR_PROFILE_ENV)
    resolved_profile_value = profile_path or env_profile

    if resolved_profile_value:
        profile_file = Path(resolved_profile_value).expanduser().resolve()
        repo_root = guess_repo_root_from_profile_path(profile_file)
    else:
        repo_root = repo_root_from_backend_module()
        profile_file = repo_root / 'runtime/agent_orchestrator/project_profile.json'

    if schema_path:
        schema_file = Path(schema_path).expanduser().resolve()
    else:
        schema_file = resolve_with_root(repo_root, 'runtime/agent_orchestrator/project_profile.schema.json')

    if not profile_file.exists():
        raise FileNotFoundError(f'Orchestrator profile not found: {profile_file}')
    if not schema_file.exists():
        raise FileNotFoundError(f'Orchestrator schema not found: {schema_file}')

    profile = read_json(profile_file)
    schema = read_json(schema_file)
    validate_profile_against_schema(profile, schema)
    ensure_runtime_structure(repo_root, profile)
    return LoadedProfile(repo_root=repo_root, profile_path=profile_file, schema_path=schema_file, profile=profile)


def save_project_profile(loaded: LoadedProfile, profile: dict[str, Any]) -> None:
    schema = read_json(loaded.schema_path)
    validate_profile_against_schema(profile, schema)
    write_json(loaded.profile_path, profile)


def ensure_runtime_structure(repo_root: Path, profile: dict[str, Any]) -> None:
    for key in ['orchestrator_root', 'task_storage_path', 'log_storage_path']:
        resolve_with_root(repo_root, profile[key]).mkdir(parents=True, exist_ok=True)
    backlog_path = resolve_with_root(repo_root, profile['backlog_path'])
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    if not backlog_path.exists():
        backlog_path.write_text('# Agent Orchestrator Backlog\n', encoding='utf-8')


def slugify(text: str, limit: int = 56) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')
    if not normalized:
        normalized = 'task'
    return normalized[:limit]


def make_task_uid(now: datetime | None = None) -> str:
    current = now or utc_now()
    return current.strftime('%Y%m%d%H%M%S')


def build_task_paths(loaded: LoadedProfile, task_uid: str, slug: str) -> dict[str, str]:
    day_partition = task_uid[:8]
    task_dir_rel = Path(loaded.profile['task_storage_path']) / day_partition
    base_name = f'{task_uid}-{slug}'
    paths = {
        'task_dir': task_dir_rel.as_posix(),
        'prompt_path': (task_dir_rel / f'{base_name}-prompt.md').as_posix(),
        'contract_path': (task_dir_rel / f'{base_name}-contract.json').as_posix(),
        'worker_log_path': (task_dir_rel / f'{base_name}-worker-stdout.log').as_posix(),
        'completed_path': (task_dir_rel / f'{base_name}-completed.md').as_posix(),
        'result_path': (task_dir_rel / f'{base_name}-result.json').as_posix(),
        'meta_path': (task_dir_rel / f'{base_name}-meta.json').as_posix(),
    }
    resolve_with_root(loaded.repo_root, paths['task_dir']).mkdir(parents=True, exist_ok=True)
    return paths


def read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding='utf-8')


def detect_rate_limit_details(text: str | None, provider: str | None = None) -> dict[str, str] | None:
    if not text:
        return None

    normalized = ' '.join(text.split())
    lowered = normalized.lower()
    signals = [
        "you've hit your rate limit",
        'you have hit your rate limit',
        'please wait for your limit to reset',
        'rate limit exceeded',
        'rate limited',
        'too many requests',
        '429',
    ]
    if not any(signal in lowered for signal in signals) and 'rate limit' not in lowered:
        return None

    matched_excerpt = normalized[:240]
    provider_name = provider or 'provider'
    final_message = (
        f'Detected {provider_name} rate limit output and terminalized the task to avoid planner deadlock.'
    )
    return {
        'failure_reason': 'PROVIDER_RATE_LIMIT',
        'gate_reason': f'{provider_name} rate limit detected: {matched_excerpt}',
        'final_message': final_message,
        'reset_hint': 'Wait for the provider quota window to reset or switch worker provider before retrying.',
        'matched_excerpt': matched_excerpt,
        'provider': provider_name,
    }


def build_rate_limit_result(
    task_id: int,
    provider: str | None,
    evidence_text: str,
    duration_seconds: int,
) -> dict[str, Any]:
    details = detect_rate_limit_details(evidence_text, provider=provider)
    if details is None:
        raise ValueError('rate-limit result requested without a rate-limit signal')

    return {
        'version': '1.0',
        'task_id': task_id,
        'status': STATUS_FAILED_RATE_LIMIT,
        'gate_verdict': GATE_RATE_LIMIT,
        'gate_reason': details['gate_reason'],
        'duration_seconds': max(1, duration_seconds),
        'changed_files': [],
        'error_markers_hit': ['provider_rate_limit'],
        'missing_required_outputs': [],
        'forbidden_change_violations': [],
        'acceptance_results': [],
        'next_action': 'Planner may proceed to other tasks while this one waits for provider quota reset.',
        'failure_reason': details['failure_reason'],
        'final_message': details['final_message'],
        'reset_hint': details['reset_hint'],
        'provider': details['provider'],
        'matched_excerpt': details['matched_excerpt'],
    }


def summarize_progress_line(line: str, limit: int = 240) -> str:
    cleaned = ' '.join(line.strip().split())
    return cleaned[:limit]


def is_forbidden_change(path_value: str, protected_paths: list[str]) -> bool:
    normalized = path_value.strip().replace('\\', '/').lstrip('./')
    for protected in protected_paths:
        protected_norm = protected.strip().replace('\\', '/').lstrip('./')
        protected_norm = protected_norm.rstrip('/')
        if not protected_norm:
            continue
        if normalized == protected_norm or normalized.startswith(f'{protected_norm}/'):
            return True
    return False


def validate_profile_against_schema(profile: dict[str, Any], schema: dict[str, Any]) -> None:
    errors: list[str] = []
    _validate_schema_node(profile, schema, '$', errors)
    if errors:
        raise ValueError('Profile schema validation failed:\n' + '\n'.join(errors))


def _validate_schema_node(instance: Any, schema: dict[str, Any], pointer: str, errors: list[str]) -> None:
    expected_type = schema.get('type')
    if expected_type:
        if not _is_schema_type(instance, expected_type):
            errors.append(f'{pointer}: expected type "{expected_type}", got "{type(instance).__name__}"')
            return

    if 'enum' in schema and instance not in schema['enum']:
        errors.append(f'{pointer}: value "{instance}" not in enum {schema["enum"]}')

    if expected_type == 'object':
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        additional = schema.get('additionalProperties', True)

        for key in required:
            if key not in instance:
                errors.append(f'{pointer}: missing required key "{key}"')

        if additional is False:
            unknown_keys = sorted(set(instance.keys()) - set(properties.keys()))
            for key in unknown_keys:
                errors.append(f'{pointer}: unexpected key "{key}"')

        for key, value in instance.items():
            if key in properties:
                _validate_schema_node(value, properties[key], f'{pointer}.{key}', errors)

    if expected_type == 'array':
        min_items = schema.get('minItems')
        if min_items is not None and len(instance) < min_items:
            errors.append(f'{pointer}: expected at least {min_items} items, got {len(instance)}')
        item_schema = schema.get('items')
        if item_schema:
            for idx, item in enumerate(instance):
                _validate_schema_node(item, item_schema, f'{pointer}[{idx}]', errors)

    if expected_type == 'string':
        min_length = schema.get('minLength')
        if min_length is not None and len(instance) < min_length:
            errors.append(f'{pointer}: expected minLength {min_length}, got {len(instance)}')
        pattern = schema.get('pattern')
        if pattern and re.fullmatch(pattern, instance) is None:
            errors.append(f'{pointer}: value "{instance}" does not match pattern "{pattern}"')

    if expected_type == 'integer':
        minimum = schema.get('minimum')
        maximum = schema.get('maximum')
        if minimum is not None and instance < minimum:
            errors.append(f'{pointer}: expected minimum {minimum}, got {instance}')
        if maximum is not None and instance > maximum:
            errors.append(f'{pointer}: expected maximum {maximum}, got {instance}')


def _is_schema_type(instance: Any, expected_type: str) -> bool:
    if expected_type == 'object':
        return isinstance(instance, dict)
    if expected_type == 'array':
        return isinstance(instance, list)
    if expected_type == 'string':
        return isinstance(instance, str)
    if expected_type == 'integer':
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == 'boolean':
        return isinstance(instance, bool)
    return True


# ── Auto-commit helpers ───────────────────────────────────────────────────────

# Files / directories that should never be auto-committed
_COMMIT_EXCLUDED_PATTERNS: list[str] = [
    'runtime/agent_orchestrator/orchestrator.db',
    'runtime/agent_orchestrator/locks/',
    '__pycache__/',
    '.next/',
    'node_modules/',
]
_COMMIT_EXCLUDED_EXTENSIONS: frozenset[str] = frozenset({'.pyc', '.pyo', '.pyd'})

# Directories whose changes frequently conflict with other branches
_HIGH_CONFLICT_DIRS: frozenset[str] = frozenset({
    'backend/',
    'frontend/',
    'database/',
    'scripts/',
    'infra/',
})


def git_changed_files(repo_root: Path) -> list[str]:
    """Return a list of changed/new files reported by ``git status --porcelain``.

    Returns an empty list when git is unavailable or the directory is not a
    repository — allowing callers to degrade gracefully.
    """
    import subprocess  # noqa: PLC0415
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=repo_root, timeout=15, check=False,
        )
        if result.returncode != 0:
            return []
        files: list[str] = []
        for line in result.stdout.splitlines():
            if len(line) < 3:
                continue
            file_part = line[3:].strip()
            # Handle renames: "old -> new"
            if ' -> ' in file_part:
                file_part = file_part.split(' -> ')[-1]
            files.append(file_part.strip())
        return files
    except Exception:
        return []


def filter_committable_paths(
    changed_files: list[str],
    protected_paths: list[str],
    task_artifact_paths: list[str] | None = None,
) -> list[str]:
    """Return files from *changed_files* that are safe to auto-commit.

    Always includes *task_artifact_paths* (task-owned output files).
    Excludes: protected paths from profile, runtime DB/lock files, and build
    artefacts (.pyc, node_modules, .next, etc.).
    """
    artifact_set: frozenset[str] = frozenset(task_artifact_paths or [])
    result: list[str] = []
    for f in changed_files:
        # Task-owned artifacts always go in
        if f in artifact_set:
            result.append(f)
            continue
        # Skip profile-protected paths
        if is_forbidden_change(f, protected_paths):
            continue
        # Skip excluded extensions
        if Path(f).suffix.lower() in _COMMIT_EXCLUDED_EXTENSIONS:
            continue
        # Skip excluded runtime / build directories
        if any(f == pat or f.startswith(pat) for pat in _COMMIT_EXCLUDED_PATTERNS):
            continue
        result.append(f)
    return sorted(set(result))


def is_high_conflict_path(path: str) -> bool:
    """Return True when *path* lives in a directory prone to merge conflicts."""
    norm = path.strip().lstrip('./')
    return any(norm == d.rstrip('/') or norm.startswith(d) for d in _HIGH_CONFLICT_DIRS)


def git_branch_name_for_task(task_uid: str, task_id: int, slug: str) -> str:
    """Return the auto-commit inbox branch name for a task."""
    day = task_uid[:8]
    safe_slug = slug[:40].rstrip('-')
    return f'runtime/agent_orchestrator/inbox/{day}/task-{task_id}-{safe_slug}'
