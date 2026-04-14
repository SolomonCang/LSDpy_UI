# LSD_UI

基于最小二乘反卷积（Least Squares Deconvolution，LSD）算法的光谱分析工具，支持 JSON 配置驱动的命令行运行方式。

---

## 目录结构

```
LSD_UI/
├── LSDConfig.json          # 主配置文件（运行前必须编辑）
├── lsd_runner.py           # 命令行入口（顶层快捷脚本）
├── config_loader.py        # 配置加载器
├── core/                   # 核心层：配置定义、IO、求解器、绘图
│   ├── lsd_config.py       # paramsLSD 参数对象与权重模式定义
│   ├── lsd_io.py           # 观测数据、掩膜、剖面的读写
│   ├── lsd_solver.py       # LSD 矩阵构造与求解
│   ├── lsd_report.py       # Null 检验与统计报告
│   └── plotting/           # 可视化模块
├── pipeline/               # 任务编排层
│   ├── lsd_pipeline.py     # 单次 LSD 运行流程
│   └── lsd_runner.py       # 命令行参数解析与任务启动
├── data/                   # 观测输入数据（.s 格式）
├── masks/                  # 线掩膜文件（.dat 格式）
├── results/                # 输出结果目录
└── tests/                  # 单元测试
```

---

## 快速开始

### 1. 环境准备

推荐使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # 如存在
```

### 2. 准备输入文件

- **观测光谱**：放入 `data/` 目录，格式为 Stokes IVNU 列式 `.s` 文件。
- **线掩膜**：放入 `masks/` 目录，格式为波长/谱线深度/Landé 因子列式 `.dat` 文件。

### 3. 编辑配置文件

打开 `LSDConfig.json`，按实际路径和参数需求修改各字段（详见下方参数说明）。

### 4. 运行

```bash
# 使用默认 LSDConfig.json
python lsd_runner.py

# 手动指定观测文件和输出路径（覆盖配置中的路径）
python lsd_runner.py data/my_obs.s results/my_profile.dat

# 手动指定掩膜文件
python lsd_runner.py -m masks/my_mask.dat

# 指定自定义配置文件路径
python lsd_runner.py -c /path/to/MyConfig.json

# 批量处理（在 LSDConfig.json 里配置 input.spectra）
python lsd_runner.py -c LSDConfig.json
```

### 批量光谱处理（新增）

当 `input.spectra` 存在且为列表时，程序会按顺序对每个条目执行一次 LSD。

- 支持共用 mask：条目写成字符串（仅 observation），mask 使用 `input.mask`
- 支持独立 mask：条目写成对象，包含 `observation` 和可选 `mask`
- 每个任务的 LSD 主输出固定为观测文件同目录、同名 `.lsd`

示例：

```json
{
  "input": {
    "mask": "masks/shared_mask.dat",
    "spectra": [
      "data/night1_obs1.s",
      {
        "observation": "data/night1_obs2.s",
        "mask": "masks/custom_obs2.dat"
      }
    ]
  }
}
```

---

## 配置文件详解（LSDConfig.json）

```json
{
  "input": { ... },
  "profile": { ... },
  "normalization": { ... },
  "processing": { ... },
  "output": { ... },
  "model_options": { ... }
}
```

---

### `input` — 输入文件路径

| 字段 | 类型 | 说明 |
|------|------|------|
| `observation` | string | 观测光谱文件路径，支持相对路径（相对于配置文件所在目录）。格式为多列文本，包含波长、Stokes I/V/N/U 及误差。示例：`"data/obs.s"` |
| `mask` | string | 线掩膜文件路径。每行包含谱线中心波长（nm）、谱线深度、Landé 因子三列。示例：`"masks/mask.dat"` |
| `spectra` | array | 批量模式条目列表。每个条目可为字符串（仅 observation，复用 `input.mask`）或对象（`observation` + 可选 `mask`）。启用后将逐条运行并为每条观测生成同目录 `.lsd` 文件。 |

---

### `profile` — LSD 剖面参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `vel_start_kms` | float | 剖面速度轴起点（km/s）。通常取负值，代表蓝移端。示例：`-200.0` |
| `vel_end_kms` | float | 剖面速度轴终点（km/s）。须大于 `vel_start_kms`。示例：`200.0` |
| `pixel_velocity_kms` | float | 剖面每像素速度步长（km/s）。应与观测光谱速度分辨率匹配，过小会导致欠约束，过大会导致欠采样。示例：`1.8` |

---

### `normalization` — 归一化参考参数

这三个参数定义"参考谱线"，用于对全部谱线的权重在量纲上进行归一化，使 LSD 剖面拥有物理上可解释的幅度。

| 字段 | 类型 | 说明 |
|------|------|------|
| `depth` | float | 参考谱线深度（归一化连续谱 = 1 时的线深，范围 0–1）。示例：`0.7` |
| `lande` | float | 参考谱线有效 Landé 因子。对磁场敏感的谱线典型值约为 1.0–1.5。示例：`1.2` |
| `wavelength_nm` | float | 参考谱线中心波长（nm）。示例：`500.0` |
| `weighting_mode` | int | 权重方案，控制各谱线对 LSD 剖面的贡献权重。详见下表。默认：`2` |

#### `weighting_mode` 选项

| 值 | 权重公式 | 说明 |
|----|----------|------|
| `0` | `g` | 仅用 Landé 因子作权重 |
| `1` | `prof × g` | 谱线深度 × Landé 因子 |
| `2` | `λ × prof × g` | 波长 × 谱线深度 × Landé 因子（**推荐默认**，物理上最完整） |
| `3` | `prof` | 仅使用谱线深度 |
| `4` | `λ × prof` | 波长 × 谱线深度 |
| `5` | `1` | 所有谱线等权重 |
| `6` | `prof × (λ × g)²` | 谱线深度 × (波长 × Landé 因子)² |

---

### `processing` — 数据处理选项

| 字段 | 类型 | 说明 |
|------|------|------|
| `remove_continuum_polarization` | int | 是否移除连续偏振基线。`1` = 是（推荐），`0` = 否。用于消除仪器或大气引入的宽带偏振残差。 |
| `interp_mode` | int | 谱线插值模式。`1` = 线性插值（推荐）；其他值对应不同插值方案。 |

#### `sigma_clip` — sigma 截断迭代参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `limit` | float | sigma 截断阈值（单位：sigma 倍数）。超出该倍数残差的像素将被排除在拟合之外。`500.0` 等效于不做截断。示例：`3.0`（截断 3σ 以外的异常点） |
| `iterations` | int | sigma 截断迭代次数。`0` = 不迭代（仅做一次拟合）；增大该值可逐步排除坏像素，但会增加计算时间。 |

---

### `output` — 输出文件设置

| 字段 | 类型 | 说明 |
|------|------|------|
| `profile` | string | LSD 剖面输出路径（`.dat` 格式）。包含速度轴、Stokes I/V/N1 及各自误差。示例：`"results/prof.dat"` |
| `save_model_spectrum` | int | 是否保存模型重建光谱。`1` = 保存，`0` = 不保存。 |
| `model_spectrum` | string | 模型光谱输出路径（仅 `save_model_spectrum = 1` 时生效）。示例：`"results/outModelSpec.dat"` |
| `plot_profile` | int | 是否在运行后显示剖面图窗口。`1` = 显示，`0` = 不显示。 |
| `save_plot` | int | 是否将剖面图保存为文件。`1` = 保存，`0` = 不保存。 |
| `plot_image` | string | 剖面图输出路径（仅 `save_plot = 1` 时生效）。示例：`"results/prof.png"` |
| `save_lsdout` | int | 是否保存详细 lsdout 诊断文件（包含 chi² 统计、各通道误差缩放信息等）。`1` = 保存，`0` = 不保存。 |
| `lsdout` | string | lsdout 文件输出路径。`"auto"` 表示自动使用剖面路径并替换扩展名为 `_lsdout.txt`。 |

---

### `model_options` — 模型处理选项

| 字段 | 类型 | 说明 |
|------|------|------|
| `saturation_correction` | int | 是否启用饱和线修正。`1` = 启用，`0` = 禁用。对强线（等值宽度较大）进行非线性修正，提高 LSD 精度。 |
| `telluric_filtering` | int | 是否过滤大气痕迹（telluric）谱线。`1` = 启用，`0` = 禁用。排除受大气吸收污染的掩膜谱线。 |
| `line_filtering` | int | 是否启用谱线质量过滤。`1` = 启用，`0` = 禁用。自动过滤超出观测范围或深度异常的谱线。 |

---

## 输出文件说明

### LSD 剖面文件（`results/prof.dat`）

多列文本，每行一个速度点，列顺序为：

```
velocity(km/s)  StokesI  sigI  StokesV  sigV  StokesN1  sigN1  StokesN2  sigN2
```

### lsdout 诊断文件（`results/prof_lsdout.txt`）

包含完整运行统计信息：掩膜统计、各 Stokes 通道 chi² 值、误差缩放因子、Null 检验结果等，用于评估 LSD 拟合质量。

### 模型重建光谱（`results/outModelSpec.dat`）

由 LSD 剖面反卷积重建的合成光谱，可与原始观测光谱对比验证拟合效果。

---

## 命令行参数参考

```
python lsd_runner.py [observation] [output] [-m MASK] [-c CONFIG] [--legacy-config INLSD]
```

| 参数 | 说明 |
|------|------|
| `observation`（可选位置参数） | 观测光谱文件路径，覆盖配置文件中的 `input.observation` |
| `output`（可选位置参数） | 输出剖面路径，覆盖配置文件中的 `output.profile` |
| `-m` / `--mask` | 掩膜文件路径，覆盖配置文件中的 `input.mask` |
| `-c` / `--config` | JSON 配置文件路径，默认为 `LSDConfig.json` |
| `--legacy-config` | 旧版 `inlsd.dat` 格式配置文件路径（兼容模式） |

---

## 典型配置示例

```json
{
  "input": {
    "observation": "data/hd219134_19jun16_v_01.s",
    "mask": "masks/atomic_6300_depth0.1_geff0.0.dat"
  },
  "profile": {
    "vel_start_kms": -150.0,
    "vel_end_kms": 150.0,
    "pixel_velocity_kms": 1.8
  },
  "normalization": {
    "depth": 0.7,
    "lande": 1.2,
    "wavelength_nm": 500.0,
    "weighting_mode": 2
  },
  "processing": {
    "remove_continuum_polarization": 1,
    "interp_mode": 1,
    "sigma_clip": {
      "limit": 3.0,
      "iterations": 5
    }
  },
  "output": {
    "profile": "results/hd219134_prof.dat",
    "save_model_spectrum": 0,
    "model_spectrum": "results/outModelSpec.dat",
    "plot_profile": 0,
    "save_plot": 0,
    "plot_image": "results/hd219134_prof.png",
    "save_lsdout": 1,
    "lsdout": "auto"
  },
  "model_options": {
    "saturation_correction": 1,
    "telluric_filtering": 1,
    "line_filtering": 1
  }
}
```

---

## 注意事项

- 路径均支持相对路径，相对于 `LSDConfig.json` 所在目录解析。
- `weighting_mode` 改变后，LSD 剖面的幅度定义会发生变化；同一恒星不同观测的比较应保持该参数一致。
- `pixel_velocity_kms` 建议设为观测光谱速度分辨率的 0.5–1 倍；过小（欠约束）或过大（欠采样）均会触发运行时警告。
- 每次运行会在 `results/` 下生成独立输出文件；建议为不同观测指定不同的输出路径以避免覆盖。
