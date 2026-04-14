#!/usr/bin/env python3
"""LSD UI Launcher — thin entry point that delegates to app.py (FastAPI/uvicorn).

Usage:
    python launch_ui.py [--port PORT]   # named flag
    python launch_ui.py [PORT]          # positional (from launch_ui.sh)
    ./launch_ui.sh [PORT]
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so app.py package imports resolve.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _normalize_argv() -> None:
    """Convert a bare positional port number to the --port flag expected by app.py.

    launch_ui.sh calls `python launch_ui.py "$@"` which forwards the raw
    positional argument, e.g. `launch_ui.py 8080`.  app.py uses argparse
    with a --port option, so translate here.
    """
    extra = sys.argv[1:]
    if extra and not extra[0].startswith("-") and extra[0].isdigit():
        sys.argv = [sys.argv[0], "--port", extra[0]] + extra[1:]


if __name__ == "__main__":
    _normalize_argv()
    import runpy
    runpy.run_path(str(BASE_DIR / "app.py"), run_name="__main__")
