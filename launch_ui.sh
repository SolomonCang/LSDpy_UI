#!/usr/bin/env zsh
# LSD UI Launcher — macOS shell entry point
# Usage: ./launch_ui.sh [port]
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PORT="${1:-8080}"

# Prefer project venv if present
VENV="$SCRIPT_DIR/.venv/bin/python3"
if [[ -x "$VENV" ]]; then
  PYTHON="$VENV"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
else
  echo "error: python3 not found" >&2
  exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/launch_ui.py" "$@"
