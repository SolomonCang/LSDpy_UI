/**
 * data.js — Spectrum & mask file management for the Data tab.
 */

document.addEventListener("DOMContentLoaded", async function() {
  const statusEl = document.getElementById("data-status");

  function fill() {
    const cfg = window.LSDUI.loadConfig();
    document.getElementById("input-observation").value = cfg.input.observation || "";
    document.getElementById("input-mask").value        = cfg.input.mask        || "";
  }

  async function loadFiles() {
    try {
      const dataFiles = await apiFetch("/api/files/data").catch(function() { return []; });
      const datalist  = document.getElementById("data-files-list");
      datalist.innerHTML = "";
      dataFiles.forEach(function(f) {
        const btn = document.createElement("button");
        btn.className = "file-chip";
        btn.textContent = f;
        btn.addEventListener("click", function() {
          document.getElementById("input-observation").value = "data/" + f;
        });
        datalist.appendChild(btn);
      });
      if (!dataFiles.length) datalist.innerHTML = "<span class=\"no-files\">No files in data/</span>";
    } catch (e) {
      console.error("Failed to load data files", e);
    }

    try {
      const maskFiles = await apiFetch("/api/files/masks").catch(function() { return []; });
      const masklist  = document.getElementById("mask-files-list");
      masklist.innerHTML = "";
      maskFiles.forEach(function(f) {
        const btn = document.createElement("button");
        btn.className = "file-chip";
        btn.textContent = f;
        btn.addEventListener("click", function() {
          document.getElementById("input-mask").value = "masks/" + f;
        });
        masklist.appendChild(btn);
      });
      if (!maskFiles.length) masklist.innerHTML = "<span class=\"no-files\">No files in masks/</span>";
    } catch (e) {
      console.error("Failed to load mask files", e);
    }
  }

  // ── Init ────────────────────────────────────────────────────────────────
  setStatusBar(statusEl, "Loading…");
  try {
    await window.LSDUI.fetchServerConfig();
    setStatusBar(statusEl, "");
  } catch (e) {
    setStatusBar(statusEl, "Server unavailable — showing local config.", "warn");
  }
  fill();
  loadFiles();

  // ── Buttons
  document.getElementById("btn-data-reload").addEventListener("click", async function() {
    setStatusBar(statusEl, "Loading…");
    try {
      await window.LSDUI.fetchServerConfig();
      fill();
      await loadFiles();
      setStatusBar(statusEl, "Reloaded.", "ok");
      setTimeout(function() { setStatusBar(statusEl, ""); }, 2000);
    } catch (e) {
      setStatusBar(statusEl, "Reload failed: " + e.message, "error");
    }
  });

  document.getElementById("btn-data-save").addEventListener("click", async function() {
    const cfg = window.LSDUI.loadConfig();
    cfg.input.observation = document.getElementById("input-observation").value.trim();
    cfg.input.mask        = document.getElementById("input-mask").value.trim();
    setStatusBar(statusEl, "Saving…");
    try {
      await window.LSDUI.saveServerConfig(cfg);
      setStatusBar(statusEl, "✔ Saved to LSDConfig.json", "ok");
      setTimeout(function() { setStatusBar(statusEl, ""); }, 3000);
    } catch (e) {
      setStatusBar(statusEl, "Save failed: " + e.message, "error");
    }
  });

  document.getElementById("btn-validate").addEventListener("click", async function() {
    const obs  = document.getElementById("input-observation").value.trim();
    const mask = document.getElementById("input-mask").value.trim();
    if (!obs || !mask) {
      setStatusBar(statusEl, "Please provide both paths.", "warn");
      return;
    }
    setStatusBar(statusEl, "Validating…");
    try {
      const results = await apiFetch("/api/files/validate", { method: "POST", body: [obs, mask] });
      const obsOk  = results[obs];
      const maskOk = results[mask];
      if (obsOk && maskOk) {
        setStatusBar(statusEl, "✔ Both files found.", "ok");
      } else {
        const missing = [];
        if (!obsOk)  missing.push(obs);
        if (!maskOk) missing.push(mask);
        setStatusBar(statusEl, "Missing: " + missing.join(", "), "error");
      }
    } catch (e) {
      setStatusBar(statusEl, "Validation failed: " + e.message, "error");
    }
  });
});
