#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

echo "== launchctl list =="
launchctl list | grep -E 'com\.personalhealthos\.' || true

echo
echo "== Service Ports =="
echo "backend:${BACKEND_PORT}"
lsof -nP -iTCP:"${BACKEND_PORT}" -sTCP:LISTEN || true
echo "frontend:${FRONTEND_PORT}"
lsof -nP -iTCP:"${FRONTEND_PORT}" -sTCP:LISTEN || true

echo
echo "== PID Files =="
ls -la "${LAUNCHD_PID_DIR}" || true

echo
echo "== LLM Control State =="
PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
	PYTHONPATH="${PROJECT_ROOT}/backend" "${PYTHON_BIN}" - <<'PY'
import json

from app.orchestrator.execution_policy import get_llm_control_state

state = get_llm_control_state(profile_path='runtime/agent_orchestrator/project_profile.json')
print(json.dumps(state, ensure_ascii=False, indent=2))
PY
else
	echo "backend python runtime missing: ${PYTHON_BIN}"
fi

echo
echo "== Log Files =="
ls -la "${LAUNCHD_LOG_DIR}" || true
