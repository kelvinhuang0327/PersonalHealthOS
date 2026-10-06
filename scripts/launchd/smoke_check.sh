#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs
require_cmd curl
require_cmd python3

ORCH_SUMMARY_URL="http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1/orchestrator/summary"
TMP_JSON="${LAUNCHD_RUNTIME_DIR}/smoke_orchestrator_summary.json"

log "Smoke check: orchestrator summary ${ORCH_SUMMARY_URL}"
HTTP_CODE="$(curl -sS -o "${TMP_JSON}" -w '%{http_code}' "${ORCH_SUMMARY_URL}")"

if [[ "${HTTP_CODE}" == "401" ]]; then
    log "Smoke check: orchestrator summary is auth-protected and reachable (401)"
    exit 0
fi

[[ "${HTTP_CODE}" == "200" ]] || fail "orchestrator summary request failed with status ${HTTP_CODE}"

python3 - <<'PY' "${TMP_JSON}"
import json
import sys

path = sys.argv[1]
with open(path, encoding='utf-8') as fp:
    payload = json.load(fp)

required = ['project_name', 'project_slug', 'scheduler', 'task_counts']
missing = [k for k in required if k not in payload]
if missing:
    print(f'Missing keys in orchestrator summary: {missing}')
    sys.exit(1)
PY

log "Smoke checks passed"
