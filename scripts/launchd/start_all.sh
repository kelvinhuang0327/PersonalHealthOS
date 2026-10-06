#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

MODE="${1:-}"
FOREGROUND=false
if [[ "${MODE}" == "--foreground" ]]; then
  FOREGROUND=true
fi

ensure_dirs
require_cmd curl
require_cmd lsof
require_cmd node
load_backend_env_files

BACKEND_LOG_FILE="${LAUNCHD_LOG_DIR}/backend.service.log"
FRONTEND_LOG_FILE="${LAUNCHD_LOG_DIR}/frontend.service.log"

start_backend() {
  local python_bin="${PROJECT_ROOT}/backend/.venv/bin/python"
  [[ -x "${python_bin}" ]] || fail "backend python runtime missing: ${python_bin}"

  ensure_port_available_for_service "backend" "${BACKEND_PORT}" "${BACKEND_PID_FILE}"

  local existing_pid
  existing_pid="$(read_pid_file "${BACKEND_PID_FILE}")"
  if [[ -n "${existing_pid}" ]] && pid_is_running "${existing_pid}"; then
    log "Backend already running (pid=${existing_pid})"
    return 0
  fi

  log "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
  (
    cd "${PROJECT_ROOT}"
    export PYTHONPATH="${PROJECT_ROOT}/backend"
    export ORCHESTRATOR_SCHEDULER_AUTOSTART="${ORCHESTRATOR_SCHEDULER_AUTOSTART:-false}"
    export APP_AUTO_CREATE_TABLES="${APP_AUTO_CREATE_TABLES:-false}"
    "${python_bin}" -m uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" >>"${BACKEND_LOG_FILE}" 2>&1
  ) &
  local pid=$!
  write_pid_file "${BACKEND_PID_FILE}" "${pid}"
  sleep 1
  pid_is_running "${pid}" || fail "backend failed to start; inspect ${BACKEND_LOG_FILE}"
}

start_frontend() {
  local next_bin="${PROJECT_ROOT}/frontend/node_modules/.bin/next"
  [[ -x "${next_bin}" ]] || fail "frontend next runtime missing: ${next_bin}"

  ensure_port_available_for_service "frontend" "${FRONTEND_PORT}" "${FRONTEND_PID_FILE}"

  local existing_pid
  existing_pid="$(read_pid_file "${FRONTEND_PID_FILE}")"
  if [[ -n "${existing_pid}" ]] && pid_is_running "${existing_pid}"; then
    log "Frontend already running (pid=${existing_pid})"
    return 0
  fi

  log "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT}"
  (
    cd "${PROJECT_ROOT}/frontend"
    "${next_bin}" dev -H "${FRONTEND_HOST}" -p "${FRONTEND_PORT}" >>"${FRONTEND_LOG_FILE}" 2>&1
  ) &
  local pid=$!
  write_pid_file "${FRONTEND_PID_FILE}" "${pid}"
  sleep 1
  pid_is_running "${pid}" || fail "frontend failed to start; inspect ${FRONTEND_LOG_FILE}"
}

run_startup_checks() {
  log "Running startup health checks"
  "${SCRIPT_DIR}/health_check.sh"
  log "Running startup smoke checks"
  "${SCRIPT_DIR}/smoke_check.sh"
}

shutdown_all() {
  log "Shutting down all services"
  "${SCRIPT_DIR}/stop_all.sh" --quiet || true
}

monitor_foreground() {
  trap 'shutdown_all; exit 0' INT TERM
  log "Foreground monitor started"

  while true; do
    local backend_pid
    local frontend_pid
    backend_pid="$(read_pid_file "${BACKEND_PID_FILE}")"
    frontend_pid="$(read_pid_file "${FRONTEND_PID_FILE}")"

    if [[ -z "${backend_pid}" || -z "${frontend_pid}" ]]; then
      log "Missing pid file(s), exiting foreground monitor"
      shutdown_all
      exit 1
    fi
    if ! pid_is_running "${backend_pid}"; then
      log "Backend exited unexpectedly (pid=${backend_pid})"
      shutdown_all
      exit 1
    fi
    if ! pid_is_running "${frontend_pid}"; then
      log "Frontend exited unexpectedly (pid=${frontend_pid})"
      shutdown_all
      exit 1
    fi
    sleep 10
  done
}

start_backend
start_frontend

if ! run_startup_checks; then
  log "Startup checks failed"
  shutdown_all
  exit 1
fi

if [[ "${FOREGROUND}" == "true" ]]; then
  monitor_foreground
else
  log "Services started in background mode"
fi
