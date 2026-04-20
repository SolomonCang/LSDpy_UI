/**
 * data.js — Spectrum & mask file management for the Data page.
 *
 * Layout: Mask selector → Available data files table → Observation entries table.
 * Follows ZDIpy_WebUI table-based pattern adapted for LSD_UI light theme.
 */

var SPECTRA_KEY = "lsd_ui_spectra_v1";
var _obsRowCounter = 0;

// ── Spectra list persistence ─────────────────────────────────────────────────
function _loadSpectra() {
  try { return JSON.parse(localStorage.getItem(SPECTRA_KEY)) || []; } catch (_) { return []; }
}
function _saveSpectra(list) { localStorage.setItem(SPECTRA_KEY, JSON.stringify(list)); }

// ── Utility: HTML-safe text ──────────────────────────────────────────────────
function _escHtml(s) {
  var d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ── Mask file table ──────────────────────────────────────────────────────────
async function _refreshMaskFiles() {
  var tbody = document.getElementById("mask-file-tbody");
  var noMsg = document.getElementById("mask-no-files");
  if (!tbody) return;
  try {
    var files = await apiFetch("/api/files/masks");
    tbody.innerHTML = "";
    if (!files.length) {
      noMsg && (noMsg.style.display = "");
      return;
    }
    noMsg && (noMsg.style.display = "none");
    files.forEach(function (f) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><code>' + _escHtml(f) + '</code></td>' +
        '<td><button class="btn btn-secondary btn-sm mask-select-btn" data-name="' + _escHtml(f) + '">Select</button></td>';
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Failed to load mask files", e);
  }
}

// Delegated: mask select button
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".mask-select-btn");
  if (!btn) return;
  document.getElementById("input-mask").value = "masks/" + btn.dataset.name;
  setStatusBar("data-status", "Mask set: " + btn.dataset.name, "ok");
});

// ── Data file table ──────────────────────────────────────────────────────────
var _dataFileNames = [];

async function _refreshDataFiles() {
  var tbody = document.getElementById("data-file-tbody");
  var noMsg = document.getElementById("data-no-files");
  if (!tbody) return;
  try {
    var files = await apiFetch("/api/files/data");
    _dataFileNames = files;
    tbody.innerHTML = "";
    if (!files.length) {
      noMsg && (noMsg.style.display = "");
      return;
    }
    noMsg && (noMsg.style.display = "none");
    files.forEach(function (f) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><code>' + _escHtml(f) + '</code></td>' +
        '<td><button class="btn btn-secondary btn-sm data-link-btn" data-name="' + _escHtml(f) + '" title="Add to observation entries">＋ Link</button></td>';
      tbody.appendChild(tr);
    });
    _populateDatalist();
  } catch (e) {
    console.error("Failed to load data files", e);
  }
}

function _populateDatalist() {
  var dl = document.getElementById("obs-file-datalist");
  if (!dl) return;
  dl.innerHTML = "";
  _dataFileNames.forEach(function (n) {
    var opt = document.createElement("option");
    opt.value = "data/" + n;
    dl.appendChild(opt);
  });
}

// Delegated: data file link button → add observation entry
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".data-link-btn");
  if (!btn) return;
  var name = btn.dataset.name;
  var tbody = document.getElementById("obs-entries-tbody");
  if (!tbody) return;
  tbody.appendChild(_buildObsRow("data/" + name));
  _renumberRows();
  document.querySelector(".obs-table-wrap") &&
    document.querySelector(".obs-table-wrap").scrollIntoView({ behavior: "smooth", block: "nearest" });
  setStatusBar("data-status", 'Added "' + name + '" to observation entries.', "ok");
});

// ── Observation entries table ────────────────────────────────────────────────
function _buildObsRow(filename) {
  var idx = ++_obsRowCounter;
  var tr = document.createElement("tr");
  tr.dataset.rowId = idx;
  var fn = filename ? _escHtml(String(filename)) : "";
  tr.innerHTML =
    '<td class="obs-row-num"></td>' +
    '<td><input type="text" class="field-input obs-fn" value="' + fn + '" ' +
    'list="obs-file-datalist" placeholder="data/spectrum.s" spellcheck="false" autocomplete="off" /></td>' +
    '<td class="obs-file-status obs-file-unknown" title="Not validated">—</td>' +
    '<td><button class="btn btn-danger btn-sm obs-del-row" title="Remove">✕</button></td>';
  // Clear status on filename change
  tr.querySelector(".obs-fn").addEventListener("change", function () {
    var cell = tr.querySelector(".obs-file-status");
    if (cell) { cell.className = "obs-file-status obs-file-unknown"; cell.textContent = "—"; cell.title = "Not validated"; }
  });
  return tr;
}

function _renumberRows() {
  var rows = document.querySelectorAll("#obs-entries-tbody tr");
  rows.forEach(function (tr, i) {
    var num = tr.querySelector(".obs-row-num");
    if (num) num.textContent = i + 1;
  });
  var noMsg = document.getElementById("obs-no-entries");
  if (noMsg) noMsg.style.display = rows.length ? "none" : "";
}

// Delegated: delete row button
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".obs-del-row");
  if (!btn) return;
  btn.closest("tr").remove();
  _renumberRows();
});

// ── Populate entries from localStorage / config ──────────────────────────────
function _loadEntriesToTable() {
  var tbody = document.getElementById("obs-entries-tbody");
  if (!tbody) return;
  var cfg = window.LSDUI.loadConfig();
  // Always prefer server config's input fields as source-of-truth;
  // filter out empty strings from any previously persisted stale state.
  var spectra = _loadSpectra().filter(function(s) { return s && s.trim(); });
  // Fall back to config.input.spectra if localStorage empty
  if (!spectra.length && cfg.input && cfg.input.spectra && cfg.input.spectra.length) {
    spectra = cfg.input.spectra.filter(function(s) { return s && s.trim(); });
    _saveSpectra(spectra);
  }
  // Fall back to config.input.observation for single-spectrum mode
  if (!spectra.length && cfg.input && cfg.input.observation) {
    spectra = [cfg.input.observation];
    _saveSpectra(spectra);
  }
  tbody.innerHTML = "";
  _obsRowCounter = 0;
  spectra.forEach(function (s) {
    tbody.appendChild(_buildObsRow(s.trim()));
  });
  _renumberRows();
}

// ── Collect entries from table ───────────────────────────────────────────────
function _collectEntries() {
  var rows = document.querySelectorAll("#obs-entries-tbody tr");
  var paths = [];
  rows.forEach(function (tr) {
    var fn = tr.querySelector(".obs-fn");
    if (fn) {
      var v = fn.value.trim();
      if (v) paths.push(v);
    }
  });
  return paths;
}

// ── DOMContentLoaded ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async function () {
  var statusEl = document.getElementById("data-status");

  function fillMask() {
    var cfg = window.LSDUI.loadConfig();
    document.getElementById("input-mask").value = cfg.input.mask || "";
  }

  async function reload() {
    setStatusBar(statusEl, "Loading…");
    try {
      await window.LSDUI.fetchServerConfig();
    } catch (_) {}
    fillMask();
    _loadEntriesToTable();
    await Promise.all([_refreshDataFiles(), _refreshMaskFiles()]);
    setStatusBar(statusEl, "");
  }

  // ── Init ────────────────────────────────────────────────────────────────
  await reload();

  // ── Add Row ─────────────────────────────────────────────────────────────
  document.getElementById("btn-obs-add").addEventListener("click", function () {
    var tbody = document.getElementById("obs-entries-tbody");
    tbody.appendChild(_buildObsRow(""));
    _renumberRows();
    // Focus the new input
    var inputs = tbody.querySelectorAll(".obs-fn");
    if (inputs.length) inputs[inputs.length - 1].focus();
  });

  // ── Clear All ───────────────────────────────────────────────────────────
  document.getElementById("btn-obs-clear").addEventListener("click", function () {
    document.getElementById("obs-entries-tbody").innerHTML = "";
    _obsRowCounter = 0;
    _renumberRows();
    _saveSpectra([]);
    setStatusBar(statusEl, "Entries cleared.", "ok");
  });

  // ── Reload ──────────────────────────────────────────────────────────────
  document.getElementById("btn-data-load").addEventListener("click", async function () {
    await reload();
    setStatusBar(statusEl, "Reloaded.", "ok");
    setTimeout(function () { setStatusBar(statusEl, ""); }, 2000);
  });

  // ── Validate ────────────────────────────────────────────────────────────
  document.getElementById("btn-validate").addEventListener("click", async function () {
    var mask = document.getElementById("input-mask").value.trim();
    var entries = _collectEntries();
    var allPaths = [];
    if (mask) allPaths.push(mask);
    entries.forEach(function (p) { if (allPaths.indexOf(p) === -1) allPaths.push(p); });

    if (!mask) { setStatusBar(statusEl, "Please set a mask path.", "warn"); return; }
    if (!entries.length) { setStatusBar(statusEl, "Add at least one observation entry.", "warn"); return; }

    setStatusBar(statusEl, "Validating " + allPaths.length + " paths…");
    try {
      var result = await apiFetch("/api/files/validate", { method: "POST", body: allPaths });
      var missing = 0;

      // Update table row status icons
      var rows = document.querySelectorAll("#obs-entries-tbody tr");
      rows.forEach(function (tr) {
        var fn = (tr.querySelector(".obs-fn") || {}).value || "";
        fn = fn.trim();
        var cell = tr.querySelector(".obs-file-status");
        if (!cell || !fn) return;
        if (result[fn]) {
          cell.className = "obs-file-status obs-file-ok";
          cell.textContent = "✓";
          cell.title = "File found";
        } else {
          cell.className = "obs-file-status obs-file-missing";
          cell.textContent = "✗";
          cell.title = "File not found";
          missing++;
        }
      });

      // Check mask
      if (!result[mask]) {
        setStatusBar(statusEl, "Mask file not found: " + mask, "error");
        return;
      }

      if (missing) {
        setStatusBar(statusEl, missing + " observation file(s) not found.", "warn");
      } else {
        setStatusBar(statusEl, "All " + allPaths.length + " files found.", "ok");
      }
    } catch (e) {
      setStatusBar(statusEl, "Validation error: " + e.message, "error");
    }
  });

  // ── Save ────────────────────────────────────────────────────────────────
  document.getElementById("btn-data-save").addEventListener("click", async function () {
    var cfg = window.LSDUI.loadConfig();
    var mask = document.getElementById("input-mask").value.trim();
    var entries = _collectEntries();

    cfg.input.mask = mask;
    cfg.input.spectra = entries;
    // Set single observation to first entry for backward compat
    cfg.input.observation = entries.length ? entries[0] : "";
    _saveSpectra(entries);

    setStatusBar(statusEl, "Saving…");
    try {
      await window.LSDUI.saveServerConfig(cfg);
      setStatusBar(statusEl, "Saved to LSDConfig.json", "ok");
      setTimeout(function () { setStatusBar(statusEl, ""); }, 3000);
    } catch (e) {
      setStatusBar(statusEl, "Save failed: " + e.message, "error");
    }
  });
});
