# LSD_UI

基于最小二乘反卷积（Least Squares Deconvolution，LSD）算法的恒星光谱分析工具。从多条谱线中提取高信噪比的平均 Stokes I / V / N 轮廓，用于径向速度测量与恒星磁场检测。

提供两种使用方式：

- **Web UI**（推荐）：浏览器图形界面，通过 `app.py` 启动 FastAPI 后端 + 静态前端
- **命令行**：JSON 配置驱动，通过 `lsd_runner.py` 直接运行

---

## 项目结构

```
LSD_UI/
│
├── app.py                  # FastAPI 服务入口（Web UI + REST API）
├── launch_ui.py            # 启动器（端口规范化后转发给 app.py）
├── launch_ui.sh            # macOS / Linux Shell 启动脚本
├── lsd_runner.py           # 命令行快捷入口（转发到 pipeline/lsd_runner.py）
├── config_loader.py        # LSDConfig JSON 加载器
├── LSDConfig.json          # 默认配置模板
├── requirements.txt        # Python 依赖
│
├── core/                   # 算法核心层（不依赖 Web 框架）
│   ├── lsd_config.py       #   paramsLSD 参数容器与路径解析
│   ├── lsd_io.py           #   观测（observation）、掩膜（mask）、剖面（prof）读写
│   ├── lsd_solver.py       #   LSD 矩阵构造（buildM）、求解（lsdFit）、σ-clipping
│   ├── lsd_report.py       #   Null 检验（nullTest）与 lsdout 诊断报告
│   ├── lsd_analysis.py     #   剖面统计分析、RV 拟合、磁场测量
│   └── plotting/           #   可视化
│       ├── basic_plots.py  #     LSD 三面板绘图（Stokes V / N1 / I + 误差）
│       └── spectrum_plots.py #   观测光谱 + mask 交互式 Plotly 图
│
├── pipeline/               # 任务编排层（调用 core/，不含科学计算）
│   ├── lsd_pipeline.py     #   LSDPipeline.run()：读取→过滤→拟合→缩放→null test→保存
│   └── lsd_runner.py       #   命令行参数解析、加载配置、启动 pipeline
│
├── api/                    # Web API 路由
│   └── routes_analysis.py  #   POST /api/analysis — 剖面分析与磁场检测
│
├── frontend/               # Web UI 前端（四页面模块化架构）
│   ├── index.html          #   导航入口
│   ├── params.html         #   参数配置（profile / normalization / processing / output）
│   ├── data.html           #   光谱与掩膜路径管理
│   ├── task.html           #   LSD 任务启动 / 日志 / 轮询（Mock + API 双模式）
│   ├── results.html        #   结果可视化（三面板 LSD profile + 检测统计）
│   ├── spectrum_view.html  #   光谱 + mask 交互式查看器
│   ├── css/app.css         #   全局样式表
│   └── js/
│       ├── common.js       #     共享状态 window.LSDUI、localStorage 读写
│       ├── config.js       #     配置同步工具
│       ├── params.js       #     参数页逻辑
│       ├── data.js         #     数据页逻辑
│       ├── task.js         #     任务页逻辑（含 mock profile 生成）
│       └── results.js      #     结果页：三面板 SVG 绘图（V / N / I + 不确定度）
│
├── data/                   # 观测输入数据（.s 格式 Stokes IVNU 列式文件）
├── masks/                  # 谱线掩膜（.dat 格式：波长 / 深度 / Landé 因子）
├── results/                # 运行输出（profile .dat、lsdout .txt、图像）
├── tests/                  # 测试（配置解析、权重计算、数值回归）
└── docs/                   # 技术文档
    ├── architecture.md     #   目录结构、分层职责、配置系统
    ├── algorithm.md        #   矩阵构造、噪声权重、正则方程、σ-clipping
    ├── physics.md          #   LSD 物理假设、Stokes 参数、检测统计
    ├── weighting_modes.md  #   8 种权重模式说明与调参指南
    └── frontend_architecture.md  # 前端四页面数据流与状态模型
```

### 分层架构

```
┌─────────────┐     ┌──────────────────┐
│  frontend/  │────→│  app.py (API)    │
│  浏览器 UI   │     │  FastAPI 服务     │
└─────────────┘     └───────┬──────────┘
                            │
                   ┌────────▼─────────┐
                   │    pipeline/     │
                   │  任务编排 / CLI   │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │      core/       │
                   │  算法 / IO / 绘图  │
                   └──────────────────┘
```

---

## 快速开始

### 1. 环境准备

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 准备输入文件

- **观测光谱**：放入 `data/`，格式为 Stokes IVNU 列式 `.s` 文件
- **谱线掩膜**：放入 `masks/`，格式为波长/深度/Landé 因子 `.dat` 文件

### 3. 启动 Web UI（推荐）

```bash
python app.py            # 自动选端口，自动打开浏览器
python app.py --port 8080
```

浏览器打开后，四个标签页对应完整工作流：

| 标签页 | 功能 |
|--------|------|
| **Parameters** | 编辑 LSD 参数（profile / normalization / processing / output） |
| **Spectrum & Mask** | 选择观测光谱和掩膜文件，浏览服务器上的可用文件 |
| **LSD Task** | 验证配置、启动 LSD 任务、查看实时日志（Mock / API 双模式） |
| **Result Plot** | 渲染 Stokes I / V / N 三面板 LSD profile（含不确定度），查看检测统计 |

API 文档：`http://127.0.0.1:<port>/api/docs`

### 4. 命令行运行

```bash
python lsd_runner.py                          # 使用 LSDConfig.json 默认配置
python lsd_runner.py data/obs.s results/p.dat # 指定观测和输出路径
python lsd_runner.py -m masks/mask.dat        # 指定掩膜
python lsd_runner.py -m masks/my_mask.dat
python lsd_runner.py -c MyConfig.json  # 自定义配置
```

### 批量处理

当 `input.spectra` 为列表时，逐条执行 LSD，每条输出同名 `.lsd`：

```json
{
  "input": {
    "mask": "masks/shared_mask.dat",
    "spectra": [
      "data/night1_obs1.s",
      { "observation": "data/night1_obs2.s", "mask": "masks/custom.dat" }
    ]
  }
}
```

---

## 配置文件（LSDConfig.json）

顶层结构：`input` / `profile` / `normalization` / `processing` / `output` / `model_options`

### `input` — 输入路径

| 字段 | 类型 | 说明 |
|------|------|------|
| `observation` | string | 观测光谱 `.s` 文件（相对路径） |
| `mask` | string | 谱线掩膜 `.dat` 文件 |
| `spectra` | array | 批量模式条目（字符串或 `{observation, mask}` 对象） |

### `profile` — 剖面参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `vel_start_kms` | float | 速度轴起点 (km/s)，如 `-200.0` |
| `vel_end_kms` | float | 速度轴终点 (km/s)，如 `200.0` |
| `pixel_velocity_kms` | float | 像素步长 (km/s)，如 `1.8` |

### `normalization` — 归一化

| 字段 | 类型 | 说明 |
|------|------|------|
| `depth` | float | 参考谱线深度 (0–1) |
| `lande` | float | 参考 Landé 因子 |
| `wavelength_nm` | float | 参考波长 (nm) |
| `weighting_mode` | int | 权重模式（0–6），默认 `2`（λ × d × g） |

### `processing` — 处理选项

| 字段 | 说明 |
|------|------|
| `remove_continuum_polarization` | 移除连续偏振基线 (0/1) |
| `interp_mode` | 插值模式 (1=线性) |
| `sigma_clip.limit` | σ-clipping 阈值 |
| `sigma_clip.iterations` | 迭代次数 |

### `output` — 输出

| 字段 | 说明 |
|------|------|
| `profile` | LSD 剖面输出路径 `.dat` |
| `save_model_spectrum` / `model_spectrum` | 模型重建光谱 |
| `plot_profile` / `save_plot` / `plot_image` | 绘图控制 |
| `save_lsdout` / `lsdout` | 诊断文件 (`"auto"` 自动命名) |

### `model_options` — 模型选项

| 字段 | 说明 |
|------|------|
| `saturation_correction` | 饱和线修正 (0/1) |
| `telluric_filtering` | 大气吸收过滤 (0/1) |
| `line_filtering` | 谱线质量过滤 (0/1) |

---

## 输出文件格式

### LSD 剖面（`.dat`）

```
***Reduced spectrum of 'STAR    '
 <npix> 6
 vel(km/s)  I/Ic  sigI  V/Ic  sigV  N1/Ic  sigN1
 ...
```

7 列：速度、Stokes I 归一化强度及误差、Stokes V 及误差、Null N1 及误差。

### lsdout 诊断文件（`_lsdout.txt`）

运行统计：掩膜统计、各 Stokes 通道 χ² 值、误差缩放因子、Null 检验结果。

---

## REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/config` | 读取 LSDConfig.json |
| `PUT` | `/api/config` | 写入配置 |
| `POST` | `/api/tasks` | 创建 LSD 任务 |
| `GET` | `/api/tasks/{id}` | 查询任务状态与日志 |
| `POST` | `/api/tasks/{id}/cancel` | 取消任务 |
| `GET` | `/api/profile/data?path=results/prof.dat` | 读取剖面数据（JSON） |
| `POST` | `/api/analysis` | 剖面分析（RV、磁场、检测统计） |
| `GET` | `/api/files/{data,masks,results}` | 列出文件 |
| `GET` | `/api/plot/spectrum` | 交互式光谱 + mask 图 |

完整 Swagger 文档：`/api/docs`

---

## 命令行参数

```
python lsd_runner.py [observation] [output] [-m MASK] [-c CONFIG] [--legacy-config INLSD]
```

---

## 注意事项

- 所有路径相对于 `LSDConfig.json` 所在目录解析
- `weighting_mode` 影响剖面幅度定义；同一目标不同观测应保持一致
- `pixel_velocity_kms` 建议为光谱速度分辨率的 0.5–1 倍
- 每次运行在 `results/` 下生成独立输出；建议不同观测使用不同输出路径
