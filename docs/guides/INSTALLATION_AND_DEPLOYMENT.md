# EXAM-MASTER 安装与部署手册

本文档说明 **Python 后端**、**Web 前端** 的项目结构、本地安装、构建发布，以及 **Docker 一键部署**（适用于已安装 Docker 的新机器）。

---

## 目录

1. [仓库总览](#1-仓库总览)
2. [Python 后端项目结构](#2-python-后端项目结构)
3. [本地开发安装（非 Docker）](#3-本地开发安装非-docker)
4. [Web 项目结构与发布](#4-web-项目结构与发布)
5. [Docker 打包原理](#5-docker-打包原理)
6. [新机器 Docker 快速部署](#6-新机器-docker-快速部署)
7. [运维：升级、备份、环境变量](#7-运维升级备份环境变量)
8. [访问地址一览](#8-访问地址一览)

---

## 1. 仓库总览

```
EXAM-MASTER/
├── backend/                 # Python FastAPI 后端（核心）
│   ├── app/                 # 应用源码
│   ├── databases/           # SQLite（运行时生成，建议备份）
│   ├── storage/             # 题库文件、上传资源
│   ├── web_app/             # Flutter Web 构建产物 → /app-web
│   ├── hero_web_app/        # Hero Web 构建产物 → /app-exam
│   ├── run.py               # 开发入口（热重载 + 端口检测）
│   ├── init_admin.py        # 创建/重置 admin 账号
│   └── requirements.txt
├── hero_web/                # React + HeroUI 考试端源码
├── flutter_app/             # Flutter 全功能客户端（含 Web）
├── docs/                    # 项目文档
├── docker/                  # Docker 入口脚本
├── Dockerfile               # 多阶段镜像（Hero Web + Backend）
├── docker-compose.yml       # 一键启动
└── .env.docker.example      # Docker 环境变量模板
```

| 组件 | 技术栈 | 生产访问路径 |
|------|--------|--------------|
| 后端 API + 管理后台 | FastAPI + SQLite | `http://host:8000` |
| Swagger / ReDoc | 内置 | `/api/docs`、`/api/redoc` |
| Hero Web 考试端 | React 19 + Vite | `/app-exam` |
| Flutter Web 答题端 | Flutter Web | `/app-web`（可选） |
| 移动客户端 | Flutter | 独立 APK/IPA，连同一 API |

---

## 2. Python 后端项目结构

根目录：`backend/`

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口：路由挂载、Admin、静态 Web
│   ├── api/
│   │   ├── v1/              # 主 API（auth、qbank、practice、favorites…）
│   │   ├── v2/              # 新版 REST（banks、questions、exams）
│   │   ├── integration/     # 外部系统 Integration API
│   │   └── mcp/             # MCP Agent 工具
│   ├── core/
│   │   ├── config.py        # 环境变量 / Settings
│   │   ├── database.py      # 双库 SQLAlchemy（main + qbank）
│   │   ├── security.py      # JWT、密码哈希
│   │   └── init_templates.py
│   ├── models/              # ORM 模型
│   │   ├── user_models.py
│   │   ├── question_models_v2.py
│   │   ├── user_practice.py # 练习会话、错题、收藏
│   │   └── …
│   ├── schemas/             # Pydantic 请求/响应
│   ├── services/            # 业务逻辑（题库、LLM、Integration）
│   └── utils/               # 工具（如 composite_question.py）
├── templates/               # Admin Jinja2 模板
├── static/                  # Admin 静态资源
├── tests/                   # pytest（含 test_practice_modes.py）
├── databases/               # main.db + question_bank.db
├── storage/                 # 持久化文件
├── run.py                   # 开发：`uvicorn` + reload + 端口释放
├── init_admin.py            # 管理员初始化
├── requirements.txt
└── .env                     # 本地密钥（勿提交 Git）
```

### 2.1 双数据库

| 文件 | 环境变量 | 内容 |
|------|----------|------|
| `databases/main.db` | `DATABASE_URL` | 用户、权限、部分统计 |
| `databases/question_bank.db` | `QUESTION_BANK_DATABASE_URL` | 题库、题目、练习会话、错题、收藏 |

**首次启动**时 `init_databases()` 自动建表，无需手动迁移（开发环境）。

### 2.2 主要 API 前缀

| 前缀 | 说明 |
|------|------|
| `/api/v1` | 主业务 API |
| `/api/v2` | 新版题库/考试 API |
| `/api/integration` | Integration API（API Key） |
| `/admin` | 管理后台 HTML |

练习模式详见 [backend/docs/PRACTICE_MODES.md](../../backend/docs/PRACTICE_MODES.md)。

### 2.3 开发启动

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Linux: source venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env     # 编辑 SECRET_KEY、JWT_SECRET_KEY
python run.py                   # http://localhost:8000
python init_admin.py            # 首次：admin / admin123
```

`run.py` 会在启动前**自动释放 8000 端口**（避免 Windows 热重载孤儿进程占端口）。

生产环境（非 Docker）推荐：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

---

## 3. 本地开发安装（非 Docker）

### 3.1 环境要求

| 工具 | 版本 |
|------|------|
| Python | **3.11.x**（见 `backend/.python-version`） |
| Node.js | 20+（Hero Web） |
| Flutter | 3.x（可选，Flutter Web / 移动端） |

系统依赖（Linux）：

```bash
sudo apt-get install -y libmagic1
```

### 3.2 后端

见 §2.3。

### 3.3 Hero Web 开发

```powershell
cd hero_web
npm install
npm run dev          # http://127.0.0.1:5173，API 代理到 8000
```

需另开终端运行 `backend` 的 `python run.py`。

### 3.4 Flutter Web 开发（可选）

```powershell
cd flutter_app
.\scripts\setup_flutter_env.ps1
.\scripts\run_web_dev.ps1       # Chrome http://127.0.0.1:8080
```

详见 [FLUTTER_WEB_GUIDE.md](FLUTTER_WEB_GUIDE.md)。

### 3.5 测试

```powershell
cd backend
pytest tests/test_ci_smoke.py tests/test_practice_modes.py -v
python test_practice_api.py     # 需 run.py 已启动
```

---

## 4. Web 项目结构与发布

### 4.1 Hero Web（`hero_web/`）— 考试专精端

```
hero_web/
├── src/
│   ├── api/           # axios 封装（practice.ts、qbank.ts…）
│   ├── components/    # exam/、question/、layout/
│   ├── pages/         # BankList、BankDetail、ExamRoom…
│   ├── routes/
│   ├── stores/        # zustand examStore
│   └── types/
├── public/
├── vite.config.ts     # dev 代理 /api → 8000
├── scripts/
│   └── build_deploy.ps1
└── package.json
```

**开发**：Vite dev server，`base` 为 `/`，API 走 proxy。

**生产发布**：构建为静态文件，由 FastAPI 挂载在 `/app-exam`：

```powershell
cd hero_web
npm install
.\scripts\build_deploy.ps1
# 产物复制到 backend/hero_web_app/
```

脚本等价于：

```powershell
$env:VITE_BASE_PATH = "/app-exam/"
npm run build
Copy-Item dist\* ..\backend\hero_web_app\ -Recurse
```

启动后端后访问：`http://<host>:8000/app-exam`

环境变量（生产构建）：

| 变量 | 说明 |
|------|------|
| `VITE_BASE_PATH` | 必须 `/app-exam/` |
| `VITE_API_BASE` | 空=同源；跨域时填完整 API 根 URL |

### 4.2 Flutter Web（`flutter_app/`）— 全功能 Web 端

```
flutter_app/
├── lib/
│   ├── routes/        # go_router
│   ├── presentation/  # UI + Provider
│   └── data/          # API、Repository
├── web/
└── scripts/
    ├── build_web.ps1      # 构建并部署到 backend/web_app
    └── run_web_dev.ps1
```

**生产发布**：

```powershell
cd flutter_app
.\scripts\build_web.ps1 -Production
# 或指定 API：.\scripts\build_web.ps1 -ApiBase "https://your-domain.com"
```

产物部署到 `backend/web_app/`，访问：`http://<host>:8000/app-web`

> Flutter Web 构建体积较大；Docker 默认镜像**仅内置 Hero Web**。若需 `/app-web`，请在构建镜像前执行 `build_web.ps1`（见 §5.2）。

### 4.3 后端如何挂载 Web

`app/main.py` 末尾：

```python
app.mount("/app-web", StaticFiles(directory="web_app", html=True), ...)
app.mount("/app-exam", StaticFiles(directory="hero_web_app", html=True), ...)
```

目录不存在时跳过挂载，不影响 API。

### 4.4 发布检查清单

- [ ] `backend/.env` 中 `SECRET_KEY`、`JWT_SECRET_KEY` 已改为强随机值
- [ ] `DEBUG=false`
- [ ] Hero Web 已 `build_deploy` 到 `hero_web_app/`
- [ ] （可选）Flutter Web 已 `build_web` 到 `web_app/`
- [ ] `python init_admin.py` 或确认管理员密码已修改
- [ ] `databases/`、`storage/` 已纳入备份策略

---

## 5. Docker 打包原理

### 5.1 镜像构成（多阶段 `Dockerfile`）

```
Stage 1 (node:20-alpine)
  hero_web → npm ci → npm run build → dist/

Stage 2 (python:3.11-slim)
  pip install requirements.txt
  COPY backend/
  COPY dist → /app/hero_web_app
  COPY backend/web_app → /app/web_app（若存在）
  entrypoint: 建表 + init_admin
  CMD: uvicorn :8000
```

### 5.2 构建命令

**仅后端 + Hero Web（默认，推荐）**

```bash
git clone <repo> EXAM-MASTER && cd EXAM-MASTER
docker compose build
```

**含 Flutter Web `/app-web`**

在构建前先在本机（需 Flutter SDK）执行：

```powershell
cd flutter_app
.\scripts\build_web.ps1 -Production
cd ..
docker compose build
```

`backend/web_app/` 会随 `COPY backend/` 打入镜像。

### 5.3 数据持久化

`docker-compose.yml` 使用命名卷：

| 卷名 | 容器路径 | 内容 |
|------|----------|------|
| `exam-databases` | `/app/databases` | SQLite |
| `exam-storage` | `/app/storage` | 题库文件、上传 |

重建容器不会丢失数据；**删卷会清空**。

### 5.4 .dockerignore

排除 `venv/`、`node_modules/`、测试库、大型备份等，加快构建。见项目根 `.dockerignore`。

---

## 6. 新机器 Docker 快速部署

前提：**已安装 Docker Engine + Docker Compose v2**（Docker Desktop 或 Linux 原生）。

### 6.1 Linux 示例（Ubuntu）

```bash
# 安装 Docker（官方文档为准，以下为示例）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录后验证
docker --version
docker compose version
```

### 6.2 部署步骤

```bash
# 1. 获取代码
git clone <your-repo-url> EXAM-MASTER
cd EXAM-MASTER

# 2. 配置环境变量
cp .env.docker.example .env
# 编辑 .env：务必修改 SECRET_KEY、JWT_SECRET_KEY
nano .env

# 3. 构建并启动
docker compose up -d --build

# 4. 查看日志
docker compose logs -f exam-master

# 5. 健康检查
curl http://127.0.0.1:8000/health
# 期望：{"status":"healthy"}
```

### 6.3 首次登录

| 项目 | 值 |
|------|-----|
| 管理后台 | http://\<服务器IP\>:8000/admin |
| Hero 考试端 | http://\<服务器IP\>:8000/app-exam |
| API 文档 | http://\<服务器IP\>:8000/api/docs |
| 默认账号 | `admin` / `admin123` |

容器启动时 `init_admin.py` 会自动执行（幂等）。**生产环境请立即修改密码。**

### 6.4 常用命令

```bash
docker compose ps
docker compose stop
docker compose start
docker compose restart
docker compose down              # 停止并删除容器（保留卷）
docker compose down -v           # ⚠️ 同时删除数据卷
docker compose up -d --build     # 代码更新后重新构建
```

### 6.5 修改端口

编辑 `.env`：

```
EXAM_MASTER_PORT=9000
```

然后 `docker compose up -d`。

### 6.6 反向代理（可选）

生产环境建议在 Docker 前加 Nginx/Caddy，终止 HTTPS 并反代到 `127.0.0.1:8000`：

```nginx
server {
    listen 443 ssl;
    server_name exam.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50m;
    }
}
```

构建 Hero Web 时 `VITE_API_BASE` 留空即可同源访问。

---

## 7. 运维：升级、备份、环境变量

### 7.1 升级版本

```bash
cd EXAM-MASTER
git pull
docker compose up -d --build
```

SQLite 文件在卷中会自动保留；如有 schema 变更，请查阅 release note 或运行迁移脚本。

### 7.2 备份

```bash
# 备份数据卷到本地目录
docker run --rm \
  -v exam-master_exam-databases:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/databases-$(date +%Y%m%d).tar.gz -C /data .

docker run --rm \
  -v exam-master_exam-storage:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/storage-$(date +%Y%m%d).tar.gz -C /data .
```

卷名前缀以 `docker volume ls` 实际为准（通常为 `<项目目录>_exam-databases`）。

### 7.3 关键环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SECRET_KEY` | 是 | 应用密钥 |
| `JWT_SECRET_KEY` | 是 | JWT 签名 |
| `DEBUG` | 否 | 生产 `false` |
| `DATABASE_URL` | 否 | 默认 SQLite 路径 |
| `CORS_ORIGINS` | 否 | JSON 数组，跨域前端域名 |

完整列表见 `backend/.env.example` 与 `.env.docker.example`。

---

## 8. 访问地址一览

| 地址 | 说明 |
|------|------|
| `/` | API 根信息 |
| `/health` | 健康检查 |
| `/admin` | 管理后台 |
| `/api/docs` | Swagger |
| `/app-exam` | Hero Web 考试端 |
| `/app-web` | Flutter Web（若已构建） |
| `/api/v1/practice/modes/preview` | 练习模式预览 API |

---

## 相关文档

- [backend/README.md](../../backend/README.md) — 后端快速入门
- [hero_web/README.md](../../hero_web/README.md) — Hero Web 开发
- [FLUTTER_WEB_GUIDE.md](FLUTTER_WEB_GUIDE.md) — Flutter Web
- [backend/docs/PRACTICE_MODES.md](../../backend/docs/PRACTICE_MODES.md) — 练习模式
- [backend/docs/INTEGRATION_API.md](../../backend/docs/INTEGRATION_API.md) — 外部集成
