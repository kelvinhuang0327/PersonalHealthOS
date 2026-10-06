#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

WITH_DAEMON=false
if [[ "${1:-}" == "--with-daemon" ]]; then
  WITH_DAEMON=true
fi

require_cmd launchctl

TARGET_DIR="${HOME}/Library/LaunchAgents"
PLISTS=(
  "com.personalhealthos.main.plist"
  "com.personalhealthos.planner.tick.plist"
  "com.personalhealthos.worker.tick.plist"
)
if [[ "${WITH_DAEMON}" == "true" ]]; then
  PLISTS+=("com.personalhealthos.worker.daemon.plist")
fi

for plist in "${PLISTS[@]}"; do
  if [[ -f "${TARGET_DIR}/${plist}" ]]; then
    launchctl unload -w "${TARGET_DIR}/${plist}" >/dev/null 2>&1 || true
    rm -f "${TARGET_DIR:?}/${plist}"
  fi
done

log "Uninstalled launch agents: ${PLISTS[*]}"
launchctl list | grep -E 'com\.personalhealthos\.' || true
