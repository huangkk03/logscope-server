# LogScope Server（logscope-server）

一个轻量的 **Elasticsearch 日志导出/检索服务**，内置 Web 控制台与后台配置页，基于 **FastAPI**。

## 功能

- **Web 控制台**：`/console`
  - 同域调用后端搜索接口，返回可下载的日志文件链接
  - 支持 index 通配、Lucene `query_string`、时间范围、filters（单值/多值 OR）
  - 支持索引候选与字段值候选（下拉建议）
- **后台管理**：`/admin`
  - 维护 ES 连接配置（host + api_key），保存在 `data/config.db`
  - 维护 filters 预设（key + 多个可选 values），供控制台下拉多选使用
- **导出文件**：
  - 导出文件写入 `logs/` 目录
  - 默认 **120 秒后自动清理**（后端后台任务）
- **接口鉴权**：所有 API 通过 `Authorization: Bearer <token>` 保护

## 主要路由

- **页面**
  - `/` → 重定向到 `/console`
  - `/console`：控制台页面（纯静态 HTML + 原生 JS）
  - `/admin`：后台管理页面（纯静态 HTML + 原生 JS）
- **LogScope API**（前缀：`/api/logscope`）
  - `POST /api/logscope/search`：搜索并导出，返回下载 URL（纯文本）
  - `GET /api/logscope/download/{file}`：下载导出文件
  - `GET /api/logscope/preview/{file}`：预览文件（默认最多 200KB）
  - `POST /api/logscope/suggest-indices`：索引候选（支持通配 + 正则二次过滤）
  - `POST /api/logscope/suggest-values`：字段值候选（terms 聚合）
- **Admin API**（前缀：`/api/admin`）
  - `GET/POST/DELETE /api/admin/es-configs`：管理 ES 连接配置
  - `GET/POST/DELETE /api/admin/filter-presets`：管理 filters 预设
  - `GET /api/admin/filter-options`：一次性返回 key/label/values（供控制台使用）

## Linux 启动（推荐：venv + uvicorn）

### 1) 准备环境

- 建议 **Python 3.10+**
- 确保有 `python3-venv`（不同发行版安装方式不同）

### 2) 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### 3) 配置环境变量（重要）

```bash
# API 鉴权 Token（生产环境务必修改）
export LOGSCOPE_AUTH_TOKEN='change-me-to-a-long-random-string'

# 可选：默认 ES hosts（逗号分隔）。未设置时默认 http://localhost:9200
export ES_HOSTS='http://localhost:9200'
```

### 4) 启动服务

开发模式（自动 reload）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

生产模式（示例）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问：

- 控制台：`http://<你的IP或域名>:8000/console`
- 后台：`http://<你的IP或域名>:8000/admin`

在页面里填入 **Bearer Token**（就是 `LOGSCOPE_AUTH_TOKEN`），即可调用 API。

## Docker 启动（推荐：docker compose）

项目已提供 `Dockerfile` 与 `docker-compose.yml`。

### 1) 启动（含内置 ES）

```bash
export LOGSCOPE_AUTH_TOKEN='change-me-to-a-long-random-string'
docker compose up -d --build
```

默认端口：

- LogScope：`http://localhost:8000`
- Elasticsearch（可选）：`http://localhost:9200`

数据持久化：

- `./data` → 容器 `/app/data`（SQLite 配置库 `config.db`）
- `./logs` → 容器 `/app/logs`（导出文件，默认 120 秒清理）

### 2) 使用外部 ES（不使用 compose 内置 ES）

方式一：直接改 `docker-compose.yml` 里的 `ES_HOSTS` 为外部地址，并删除/注释 `elasticsearch` 服务。

方式二：启动时覆盖环境变量：

```bash
export LOGSCOPE_AUTH_TOKEN='change-me-to-a-long-random-string'
export ES_HOSTS='http://your-es:9200'
docker compose up -d --build
```

## 使用流程（最短路径）

1. 打开 `/admin`，输入 token 并保存
2. 新增一条 ES 配置（name/host/api_key）
3.（可选）新增 filters 预设：key + values（控制台会以下拉多选形式使用）
4. 打开 `/console`：
   - 选择 ES 配置（推荐），填 index / query / 时间范围 / filters
   - 点击搜索后得到下载链接，下载或在线预览

## 数据与目录

- **配置库**：`data/config.db`（SQLite，会自动创建目录/表）
- **导出文件目录**：`logs/`（会自动创建；文件默认 120 秒清理）

## 常见问题

- **启动后 403 / Invalid Token**
  - 检查请求头是否是 `Authorization: Bearer <token>`
  - 检查环境变量 `LOGSCOPE_AUTH_TOKEN` 是否与页面中填写一致
- **ES 连接失败**
  - 优先在 `/admin` 配置正确的 `host` 与 `api_key`
  - `host` 建议带协议（如 `http://es:9200`）；不带协议也会自动补成 `http://`
- **端口占用**
  - 修改启动参数的 `--port`（或在反向代理/Nginx 后面转发）

## systemd（可选示例）

下面是一个最小化示例（自行修改路径/用户/环境变量）：

```ini
[Unit]
Description=LogScope Server
After=network.target

[Service]
WorkingDirectory=/opt/logscope-server
Environment=LOGSCOPE_AUTH_TOKEN=change-me
Environment=ES_HOSTS=http://localhost:9200
ExecStart=/opt/logscope-server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

