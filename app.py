#!/usr/bin/env python3
"""LSD UI — FastAPI server entry point.

Usage:
    python app.py [--port 8080]
"""

import json
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api import routes_analysis

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "LSDConfig.json"
FRONTEND_DIR = BASE_DIR / "frontend"
DEFAULT_PORT = 8080

app = FastAPI(title="LSD UI API", version="1.0.0", docs_url="/api/docs")

# ── Analysis routes ──────────────────────────────────────────────────────────
routes_analysis.init(BASE_DIR)
app.include_router(routes_analysis.router)

# ── Task state machine ──────────────────────────────────────────────────────
_tasks: dict = {}
_run_lock = threading.Lock()


# ── Config routes ────────────────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    if not CONFIG_FILE.exists():
        return JSONResponse({})
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return JSONResponse(json.loads(f.read()))


def _write_config(body: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)


@app.put("/api/config")
def put_config(body: dict = Body(...)):
    try:
        _write_config(body)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
def post_config(body: dict = Body(...)):
    try:
        _write_config(body)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── File listing routes ───────────────────────────────────────────────────────
@app.get("/api/files/data")
def list_data_files():
    d = BASE_DIR / "data"
    if not d.exists():
        return []
    return sorted(f.name for f in d.glob("*")
                  if f.is_file() and not f.name.startswith("."))


@app.get("/api/files/masks")
def list_mask_files():
    d = BASE_DIR / "masks"
    if not d.exists():
        return []
    return sorted(f.name for f in d.glob("*")
                  if f.is_file() and not f.name.startswith("."))


@app.get("/api/files/results")
def list_result_files():
    d = BASE_DIR / "results"
    if not d.exists():
        return []
    return sorted(
        str(f.relative_to(BASE_DIR)) for f in d.rglob("*.dat")
        if f.is_file() and not f.name.startswith(".")
    )


@app.post("/api/files/validate")
def validate_files(paths: list = Body(...)):
    return {p: (BASE_DIR / p).is_file() for p in paths}


# ── Task routes ───────────────────────────────────────────────────────────────
def _run_pipeline(task_id: str, cfg: dict):
    log = _tasks[task_id]["log"]

    def _log(msg: str):
        log.append(msg)

    try:
        _log("Initializing configuration...")
        from core.lsd_config import paramsLSD  # noqa: PLC0415
        from pipeline.lsd_pipeline import LSDPipeline  # noqa: PLC0415

        params = paramsLSD(config=cfg, base_dir=BASE_DIR)
        output_cfg = cfg.get("output", {})
        output_profile = str(BASE_DIR /
                             output_cfg.get("profile", "results/prof.dat"))

        _log(f"Running LSD pipeline → {output_profile}")
        pipeline = LSDPipeline(params, output_profile)
        pipeline.run()

        _tasks[task_id]["status"] = "done"
        _tasks[task_id]["message"] = "Completed successfully"
        _log("Pipeline completed.")
    except Exception as exc:
        _tasks[task_id]["status"] = "error"
        _tasks[task_id]["message"] = str(exc)
        _log(f"Error: {exc}")
    finally:
        try:
            _run_lock.release()
        except RuntimeError:
            pass


@app.post("/api/tasks")
def create_task(body: dict = Body(...)):
    cfg = body.get("config", {})
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(status_code=409,
                            detail="A task is already running")
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "running", "message": "", "log": []}
    thread = threading.Thread(target=_run_pipeline,
                              args=(task_id, cfg),
                              daemon=True)
    thread.start()
    return {"task_id": task_id}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = _tasks[task_id]
    return {"status": t["status"], "message": t["message"], "log": t["log"]}


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    if _tasks[task_id]["status"] == "running":
        _tasks[task_id]["status"] = "error"
        _tasks[task_id]["message"] = "Cancelled by user"
        _tasks[task_id]["log"].append("Task cancelled by user.")
        try:
            _run_lock.release()
        except RuntimeError:
            pass
    return {"status": "ok"}


# ── Static files (mount last so API routes take priority) ────────────────────
if FRONTEND_DIR.exists():
    app.mount("/",
              StaticFiles(directory=str(FRONTEND_DIR), html=True),
              name="frontend")


# ── Startup ───────────────────────────────────────────────────────────────────
def _find_free_port(start: int = DEFAULT_PORT) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in {start}–{start + 20}")


def _open_browser(url: str):
    time.sleep(0.5)
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
    else:
        import webbrowser
        webbrowser.open(url)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LSD UI Server")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    port = args.port if args.port else _find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"LSD UI  →  {url}")
    print("Press Ctrl+C to stop.\n")
    threading.Thread(target=_open_browser, args=(url, ), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
