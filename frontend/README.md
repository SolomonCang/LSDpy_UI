# LSD_UI Frontend

当前前端已按模块拆分为 4 个独立子页面，整体组织方式参考 ZDIpy_WebUI 的前端分层思路。

## 运行方式

直接用浏览器打开 `index.html` 即可预览入口页。

如需本地静态服务（推荐，便于后续接口联调），可在项目根目录执行：

```bash
python -m http.server 8080
```

然后访问：

- `http://127.0.0.1:8080/frontend/index.html`

## 页面与模块

- `index.html`：四个子页面入口
- `params.html`：参数页面（profile/normalization/processing/output）
- `data.html`：光谱与 mask 页面（`input.observation`、`input.mask`）
- `task.html`：LSD 任务页面（配置校验、Mock/API 启动、日志）
- `results.html`：结果 plot 页面（加载最新任务缓存并绘制 profile）

## 关键实现

- 共享样式：`css/app.css`
- 共享状态与配置存储：`js/common.js`（localStorage）
- 页面独立脚本：
  - `js/params.js`
  - `js/data.js`
  - `js/task.js`
  - `js/results.js`

## 当前能力

- 独立页面导航与职责分离
- 参数编辑、校验、保存与导出
- 光谱与 mask 路径单独维护
- LSD 任务运行：
  - Mock 模式：前端模拟流程并生成结果缓存
  - API 模式：预留后端任务接口对接
- 结果页面读取最近一次任务缓存并绘制 profile 折线

## 预留后端接口约定

在 API 模式下，前端会请求：

- `POST /api/tasks`
  - 请求体：`{ "config": { ...LSDConfig... } }`
  - 返回体示例：`{ "task_id": "task-123" }`
- `GET /api/tasks/{task_id}`
  - 返回体示例：`{ "status": "running|done|error", "message": "..." }`
- `POST /api/tasks/{task_id}/cancel`
  - 取消任务

## 下一步建议

- 在 `api/` 下实现任务队列与状态查询
- 把 `results/` 下 profile 与 lsdout 解析后回传给前端
- 在前端增加 profile 曲线图（含误差条）与运行摘要卡片
