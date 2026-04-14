# LSD 算法文档

## 0. 输入光谱分类与检查

用户提供的输入文件可能是多种格式之一。为防止误用（如将 LSD profile 作为输入重复运行），`observation.__init__()` 调用 `classify_spectrum(fname)` 自动分类。

### 分类规则

函数 `classify_spectrum()` 从文件中读取前几行数据，按以下规则判别：

1. **过滤注释行**：跳过 `*` 开头的行
2. **跳过元数据行**：通常第一个有效数据行为 2 列的元数据 `nLines stokes_code`
3. **按列数硬判别**：
   - 15 列 → `spec_harps`（暂不支持）
   - 6 列 → `spec_pol`（完整 Stokes：I, V, N1, N2）
   - 7 列 → `lsd_pol`（**已处理的 LSD profile**）
4. **对 2–3 列根据第一列范围判别**：
   - 若 `200 ≤ col1 ≤ 5000` nm → 波长坐标
     - 3 列 → `spec_i`；2 列 → `spec_i_simple`
   - 若 `col1 < 0` 或 `col1 < 200 && |col1| ≤ 10000` → 速度坐标  
     - 3 列 → `lsd_i`（**已处理的 LSD**）
     - 2 列 → `lsd_i_simple`（**已处理的 LSD**）

### 异常处理

若 `observation.__init__()` 检测到 LSD 类型（`lsd_pol`/`lsd_i`/`lsd_i_simple`），立即打印错误并退出：

```
ERROR: input file "..." is already an LSD profile (detected type: lsd_pol).
LSD cannot be run on an existing LSD profile. Please provide a raw spectrum.
```

这防止用户误将 LSD profile 作为输入重复处理。HARPS 15 列格式也被拒绝，需转换为 6 列。

---

## 1. 问题建模

LSD 将恒星光谱建模为谱线掩膜 M 与平均线轮廓 Z 的矩阵乘积：

$$Y = M \cdot Z$$

- $Y$：观测向量，长度 $n$（观测波长像素数）
- $Z$：待求的平均 LSD profile，长度 $m$（速度像素数）
- $M$：投影矩阵，形状 $n \times m$，将每条掩膜谱线的权重映射到观测像素

对 Stokes I 和 Stokes V/N1 分别建立独立的矩阵 $M_I$ 和 $M_V$。

---

## 2. 速度像素定义

Profile 的速度轴由下式生成：

$$v_j = v_{\rm start} + j \cdot \Delta v, \quad j = 0, 1, \ldots, m-1$$

每个速度像素对应谱线 $l$（中心波长 $\lambda_l$）的观测波长：

$$\lambda_{l,j} = \lambda_l \left(1 + \frac{v_j}{c}\right)$$

---

## 3. 投影矩阵构造（`buildM`）

函数 `buildM(obs, mask, prof, interpMode)` 构造 $M_I$ 和 $M_V$ 两个矩阵（形状均为 $n \times m$），外循环遍历掩膜中每条谱线 $l$：

对每条谱线找到其覆盖的观测像素范围 $\{i\}$，然后将权重分配到 profile 的速度像素上。

**插值模式 0（最近邻）**：

$$M_{i, j^*} \mathrel{+}= w_l, \quad j^* = \arg\min_j |\lambda_{l,j} - \lambda_i|$$

**插值模式 1（线性插值，默认 `interpMode=1`）**：

找到满足 $\lambda_{l,j-1} < \lambda_i \leq \lambda_{l,j}$ 的 $j$，权重按位置比例分配：

$$\alpha = \frac{\lambda_i - \lambda_{l,j-1}}{\lambda_{l,j} - \lambda_{l,j-1}}$$

$$M_{i,j-1} \mathrel{+}= w_l \cdot (1 - \alpha), \quad M_{i,j} \mathrel{+}= w_l \cdot \alpha$$

所有谱线的贡献累加，最终 $M$ 的每行是覆盖该观测像素的所有掩膜谱线的加权叠加。

> **实现说明**：`buildM` 的外循环遍历掩膜谱线（O(L) 循环），比 `buildMold`（外循环遍历观测像素，O(N) 循环）快约 2–3 倍。两者结果等价。

---

## 4. 噪声权重矩阵（`buildInvSig2`）

构造对角稀疏矩阵 $S^2$，形状 $n \times n$：

$$S^2_{ii} = \frac{I_i}{\sigma_i^2}$$

其中 $I_i$ 为强度（由深度 $1 - I_i/I_c$ 恢复），$\sigma_i$ 为该像素的观测误差。乘以强度因子模拟光子噪声的相关性，与 C 版本行为一致，对深谱线区域进行适度降权。

---

## 5. LSD 正则方程（`lsdFit`）

对加权最小二乘问题：

$$\min_Z \; \chi^2 = (Y_o - M Z)^T S^2 (Y_o - M Z)$$

令导数为零，得到正则方程：

$$\underbrace{(M^T S^2 M)}_{\alpha} Z = \underbrace{M^T S^2 Y_o}_{\beta}$$

故解为：

$$Z = \alpha^{-1} \beta = (M^T S^2 M)^{-1} M^T S^2 Y_o$$

其中：
- $\beta = M^T S^2 Y_o$：掩膜与观测的加权互相关
- $\alpha = M^T S^2 M$：掩膜的加权自相关矩阵（实对称正定）

误差棒由协方差矩阵对角元给出：

$$\sigma^2(Z_i) = (M^T S^2 M)^{-1}_{ii}$$

---

## 6. Cholesky 求解（`lsdFit` 内部）

$\alpha$ 是实对称正定矩阵，使用 Cholesky 分解求解：

1. **分解**：$\alpha = L L^T$（`scipy.linalg.cho_factor`）
2. **前后向代入**：$Z = L^{-T} L^{-1} \beta$（`scipy.linalg.cho_solve`）
3. **误差估计**：对单位矩阵求解得到 $\alpha^{-1}$，取对角平方根

相比直接矩阵求逆，Cholesky 方法数值稳定性提升约 $10^6$ 倍，是处理病态矩阵的标准做法。如果 Cholesky 分解失败（严重病态），自动回退到 `numpy.linalg.inv` 直接求逆。

对 $I$、$V$、$N_1$ 分别独立求解，$V$ 和 $N_1$ 共享同一个 $\alpha_V$ 分解。

---

## 7. 自适应平滑（`_smooth_profile`）

求解后对 profile 施加基于自相关矩阵的 3 点平滑，模拟 C 版本的 `get_psf()` 行为：

$$Z'_k = \frac{d_1 \cdot Z_k + \frac{d_2}{2}(Z_{k+1} + Z_{k-1})}{d_1 + d_2}, \quad k = 1, \ldots, m-2$$

其中：
- $d_1 = \text{mean}(\text{diag}(\alpha))$：自相关矩阵主对角线均值
- $d_2 = \text{mean}(\text{diag}(\alpha, 1))$：自相关矩阵次对角线均值

$\alpha$ 的次对角线为正值（相邻速度像素的线性插值重叠量），产生正向加权平均平滑效果（而非协方差矩阵的负次对角线所导致的锐化）。

---

## 8. χ² 计算（`getChi2`）

$$\chi^2 = (Y_o - M Z)^T S^2 (Y_o - M Z)$$

分别计算 $\chi^2_I$、$\chi^2_V$、$\chi^2_{N_1}$，自由度为：

$$\text{dof} = n_{\rm obs} - m_{\rm prof}$$

Reduced χ² = χ² / dof，期望值为 1。

---

## 9. σ-clipping 迭代（`lsdFitSigmaClip`）

重复执行以下循环 `sigmaClipIter + 1` 次：

1. 调用 `lsdFit()` → 得到 profile Z 和矩阵 MI
2. 计算模型谱 $\hat{Y} = M_I \cdot Z_I$
3. 计算每个观测像素的残差：$r_i = |Y_i - \hat{Y}_i| / \sigma_i$
4. 拒绝 $r_i > $ `sigmaClip` 的像素（`obs.sigmaClipI()`）
5. 在最后一次迭代后不再 clip

当 `sigmaClipIter=0` 时，仅执行一次拟合，不做 clip。

---

## 10. 误差棒缩放（`scaleErr`）

若 reduced χ² > 1，将误差棒整体缩放：

$$\sigma' = \sigma \cdot \sqrt{\chi^2_{\rm red}}$$

此操作确保 final reduced χ² ≈ 1，适用于光子噪声估计偏低（如系统噪声主导）的情形。

---

## 11. 连续谱偏振去除（`zeroProf`）

计算 profile 的加权均值，若 `removeContPol ≠ 0` 则从全 profile 中减去：

$$Z'_j = Z_j - \langle Z \rangle_{\rm avg}$$

适用于 V 和 N1，防止系统性仪器偏振偏移影响检测统计。

---

## 12. 观测范围提取（`obs.setInRange`）

为减少内存和计算量，在 LSD 拟合前将观测截取为仅覆盖掩膜谱线的像素。

实现思路：
1. 计算掩膜中每条谱线在 `[velStart, velEnd]` 速度范围对应的波长窗口 `[λ_low, λ_high]`
2. 对已排序的 `maskWlLow` 和 `maskWlHigh` 数组，用 `numpy.searchsorted` 确定每个观测像素是否落在某条谱线的覆盖范围内
3. 以向量化方式判断：若 `indNearestStart > indNearestEnd`，该像素在某条谱线范围内

---

## 13. 谱线范围估计（`estimateLineRange`）

为 null test 提供 profile 中谱线的速度范围：

1. 取 profile 两端各 20 个像素估计连续谱均值 $\bar{I}$ 和标准差
2. 若标准差 > 1.1 × 平均误差棒，认为误差低估，计算缩放因子
3. 找出 $I_j < \bar{I} + 4\sigma$ 的速度像素集合（谱线内），其余为谱线外

---

## 14. Null Test（`nullTest`）

在谱线内 ($\mathcal{I}_{\rm in}$) 和谱线外 ($\mathcal{I}_{\rm out}$) 分别计算 V 和 N1 的 χ²：

1. 在谱线内估计 V / N1 的"连续谱"（加权均值）$\bar{v}$
2. 对谱线内外分别计算：

$$\chi^2_{\rm in} = \sum_{j \in \mathcal{I}_{\rm in}} \left(\frac{V_j - \bar{v}}{\sigma_{V,j}}\right)^2$$

3. 计算检测概率：

$$P_{\rm in} = \Gamma_{\rm inc}\left(\frac{\nu_{\rm in}}{2}, \frac{\chi^2_{\rm in}}{2}\right)$$

通过 `scipy.special.gammainc` 计算不完全 Gamma 函数。误报率 FAP = $1 - P$。

检测标准与 Donati et al. (1997) 一致：FAP < $10^{-4}$ 为确定检测，FAP < $10^{-2}$ 为边缘检测。

---

## 参考文献

- Donati J.-F. et al., 1997, MNRAS 291, 658 — LSD 原始方法论文
- Kochukhov O. et al., 2010, A&A 524, A5 — LSD 方法综述与权重讨论
