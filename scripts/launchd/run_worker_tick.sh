#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs

PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
[[ -x "${PYTHON_BIN}" ]] || fail "backend python runtime missing: ${PYTHON_BIN}"

log "Worker tick start"

PYTHONPATH="${PROJECT_ROOT}/backend" "${PYTHON_BIN}" - <<'PY'
import json
import sys

from app.orchestrator.worker_tick import run_worker_tick

result = run_worker_tick(
    profile_path='runtime/agent_orchestrator/project_profile.json',
    run_type='scheduler',
)
print(json.dumps(result, ensure_ascii=False))
if result.get('status') == 'FAILED':
    sys.exit(1)
PY

log "Worker tick done"
