#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "Error: Python 3.10+ is required. Install Python manually, then rerun." >&2
    exit 1
fi
exec python3 "$SCRIPT_DIR/scripts/install_kit.py" "$@"
