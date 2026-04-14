/**
 * params.js — Schema-driven parameter configuration panel for LSD UI.
 *
 * PARAMS_SCHEMA is the single source of truth for all LSD config fields.
 * Adding/removing a parameter only requires updating this array.
 */

// ── Schema definition ─────────────────────────────────────────────────────────
const PARAMS_SCHEMA = [
  {
    section: "profile", jsonKey: "profile",
    label: "LSD Profile Window", icon: "📈", open: true,
    fields: [
      { key: "vel_start_kms",      label: "Velocity start (km/s)",  type: "number", step: 1,   tooltip: "Starting velocity of the LSD profile window (km/s). Typically a negative value, e.g. −200." },
      { key: "vel_end_kms",        label: "Velocity end (km/s)",    type: "number", step: 1,   tooltip: "Ending velocity of the LSD profile window (km/s). Typically a positive value, e.g. +200." },
      { key: "pixel_velocity_kms", label: "Pixel velocity (km/s)",  type: "number", min: 0.01, step: 0.1, tooltip: "Velocity spacing per pixel in the output LSD profile (km/s). Should be comparable to the spectral resolution element of the spectrograph." }
    ]
  },
  {
    section: "normalization", jsonKey: "normalization",
    label: "Normalization & Weighting", icon: "⚖️", open: true,
    fields: [
      { key: "weighting_mode", label: "Weighting mode", type: "select",
        options: [
          { value: "0", label: "0 — g  (Landé only)" },
          { value: "1", label: "1 — prof × g  (depth, Landé)" },
          { value: "2", label: "2 — λ × prof × g  (depth, Landé, λ)" },
          { value: "3", label: "3 — prof  (depth only)" },
          { value: "4", label: "4 — λ × prof  (depth, λ)" },
          { value: "5", label: "5 — equal  (no weighting)" },
          { value: "6", label: "6 — prof × (λ × g)²  (depth, Landé, λ)" },
          { value: "7", label: "7 — fixed threshold  (binary weight)" }
        ],
        tooltip: "LSD line weighting formula. Modes 0–6 use analytic weights; mode 7 assigns a binary high/low weight based on a normalised depth threshold. See docs/weighting_modes.md." },
      { key: "depth",          label: "Normalisation depth",       type: "number", min: 0, step: 0.01, tooltip: "Reference line depth used as the normalisation constant in the LSD weighting formula. Typically set to a representative strong line depth (0–1)." },
      { key: "lande",          label: "Normalisation Landé g",     type: "number", min: 0, step: 0.01, tooltip: "Reference Landé effective g-factor for normalisation. Typically ≈ 1.2 for a solar-type star." },
      { key: "wavelength_nm",  label: "Normalisation wavelength (nm)", type: "number", min: 0, step: 1, tooltip: "Reference wavelength (nm) for normalisation. Typically the central wavelength of the observed spectral range, e.g. 500 nm." },
      { key: "weighting_threshold",  label: "Fixed threshold (normalised depth)", type: "number", min: 0, max: 1, step: 0.01,
        visibleWhen: { key: "weighting_mode", value: "7" },
        tooltip: "Normalised line depth threshold for mode 7. Lines with depth above this value receive the high weight; lines below receive the low weight. Range 0–1." },
      { key: "weighting_low_value",  label: "Weight below threshold", type: "number", min: 0, step: 0.01,
        visibleWhen: { key: "weighting_mode", value: "7" },
        tooltip: "LSD weight assigned to lines whose normalised depth is below the threshold (mode 7). Typically a small positive value, e.g. 0.1." },
      { key: "weighting_high_value", label: "Weight above threshold", type: "number", min: 0, step: 0.1,
        visibleWhen: { key: "weighting_mode", value: "7" },
        tooltip: "LSD weight assigned to lines whose normalised depth is above the threshold (mode 7). Should be much larger than the low weight, e.g. 10." }
    ]
  },
  {
    section: "processing", jsonKey: "processing",
    label: "Processing Options", icon: "⚙️", open: false,
    fields: [
      { key: "interp_mode", label: "Interpolation mode", type: "select",
        options: [
          { value: "0", label: "0 — Nearest neighbour" },
          { value: "1", label: "1 — Linear" }
        ],
        tooltip: "Interpolation scheme used when resampling the observed spectrum onto the LSD velocity grid. Linear (mode 1) is recommended." },
      { key: "remove_continuum_polarization", label: "Remove continuum polarization", type: "checkbox",
        tooltip: "Subtract the mean continuum polarization level from Stokes V/N before LSD fitting. Recommended when the target or instrument shows a polarized continuum." },
      { key: "sigma_clip.limit",      label: "σ-clip limit (σ)",     type: "number", min: 0, step: 0.1,
        tooltip: "Sigma-clipping rejection threshold. Spectral pixels deviating more than this many σ from the LSD model are masked iteratively. Set to a large value (e.g. 500) to disable." },
      { key: "sigma_clip.iterations", label: "σ-clip iterations",    type: "number", min: 0, step: 1,
        tooltip: "Maximum number of sigma-clipping iterations. Set to 0 to run a single pass without iteration." }
    ]
  },
  {
    section: "model_options", jsonKey: "model_options",
    label: "Model Options", icon: "🔧", open: false,
    fields: [
      { key: "saturation_correction", label: "Saturation correction",   type: "checkbox",
        tooltip: "Apply a line-saturation correction that reduces the effective weight of strong, potentially saturated spectral lines." },
      { key: "telluric_filtering",    label: "Telluric line filtering", type: "checkbox",
        tooltip: "Flag and exclude known telluric absorption features (atmospheric O₂, H₂O bands) from the LSD mask before fitting." },
      { key: "line_filtering",        label: "Line overlap filtering",  type: "checkbox",
        tooltip: "Remove spectral lines whose model profiles overlap substantially with their neighbours, preventing blending artefacts in the LSD profile." }
    ]
  },
  {
    section: "output", jsonKey: "output",
    label: "Output Files", icon: "📁", open: false,
    fields: [
      { key: "profile",      label: "Output profile path",               type: "text",     tooltip: "File path for the output LSD profile (relative to project root). e.g. results/prof.dat" },
      { key: "save_lsdout",  label: "Save run summary (.lsdout)",        type: "checkbox", tooltip: "Write a machine-readable run summary file containing detection statistics, pipeline parameters, and per-Stokes reduced χ²." },
      { key: "lsdout",       label: "Run summary path  (\"auto\" = auto)", type: "text",  tooltip: "Path for the .lsdout run summary file. Use \"auto\" to automatically generate a timestamped filename in results/." },
      { key: "save_model_spectrum", label: "Save model spectrum",         type: "checkbox", tooltip: "Write the best-fit reconstructed model spectrum (sum of LSD profile convolved with the mask) to a file." },
      { key: "model_spectrum", label: "Model spectrum path",              type: "text",
        visibleWhen: { key: "save_model_spectrum", checked: true },
        tooltip: "File path for the output model spectrum. Only used when 'Save model spectrum' is enabled." },
      { key: "plot_profile", label: "Show profile plot (requires display)", type: "checkbox", tooltip: "Display an interactive matplotlib profile plot after the run completes. Not suitable for headless/no-display environments." },
      { key: "save_plot",    label: "Save profile plot to image",         type: "checkbox", tooltip: "Save the LSD profile plot to an image file after the run." },
      { key: "plot_image",   label: "Profile plot image path",            type: "text",
        visibleWhen: { key: "save_plot", checked: true },
        tooltip: "Output file path for the saved profile plot image (PNG). Only used when 'Save profile plot' is enabled." }
    ]
  }
];

// ── DOM helpers ───────────────────────────────────────────────────────────────
function _fieldId(section, key) {
  return "field-" + section + "-" + key.replace(/\./g, "-");
}

function _helpIcon(tooltip) {
  if (!tooltip) return "";
  const escaped = tooltip.replace(/"/g, "&quot;");
  return '<span class="param-help" data-tip="' + escaped + '" title="' + escaped + '">?</span>';
}

// ── Conditional visibility ────────────────────────────────────────────────────
function _applyAllConditionals() {
  document.querySelectorAll("[data-cond-field]").forEach(function(wrapper) {
    const ctrlId = wrapper.dataset.condField;
    const ctrl = document.getElementById(ctrlId);
    let show = false;
    if (ctrl) {
      if (wrapper.dataset.condChecked !== undefined) {
        show = ctrl.checked;
      } else {
        show = String(ctrl.value) === wrapper.dataset.condVal;
      }
    }
    wrapper.classList.toggle("field-row--hidden", !show);
  });
}

function _setupConditionalListeners() {
  const seen = new Set();
  document.querySelectorAll("[data-cond-field]").forEach(function(wrapper) {
    const id = wrapper.dataset.condField;
    if (seen.has(id)) return;
    seen.add(id);
    const ctrl = document.getElementById(id);
    if (!ctrl) return;
    ctrl.addEventListener("change", _applyAllConditionals);
    ctrl.addEventListener("input",  _applyAllConditionals);
  });
}

// ── Form rendering ────────────────────────────────────────────────────────────
function _renderField(section, f) {
  const id = _fieldId(section, f.key);

  let condAttrs = "";
  let condClass = "";
  if (f.visibleWhen) {
    const ctrlId = _fieldId(section, f.visibleWhen.key);
    if (f.visibleWhen.value !== undefined) {
      condAttrs = ' data-cond-field="' + ctrlId + '" data-cond-val="' + f.visibleWhen.value + '"';
    } else if (f.visibleWhen.checked) {
      condAttrs = ' data-cond-field="' + ctrlId + '" data-cond-checked="1"';
    }
    condClass = " field-row--conditional field-row--hidden";
  }

  const fullClass = f.fullWidth ? " field-row--full" : "";
  const wrapClass = "field-row" + condClass + fullClass;

  if (f.type === "subheader") {
    return '<div class="field-subheader' + condClass + fullClass + '"' + condAttrs + ">" + f.label + "</div>";
  }

  if (f.type === "checkbox") {
    return '<div class="' + wrapClass + '"' + condAttrs + ">" +
      '<label class="checkbox-label" for="' + id + '">' +
      '<input type="checkbox" id="' + id + '" />' +
      f.label + " " + _helpIcon(f.tooltip) +
      "</label></div>";
  }

  if (f.type === "select") {
    const opts = f.options.map(function(o) {
      const val = typeof o === "object" ? o.value : String(o);
      const lbl = typeof o === "object" ? o.label : String(o);
      return '<option value="' + val + '">' + lbl + "</option>";
    }).join("");
    return '<div class="' + wrapClass + '"' + condAttrs + ">" +
      '<label class="field-label" for="' + id + '">' + f.label + " " + _helpIcon(f.tooltip) + "</label>" +
      '<select id="' + id + '" class="field-select">' + opts + "</select>" +
      "</div>";
  }

  // number / text
  const attrs = [
    'type="' + f.type + '"',
    'id="' + id + '"',
    'class="field-input"',
    f.min  !== undefined ? 'min="' + f.min + '"'   : "",
    f.max  !== undefined ? 'max="' + f.max + '"'   : "",
    f.step !== undefined ? 'step="' + f.step + '"' : ""
  ].filter(Boolean).join(" ");

  return '<div class="' + wrapClass + '"' + condAttrs + ">" +
    '<label class="field-label" for="' + id + '">' + f.label + " " + _helpIcon(f.tooltip) + "</label>" +
    '<input ' + attrs + " />" +
    "</div>";
}

function _buildForm() {
  const container = document.getElementById("params-form");
  if (!container) return;

  const html = PARAMS_SCHEMA.map(function(sec) {
    const body = '<div class="field-grid">' +
      sec.fields.map(function(f) { return _renderField(sec.section, f); }).join("") +
      "</div>";
    return '<div class="accordion' + (sec.open ? " open" : "") + '">' +
      '<div class="accordion-header">' +
      '<span class="accordion-icon">' + sec.icon + "</span>" +
      '<span class="accordion-label">' + sec.label + "</span>" +
      '<span class="accordion-arrow">▶</span>' +
      "</div>" +
      '<div class="accordion-body">' + body + "</div>" +
      "</div>";
  }).join("");

  container.innerHTML = html;
  _applyAllConditionals();
  _setupConditionalListeners();
}

// ── Populate / collect ────────────────────────────────────────────────────────
function _populate(cfg) {
  PARAMS_SCHEMA.forEach(function(sec) {
    const secData = cfg[sec.jsonKey] || {};
    sec.fields.forEach(function(f) {
      if (f.type === "subheader") return;
      const el = document.getElementById(_fieldId(sec.section, f.key));
      if (!el) return;
      // Drill into nested keys (e.g. "sigma_clip.limit")
      const parts = f.key.split(".");
      let val = secData;
      for (let i = 0; i < parts.length; i++) {
        if (val == null) { val = undefined; break; }
        val = val[parts[i]];
      }
      if (val === undefined || val === null) return;
      if (f.type === "checkbox") {
        el.checked = (val === 1 || val === true);
      } else {
        el.value = val;
      }
    });
  });
  _applyAllConditionals();
}

function _collect() {
  const cfg = {};
  PARAMS_SCHEMA.forEach(function(sec) {
    cfg[sec.jsonKey] = cfg[sec.jsonKey] || {};
    sec.fields.forEach(function(f) {
      if (f.type === "subheader") return;
      const el = document.getElementById(_fieldId(sec.section, f.key));
      if (!el) return;
      // Build nested structure for dotted keys
      const parts = f.key.split(".");
      let target = cfg[sec.jsonKey];
      for (let i = 0; i < parts.length - 1; i++) {
        if (!target[parts[i]]) target[parts[i]] = {};
        target = target[parts[i]];
      }
      const lastKey = parts[parts.length - 1];
      if (f.type === "checkbox") {
        target[lastKey] = el.checked ? 1 : 0;
      } else if (f.type === "number") {
        target[lastKey] = parseFloat(el.value);
      } else if (f.type === "select") {
        const raw = el.value;
        target[lastKey] = isNaN(Number(raw)) ? raw : Number(raw);
      } else {
        target[lastKey] = el.value;
      }
    });
  });
  return cfg;
}

// ── Validation ────────────────────────────────────────────────────────────────
function _validate(cfg) {
  const issues = [];
  const p = cfg.profile || {};
  const n = cfg.normalization || {};
  const o = cfg.output || {};
  if (p.vel_end_kms <= p.vel_start_kms) issues.push("vel_end_kms must be greater than vel_start_kms");
  if (p.pixel_velocity_kms <= 0) issues.push("pixel_velocity_kms must be positive");
  if (n.weighting_mode < 0 || n.weighting_mode > 7) issues.push("weighting_mode must be 0–7");
  if (!o.profile) issues.push("output.profile cannot be empty");
  return issues;
}

// ── Actions ───────────────────────────────────────────────────────────────────
function _refreshPreview() {
  const pre = document.getElementById("params-json-preview");
  if (pre) pre.value = JSON.stringify(_collect(), null, 2);
}

// ── Wire up ───────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async function() {
  _buildForm();

  // Wire change events → refresh JSON preview
  document.getElementById("params-form").addEventListener("change", _refreshPreview);
  document.getElementById("params-form").addEventListener("input",  _refreshPreview);

  const statusEl = document.getElementById("params-status");

  async function _load() {
    setStatusBar(statusEl, "Loading…");
    try {
      const cfg = await apiFetch("/api/config");
      if (cfg && Object.keys(cfg).length > 0) {
        const merged = window.LSDUI._mergeDeep
          ? window.LSDUI._mergeDeep(window.LSDUI.defaultConfig(), cfg)
          : Object.assign(window.LSDUI.defaultConfig(), cfg);
        window.LSDUI.saveConfig(merged);
        _populate(merged);
      } else {
        _populate(window.LSDUI.loadConfig());
      }
      _refreshPreview();
      setStatusBar(statusEl, "Config loaded.", "ok");
      setTimeout(function() { setStatusBar(statusEl, ""); }, 2500);
    } catch (e) {
      _populate(window.LSDUI.loadConfig());
      _refreshPreview();
      setStatusBar(statusEl, "Server unavailable — showing local config.", "warn");
    }
  }

  await _load();

  document.getElementById("params-save-btn").addEventListener("click", async function() {
    const cfg = _collect();
    const issues = _validate(cfg);
    if (issues.length) { setStatusBar(statusEl, issues[0], "error"); return; }
    setStatusBar(statusEl, "Saving…");
    try {
      await apiFetch("/api/config", { method: "PUT", body: cfg });
      window.LSDUI.saveConfig(cfg);
      _refreshPreview();
      setStatusBar(statusEl, "✔ Saved to LSDConfig.json", "ok");
      setTimeout(function() { setStatusBar(statusEl, ""); }, 3000);
    } catch (e) {
      setStatusBar(statusEl, "Save failed: " + e.message, "error");
    }
  });

  document.getElementById("params-reload-btn").addEventListener("click", _load);

  document.getElementById("params-reset-btn").addEventListener("click", function() {
    const def = window.LSDUI.defaultConfig();
    window.LSDUI.saveConfig(def);
    _populate(def);
    _refreshPreview();
    setStatusBar(statusEl, "Reset to defaults.", "warn");
  });

  document.getElementById("params-export-btn").addEventListener("click", function() {
    const cfg = _collect();
    const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "LSDConfig.exported.json";
    a.click();
    URL.revokeObjectURL(url);
    setStatusBar(statusEl, "Exported.", "ok");
  });
});
