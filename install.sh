#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${FORGANIZE_INSTALL_DIR:-$HOME/.local/bin}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found in PATH." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"
install -m 755 "$SCRIPT_DIR/organizer.py" "$INSTALL_DIR/forganize"

echo "Installed forganize to $INSTALL_DIR/forganize"

case ":$PATH:" in
    *":$INSTALL_DIR:"*)
        echo "Run 'forganize -h' to get started."
        ;;
    *)
        echo
        echo "Note: $INSTALL_DIR is not on your PATH yet."
        echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, ...), then restart your shell:"
        echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
        ;;
esac
