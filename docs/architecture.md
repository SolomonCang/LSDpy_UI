# LSD_UI 架构文档

## 项目目标

LSD_UI 是对 LSDpy 算法的模块化重构，保留原始数值逻辑的同时，将代码组织为清晰的分层架构，以便接入 Web UI 或 CLI。

---

## 目录结构

```
LSD_UI/
├── core/                   # 算法核心层
│   ├── lsd_config.py       # 配置参数类 (paramsLSD)
│   ├── lsd_io.py           # 数据读写 (observation, mask, prof)
│   ├── lsd_solver.py       # LSD 矩阵构造与最小二乘求解
│   ├── lsd_report.py       # 输出报告与检测统计
│   └── plotting/
│       └── basic_plots.py  # 基础可视化函数
│
├── pipeline/               # 任务编排层
│   ├── lsd_pipeline.py     # LSDPipeline — 单次完整运行流程
│   └── lsd_runner.py       # LSDRunner — CLI 参数解析与启动入口
│
├── api/                    # （预留）Web 后端接口
├── frontend/               # Web 前端（四页面模块化）
├── tests/                  # （预留）自动化测试
│
├── data/                   # 观测数据（.s 光谱文件）
├── masks/                  # 谱线掩膜文件（.dat）
├── results/                # 运行输出（profile、lsdout、图像）
│
├── config_loader.py        # JSON 配置加载器 (LSDConfig)
├── LSDConfig.json          # 默认配置模板
└── lsd_runner.py           # 根级别 CLI 入口（转发到 pipeline/）
```

---

## 分层职责

### 配置层 (`core/lsd_config.py`, `config_loader.py`)

- `paramsLSD`：运行参数容器，通过 `_load_from_mapping()` 从 JSON 配置字典加载。
- `LSDConfig`（`config_loader.py`）：JSON 配置的加载与验证，支持运行时参数覆盖（命令行优先于配置文件）。
- 相对路径由 `paramsLSD._resolve_path()` 基于 `base_dir` 解析为绝对路径。

### 数据模型层 (`core/lsd_io.py`)

| 类/函数 | 职责 |
|---|---|
| `classify_spectrum(fname)` | 自动分类输入光谱类型，检查是否为 LSD profile 并拒绝 |
| `observation` | 读取 6 列 `.s` 光谱文件，排序，过滤负 sigma 点 |
| `mask` | 读取谱线掩膜，计算权重，过滤视差带和覆盖范围外的谱线 |
| `prof` | 在速度空间分配 LSD profile 的像素数组 |

`prof.save()` 将结果写为 `.dat` 格式（7 列），`prof.lsdplot()` 使用 matplotlib 显示三面板图。

### 算法核心层 (`core/lsd_solver.py`, `core/lsd_report.py`)

- `buildM()`：构造观测像素对 profile 像素的权重矩阵 M（线性插值模式）
- `buildInvSig2()`：构造噪声权重对角矩阵 S²
- `lsdFit()`：通过 Cholesky 分解求解 LSD 正则方程
- `getChi2()`：计算残差 χ²
- `lsdFitSigmaClip()`：带 σ-clipping 迭代的完整拟合循环
- `scaleErr()`：按 reduced χ² 缩放误差棒
- `zeroProf()`：去除连续谱偏振基线
- `nullTest()`（`lsd_report.py`）：在谱线范围内外计算 V 和 N1 的检测概率

### 任务编排层 (`pipeline/`)

- `LSDPipeline.run()`：完整运行一次 LSD 任务，按顺序执行：
  1. 读取观测与掩膜
  2. 过滤谱线、缩减观测范围
  3. 打印观测光谱速度步长诊断信息
  4. 调用 `lsdFitSigmaClip()` 拟合
  5. 缩放误差棒，去除连续谱偏振
  6. 执行 null test
  7. 保存 profile、可选模型谱、LSD 报告

- `LSDRunner`：解析命令行参数，选择配置来源（JSON 或 `inlsd.dat`），启动 pipeline。

### 可视化层 (`core/plotting/basic_plots.py`)

- `plot_lsd_profile()`：三面板（V、N1、I）profile 图，带误差棒
- `plot_observation_vs_model()`：观测 I 与模型 I 对比图

matplotlib 在函数调用时才导入（懒加载），避免在无显示环境中导入失败。

### 前端层 (`frontend/`)

- 当前采用多页面模块化结构：
  - `params.html`：参数配置
  - `data.html`：光谱与 mask 输入
  - `task.html`：LSD 任务控制
  - `results.html`：结果绘图
- 页面共享样式位于 `frontend/css/app.css`。
- 共享状态与工具位于 `frontend/js/common.js`，页面逻辑按功能拆分到 `frontend/js/*.js`。

前端详细架构见：`docs/frontend_architecture.md`。

---

## 配置系统

`LSDConfig.json` 的顶层键映射到 `paramsLSD` 属性：

| JSON 路径 | paramsLSD 属性 | 含义 |
|---|---|---|
| `input.observation` | `inObs` | 观测光谱文件路径 |
| `input.mask` | `inMask` | 谱线掩膜文件路径 |
| `profile.vel_start_kms` | `velStart` | profile 速度起点 (km/s) |
| `profile.vel_end_kms` | `velEnd` | profile 速度终点 (km/s) |
| `profile.pixel_velocity_kms` | `pixVel` | 速度像素大小 (km/s) |
| `normalization.depth` | `normDepth` | 归一化谱线深度 |
| `normalization.lande` | `normLande` | 归一化 Landé g 因子 |
| `normalization.wavelength_nm` | `normWave` | 归一化波长 (nm) |
| `normalization.weighting_mode` | `weightingMode` | 权重模式 (0–6) |
| `processing.remove_continuum_polarization` | `removeContPol` | 是否去除连续谱偏振 |
| `processing.sigma_clip.limit` | `sigmaClip` | σ-clipping 阈值 |
| `processing.sigma_clip.iterations` | `sigmaClipIter` | σ-clipping 迭代次数 |
| `processing.interp_mode` | `interpMode` | 插值模式（0=最近邻，1=线性） |
| `output.save_model_spectrum` | `fSaveModelSpec` | 是否保存模型谱 |
| `output.plot_profile` | `fLSDPlotImg` | 是否绘制 profile 图 |
| `output.save_lsdout` | `fSaveLSDOut` | 是否保存运行摘要 |
| `model_options.saturation_correction` | `saturationCorrection` | 饱和校正开关 |
| `model_options.telluric_filtering` | `telluricFiltering` | 地球大气带过滤开关 |
| `model_options.line_filtering` | `lineFiltering` | 谱线覆盖过滤开关 |

---

## 数据流

```
LSDConfig.json
      │  LSDConfig.load()
      ▼
  paramsLSD
      │
      ├──── obs = observation(params.inObs)         # 读取6列.s观测文件
      ├──── line_mask = mask(params.inMask)          # 读取.dat掩膜
      │          mask.setWeights(params)             # 计算谱线权重
      │          mask.filterLines(obs, prof)         # 过滤天空吸收带/覆盖范围外
      ├──── profile = prof(params)                   # 初始化速度空间profile
      │
      │  obs.setInRange(mask, profile)               # 截取观测到掩膜范围
      │
      ├──── lsdFitSigmaClip(obs, mask, profile, params)
      │          buildM() → [MI, MV]                # 构造投影矩阵
      │          buildInvSig2() → S²               # 构造噪声权重
      │          lsdFit() → [specI, specV, specN1]  # Cholesky 求解
      │          sigma clip → obs.sigmaClipI()      # 迭代去除离群点
      │
      ├──── scaleErr() × 3                          # 误差棒缩放
      ├──── zeroProf() × 2                          # 去连续谱偏振 (V, N1)
      ├──── nullTest()                              # 磁场检测统计
      │
      ├──── profile.save(output_profile)            # 输出 .dat
      ├──── saveLSDOut()                            # 输出运行摘要 .txt
      └──── (可选) saveModelSpec()                  # 输出模型谱 .dat
```

---

## CLI 用法

```bash
# 使用默认 LSDConfig.json
python lsd_runner.py

# 手动指定观测文件和输出路径（覆盖配置中的路径）
python lsd_runner.py [observation.s] [output.dat] [-m mask.dat] [-c LSDConfig.json]

# 批量处理（在 LSDConfig.json 里配置 input.spectra）
python lsd_runner.py -c LSDConfig.json
```

---

## 文件格式约定

**观测输入 (`.s`)**：6 列，前两行为头，每行：
```
wavelength(nm)  I/Ic  V/Ic  N1/Ic  N2/Ic  sigma
```
（sigma ≤ 0 的行自动跳过）

**谱线掩膜 (`.dat`)**：6 列，首行为头，每行：
```
wavelength(nm)  element+ion*0.01  depth  excitation_potential  lande_g  use_flag
```

**LSD profile 输出 (`.dat`)**：7 列：
```
vel(km/s)  I/Ic  sigI  V/Ic  sigV  N1/Ic  sigN1
```
（保存时 I 从 1-I 深度格式转回 I/Ic 强度格式）
