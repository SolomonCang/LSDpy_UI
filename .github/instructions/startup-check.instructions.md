---
description: "Use when modifying app.py, launch_ui.py, or any code that affects server startup, port binding, middleware, route registration, or static file mounting. Enforces a startup integrity checklist after every such change."
applyTo: ["app.py", "launch_ui.py"]
---

# Startup Integrity Check

每次修改 `app.py` 或 `launch_ui.py`，或任何可能影响服务启动的代码（中间件、路由注册、静态文件挂载、端口逻辑）后，必须执行以下检查。

## 必检项

### 1. Launch 链路完整性

`launch_ui.py` 通过 `runpy.run_path` 执行 `app.py`，等价于 `python app.py`。确认：

- `launch_ui.py` 的 `BASE_DIR` 仍指向项目根目录（`Path(__file__).resolve().parent`）
- `_normalize_argv()` 正确将位置参数 `PORT` 转换为 `--port PORT`
- `runpy.run_path(str(BASE_DIR / "app.py"), run_name="__main__")` 路径未变

### 2. app.py `__main__` 块

确认以下四项均存在且逻辑正确：

```
argparse --port → _find_free_port(DEFAULT_PORT=8080)
                          ↓
               threading.Thread(_open_browser, url)  ← 0.5s 延迟后打开浏览器
                          ↓
               uvicorn.run(app, host="127.0.0.1", port=port)
```

### 3. 静态文件挂载

`frontend/` 目录必须在 **所有 API 路由注册之后** 挂载，否则 `/` 会拦截 API 请求：

```python
# ✅ 正确顺序
@app.get("/api/...")  # API 路由先注册
...
app.mount("/", StaticFiles(...))  # 最后挂载静态文件
```

挂载后紧跟 no-cache 中间件（`@app.middleware("http")`），确认它对 `.html`/`.css`/`.js` 注入禁缓存响应头，对 `/api` 路径跳过。

### 4. 端口变更影响

若修改了 `DEFAULT_PORT` 或 `_find_free_port` 逻辑，同步检查：

- `frontend/task.html` 中 `id="api-base-url"` 的默认值（当前应为 `http://127.0.0.1:8080`）
- `launch_ui.sh` 中的默认端口参数

### 5. 快速验证命令

变更后运行以下命令确认服务可启动、前端可访问、关键 API 正常：

```bash
python -c "
from fastapi.testclient import TestClient
from app import app
c = TestClient(app)
print('index    :', c.get('/').status_code)           # 200
print('data.html:', c.get('/data.html').status_code)  # 200
print('cache    :', c.get('/data.html').headers.get('cache-control'))  # no-cache
print('masks    :', c.get('/api/files/masks').status_code)  # 200
print('data     :', c.get('/api/files/data').status_code)   # 200
"
```

所有结果均应符合注释预期，否则视为启动链路损坏，需在 PR/commit 前修复。

## 常见失误

| 失误 | 现象 | 修复 |
|------|------|------|
| 静态挂载顺序错误（先于 API 路由） | `/api/*` 返回 404 或 HTML | 将 `app.mount("/", ...)` 移到文件末尾 |
| `__main__` 块被移除或缩进错误 | `launch_ui.py` 执行无输出、浏览器不打开 | 确认 `if __name__ == "__main__":` 缩进 |
| 端口硬编码与 `DEFAULT_PORT` 不一致 | task.html API 调用失败 | 统一为 8080 |
| `no-cache` 中间件缺失 | 前端改动在浏览器中不生效 | 确认 `@app.middleware("http")` 块存在 |
