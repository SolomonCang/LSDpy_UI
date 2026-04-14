# LSD_UI Frontend

前端采用单页应用（SPA）架构，所有功能集中在 `index.html`，通过四个标签页组织工作流。样式与脚本均为模块化独立文件，通过 `app.py` 提供的 FastAPI 静态服务访问。

## 运行方式

在项目根目录启动后端服务，前端随即可用：

```bash
python app.py
# 或
./launch_ui.sh
```

服务启动后，浏览器自动打开 `http://127.0.0.1:8080`（端口自动探测）。

## 目录结构

```
frontend/
├── index.html          # 单页应用主入口（含四个标签页）
├── params.html         # 独立参数页（多页兼容，与 index.html 共享样式）
├── data.html           # 独立数据页（多页兼容）
├── task.html           # 独立任务页（多页兼容）
├── results.html        # 独立结果页（多页兼容）
├── css/
│   └── app.css         # 唯一全局样式表
└── js/
    ├── common.js       # 共享状态与工具（window.LSDUI）
    ├── params.js       # 参数配置面板（schema 驱动）
    ├── data.js         # 光谱与掩膜路径管理
    ├── task.js         # 任务启动 / 日志 / 轮询
    └── results.js      # LSD profile 绘图（SVG）
```

## 标签页功能

| 标签页 | 功能 |
|--------|------|
| **⚙️ Params** | 编辑 profile / normalization / processing / model_options / output 全部参数；支持从服务器加载、重置为默认值、导出 JSON |
| **📂 Data** | 管理 `input.observation` 和 `input.mask` 路径；列出服务器 `data/` 和 `masks/` 目录中的可用文件，点击文件名自动填充路径 |
| **▶ Task** | 配置校验、启动 LSD 任务、查看实时日志；支持 Mock（前端模拟流程）和 API（调用后端 `/api/tasks`）两种运行模式 |
| **📊 Results** | 读取最近任务结果（`localStorage`），SVG 渲染 Stokes I profile 折线图，展示运行摘要 JSON |

## 状态模型

前端状态通过 `localStorage` 持久化：

| 键名 | 用途 |
|------|------|
| `lsd_ui_config_v1` | 当前配置，结构与 `LSDConfig.json` 对齐 |
| `lsd_ui_last_result_v1` | 最近任务结果，含 profile 数据点和运行信息 |

`common.js` 的 `loadConfig()` / `saveConfig()` 是读写配置的唯一入口。

## API 接口约定

Task 标签页在 API 模式下调用以下接口：

| 接口 | 说明 |
|------|------|
| `POST /api/tasks` — body: `{ "config": {...} }` | 提交任务，返回 `{ "task_id": "..." }` |
| `GET /api/tasks/{task_id}` | 查询任务状态，返回 `{ "status": "running|done|error", "log": [...] }` |
| `POST /api/tasks/{task_id}/cancel` | 取消任务 |
| `GET /api/config` / `PUT /api/config` | 读写 `LSDConfig.json` |
| `GET /api/files/data` / `GET /api/files/masks` | 列出可用输入文件 |
