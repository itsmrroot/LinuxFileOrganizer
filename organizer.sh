#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found in PATH." >&2
    exit 1
fi

python3 "$SCRIPT_DIR/organizer.py" "$@"
