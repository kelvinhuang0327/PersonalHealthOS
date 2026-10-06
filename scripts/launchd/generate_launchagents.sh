#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/launchd/common.sh
source "${SCRIPT_DIR}/common.sh"

ensure_dirs
require_cmd python3

RENDER_PATH="${LAUNCHD_PATH_OVERRIDE:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"

python3 - <<'PY' "${LAUNCHD_TEMPLATE_DIR}" "${LAUNCHD_PLIST_GEN_DIR}" "${PROJECT_ROOT}" "${RENDER_PATH}"
import pathlib
import sys

template_dir = pathlib.Path(sys.argv[1])
target_dir = pathlib.Path(sys.argv[2])
project_root = sys.argv[3]
path_value = sys.argv[4]

target_dir.mkdir(parents=True, exist_ok=True)
for template in sorted(template_dir.glob("*.plist.template")):
    content = template.read_text(encoding="utf-8")
    content = content.replace("__PROJECT_ROOT__", project_root)
    content = content.replace("__PATH__", path_value)
    output_name = template.name.replace(".template", "")
    (target_dir / output_name).write_text(content, encoding="utf-8")
PY

log "Generated plists in ${LAUNCHD_PLIST_GEN_DIR}"
