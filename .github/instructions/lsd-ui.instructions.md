---
description: "Use when editing LSD_UI Python code, future FastAPI or backend APIs, UI files, config schemas, task runners, or result plotting. Enforces modular architecture, config-driven I/O via LSDConfig.json, and maintainable UI-oriented workflow."
name: "LSD UI Project Rules"
applyTo: ["**/*.py", "**/*.js", "**/*.ts", "**/*.css", "**/*.html", "**/*.json", "**/*.md", "**/*.yml", "**/*.yaml"]
---
# LSD_UI 项目指令

## 项目目标

- 本项目保留 LSDpy 的原始数值逻辑与科学含义，代码以清晰分层架构组织。
- 所有重构都应服务于三个方向：模块清晰、维护方便、便于接入 UI。

## 当前目录结构

### `core/` — 算法核心，严禁依赖 UI / Web 框架

| 文件                        | 放置内容                                                                                                                     |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `lsd_config.py`           | `paramsLSD` 类：参数容器、`_load_from_mapping()`、`_resolve_path()`                                                    |
| `lsd_io.py`               | `classify_spectrum()`、`observation`、`mask`（含 `setWeights`/`filterLines`）、`prof`（含 `save`/`lsdplot`） |
| `lsd_solver.py`           | `buildM()`、`buildInvSig2()`、`lsdFit()`、`getChi2()`、`lsdFitSigmaClip()`、`scaleErr()`、`zeroProf()`         |
| `lsd_report.py`           | `nullTest()`、`saveLSDOut()` 及其他输出报告函数                                                                          |
| `plotting/basic_plots.py` | `plot_lsd_profile()`、`plot_observation_vs_model()`，matplotlib 懒加载                                                   |

### `pipeline/` — 任务编排，调用 `core/`，不含科学计算逻辑

| 文件                | 放置内容                                                                               |
| ------------------- | -------------------------------------------------------------------------------------- |
| `lsd_pipeline.py` | `LSDPipeline` 类及 `run()` 方法：读取→过滤→拟合→缩放→null test→保存的完整流程 |
| `lsd_runner.py`   | `LSDRunner` 类：CLI 参数解析、加载 `LSDConfig.json`、启动 pipeline                 |

### `api/` — Web 接口，仅做请求校验与任务代理

- 路由不得直接承载科学计算；仅调用 `pipeline/` 中的 runner
- 新增路由文件放在 `api/` 下，按功能分文件（如 `api/routes_task.py`、`api/routes_results.py`）

### `frontend/` — 前端四页面模块

- HTML 页面对应单一功能（params / data / task / results），不得混合多种功能
- 共享状态和工具函数放 `common.js`，禁止在各页面 JS 中重复实现
- 全局样式放 `css/app.css`，页面不得内联大段样式
- UI设计参考 .github/instructions/lsd-ui.instructions.md 指导

### `data/` / `masks/` / `results/` — 数据与输出

- **`data/`**：仅放 `.s` 格式观测光谱；按目标对象或观测批次建子目录
- **`masks/`**：仅放 `.dat` 格式谱线掩膜；不得把 mask 文件散落在其他路径
- **`results/`**：每次运行输出到此目录，包含 profile `.dat`、lsdout `.txt`、图像以及实际使用的配置副本

### 根目录 — 仅放入口与配置模板

- `config_loader.py`：`LSDConfig` JSON 加载器，若需扩展配置逻辑在此文件修改
- `LSDConfig.json`：默认配置模板，**不要**把个人路径写死在此文件
- `lsd_runner.py`：仅作为转发入口，不得在根级别文件中添加新科学计算代码

### `tests/` — 测试

- 优先覆盖：配置解析、文件读取、权重计算、矩阵构造、关键数值回归
- 测试文件按模块命名：`test_config.py`、`test_io.py`、`test_solver.py` 等

## 文档体系

`docs/` 目录下各文件对应不同关注点，修改相关代码前应先查阅对应文档：

| 文档                              | 覆盖内容                                                                                            | 何时参考                              |
| --------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------- |
| `docs/architecture.md`          | 目录结构、分层职责、配置系统、数据流、CLI 用法、文件格式约定                                        | 新增模块/文件、调整目录、修改数据流时 |
| `docs/algorithm.md`             | 输入分类、矩阵构造（`buildM`）、噪声权重（`buildInvSig2`）、正则方程（`lsdFit`）、σ-clipping | 修改或理解核心求解器时                |
| `docs/physics.md`               | LSD 物理假设、Stokes 参数含义、掩膜格式、谱线权重公式、饱和校正、地球大气过滤、磁场检测统计         | 涉及权重公式、检测判据或物理量定义时  |
| `docs/weighting_modes.md`       | 8 种权重模式说明、模式 7（固定阈值二值化）配置与调参                                                | 新增/修改权重模式或配置字段时         |
| `docs/frontend_architecture.md` | 前端四页面职责、JS 模块分工、`localStorage` 状态模型、任务数据流                                  | 修改前端页面或 JS 逻辑时              |

**文档维护规则**：

- 新增或修改算法步骤，同步更新 `docs/algorithm.md`。
- 新增权重模式，同步更新 `docs/weighting_modes.md` 的模式表与"何时使用"建议。
- 调整目录约定、CLI 用法或配置字段，同步更新 `docs/architecture.md`。
- 前端页面新增功能或改变数据流，同步更新 `docs/frontend_architecture.md`。
- 不要在文档中写死绝对路径；所有路径示例使用相对于项目根目录的相对路径。

## 配置与输入输出

### 配置入口

唯一配置来源为 `LSDConfig.json`，通过 `LSDConfig.load()` 加载并生成 `paramsLSD` 对象，命令行传入的参数优先于配置文件中的值。

### JSON 配置字段映射

`LSDConfig.json` 的顶层键映射到 `paramsLSD` 属性：

| JSON 路径                                    | `paramsLSD` 属性       | 含义                                             |
| -------------------------------------------- | ------------------------ | ------------------------------------------------ |
| `input.observation`                        | `inObs`                | 观测光谱文件路径（`.s`）                       |
| `input.mask`                               | `inMask`               | 谱线掩膜文件路径（`.dat`）                     |
| `profile.vel_start_kms`                    | `velStart`             | profile 速度起点 (km/s)                          |
| `profile.vel_end_kms`                      | `velEnd`               | profile 速度终点 (km/s)                          |
| `profile.pixel_velocity_kms`               | `pixVel`               | 速度像素大小 (km/s)                              |
| `normalization.depth`                      | `normDepth`            | 归一化谱线深度                                   |
| `normalization.lande`                      | `normLande`            | 归一化 Landé g 因子                             |
| `normalization.wavelength_nm`              | `normWave`             | 归一化波长 (nm)                                  |
| `normalization.weighting_mode`             | `weightingMode`        | 权重模式（0–7，见 `docs/weighting_modes.md`） |
| `processing.remove_continuum_polarization` | `removeContPol`        | 是否去除连续谱偏振（0/1）                        |
| `processing.sigma_clip.limit`              | `sigmaClip`            | σ-clipping 阈值                                 |
| `processing.sigma_clip.iterations`         | `sigmaClipIter`        | σ-clipping 迭代次数                             |
| `processing.interp_mode`                   | `interpMode`           | 插值模式（0=最近邻，1=线性）                     |
| `output.profile`                           | `outProf`              | 输出 profile 文件路径                            |
| `output.save_model_spectrum`               | `fSaveModelSpec`       | 是否保存模型谱（0/1）                            |
| `output.model_spectrum`                    | `outModelSpec`         | 模型谱输出路径                                   |
| `output.plot_profile`                      | `fLSDPlotImg`          | 是否显示/保存 profile 图（0/1）                  |
| `output.save_plot`                         | `fSavePlot`            | 是否把图保存为文件（0/1）                        |
| `output.plot_image`                        | `outPlotImg`           | profile 图输出路径                               |
| `output.save_lsdout`                       | `fSaveLSDOut`          | 是否保存运行摘要（0/1）                          |
| `output.lsdout`                            | `outLSDOut`            | 摘要文件路径（`"auto"` 自动生成）              |
| `model_options.saturation_correction`      | `saturationCorrection` | 饱和校正开关（0/1）                              |
| `model_options.telluric_filtering`         | `telluricFiltering`    | 地球大气带过滤开关（0/1）                        |
| `model_options.line_filtering`             | `lineFiltering`        | 谱线覆盖过滤开关（0/1）                          |

### 路径规则

- 所有文件路径相对于项目根目录解析（由 `paramsLSD._resolve_path()` 处理），**不得**写死绝对路径。
- 默认约定：输入来自 `data/`（`.s`）与 `masks/`（`.dat`），输出落到 `results/`。
- `output.lsdout` 设为 `"auto"` 时，自动在 `results/` 下生成带时间戳或文件名的摘要文件。

### 新增配置字段规则

新增字段时必须同步更新以下四处，缺一不可：

1. `LSDConfig.json` — 添加带默认值的示例字段
2. `config_loader.py` — `LSDConfig` 加载与验证逻辑
3. `core/lsd_config.py` — `paramsLSD` 属性与 `_load_from_mapping()` 映射
4. `docs/architecture.md` — 配置字段映射表

如果该字段在前端可编辑，还需同步更新对应 `frontend/params.html` 表单与 `frontend/js/params.js`。

## 运行与任务编排

- UI 驱动的 LSD 运行应通过专门的 pipeline 或 runner 类执行。
- 长时间运行任务必须支持状态查询，最好支持日志回调；如果引入 WebUI，还应考虑取消运行或避免并发冲突。
- 不要让前端或 API 直接操作算法内部对象；通过明确的数据结构传递参数和结果。

## 代码风格

### Python 命名

| 类型               | 约定           | 示例                                          |
| ------------------ | -------------- | --------------------------------------------- |
| 领域数据对象（类） | 小写，无下划线 | `observation`、`mask`、`prof`           |
| 编排 / 接口类      | UpperCamelCase | `LSDPipeline`、`LSDRunner`、`LSDConfig` |
| 函数（核心算法）   | lowerCamelCase | `buildM()`、`lsdFit()`、`getChi2()`     |
| 函数（普通工具）   | snake_case     | `classify_spectrum()`、`save_lsdout()`    |
| 模块级物理常量     | 短名、小写     | `c = scipy.constants.c * 1e-3`              |
| 私有方法           | 单下划线前缀   | `_resolve_path()`、`_load_from_mapping()` |
| 内部模块常量       | 大写下划线     | `_LSD_TYPES = {...}`                        |

### Python 语法与结构

- **不加类型注解**：核心算法文件维持现有无注解风格；新增公共函数允许在 docstring 中说明参数类型，但不得在函数签名中加 `->` 返回类型或参数类型注解，以保持与基线代码一致。
- **if 条件括号**：与现有代码一致，保留 `if (condition):` 括号写法；不要在重构时批量删除括号。
- **行内注释**：使用 `#` 直接跟注释，重要算法步骤引用文档位置，例如 `# see docs/algorithm.md §4`。
- **Docstring**：新增公共函数（尤其工具函数）至少写一行 docstring；现有无 docstring 的算法函数不必补写，除非对外暴露接口。
- **布尔条件不换行**：保持 `and`/`or` 条件在同一行或将运算符置于行尾，避免在运算符前换行（参见 linter 配置限制）。

### numpy / scipy

- **向量化优先**：有现成 numpy 广播或向量化写法时，不要用纯 Python 循环替代；但不要为了向量化引入难以理解的代码。
- **稀疏矩阵**：对角矩阵用 `scipy.sparse.diags()`，不要用 `np.diag`（内存开销大）。
- **求解器**：线性方程组优先用 `scipy.linalg.cho_factor` + `cho_solve`（已验证数值稳定），不得替换为其他求解器，除非有数值测试做支撑。
- **防零除**：对用作分母的数组，用 `np.maximum(arr, small_value)` 裁底，不要直接除。

### 懒加载

- `matplotlib` 及其子模块**仅在函数体内导入**，不允许在模块顶层 `import matplotlib`，以避免无显示环境导入失败：
  ```python
  def plot_lsd_profile(...):
      import matplotlib.pyplot as plt
      ...
  ```

### JavaScript（前端）

- 共享工具函数放 `common.js`，通过 `window.LSDUI` 暴露；页面 JS 不得重复实现。
- 状态持久化使用 `localStorage`，键名统一加版本后缀（如 `lsd_ui_config_v1`）。
- 不使用 ES 模块 `import/export`（当前无打包工具），通过全局命名空间共享。
- SVG 绘图逻辑放 `results.js`，不得内联到 HTML。

## 验证要求

- 任何算法重构后，至少验证语法正确和基本导入可用。
- 一旦建立测试基线，优先添加数值回归测试，确保重构前后关键输出一致或差异可解释。
- 如果同时修改算法层和 UI 层，先确认算法接口稳定，再接入界面。
