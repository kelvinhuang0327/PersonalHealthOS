#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs
require_cmd curl

BACKEND_TIMEOUT_SECONDS="${BACKEND_TIMEOUT_SECONDS:-90}"
FRONTEND_TIMEOUT_SECONDS="${FRONTEND_TIMEOUT_SECONDS:-120}"

BACKEND_HEALTH_URL="http://${BACKEND_HOST}:${BACKEND_PORT}/health"
FRONTEND_HEALTH_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}/"

log "Health check: backend ${BACKEND_HEALTH_URL}"
wait_for_http_ok "${BACKEND_HEALTH_URL}" "${BACKEND_TIMEOUT_SECONDS}" || fail "backend health check failed"

log "Health check: frontend ${FRONTEND_HEALTH_URL}"
wait_for_http_ok "${FRONTEND_HEALTH_URL}" "${FRONTEND_TIMEOUT_SECONDS}" || fail "frontend health check failed"

if [[ "${STRICT_READY_CHECK:-false}" == "true" ]]; then
  READY_URL="http://${BACKEND_HOST}:${BACKEND_PORT}/health/ready"
  log "Health check: strict ready ${READY_URL}"
  wait_for_http_ok "${READY_URL}" "${BACKEND_TIMEOUT_SECONDS}" || fail "backend ready check failed"
fi

log "Health checks passed"
