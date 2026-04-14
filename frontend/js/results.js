/**
 * results.js — LSD profile plot renderer for the Results tab.
 */

function drawProfile(points) {
  const svg = document.getElementById("profile-svg");
  svg.innerHTML = "";
  if (!points || points.length < 2) {
    return;
  }

  const w = 900;
  const h = 280;
  const pad = 28;
  const minX = points[0].v;
  const maxX = points[points.length - 1].v;
  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));
  const yRange = maxY - minY || 1;

  const toX = (v) => pad + ((v - minX) / (maxX - minX || 1)) * (w - 2 * pad);
  const toY = (v) => h - pad - ((v - minY) / yRange) * (h - 2 * pad);

  const axis = document.createElementNS("http://www.w3.org/2000/svg", "path");
  axis.setAttribute("d", `M ${pad} ${h - pad} L ${w - pad} ${h - pad} M ${pad} ${pad} L ${pad} ${h - pad}`);
  axis.setAttribute("stroke", "#967b63");
  axis.setAttribute("fill", "none");
  svg.appendChild(axis);

  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${toX(p.v)} ${toY(p.y)}`).join(" ");
  const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
  line.setAttribute("d", d);
  line.setAttribute("stroke", "#0f8b8d");
  line.setAttribute("stroke-width", "2.2");
  line.setAttribute("fill", "none");
  svg.appendChild(line);
}

function loadResult() {
  const raw = localStorage.getItem(window.LSDUI.RESULT_KEY);
  if (!raw) {
    setStatusBar("result-status", "No data — run a task first.", "warn");
    document.getElementById("result-json").value = "No run result found. Go to the Task tab and run first.";
    drawProfile([]);
    return;
  }
  try {
    const data = JSON.parse(raw);
    drawProfile(data.profile);
    document.getElementById("result-json").value = JSON.stringify(data, null, 2);
    setStatusBar("result-status", "Loaded.", "ok");
  } catch (_err) {
    setStatusBar("result-status", "Invalid cache — run a new task.", "error");
  }
}

document.addEventListener("DOMContentLoaded", function() {
  document.getElementById("btn-result-load").addEventListener("click", loadResult);

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
