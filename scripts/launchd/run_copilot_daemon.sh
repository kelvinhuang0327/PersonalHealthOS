#!/usr/bin/env bash
# run_copilot_daemon.sh — launch script for the GitHub Copilot Daemon LaunchAgent.
# Must be run with WorkingDirectory = PROJECT_ROOT (set in the plist template).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs

PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
[[ -x "${PYTHON_BIN}" ]] || fail "backend python runtime missing: ${PYTHON_BIN}"

POLL_SECONDS="${COPILOT_DAEMON_POLL_SECONDS:-10}"
PROFILE_PATH="${COPILOT_DAEMON_PROFILE_PATH:-runtime/agent_orchestrator/project_profile.json}"

log "Copilot daemon start poll=${POLL_SECONDS}s profile=${PROFILE_PATH}"

export PYTHONPATH="${PROJECT_ROOT}/backend"
exec "${PYTHON_BIN}" -m app.orchestrator.copilot_daemon \
  --profile "${PROFILE_PATH}" \
  --poll-seconds "${POLL_SECONDS}"
