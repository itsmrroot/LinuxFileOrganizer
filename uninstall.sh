#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${FORGANIZE_INSTALL_DIR:-$HOME/.local/bin}"
TARGET="$INSTALL_DIR/forganize"

if [ -f "$TARGET" ]; then
    rm -f "$TARGET"
    echo "Removed $TARGET"
else
    echo "$TARGET not found — nothing to uninstall."
fi
