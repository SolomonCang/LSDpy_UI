# LSD_UI 前端架构文档

## 目标

前端采用多页面、模块化组织，覆盖 LSD 工作流四个核心环节：

1. 参数配置
2. 光谱与 mask 输入
3. LSD 任务运行
4. 结果绘图

设计参考 ZDIpy_WebUI 的“按功能拆分页面与脚本”方式，但领域模型保持 LSD 语义。

---

## 目录结构

```text
frontend/
├── index.html               # 前端入口页（四页导航）
├── params.html              # 参数页
├── data.html                # 光谱与 mask 页
├── task.html                # LSD 任务页
├── results.html             # 结果 plot 页
│
├── css/
│   └── app.css              # 共享样式层
│
├── js/
│   ├── common.js            # 共享状态与工具
│   ├── params.js            # 参数页逻辑
│   ├── data.js              # 数据页逻辑
│   ├── task.js              # 任务页逻辑
│   └── results.js           # 结果页逻辑
│
├── README.md
├── app.js                   # 旧版单页脚本（历史遗留）
└── styles.css               # 旧版单页样式（历史遗留）
```

---

## 页面职责

### 1) Parameters (`params.html`)

负责 profile、normalization、processing、output 关键字段：

- `profile.vel_start_kms`
- `profile.vel_end_kms`
- `profile.pixel_velocity_kms`
- `normalization.depth/lande/wavelength_nm/weighting_mode`
- `processing.sigma_clip.limit/iterations`
- `output.profile/save_lsdout/lsdout`

支持：

- 配置实时预览
- 参数合法性校验
- 保存到本地配置缓存
- 导出 JSON 文件

### 2) Spectrum & Mask (`data.html`)

负责输入路径与数据备注：

- `input.observation`
- `input.mask`
- `lsd_ui_data_notes`（本地备注）

支持文件选择器自动填充相对路径：

- 观测文件 -> `data/<filename>`
- mask 文件 -> `masks/<filename>`

### 3) LSD Task (`task.html`)

负责任务控制与运行日志：

- 配置校验
- 运行模式切换：`mock` / `api`
- 启动任务、停止任务
- 实时日志输出

Mock 模式会生成一份可视化结果缓存，供结果页读取。

### 4) Result Plot (`results.html`)

负责展示最近一次任务结果：

- 读取本地缓存结果
- 绘制 profile 折线（SVG）
- 展示结果 JSON 明细

---

## 模块职责

### `js/common.js`

共享配置和通用能力：

- `defaultConfig()`
- `loadConfig()` / `saveConfig()`
- `setActiveNav(page)`
- `fmtNow()`

并通过 `window.LSDUI` 暴露公共 API。

### `js/params.js`

- 参数表单与配置对象互转
- 参数校验
- 导出 JSON

### `js/data.js`

- 输入路径读写
- 文件选择器映射到相对路径
- 数据备注存储

### `js/task.js`

- 任务状态机（Idle/Running/Completed/Error）
- Mock 任务步骤模拟
- API 模式提交、轮询、取消
- 写入最近任务结果缓存

### `js/results.js`

- 读取结果缓存
- 将 profile 点列渲染为 SVG 曲线

---

## 前端状态模型

使用 `localStorage` 作为当前阶段状态容器：

- `lsd_ui_config_v1`: 当前前端配置对象
- `lsd_ui_last_result_v1`: 最近一次任务结果（用于结果页）
- `lsd_ui_data_notes`: 输入数据备注

说明：当前实现是前端本地状态优先，不会自动读取根目录 `LSDConfig.json` 文件。

---

## 任务与数据流

```text
params/data 页面修改配置
        │
        ▼
localStorage: lsd_ui_config_v1
        │
        ▼
task 页面读取配置并校验
        │
        ├── mock 模式: 生成模拟 profile 点列
        │       ▼
        │   localStorage: lsd_ui_last_result_v1
        │
        └── api 模式: POST /api/tasks
                │
                ├── GET /api/tasks/{task_id}
                └── POST /api/tasks/{task_id}/cancel
                        ▼
                 (后端返回真实结果后再落地)
        │
        ▼
results 页面读取 lsd_ui_last_result_v1 并绘图
```

---

## 后端接口约定（当前前端已预留）

- `POST /api/tasks`
  - body: `{ "config": <LSDConfig对象> }`
  - response: `{ "task_id": "..." }`
- `GET /api/tasks/{task_id}`
  - response: `{ "status": "running|done|error", "message": "..." }`
- `POST /api/tasks/{task_id}/cancel`
  - 取消任务

---

## 维护建议

1. 新增页面时，优先复用 `common.js` 的配置读写接口。
2. 避免在页面脚本之间直接读写对方 DOM。
3. 前端配置字段新增后，需同步更新：
   - `defaultConfig()`
   - 参数页表单字段
   - 任务页校验逻辑
4. 完成后端联调后，逐步替换 mock 结果来源为真实 `results/` 数据。
5. 清理旧版单页遗留文件（`frontend/app.js`、`frontend/styles.css`）前，确认所有入口已迁移。
