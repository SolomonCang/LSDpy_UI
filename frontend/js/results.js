/**
 * results.js — LSD profile three-panel plot renderer for the Results tab.
 *
 * Renders Stokes V, Null N1, and Stokes I panels with uncertainty bands,
 * matching the layout of core/plotting/basic_plots.py.
 */

var SVG_NS = "http://www.w3.org/2000/svg";

function _svgEl(tag, attrs) {
  var el = document.createElementNS(SVG_NS, tag);
  for (var k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

/**
 * Draw a single panel into the given SVG element.
 * @param {SVGElement} svg
 * @param {number} w         viewBox width
 * @param {number} h         viewBox height
 * @param {number[]} vel     velocity array
 * @param {number[]} yData   signal array
 * @param {number[]} yErr    uncertainty array (1-sigma)
 * @param {string}   color   line color
 * @param {string}   errColor fill color for error band
 * @param {string}   ylabel  Y-axis label
 * @param {boolean}  showXLabel  whether to show x-axis label
 * @param {number|null} hline  horizontal reference line value (null to skip)
 */
function _drawPanel(svg, w, h, vel, yData, yErr, color, errColor, ylabel, showXLabel, hline) {
  svg.innerHTML = "";
  if (!vel || vel.length < 2) return;

  var pad = { left: 60, right: 20, top: 12, bottom: showXLabel ? 28 : 8 };
  var pw = w - pad.left - pad.right;
  var ph = h - pad.top - pad.bottom;

  var minX = vel[0];
  var maxX = vel[vel.length - 1];
  var xRange = maxX - minX || 1;

  // Compute Y range including error bars
  var allY = [];
  for (var i = 0; i < yData.length; i++) {
    allY.push(yData[i] + (yErr[i] || 0));
    allY.push(yData[i] - (yErr[i] || 0));
  }
  var minY = Math.min.apply(null, allY);
  var maxY = Math.max.apply(null, allY);
  var yMargin = (maxY - minY) * 0.08 || 1e-6;
  minY -= yMargin;
  maxY += yMargin;
  var yRange = maxY - minY || 1;

  function toX(v) { return pad.left + ((v - minX) / xRange) * pw; }
  function toY(v) { return pad.top + ((maxY - v) / yRange) * ph; }

  // Axes
  var axisD = "M " + pad.left + " " + (h - pad.bottom) +
              " L " + (w - pad.right) + " " + (h - pad.bottom) +
              " M " + pad.left + " " + pad.top +
              " L " + pad.left + " " + (h - pad.bottom);
  svg.appendChild(_svgEl("path", { d: axisD, stroke: "#967b63", fill: "none", "stroke-width": "1" }));

  // Horizontal reference line
  if (hline !== null && hline !== undefined) {
    var hy = toY(hline);
    if (hy >= pad.top && hy <= h - pad.bottom) {
      svg.appendChild(_svgEl("line", {
        x1: pad.left, y1: hy, x2: w - pad.right, y2: hy,
        stroke: "#000", "stroke-dasharray": "4,3", "stroke-opacity": "0.4", "stroke-width": "1"
      }));
    }
  }

  // Error band (filled polygon)
  if (yErr && yErr.length === vel.length) {
    var upper = [];
    var lower = [];
    for (var j = 0; j < vel.length; j++) {
      upper.push(toX(vel[j]) + "," + toY(yData[j] + yErr[j]));
      lower.unshift(toX(vel[j]) + "," + toY(yData[j] - yErr[j]));
    }
    svg.appendChild(_svgEl("polygon", {
      points: upper.concat(lower).join(" "),
      fill: errColor, "fill-opacity": "0.30", stroke: "none"
    }));
  }

  // Data line
  var d = "";
  for (var k = 0; k < vel.length; k++) {
    d += (k === 0 ? "M " : " L ") + toX(vel[k]).toFixed(1) + " " + toY(yData[k]).toFixed(1);
  }
  svg.appendChild(_svgEl("path", { d: d, stroke: color, "stroke-width": "1.8", fill: "none" }));

  // Y-axis label
  var labelEl = _svgEl("text", {
    x: "14", y: String(pad.top + ph / 2),
    fill: "#967b63", "font-size": "12", "font-family": "Inter, sans-serif",
    "text-anchor": "middle", "dominant-baseline": "central",
    transform: "rotate(-90, 14, " + (pad.top + ph / 2) + ")"
  });
  labelEl.textContent = ylabel;
  svg.appendChild(labelEl);

  // X-axis label
  if (showXLabel) {
    var xLabel = _svgEl("text", {
      x: String(pad.left + pw / 2), y: String(h - 2),
      fill: "#967b63", "font-size": "11", "font-family": "Inter, sans-serif",
      "text-anchor": "middle"
    });
    xLabel.textContent = "Velocity (km/s)";
    svg.appendChild(xLabel);
  }

  // Tick labels on Y axis (min, mid, max)
  var yTicks = [minY + yMargin, (minY + maxY) / 2, maxY - yMargin];
  yTicks.forEach(function(tv) {
    var ty = toY(tv);
    svg.appendChild(_svgEl("line", {
      x1: pad.left - 3, y1: ty, x2: pad.left, y2: ty,
      stroke: "#967b63", "stroke-width": "1"
    }));
    var tl = _svgEl("text", {
      x: String(pad.left - 5), y: String(ty),
      fill: "#967b63", "font-size": "9", "font-family": "Inter, sans-serif",
      "text-anchor": "end", "dominant-baseline": "central"
    });
    tl.textContent = tv.toExponential(1);
    svg.appendChild(tl);
  });

  // Tick labels on X axis (if shown)
  if (showXLabel) {
    var nXTicks = 5;
    for (var t = 0; t <= nXTicks; t++) {
      var xv = minX + (xRange * t / nXTicks);
      var tx = toX(xv);
      svg.appendChild(_svgEl("line", {
        x1: tx, y1: h - pad.bottom, x2: tx, y2: h - pad.bottom + 3,
        stroke: "#967b63", "stroke-width": "1"
      }));
      var xt = _svgEl("text", {
        x: String(tx), y: String(h - pad.bottom + 14),
        fill: "#967b63", "font-size": "9", "font-family": "Inter, sans-serif",
        "text-anchor": "middle"
      });
      xt.textContent = xv.toFixed(0);
      svg.appendChild(xt);
    }
  }
}

/**
 * Render three-panel LSD profile plot.
 * @param {object} prof  { vel[], specI[], sigI[], specV[], sigV[], specN1[], sigN1[] }
 */
function drawProfile(prof) {
  var svgV = document.getElementById("profile-svg-v");
  var svgN = document.getElementById("profile-svg-n");
  var svgI = document.getElementById("profile-svg-i");
  if (!prof || !prof.vel || prof.vel.length < 2) {
    svgV.innerHTML = "";
    svgN.innerHTML = "";
    svgI.innerHTML = "";
    return;
  }

  // Panel 1: Stokes I (blue) — shown on top, raw I/Ic
  _drawPanel(svgI, 900, 220, prof.vel, prof.specI, prof.sigI,
    "#2471a3", "#5dade2", "I/Ic", false, null);

  // Panel 2: Stokes V (red)
  _drawPanel(svgV, 900, 140, prof.vel, prof.specV, prof.sigV,
    "#c0392b", "#e74c3c", "V/Ic", false, 0.0);

  // Panel 3: Null N1 (magenta) — shown at bottom with x-axis label
  _drawPanel(svgN, 900, 140, prof.vel, prof.specN1, prof.sigN1,
    "#8e44ad", "#9b59b6", "N/Ic", true, 0.0);
}

var BATCH_RESULT_KEY = "lsd_ui_batch_result_v1";
var _batchData = null;

function _showBatchSelector(items) {
  var container = document.getElementById("batch-selector");
  var select = document.getElementById("batch-select");
  var countEl = document.getElementById("batch-count");
  if (!items || items.length <= 1) {
    container.style.display = "none";
    _batchData = null;
    return;
  }
  _batchData = items;
  container.style.display = "";
  countEl.textContent = items.length + " profiles";
  select.innerHTML = "";
  items.forEach(function(item, idx) {
    var opt = document.createElement("option");
    opt.value = idx;
    opt.textContent = (item.name || item.output_profile || ("Spectrum #" + (idx + 1)));
    select.appendChild(opt);
  });
}

function _drawBatchItem(idx) {
  if (!_batchData || !_batchData[idx]) return;
  var item = _batchData[idx];
  drawProfile(item.profile);
  var summary = {
    name: item.name,
    output_profile: item.output_profile,
    profile_points: item.profile && item.profile.vel ? item.profile.vel.length : 0
  };
  document.getElementById("result-json").value = JSON.stringify(summary, null, 2);
  setStatusBar("result-status", "Showing: " + (item.name || "Spectrum #" + (idx + 1)), "ok");
}

function loadResult() {
  // First check batch data
  var batchRaw = localStorage.getItem(BATCH_RESULT_KEY);
  if (batchRaw) {
    try {
      var batchObj = JSON.parse(batchRaw);
      if (batchObj.items && batchObj.items.length > 1) {
        _showBatchSelector(batchObj.items);
        _drawBatchItem(0);
        document.getElementById("result-json").value = JSON.stringify({
          batch_count: batchObj.items.length,
          run_at: batchObj.run_at,
          items: batchObj.items.map(function(it) { return { name: it.name, output_profile: it.output_profile }; })
        }, null, 2);
        setStatusBar("result-status", "Batch loaded: " + batchObj.items.length + " profiles.", "ok");
        return;
      }
    } catch(_) {}
  }

  // Single result fallback
  _showBatchSelector(null);
  var raw = localStorage.getItem(window.LSDUI.RESULT_KEY);
  if (!raw) {
    setStatusBar("result-status", "No data — run a task first.", "warn");
    document.getElementById("result-json").value = "No run result found. Go to the Task tab and run first.";
    drawProfile(null);
    return;
  }
  try {
    var data = JSON.parse(raw);
    drawProfile(data.profile);
    document.getElementById("result-json").value = JSON.stringify(data, null, 2);
    setStatusBar("result-status", "Loaded.", "ok");
  } catch (_err) {
    setStatusBar("result-status", "Invalid cache — run a new task.", "error");
  }
}

async function loadFromFile() {
  try {
    var cfg = window.LSDUI.loadConfig();
    var profPath = (cfg.output && cfg.output.profile) || "";
    if (!profPath) {
      setStatusBar("result-status", "No output.profile path configured.", "warn");
      return;
    }
    var url = "/api/profile/data?path=" + encodeURIComponent(profPath);
    var resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    var profileData = await resp.json();
    _showBatchSelector(null);
    var payload = {
      run_at: new Date().toISOString(),
      mode: "file",
      output_profile: profPath,
      profile: profileData
    };
    localStorage.setItem(window.LSDUI.RESULT_KEY, JSON.stringify(payload));
    drawProfile(profileData);
    document.getElementById("result-json").value = JSON.stringify(payload, null, 2);
    setStatusBar("result-status", "Loaded from server file.", "ok");
  } catch (err) {
    setStatusBar("result-status", "Failed to load: " + err.message, "error");
  }
}

async function loadBatchFromFiles() {
  try {
    var resp = await fetch("/api/files/results");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    var files = await resp.json();
    var lsdFiles = files.filter(function(f) { return f.match(/_lsd\.dat$/); });
    if (!lsdFiles.length) {
      setStatusBar("result-status", "No batch _lsd.dat files found in results/.", "warn");
      return;
    }
    setStatusBar("result-status", "Loading " + lsdFiles.length + " profiles…", "warn");
    var items = [];
    for (var i = 0; i < lsdFiles.length; i++) {
      var f = lsdFiles[i];
      try {
        var profResp = await fetch("/api/profile/data?path=" + encodeURIComponent(f));
        if (profResp.ok) {
          var pdata = await profResp.json();
          var stem = f.replace(/^.*\//, "").replace(/\.[^.]+$/, "");
          items.push({ name: stem, output_profile: f, profile: pdata });
        }
      } catch(_) {}
    }
    if (items.length > 0) {
      _showBatchSelector(items);
      _drawBatchItem(0);
      localStorage.setItem(BATCH_RESULT_KEY, JSON.stringify({
        run_at: new Date().toISOString(), mode: "file", items: items
      }));
      setStatusBar("result-status", "Loaded " + items.length + " profiles from server.", "ok");
    } else {
      setStatusBar("result-status", "Could not parse any profile files.", "error");
    }
  } catch (err) {
    setStatusBar("result-status", "Failed: " + err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", function() {
  document.getElementById("btn-result-load").addEventListener("click", loadResult);
  document.getElementById("btn-load-file").addEventListener("click", loadFromFile);
  document.getElementById("btn-load-batch").addEventListener("click", loadBatchFromFiles);

  // Batch selector change
  document.getElementById("batch-select").addEventListener("change", function() {
    var idx = parseInt(this.value, 10);
    _drawBatchItem(idx);
  });

  var btnSpectrum = document.getElementById("btn-view-spectrum");
  if (btnSpectrum) {
    btnSpectrum.addEventListener("click", function () {
      var cfg = window.LSDUI.loadConfig();
      var obs = (cfg.input && cfg.input.observation) || "";
      var mask = (cfg.input && cfg.input.mask) || "";
      if (!obs || !mask) {
        setStatusBar("result-status", "Set observation and mask paths in the Data tab first.", "warn");
        return;
      }
      var url = "spectrum_view.html?obs=" + encodeURIComponent(obs) + "&mask=" + encodeURIComponent(mask);
      window.open(url, "_blank");
    });
  }

  loadResult();
});
