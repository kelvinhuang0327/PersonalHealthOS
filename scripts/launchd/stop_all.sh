#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

QUIET=false
if [[ "${1:-}" == "--quiet" ]]; then
  QUIET=true
fi

ensure_dirs
require_cmd lsof

log_if_needed() {
  if [[ "${QUIET}" != "true" ]]; then
    log "$*"
  fi
}

stop_service() {
  local service_name="$1"
  local pid_file="$2"
  local port="$3"
  local pid

  pid="$(read_pid_file "${pid_file}")"
  if [[ -n "${pid}" ]] && pid_is_running "${pid}"; then
    log_if_needed "Stopping ${service_name} (pid=${pid})"
    kill_pid_gracefully "${pid}" 12
  fi
  remove_pid_file "${pid_file}"

  if is_port_listening "${port}"; then
    local occupiers
    occupiers="$(list_port_pids "${port}")"
    log_if_needed "Cleaning remaining ${service_name} port occupants ${port}: ${occupiers}"
    kill_port_occupiers "${port}"
  fi
}

stop_service "frontend" "${FRONTEND_PID_FILE}" "${FRONTEND_PORT}"
stop_service "backend" "${BACKEND_PID_FILE}" "${BACKEND_PORT}"

log_if_needed "All services stopped"
