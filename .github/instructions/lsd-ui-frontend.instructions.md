---
description: "Use when editing LSD_UI frontend files (HTML, CSS, JS). Enforces the four-page modular structure, shared state via localStorage, Airtable-inspired visual design system, and scientific data-first visualization principles."
name: "LSD UI Frontend Design Rules"
applyTo: ["**/frontend/**/*.html", "**/frontend/**/*.css", "**/frontend/**/*.js", "frontend/**"]
---
# LSD_UI 前端设计指令

## 前端目标

前端覆盖 LSD 工作流四个核心环节，每个页面对应单一职责：

| 页面 | 文件 | 职责 |
|---|---|---|
| 参数配置 | `params.html` + `js/params.js` | 编辑 profile / normalization / processing / output 字段，支持导出 JSON |
| 光谱与 mask 输入 | `data.html` + `js/data.js` | 管理 `input.observation` / `input.mask` 路径，文件选择器自动填充相对路径 |
| LSD 任务 | `task.html` + `js/task.js` | 任务启动 / 停止 / 状态轮询 / 实时日志；支持 mock 模式和 api 模式切换 |
| 结果可视化 | `results.html` + `js/results.js` | 读取 `lsd_ui_last_result_v1`，渲染 profile 折线（SVG），展示检测统计摘要 |

---

## 目录结构

```text
frontend/
├── index.html               # 入口导航页
├── params.html
├── data.html
├── task.html
├── results.html
├── css/
│   └── app.css              # 唯一全局样式表
└── js/
    ├── common.js            # 共享状态与工具（window.LSDUI）
    ├── params.js
    ├── data.js
    ├── task.js
    └── results.js
```

**禁止**：页面内联 `<style>` 大段样式；跨页面 JS 直接操作对方 DOM；在页面 JS 中重复实现 `common.js` 已有功能。

---

## 状态模型

使用 `localStorage` 作为唯一前端状态容器，键名统一加版本后缀：

| 键名 | 值类型 | 用途 |
|---|---|---|
| `lsd_ui_config_v1` | JSON 对象 | 当前配置，结构与 `LSDConfig.json` 对齐 |
| `lsd_ui_last_result_v1` | JSON 对象 | 最近一次任务结果，含 profile 点列和检测统计 |
| `lsd_ui_data_notes` | 字符串 | 输入数据备注（自由文本） |

- `common.js` 的 `loadConfig()` / `saveConfig()` 是读写 `lsd_ui_config_v1` 的唯一入口。
- 新增配置字段必须同步更新 `defaultConfig()`，并在参数页添加对应表单控件。
- 前端配置仅在任务页提交时才与后端同步，不自动读写 `LSDConfig.json` 文件。

---

## 任务数据流

```text
params / data 页面
      │  saveConfig()
      ▼
lsd_ui_config_v1 (localStorage)
      │
      ▼
task.js 读取并校验配置
      ├── mock 模式 ──→ 生成模拟 profile → lsd_ui_last_result_v1
      └── api 模式 ──→ POST /api/tasks
                            │ GET /api/tasks/{id}（轮询）
                            └─→ 收到结果 → lsd_ui_last_result_v1
      │
      ▼
results.js 读取 lsd_ui_last_result_v1 → SVG 折线 + 统计表
```

后端接口约定：
- `POST /api/tasks` — body: `{ "config": <配置对象> }` → `{ "task_id": "..." }`
- `GET /api/tasks/{task_id}` → `{ "status": "running|done|error", "message": "..." }`
- `POST /api/tasks/{task_id}/cancel` — 取消任务

---

## 视觉设计系统

参考 Airtable 设计语言，在此基础上针对科学工具语境做调整——以清晰数据传达优先，精简装饰。

### 色彩

| 角色 | 值 | 用途 |
|---|---|---|
| 主文本 | `#181d26` | 所有正文、标签、数值 |
| 强调蓝 | `#1b61c9` | 主 CTA 按钮、超链接、active 导航项 |
| 主背景 | `#ffffff` | 页面主体 canvas |
| 次级表面 | `#f8fafc` | 侧边栏背景、数据表格行交替色、输入框背景 |
| 边框 | `#e0e2e6` | 卡片边框、分割线、输入框边框 |
| 弱文本 | `rgba(4,14,32,0.69)` | 占位符、次级说明文字 |
| 成功 | `#006400` | 检测结果"确定检测"标签 |
| 警告 / 边缘 | `#b45309` | "边缘检测"标签 |
| 中性 / 非检测 | `rgba(4,14,32,0.45)` | "非检测"标签 |

**禁止**使用高饱和度装饰色；科学数据曲线颜色可使用 matplotlib 默认蓝（Stokes V）、橙（I）、灰（N1）映射到 CSS 变量，保持与后端可视化输出一致。

### 阴影

```css
/* 卡片默认阴影 */
--shadow-card: 0 0 1px rgba(0,0,0,0.32), 0 0 2px rgba(0,0,0,0.08),
               0 1px 3px rgba(45,127,249,0.28), 0 0 0 0.5px rgba(0,0,0,0.06) inset;
/* 悬停 / 聚焦软光晕 */
--shadow-soft: 0 0 20px rgba(15,48,106,0.05);
```

### 字体

使用系统字体栈，不引入 Haas 商业字体：

```css
--font-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'SF Mono', 'Fira Mono', 'Consolas', monospace;
```

字号与行高遵循 Airtable 比例：

| 角色 | 字号 | 字重 | 行高 | 字距 |
|---|---|---|---|---|
| 页面标题 | 24px | 500 | 1.25 | 0.12px |
| 分节标题 | 18px | 500 | 1.30 | 0.1px |
| 正文 / 标签 | 14px | 400 | 1.35 | 0.07px |
| 按钮 | 14px | 500 | 1.25 | 0.08px |
| 数值 / 代码 | 13px mono | 400 | 1.40 | 0 |
| 说明 / caption | 12px | 400 | 1.35 | 0.07px |

**正文字距（letter-spacing）不得为 0**；保持轻微正值，提高科学标签可读性。

### 圆角

| 元素 | 半径 |
|---|---|
| 主 CTA 按钮 | 8px |
| 次级按钮 / 输入框 | 6px |
| 卡片 / 面板 | 12px |
| 标签徽章 | 4px |
| 大区块分隔 | 16px |

---

## 组件规范

### 按钮

```css
/* 主按钮 */
.btn-primary {
  background: #1b61c9;
  color: #fff;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.08px;
  border: none;
  box-shadow: var(--shadow-card);
}
/* 次级按钮 */
.btn-secondary {
  background: #fff;
  color: #181d26;
  border: 1px solid #e0e2e6;
  border-radius: 8px;
  padding: 8px 20px;
}
/* 危险 / 停止 */
.btn-danger {
  background: #fff;
  color: #b91c1c;
  border: 1px solid #fca5a5;
  border-radius: 8px;
}
```

### 输入框 / 表单控件

- 边框 `1px solid #e0e2e6`，背景 `#f8fafc`，聚焦时描边切换到 `#1b61c9`（1.5px）
- 标签（label）位于控件上方，字号 12px，颜色 `rgba(4,14,32,0.69)`
- 数值输入框右对齐，使用 `font-mono`
- 错误状态边框 `#ef4444`，错误提示文字 12px 红色，紧跟控件下方

### 卡片 / 面板

- 背景 `#ffffff`，边框 `1px solid #e0e2e6`，圆角 12px，阴影 `var(--shadow-card)`
- 内边距 20px–24px（宽松）或 16px（紧凑列表项）
- 标题 18px 500 + 说明文字 14px 弱色，两者间距 4px

### 导航栏

- 水平四项导航（Params / Data / Task / Results）
- 当前页项：文字 `#1b61c9`，下划线 2px `#1b61c9`
- 非当前项：文字 `rgba(4,14,32,0.69)`，悬停变 `#181d26`
- `common.js` 的 `setActiveNav(page)` 统一管理激活状态

### 状态标签（徽章）

| 状态 | 背景 | 文字 |
|---|---|---|
| 运行中 | `rgba(27,97,201,0.10)` | `#1b61c9` |
| 完成 | `rgba(0,100,0,0.10)` | `#006400` |
| 错误 | `rgba(185,28,28,0.10)` | `#b91c1c` |
| 空闲 | `rgba(4,14,32,0.06)` | `rgba(4,14,32,0.69)` |
| 确定检测 | `rgba(0,100,0,0.10)` | `#006400` |
| 边缘检测 | `rgba(180,83,9,0.10)` | `#b45309` |
| 非检测 | `rgba(4,14,32,0.06)` | `rgba(4,14,32,0.45)` |

---

## 科学可视化规范

### LSD Profile 图（results 页核心）

- 三面板竖向排列：V（圆偏振）→ N1（null）→ I（强度），从上到下
- 横轴：速度 km/s，居中零点，带刻度标签
- 纵轴：各面板独立量程，至少保留 1.5× 数据范围的余量
- 误差棒：半透明填充带（`rgba` 原线色，alpha 0.18）+ 细实线轮廓
- 线宽：1.5px；颜色：V=`#1b61c9`，N1=`#6b7280`，I=`#181d26`
- 曲线背景：`#ffffff`，网格线 `#e0e2e6`（极细 0.5px），参考零线 `#e0e2e6`（1px）
- 图表容器圆角 12px，边框 `1px solid #e0e2e6`，阴影 `var(--shadow-soft)`

### 数据原则

- **不得**为了美观缩放或裁切数据范围（除用户显式交互）
- 数值标签保留科学记数法精度，数值字体使用 `font-mono`
- 检测统计（FAP、χ²、N_in）以键值对形式展示在图表下方，不嵌入图表内
- 运行日志使用等宽字体，背景 `#f8fafc`，最大高度 200px + 纵向滚动

---

## 布局约定

- 最大内容宽度：1100px，水平居中
- 基础间距单位：8px
- 页面内边距（横向）：24px（桌面）/ 16px（窄视口 < 640px）
- 表单区域：两列网格（标签 / 控件），列宽比约 1 : 2；窄视口退化为单列
- 结果页 profile 图占满可用宽度（`width: 100%`），高度比约 3 : 1（宽 : 高）

---

## 维护规则

- 新增页面时，优先复用 `common.js` 的 `loadConfig()` / `saveConfig()`。
- 新增配置字段后，必须同时更新：`defaultConfig()`、参数页表单、任务页校验逻辑。
- 完成后端联调后，逐步替换 mock 结果来源为真实 `results/` 数据。
- 清理旧版遗留文件（`frontend/app.js`、`frontend/styles.css`）前，确认所有入口已完成迁移。
- 图表渲染逻辑集中在 `results.js`，不得在 `results.html` 中内联脚本实现绘图。
