# LSD 权重模式指南

## 概述

LSD 使用权重来控制不同掩膜谱线对反演的贡献。Python 版本支持 **8 种权重模式**（模式 0-7），包括新增的**模式 7**（固定阈值二值化），旨在处理高噪声光谱。

---

## 权重模式详解

### 模式 0: `g` — 仅 Landé g 因子
```
weight_V = (g_i) / norm_g
```
- 基于 Zeeman 灵敏度
- 用于纯 Zeeman 敏感
- 不考虑线深度

### 模式 1: `prof*g` — 线深度 × g 因子
```
weight_V = (depth_i × g_i) / (norm_depth × norm_g)
```
- 结合线轮廓强度和 Zeeman 灵敏度
- 平衡两个物理量

### 模式 2 (默认): `lam*prof*g` — 波长 × 线深度 × g 因子
```
weight_V = (wavelength_i × depth_i × g_i) / (norm_wavelength × norm_depth × norm_g)
```
- 最全面的权重方案
- 考虑波长相关的仪器灵敏度

### 模式 3: `prof` — 仅线深度
```
weight_V = depth_i / norm_depth
```
- 简单线强度权重

### 模式 4: `lam*prof` — 波长 × 线深度
```
weight_V = (wavelength_i × depth_i) / (norm_wavelength × norm_depth)
```
- 强度与波长依赖性

### 模式 5: `1` — 统一权重
```
weight_V = 1.0
```
- 所有线等权
- 用于对比测试

### 模式 6: `prof*(lam*g)²` — 线深度 × (波长 × g)²
```
weight_V = depth_i × (wavelength_i × g_i)² / [norm_depth × (norm_wavelength × norm_g)²]
```
- 强调 Zeeman 和波长的二阶效应
- 用于高磁场星体

### 模式 7: `fixed_threshold` — 固定阈值二值化（**新增**）
```
if (depth_i / norm_depth) < threshold:
    weight = weight_low (default: 0.1)
else:
    weight = weight_high (default: 10.0)
```
- **目的**：处理高噪声光谱
- **风格**：C 版本的二值化策略
- **优势**：
  - 对观测误差估计（σ）不敏感
  - 防止过拟合
  - 鲁棒性强
- **劣势**：
  - 可能过度降权深线
  - 需要手动选择阈值和权重值

---

## 使用模式 7 的配置

在 `LSDConfig.json` 中添加：

```json
{
  "normalization": {
    "depth": 0.7,
    "lande": 1.2,
    "wavelength_nm": 500.0,
    "weighting_mode": 7,
    "weighting_threshold": 0.5,
    "weighting_low_value": 0.1,
    "weighting_high_value": 10.0
  }
}
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `weighting_mode` | 2 | 权重模式（7 为二值化） |
| `weighting_threshold` | 0.5 | 归一化深度阈值（0-1）|
| `weighting_low_value` | 0.1 | 低权重值（深线） |
| `weighting_high_value` | 10.0 | 高权重值（浅线） |

---

## 何时使用各模式

### 推荐选择

| 数据特征 | 推荐模式 | 理由 |
|---------|---------|------|
| 高质量、高 S/N | 2 (默认) | 最全面 |
| 低 S/N、高噪声 | **7** | 鲁棒、防过拟合 |
| 强磁场星体 | 6 或 2 | 强调 Zeeman 效应 |
| 对比测试 | 5 | 无权重差异 |
| 快速检查 | 3 或 5 | 简化权重 |

---

## 模式 7 的调参建议

### 情况 1：数据噪声中等（S/N ~ 500-1000）
```json
"weighting_mode": 7,
"weighting_threshold": 0.5,
"weighting_low_value": 0.2,
"weighting_high_value": 5.0
```
→ 权重比例减小为 25:1，保留更多深线信息

### 情况 2：数据噪声很大（S/N < 200）
```json
"weighting_mode": 7,
"weighting_threshold": 0.3,
"weighting_low_value": 0.05,
"weighting_high_value": 20.0
```
→ 更激进的差异化，强制大幅降权深线

### 情况 3：深线较多且可信（强磁场星体）
```json
"weighting_mode": 7,
"weighting_threshold": 0.7,
"weighting_low_value": 0.5,
"weighting_high_value": 2.0
```
→ 阈值提高，权重差异减小，保留深线信息

---

## 与 C 版本的对比

| 特性 | C 版本 | Python 模式 7 |
|------|-------|-------------|
| 权重方案 | 硬阈值二值化 | 灵活阈值二值化 |
| 权重值 | 固定 0.1/10.0 | 可配置 |
| 阈值 | 固定 `cut` | 可配置 `weighting_threshold` |
| 自动调整 | 否 | 可在配置中调整 |

---

## 性能对比

基于 C 版本原型的测试：

**C 版本（固定权重，cut=0.5）与 Python 模式 7 等效时**：
- 权重比例：10000:1（100 vs 0.01 在归一化后）
- 深线被压制 99%
- 适合低 S/N（< 100）

**Python 模式 7 推荐配置**：
```json
{
  "weighting_threshold": 0.5,
  "weighting_low_value": 0.1,
  "weighting_high_value": 10.0
}
```
→ 权重比例：10000:1（与 C 版本相同）→ 适合 S/N 50-500 范围

---

## 示例：高噪声数据处理

```json
{
  "input": {
    "observation": "data/high_noise_spectrum.s",
    "mask": "masks/standard_mask.dat"
  },
  "profile": {
    "vel_start_kms": -200.0,
    "vel_end_kms": 200.0,
    "pixel_velocity_kms": 1.8
  },
  "normalization": {
    "depth": 0.7,
    "lande": 1.2,
    "wavelength_nm": 500.0,
    "weighting_mode": 7,
    "weighting_threshold": 0.5,
    "weighting_low_value": 0.1,
    "weighting_high_value": 10.0
  },
  "processing": {
    "remove_continuum_polarization": 1,
    "interp_mode": 1,
    "sigma_clip": {
      "limit": 500.0,
      "iterations": 2
    }
  },
  "output": {
    "save_lsdout": 1,
    "lsdout": "auto"
  }
}
```

配合 `sigma_clip` 的多次迭代以进一步降噪。

---

## 参考

- 算法文档：[docs/algorithm.md](algorithm.md)
- 物理模型：[docs/physics.md](physics.md)
- C 版本对应：`/Users/tianqi/Documents/Codes_collection/ZDI_and/LSDgen/lsd/lsd/lsfit.c`
