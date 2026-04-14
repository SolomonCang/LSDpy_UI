/**
 * task.js — LSD task runner for the Task tab.
 */

let _mockTimer    = null;
let _apiPollTimer = null;
let _taskId       = null;

function _log(msg) {
  const box = document.getElementById("task-log");
  const p = document.createElement("p");
  p.textContent = "[" + window.LSDUI.fmtNow() + "] " + msg;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function _validateConfig(cfg) {
  const issues = [];
  if (!cfg.input.observation) issues.push("input.observation missing");
  if (!cfg.input.mask) issues.push("input.mask missing");
  if (cfg.profile.vel_end_kms <= cfg.profile.vel_start_kms) issues.push("invalid velocity range");
  return issues;
}

function _buildMockProfile(cfg) {
  const points = [];
  const start = cfg.profile.vel_start_kms;
  const end = cfg.profile.vel_end_kms;
  const step = cfg.profile.pixel_velocity_kms;
  for (let v = start; v <= end; v += step) {
    const x = v / Math.max(Math.abs(start), Math.abs(end));
    const y = 1 - 0.08 * Math.exp(-(x * x) / 0.06);
    points.push({ v, y: Number(y.toFixed(6)) });
  }
  return points;
}

function _saveLastResult(cfg) {
  const payload = {
    run_at: new Date().toISOString(),
    mode: document.getElementById("run-mode").value,
    output_profile: cfg.output.profile,
    profile: _buildMockProfile(cfg)
  };
  localStorage.setItem(window.LSDUI.RESULT_KEY, JSON.stringify(payload));
}

function _stopAllTimers() {
  if (_mockTimer    !== null) { clearInterval(_mockTimer);    _mockTimer    = null; }
  if (_apiPollTimer !== null) { clearInterval(_apiPollTimer); _apiPollTimer = null; }
}

function _startMock(cfg) {
  _stopAllTimers();
  const steps = [
    "Reading observation file…",
    "Loading mask and building LSD matrix…",
    "Running LSD solver…",
    "Saving profile and report…",
    "Task completed."
  ];
  let idx = 0;
  setStatusBar("task-status", "Running", "warn");
  _log("Mock task started.");

  _mockTimer = setInterval(function() {
    _log(steps[idx]);
    idx += 1;
    if (idx >= steps.length) {
      _stopAllTimers();
      _saveLastResult(cfg);
      setStatusBar("task-status", "Completed", "ok");
      _log("Mock result stored — switch to Results tab to view.");
    }
  }, 850);
}

function _apiBase() {
  return document.getElementById("api-base-url").value.trim().replace(/\/$/, "");
}

async function _startApi(cfg) {
  _stopAllTimers();
  setStatusBar("task-status", "Submitting…", "warn");
  _log("Submitting to " + _apiBase() + "/api/tasks");
  try {
    const body = await apiFetch(_apiBase() + "/api/tasks", { method: "POST", body: { config: cfg } });
    _taskId = body.task_id;
    if (!_taskId) throw new Error("task_id missing in response");
    setStatusBar("task-status", "Running", "warn");
    _log("Task created: " + _taskId);
    _pollApi();
  } catch (err) {
    setStatusBar("task-status", "API error", "error");
    _log("Start failed: " + err.message);
  }
}

function _pollApi() {
  _apiPollTimer = setInterval(async function() {
    try {
      const body = await apiFetch(_apiBase() + "/api/tasks/" + _taskId);
      // Append new log lines from server
      if (Array.isArray(body.log) && body.log.length) {
        const box = document.getElementById("task-log");
        const existing = box.querySelectorAll("p").length;
        body.log.slice(existing).forEach(function(line) {
          const p = document.createElement("p");
          p.textContent = line;
          box.appendChild(p);
        });
        box.scrollTop = box.scrollHeight;
      }
      if (body.status === "done" || body.status === "completed") {
        _stopAllTimers();
        setStatusBar("task-status", "Completed", "ok");
        _log("Finished. Switch to Results tab to view.");
      } else if (body.status === "error") {
        _stopAllTimers();
        setStatusBar("task-status", "Failed", "error");
        _log("Task failed: " + (body.message || ""));
      }
    } catch (err) {
      _stopAllTimers();
      setStatusBar("task-status", "API error", "error");
      _log("Polling error: " + err.message);
    }
  }, 1200);
}

async function _stopApi() {
  if (!_taskId) { _log("No API task to cancel."); return; }
  try {
    await apiFetch(_apiBase() + "/api/tasks/" + _taskId + "/cancel", { method: "POST" });
    _log("Canceled task: " + _taskId);
  } catch (_err) {
    _log("Cancel request failed.");
  }
  _stopAllTimers();
  setStatusBar("task-status", "Stopped", "warn");
}

document.addEventListener("DOMContentLoaded", async function() {
  setStatusBar("task-status", "Idle");
  try {
    await window.LSDUI.fetchServerConfig();
    _log("Config loaded from server. Ready.");
  } catch (e) {
    _log("Server unavailable — using local config.");
  }

  document.getElementById("btn-log-clear").addEventListener("click", function() {
    document.getElementById("task-log").innerHTML = "";
  });

  document.getElementById("btn-run-validate").addEventListener("click", async function() {
    const cfg = await window.LSDUI.fetchServerConfig();
    const issues = _validateConfig(cfg);
    if (issues.length) {
      setStatusBar("task-status", "Invalid config", "error");
      _log("Invalid: " + issues.join("; "));
      return;
    }
    setStatusBar("task-status", "Config OK", "ok");
    _log("Configuration is valid.");
  });

  document.getElementById("btn-run-start").addEventListener("click", async function() {
    const cfg = await window.LSDUI.fetchServerConfig();
    const issues = _validateConfig(cfg);
    if (issues.length) {
      setStatusBar("task-status", "Invalid config", "error");
      _log("Cannot start: " + issues.join("; "));
      return;
    }
    if (document.getElementById("run-mode").value === "api") {
      _startApi(cfg);
    } else {
      _startMock(cfg);
    }
  });

  document.getElementById("btn-run-stop").addEventListener("click", function() {
    if (document.getElementById("run-mode").value === "api") {
      _stopApi();
    } else {
      _stopAllTimers();
      setStatusBar("task-status", "Stopped", "warn");
      _log("Mock task stopped.");
    }
  });
});
