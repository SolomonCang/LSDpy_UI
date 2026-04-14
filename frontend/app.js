const fieldMap = {
  observation: "input-observation",
  mask: "input-mask",
  velStart: "profile-vel-start",
  velEnd: "profile-vel-end",
  pixelVel: "profile-pixel-vel",
  depth: "norm-depth",
  lande: "norm-lande",
  wave: "norm-wave",
  mode: "norm-weighting-mode",
  sigmaLimit: "proc-sigma-limit",
  sigmaIters: "proc-sigma-iters",
  outProfile: "output-profile",
  removeContPol: "proc-remove-cont-pol",
  saveLsdout: "output-save-lsdout",
  savePlot: "output-save-plot"
};

let runTimer = null;
let runStep = 0;
let apiPollTimer = null;
let activeTaskId = null;

function el(id) {
  return document.getElementById(id);
}

function asNumber(id) {
  return Number(el(id).value);
}

function asInt(id) {
  return Number.parseInt(el(id).value, 10);
}

function asFlag(id) {
  return el(id).checked ? 1 : 0;
}

function getRunMode() {
  return el("run-mode").value;
}

function getApiBaseUrl() {
  return el("api-base-url").value.trim().replace(/\/$/, "");
}

function apiUrl(path) {
  return `${getApiBaseUrl()}${path}`;
}

function buildConfig() {
  return {
    input: {
      observation: el(fieldMap.observation).value.trim(),
      mask: el(fieldMap.mask).value.trim()
    },
    profile: {
      vel_start_kms: asNumber(fieldMap.velStart),
      vel_end_kms: asNumber(fieldMap.velEnd),
      pixel_velocity_kms: asNumber(fieldMap.pixelVel)
    },
    normalization: {
      depth: asNumber(fieldMap.depth),
      lande: asNumber(fieldMap.lande),
      wavelength_nm: asNumber(fieldMap.wave),
      weighting_mode: asInt(fieldMap.mode)
    },
    processing: {
      remove_continuum_polarization: asFlag(fieldMap.removeContPol),
      interp_mode: 1,
      sigma_clip: {
        limit: asNumber(fieldMap.sigmaLimit),
        iterations: asInt(fieldMap.sigmaIters)
      }
    },
    output: {
      profile: el(fieldMap.outProfile).value.trim(),
      save_model_spectrum: 0,
      model_spectrum: "results/outModelSpec.dat",
      plot_profile: 0,
      save_plot: asFlag(fieldMap.savePlot),
      plot_image: "results/profile.png",
      save_lsdout: asFlag(fieldMap.saveLsdout),
      lsdout: "auto"
    },
    model_options: {
      saturation_correction: 1,
      telluric_filtering: 1,
      line_filtering: 1
    }
  };
}

function setStatus(type, text) {
  const statusNode = el("run-status");
  statusNode.className = `status ${type}`;
  statusNode.textContent = text;
}

function logLine(message) {
  const row = document.createElement("p");
  row.className = "log-item";
  const timestamp = new Date().toLocaleTimeString();
  row.textContent = `[${timestamp}] ${message}`;
  const panel = el("log-panel");
  panel.appendChild(row);
  panel.scrollTop = panel.scrollHeight;
}

function validateConfig(config) {
  const issues = [];
  if (!config.input.observation) {
    issues.push("input.observation 不能为空");
  }
  if (!config.input.mask) {
    issues.push("input.mask 不能为空");
  }
  if (config.profile.vel_end_kms <= config.profile.vel_start_kms) {
    issues.push("profile.vel_end_kms 必须大于 vel_start_kms");
  }
  if (config.profile.pixel_velocity_kms <= 0) {
    issues.push("profile.pixel_velocity_kms 必须大于 0");
  }
  if (config.normalization.weighting_mode < 0 || config.normalization.weighting_mode > 6) {
    issues.push("normalization.weighting_mode 必须在 0-6");
  }
  if (config.processing.sigma_clip.iterations < 0) {
    issues.push("processing.sigma_clip.iterations 不能小于 0");
  }
  return issues;
}

function refreshPreview() {
  const config = buildConfig();
  el("json-preview").value = JSON.stringify(config, null, 2);
}

function exportConfig() {
  const config = buildConfig();
  const issues = validateConfig(config);
  if (issues.length > 0) {
    setStatus("error", "Invalid Config");
    logLine(`导出失败: ${issues.join("; ")}`);
    return;
  }
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "LSDConfig.generated.json";
  link.click();
  URL.revokeObjectURL(url);
  setStatus("done", "Exported");
  logLine("已导出配置文件 LSDConfig.generated.json");
}

function loadExample() {
  el(fieldMap.observation).value = "data/hd219134_19jun16_v_01.s";
  el(fieldMap.mask).value = "masks/atomic_6300_depth0.1_geff0.0.dat";
  el(fieldMap.velStart).value = "-150";
  el(fieldMap.velEnd).value = "150";
  el(fieldMap.pixelVel).value = "1.8";
  el(fieldMap.depth).value = "0.7";
  el(fieldMap.lande).value = "1.2";
  el(fieldMap.wave).value = "500";
  el(fieldMap.mode).value = "2";
  el(fieldMap.sigmaLimit).value = "3";
  el(fieldMap.sigmaIters).value = "5";
  el(fieldMap.outProfile).value = "results/hd219134_prof.dat";
  el(fieldMap.removeContPol).checked = true;
  el(fieldMap.saveLsdout).checked = true;
  el(fieldMap.savePlot).checked = false;
  el("run-mode").value = "mock";
  refreshPreview();
  logLine("已加载示例配置");
}

function startMockRun() {
  const config = buildConfig();
  const issues = validateConfig(config);
  if (issues.length > 0) {
    setStatus("error", "Invalid Config");
    logLine(`启动失败: ${issues.join("; ")}`);
    return;
  }

  if (runTimer !== null) {
    clearInterval(runTimer);
  }
  runStep = 0;
  setStatus("running", "Running");
  logLine("任务已提交: lsd_pipeline.run() [mock]");

  const steps = [
    "正在读取观测光谱...",
    "正在加载线掩膜并构造矩阵...",
    "正在执行 LSD 求解与 sigma clipping...",
    "正在写出 profile 与 lsdout 文件...",
    "任务完成"
  ];

  runTimer = setInterval(() => {
    logLine(steps[runStep]);
    runStep += 1;

    if (runStep >= steps.length) {
      clearInterval(runTimer);
      runTimer = null;
      setStatus("done", "Completed");
    }
  }, 900);
}

async function pollApiStatus(taskId) {
  if (apiPollTimer !== null) {
    clearInterval(apiPollTimer);
  }

  apiPollTimer = setInterval(async () => {
    try {
      const response = await fetch(apiUrl(`/api/tasks/${taskId}`));
      if (!response.ok) {
        throw new Error(`状态查询失败: HTTP ${response.status}`);
      }
      const payload = await response.json();
      if (payload.status === "running") {
        setStatus("running", "Running");
      }
      if (payload.status === "done") {
        setStatus("done", "Completed");
        logLine("API 任务完成");
        clearInterval(apiPollTimer);
        apiPollTimer = null;
      }
      if (payload.status === "error") {
        setStatus("error", "Failed");
        logLine(`API 任务失败: ${payload.message || "unknown error"}`);
        clearInterval(apiPollTimer);
        apiPollTimer = null;
      }
    } catch (error) {
      setStatus("error", "API Error");
      logLine(`轮询失败: ${error.message}`);
      clearInterval(apiPollTimer);
      apiPollTimer = null;
    }
  }, 1200);
}

async function startApiRun() {
  const config = buildConfig();
  const issues = validateConfig(config);
  if (issues.length > 0) {
    setStatus("error", "Invalid Config");
    logLine(`启动失败: ${issues.join("; ")}`);
    return;
  }

  setStatus("running", "Submitting");
  logLine(`正在提交 API 任务到 ${getApiBaseUrl()}`);

  try {
    const response = await fetch(apiUrl("/api/tasks"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ config })
    });
    if (!response.ok) {
      throw new Error(`任务提交失败: HTTP ${response.status}`);
    }
    const payload = await response.json();
    activeTaskId = payload.task_id;
    if (!activeTaskId) {
      throw new Error("响应中缺少 task_id");
    }
    setStatus("running", "Running");
    logLine(`API 任务已创建: ${activeTaskId}`);
    await pollApiStatus(activeTaskId);
  } catch (error) {
    setStatus("error", "API Error");
    logLine(`API 启动失败: ${error.message}`);
    logLine("提示: 目前仓库尚未实现这些接口，后端完成后即可直接连通。" );
  }
}

function stopMockRun() {
  if (runTimer !== null) {
    clearInterval(runTimer);
    runTimer = null;
    setStatus("idle", "Stopped");
    logLine("任务已停止");
    return;
  }
  logLine("当前无运行任务");
}

async function stopApiRun() {
  if (!activeTaskId) {
    logLine("当前没有可停止的 API 任务");
    return;
  }

  try {
    const response = await fetch(apiUrl(`/api/tasks/${activeTaskId}/cancel`), {
      method: "POST"
    });
    if (!response.ok) {
      throw new Error(`取消失败: HTTP ${response.status}`);
    }
    if (apiPollTimer !== null) {
      clearInterval(apiPollTimer);
      apiPollTimer = null;
    }
    setStatus("idle", "Stopped");
    logLine(`API 任务已取消: ${activeTaskId}`);
    activeTaskId = null;
  } catch (error) {
    setStatus("error", "API Error");
    logLine(`取消失败: ${error.message}`);
  }
}

function startRun() {
  if (getRunMode() === "api") {
    startApiRun();
    return;
  }
  startMockRun();
}

function stopRun() {
  if (getRunMode() === "api") {
    stopApiRun();
    return;
  }
  stopMockRun();
}

function wireEvents() {
  Object.values(fieldMap).forEach((id) => {
    const node = el(id);
    const eventType = node.tagName === "SELECT" || node.type === "checkbox" ? "change" : "input";
    node.addEventListener(eventType, refreshPreview);
  });

  el("btn-load-example").addEventListener("click", loadExample);
  el("btn-export-config").addEventListener("click", exportConfig);
  el("btn-validate").addEventListener("click", () => {
    const issues = validateConfig(buildConfig());
    if (issues.length === 0) {
      setStatus("done", "Config OK");
      logLine("配置校验通过");
      return;
    }
    setStatus("error", "Invalid Config");
    logLine(`配置校验失败: ${issues.join("; ")}`);
  });
  el("btn-run").addEventListener("click", startRun);
  el("btn-stop").addEventListener("click", stopRun);
  el("run-mode").addEventListener("change", () => {
    const mode = getRunMode();
    if (mode === "api") {
      logLine("已切换到 API 模式，将调用 /api/tasks 接口");
      return;
    }
    logLine("已切换到 Mock 模式，前端将模拟运行过程");
  });
}

wireEvents();
loadExample();
setStatus("idle", "Idle");
logLine("UI 初始化完成，等待任务启动");
