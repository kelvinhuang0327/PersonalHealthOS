#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

WITH_DAEMON=false
if [[ "${1:-}" == "--with-daemon" ]]; then
  WITH_DAEMON=true
fi

ensure_dirs
require_cmd launchctl
require_cmd cp

"${SCRIPT_DIR}/generate_launchagents.sh"

TARGET_DIR="${HOME}/Library/LaunchAgents"
mkdir -p "${TARGET_DIR}"

PLISTS=(
  "com.personalhealthos.main.plist"
  "com.personalhealthos.planner.tick.plist"
  "com.personalhealthos.worker.tick.plist"
)
if [[ "${WITH_DAEMON}" == "true" ]]; then
  PLISTS+=("com.personalhealthos.worker.daemon.plist")
fi

for plist in "${PLISTS[@]}"; do
  cp "${LAUNCHD_PLIST_GEN_DIR}/${plist}" "${TARGET_DIR}/${plist}"
  launchctl unload -w "${TARGET_DIR}/${plist}" >/dev/null 2>&1 || true
  launchctl load -w "${TARGET_DIR}/${plist}"
done

log "Installed launch agents: ${PLISTS[*]}"
launchctl list | grep -E 'com\.personalhealthos\.' || true
