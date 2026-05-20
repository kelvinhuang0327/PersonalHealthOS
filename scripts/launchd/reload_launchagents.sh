#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--with-daemon" ]]; then
  exec "${SCRIPT_DIR}/install_launchagents.sh" --with-daemon
fi

exec "${SCRIPT_DIR}/install_launchagents.sh"
