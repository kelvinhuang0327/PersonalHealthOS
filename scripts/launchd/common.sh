#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

LAUNCHD_RUNTIME_DIR="${PROJECT_ROOT}/runtime/launchd"
LAUNCHD_LOG_DIR="${LAUNCHD_RUNTIME_DIR}/logs"
LAUNCHD_PID_DIR="${LAUNCHD_RUNTIME_DIR}/pids"
LAUNCHD_PLIST_GEN_DIR="${PROJECT_ROOT}/launchd/generated"
LAUNCHD_TEMPLATE_DIR="${PROJECT_ROOT}/launchd/templates"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3100}"

BACKEND_PID_FILE="${LAUNCHD_PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${LAUNCHD_PID_DIR}/frontend.pid"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  echo "[$(timestamp)] $*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

ensure_dirs() {
  mkdir -p "${LAUNCHD_RUNTIME_DIR}" "${LAUNCHD_LOG_DIR}" "${LAUNCHD_PID_DIR}" "${LAUNCHD_PLIST_GEN_DIR}"
}

require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || fail "required command not found: ${cmd}"
}

pid_is_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1
}

read_pid_file() {
  local pid_file="$1"
  if [[ -f "${pid_file}" ]]; then
    tr -d ' \n\t\r' <"${pid_file}"
  else
    echo ""
  fi
}

write_pid_file() {
  local pid_file="$1"
  local pid="$2"
  echo "${pid}" >"${pid_file}"
}

remove_pid_file() {
  local pid_file="$1"
  rm -f "${pid_file}"
}

list_port_pids() {
  local port="$1"
  lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true
}

is_port_listening() {
  local port="$1"
  [[ -n "$(list_port_pids "${port}")" ]]
}

ensure_port_available_for_service() {
  local service_name="$1"
  local port="$2"
  local pid_file="$3"

  local existing_pid
  existing_pid="$(read_pid_file "${pid_file}")"

  if [[ -n "${existing_pid}" ]] && pid_is_running "${existing_pid}"; then
    return 0
  fi

  local occupiers
  occupiers="$(list_port_pids "${port}")"
  if [[ -n "${occupiers}" ]]; then
    fail "${service_name} target port ${port} is already occupied by pid(s): ${occupiers}"
  fi
}

kill_pid_gracefully() {
  local pid="$1"
  local timeout_seconds="${2:-10}"
  if ! pid_is_running "${pid}"; then
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  local waited=0
  while pid_is_running "${pid}" && [[ "${waited}" -lt "${timeout_seconds}" ]]; do
    sleep 1
    waited=$((waited + 1))
  done
  if pid_is_running "${pid}"; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
}

kill_port_occupiers() {
  local port="$1"
  local pids
  pids="$(list_port_pids "${port}")"
  if [[ -z "${pids}" ]]; then
    return 0
  fi
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    kill_pid_gracefully "${pid}" 5
  done <<<"${pids}"
}

wait_for_http_ok() {
  local url="$1"
  local timeout_seconds="$2"
  local waited=0
  while [[ "${waited}" -lt "${timeout_seconds}" ]]; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

load_backend_env_files() {
  local env_file
  for env_file in "${PROJECT_ROOT}/backend/.env" "${PROJECT_ROOT}/backend/.env.local"; do
    if [[ -f "${env_file}" ]]; then
      while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
        local line="${raw_line%$'\r'}"
        [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
        [[ "${line}" == *"="* ]] || continue
        local key="${line%%=*}"
        local value="${line#*=}"
        key="${key//[[:space:]]/}"
        export "${key}=${value}"
      done <"${env_file}"
    fi
  done
}
