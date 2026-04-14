/**
 * common.js — Shared state, utilities, and tab navigation for LSD UI.
 *
 * Provides window.LSDUI (config management) and window.apiFetch (fetch wrapper).
 * Must be loaded before all other page JS files.
 */

// ── Config state ─────────────────────────────────────────────────────────────
const CONFIG_KEY = "lsd_ui_config_v1";
const RESULT_KEY = "lsd_ui_last_result_v1";

function defaultConfig() {
  return {
    input: {
      observation: "data/hd219134_19jun16_v_01.s",
      mask: "masks/mask-4500g40-0.1-trim3.dat"
    },
    profile: {
      vel_start_kms: -200.0,
      vel_end_kms: 200.0,
      pixel_velocity_kms: 1.8
    },
    normalization: {
      depth: 0.7,
      lande: 1.2,
      wavelength_nm: 500.0,
      weighting_mode: 2,
      weighting_threshold: 0.5,
      weighting_low_value: 0.1,
      weighting_high_value: 10.0
    },
    processing: {
      remove_continuum_polarization: 1,
      interp_mode: 1,
      sigma_clip: { limit: 500.0, iterations: 0 }
    },
    output: {
      profile: "results/prof.dat",
      save_model_spectrum: 1,
      model_spectrum: "results/outModelSpec.dat",
      plot_profile: 0,
      save_plot: 0,
      plot_image: "results/prof.png",
      save_lsdout: 1,
      lsdout: "auto"
    },
    model_options: {
      saturation_correction: 1,
      telluric_filtering: 1,
      line_filtering: 1
    }
  };
}

function _mergeDeep(base, patch) {
  const out = Object.assign({}, base);
  for (const k of Object.keys(patch)) {
    if (patch[k] && typeof patch[k] === "object" && !Array.isArray(patch[k]) &&
        base[k] && typeof base[k] === "object") {
      out[k] = _mergeDeep(base[k], patch[k]);
    } else {
      out[k] = patch[k];
    }
  }
  return out;
}

function loadConfig() {
  const raw = localStorage.getItem(CONFIG_KEY);
  let cfg = defaultConfig();
  if (raw) {
    try { cfg = _mergeDeep(cfg, JSON.parse(raw)); } catch (_) {}
  }
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
  return cfg;
}

function saveConfig(cfg) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

// ── API fetch wrapper ─────────────────────────────────────────────────────────
async function apiFetch(url, opts) {
  const options = Object.assign({ headers: { "Content-Type": "application/json" } }, opts || {});
  if (options.body && typeof options.body === "object") {
    options.body = JSON.stringify(options.body);
  }
  const resp = await fetch(url, options);
  if (!resp.ok) {
    let detail = resp.statusText;
    try { const j = await resp.json(); detail = j.detail || JSON.stringify(j); } catch (_) {}
    throw new Error(resp.status + ": " + detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

// ── Server config sync ────────────────────────────────────────────────────────
async function fetchServerConfig() {
  try {
    const cfg = await apiFetch("/api/config");
    if (cfg && Object.keys(cfg).length > 0) {
      const merged = _mergeDeep(defaultConfig(), cfg);
      saveConfig(merged);
      return merged;
    }
  } catch (e) {
    console.error("fetchServerConfig failed", e);
  }
  return loadConfig();
}

async function saveServerConfig(cfg) {
  saveConfig(cfg);
  await apiFetch("/api/config", { method: "PUT", body: cfg });
}

// ── Status bar helpers ────────────────────────────────────────────────────────
/**
 * Set a .status-bar element's text and class.
 * @param {HTMLElement|string} elOrId
 * @param {string} msg
 * @param {'ok'|'warn'|'error'|''} cls
 */
function setStatusBar(elOrId, msg, cls) {
  const node = typeof elOrId === "string" ? document.getElementById(elOrId) : elOrId;
  if (!node) return;
  node.textContent = msg || "";
  node.className = "status-bar" + (cls ? " " + cls : "");
}

// ── Accordion toggle (delegated) ──────────────────────────────────────────────
document.addEventListener("click", function(e) {
  const hdr = e.target.closest(".accordion-header");
  if (hdr) {
    const acc = hdr.closest(".accordion");
    if (acc) acc.classList.toggle("open");
  }
});

// ── Tab navigation ────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(function(btn) {
  btn.addEventListener("click", function() {
    const target = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach(function(b) {
      b.classList.toggle("active", b.dataset.tab === target);
      b.setAttribute("aria-selected", b.dataset.tab === target);
    });
    document.querySelectorAll(".tab-panel").forEach(function(p) {
      p.classList.toggle("active", p.id === "tab-" + target);
    });
  });
});

// ── Legacy multi-page nav ─────────────────────────────────────────────────────
function setActiveNav(page) {
  document.querySelectorAll(".nav-link").forEach(function(link) {
    link.classList.toggle("active", link.dataset.page === page);
  });
}

function fmtNow() {
  return new Date().toLocaleTimeString();
}

// ── Expose globals ────────────────────────────────────────────────────────────
window.apiFetch        = apiFetch;
window.setStatusBar    = setStatusBar;
window.LSDUI = {
  CONFIG_KEY,
  RESULT_KEY,
  defaultConfig,
  loadConfig,
  saveConfig,
  fetchServerConfig,
  saveServerConfig,
  setActiveNav,
  fmtNow
};

      pixel_velocity_kms: 1.8
    },
    normalization: {
      depth: 0.7,
      lande: 1.2,
      wavelength_nm: 500,
      weighting_mode: 2,
      weighting_threshold: 0.5,
      weighting_low_value: 0.1,
      weighting_high_value: 10.0
    },
    processing: {
      remove_continuum_polarization: 1,
      interp_mode: 1,
      sigma_clip: { limit: 500.0, iterations: 0 }
    },
    output: {
      profile: "results/prof.dat",
      save_model_spectrum: 1,
      model_spectrum: "results/outModelSpec.dat",
      plot_profile: 0,
      save_plot: 0,
      plot_image: "results/prof.png",
      save_lsdout: 1,
      lsdout: "auto"
    },
    model_options: {
      saturation_correction: 1,
      telluric_filtering: 1,
      line_filtering: 1
    }
  };
}

function mergeConfig(target, source) {
  for (const key of Object.keys(source)) {
    if (source[key] instanceof Object && key in target && !Array.isArray(source[key])) {
      Object.assign(source[key], mergeConfig(target[key], source[key]));
    }
  }
  Object.assign(target || {}, source);
  return target;
}

function loadConfig() {
  const raw = localStorage.getItem(CONFIG_KEY);
  let cfg = defaultConfig();
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      cfg = mergeConfig(cfg, parsed);
    } catch (_error) {
      // Return default config if parsing fails
    }
  }
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
  return cfg;
}

function saveConfig(cfg) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

async function fetchServerConfig() {
  try {
    // Force no-cache on the request level
    const res = await fetch('/api/config', { cache: 'no-store' });
    if (res.ok) {
      const txt = await res.text();
      if (txt.trim().length > 0) {
        let cfg = JSON.parse(txt);
        if (Object.keys(cfg).length > 0) {
           cfg = mergeConfig(defaultConfig(), cfg);
           saveConfig(cfg);
           return cfg;
        }
      }
    }
  } catch (e) {
    console.error("fetch server config failed", e);
  }
  return loadConfig();
}

async function saveServerConfig(cfg) {
  saveConfig(cfg);
  try {
    const res = await fetch('/api/config', {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg, null, 2)
    });
    if (!res.ok) throw new Error("Server config save failed");
  } catch (e) {
    console.error("save server config failed", e);
    throw e;
  }
}

function setActiveNav(page) {
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === page);
  });
}

function fmtNow() {
  return new Date().toLocaleTimeString();
}

window.LSDUI = {
  CONFIG_KEY,
  RESULT_KEY,
  defaultConfig,
  loadConfig,
  saveConfig,
  fetchServerConfig,
  saveServerConfig,
  setActiveNav,
  fmtNow
};
