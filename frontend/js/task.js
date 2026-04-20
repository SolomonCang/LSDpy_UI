/**
 * task.js — LSD task runner.
 * Always connects to the same server that served this page (window.location.origin).
 */

var SPECTRA_KEY = "lsd_ui_spectra_v1";
var BATCH_RESULT_KEY = "lsd_ui_batch_result_v1";

var _pollTimer = null;
var _taskId = null;

function _apiBase() {
  return window.location.origin;
}

function _loadSpectra() {
  try { return JSON.parse(localStorage.getItem(SPECTRA_KEY)) || []; } catch (_) { return []; }
}

function _log(msg) {
  var box = document.getElementById("task-log");
  var p = document.createElement("p");
  p.textContent = "[" + window.LSDUI.fmtNow() + "] " + msg;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function _validateConfig(cfg) {
  var issues = [];
  var spectra = _loadSpectra().filter(function (s) { return s.trim() !== ""; });
  if (!cfg.input.observation && spectra.length === 0) issues.push("No observation — add spectra in Spectrum & Mask page");
  if (!cfg.input.mask) issues.push("input.mask missing");
  if (cfg.profile.vel_end_kms <= cfg.profile.vel_start_kms) issues.push("invalid velocity range");
  return issues;
}

function _saveLastResult(cfg, profileData) {
  var payload = {
    run_at: new Date().toISOString(),
    output_profile: cfg.output && cfg.output.profile,
    profile: profileData
  };
  localStorage.setItem(window.LSDUI.RESULT_KEY, JSON.stringify(payload));
}

function _saveBatchResult(items) {
  localStorage.setItem(BATCH_RESULT_KEY, JSON.stringify({
    run_at: new Date().toISOString(),
    items: items
  }));
  if (items.length > 0) {
    localStorage.setItem(window.LSDUI.RESULT_KEY, JSON.stringify({
      run_at: new Date().toISOString(),
      output_profile: items[0].output_profile,
      profile: items[0].profile,
      batch_count: items.length
    }));
  }
}

async function _fetchAndSaveProfile(outputProfiles) {
  try {
    var cfg = window.LSDUI.loadConfig();
    if (outputProfiles && outputProfiles.length > 1) {
      _log("Loading " + outputProfiles.length + " batch profiles...");
      var items = [];
      for (var i = 0; i < outputProfiles.length; i++) {
        var p = outputProfiles[i];
        try {
          var profileData = await apiFetch(_apiBase() + "/api/profile/data?path=" + encodeURIComponent(p));
          var stem = p.replace(/^.*\//, "").replace(/\.[^.]+$/, "");
          items.push({ name: stem, output_profile: p, profile: profileData });
        } catch (err) {
          _log("Warning: could not load " + p + ": " + err.message);
        }
      }
      _saveBatchResult(items);
      _log(items.length + " profiles loaded — switch to Results tab to view.");
    } else {
      var profPath = (outputProfiles && outputProfiles[0]) || (cfg.output && cfg.output.profile) || "results/prof.dat";
      var singleData = await apiFetch(_apiBase() + "/api/profile/data?path=" + encodeURIComponent(profPath));
      _saveLastResult(cfg, singleData);
      _log("Profile loaded — switch to Results tab to view.");
    }
  } catch (err) {
    _log("Could not load profile data: " + err.message);
  }
}

async function _startTask(cfg) {
  if (_pollTimer !== null) { _log("A task is already running."); return; }
  var spectra = _loadSpectra().filter(function (s) { return s.trim() !== ""; });
  var batch = spectra.length > 1;

  setStatusBar("task-status", "Submitting...", "warn");
  _log("Submitting " + (batch ? "batch of " + spectra.length + " spectra" : "single task") + "...");
  try {
    var reqBody = { config: cfg };
    if (spectra.length > 0) reqBody.spectra = spectra;
    var body = await apiFetch(_apiBase() + "/api/tasks", { method: "POST", body: reqBody });
    _taskId = body.task_id;
    if (!_taskId) throw new Error("task_id missing in response");
    setStatusBar("task-status", batch ? "Running (batch)" : "Running", "warn");
    _log("Task started: " + _taskId);
    _pollTask();
  } catch (err) {
    setStatusBar("task-status", "Error", "error");
    _log("Start failed: " + err.message);
  }
}

function _pollTask() {
  _pollTimer = setInterval(async function () {
    try {
      var body = await apiFetch(_apiBase() + "/api/tasks/" + _taskId);
      if (Array.isArray(body.log) && body.log.length) {
        var box = document.getElementById("task-log");
        var existing = box.querySelectorAll("p").length;
        body.log.slice(existing).forEach(function (line) {
          var p = document.createElement("p");
          p.textContent = line;
          box.appendChild(p);
        });
        box.scrollTop = box.scrollHeight;
      }
      if (body.status === "done" || body.status === "completed") {
        clearInterval(_pollTimer); _pollTimer = null;
        setStatusBar("task-status", "Completed", "ok");
        _log("Finished. Loading profile data...");
        _fetchAndSaveProfile(body.output_profiles || []);
      } else if (body.status === "error") {
        clearInterval(_pollTimer); _pollTimer = null;
        setStatusBar("task-status", "Failed", "error");
        _log("Task failed: " + (body.message || ""));
      }
    } catch (err) {
      clearInterval(_pollTimer); _pollTimer = null;
      setStatusBar("task-status", "API error", "error");
      _log("Polling error: " + err.message);
    }
  }, 1200);
}

async function _stopTask() {
  if (_pollTimer !== null) { clearInterval(_pollTimer); _pollTimer = null; }
  if (!_taskId) { _log("No running task."); return; }
  try {
    await apiFetch(_apiBase() + "/api/tasks/" + _taskId + "/cancel", { method: "POST" });
    _log("Cancelled task: " + _taskId);
  } catch (_err) {
    _log("Cancel request failed.");
  }
  setStatusBar("task-status", "Stopped", "warn");
  _taskId = null;
}

document.addEventListener("DOMContentLoaded", async function () {
  setStatusBar("task-status", "Idle");

  function _updateBatchInfo() {
    var el = document.getElementById("batch-info");
    if (!el) return;
    var spectra = _loadSpectra().filter(function (s) { return s.trim() !== ""; });
    el.textContent = spectra.length > 1
      ? "Batch mode: " + spectra.length + " spectra queued"
      : "Single observation mode";
  }

  try {
    await window.LSDUI.fetchServerConfig();
    _log("Config loaded. Ready.");
  } catch (_) {
    _log("Server unavailable.");
  }
  _updateBatchInfo();

  document.getElementById("btn-log-clear").addEventListener("click", function () {
    document.getElementById("task-log").innerHTML = "";
  });

  document.getElementById("btn-run-validate").addEventListener("click", async function () {
    var cfg = await window.LSDUI.fetchServerConfig();
    var issues = _validateConfig(cfg);
    if (issues.length) {
      setStatusBar("task-status", "Invalid config", "error");
      _log("Invalid: " + issues.join("; "));
    } else {
      setStatusBar("task-status", "Config OK", "ok");
      _log("Configuration is valid.");
      _updateBatchInfo();
    }
  });

  document.getElementById("btn-run-start").addEventListener("click", async function () {
    var cfg = await window.LSDUI.fetchServerConfig();
    var issues = _validateConfig(cfg);
    if (issues.length) {
      setStatusBar("task-status", "Invalid config", "error");
      _log("Cannot start: " + issues.join("; "));
      return;
    }
    _startTask(cfg);
  });

  document.getElementById("btn-run-stop").addEventListener("click", function () {
    _stopTask();
  });
});
