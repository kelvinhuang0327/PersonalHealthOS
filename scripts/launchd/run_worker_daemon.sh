#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs

PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
[[ -x "${PYTHON_BIN}" ]] || fail "backend python runtime missing: ${PYTHON_BIN}"

INTERVAL_SECONDS="${WORKER_DAEMON_INTERVAL_SECONDS:-30}"
PROFILE_PATH="${WORKER_DAEMON_PROFILE_PATH:-runtime/agent_orchestrator/project_profile.json}"

log "Worker daemon start interval=${INTERVAL_SECONDS}s profile=${PROFILE_PATH}"

export PYTHONPATH="${PROJECT_ROOT}/backend"
exec "${PYTHON_BIN}" -m app.orchestrator.worker_daemon \
  --profile "${PROFILE_PATH}" \
  --interval-seconds "${INTERVAL_SECONDS}"
