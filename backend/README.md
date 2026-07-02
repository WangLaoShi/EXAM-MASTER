# EXAM-MASTER Backend API

A modern question bank management system built with FastAPI with integrated admin panel.

## Features

- JWT Authentication with role-based access control
- User management (Admin, Teacher, Student roles)
- Multi-question bank management
- Dynamic question options (not limited to ABCD)
- File upload and resource management
- Statistics and analytics
- Import/Export support (CSV, JSON, Markdown, etc.)
- Multiple quiz modes (practice, exam, timed)

## Tech Stack

- **Framework**: FastAPI
- **Database**: Dual SQLite architecture (Main DB + Question Bank DB)
- **Authentication**: JWT tokens
- **ORM**: SQLAlchemy
- **Validation**: Pydantic

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Core configuration
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utilities
├── databases/           # SQLite databases
├── storage/             # File storage
├── init_admin.py        # Create admin user (run once after first start)
├── scripts/legacy/      # 历史数据修复脚本（正常部署无需运行）
├── run.py               # Application entry point
└── requirements.txt
```

## Installation

### Requirements

- Python **3.11.9**（见 `.python-version`）
- pip

### Windows (PowerShell)

```powershell
cd backend

# 创建虚拟环境（若 venv 已存在且服务在运行，需先停止 python run.py）
& "$env:USERPROFILE\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 确认版本
python --version   # 应显示 Python 3.11.9

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
Copy-Item .env.example .env
# 编辑 .env，至少设置 SECRET_KEY 和 JWT_SECRET_KEY
```

### Linux / macOS

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，至少设置 SECRET_KEY 和 JWT_SECRET_KEY
```

## Database Initialization

**无需手动建表。** 运行 `python run.py` 时，应用会在启动阶段自动调用 `init_databases()`，根据 `.env` 中的配置创建：

| 数据库文件 | 环境变量 | 用途 |
|-----------|---------|------|
| `databases/main.db` | `DATABASE_URL` | 用户、认证、权限、答题记录 |
| `databases/question_bank.db` | `QUESTION_BANK_DATABASE_URL` | 题库、题目、资源、LLM 模板 |

LLM 提示词模板也会在首次启动时自动初始化（`app/core/init_templates.py`）。

### 首次部署额外步骤

```bash
# 1. 启动服务（自动建表）
python run.py

# 2. 另开终端，创建管理员账号
python init_admin.py
```

默认管理员凭据：
- Username: `admin`
- Password: `admin123`

> **关于 `init_database_v2.py`**：这是历史遗留脚本，会写入独立的 `question_bank_v2.db`，当前应用**不使用**该文件。正常开发/部署**无需运行**此脚本。

## Run

```bash
python run.py
```

服务默认地址：`http://localhost:8000`

> **Windows 注意**：`run.py` 使用 `reload=True`，异常退出后可能留下**孤儿 uvicorn 子进程**，导致请求仍打到旧代码（例如 `GET /api/v2/qbank/banks` 500）。  
> 重启前先结束占用 8000 端口的进程：
> ```powershell
> Get-CimInstance Win32_Process -Filter "name='python.exe'" |
>   Where-Object { $_.CommandLine -match 'uvicorn|multiprocessing-fork|run\.py' } |
>   ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
> ```
> 或不用 reload：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Access Points

- Admin Panel: `http://localhost:8000/admin`
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- **学员 Web 答题端（Flutter Web）**: `http://localhost:8000/app-web`
- **学员 Web 考试端（Hero Web / React）**: `http://localhost:8000/app-exam`
- **Integration API 文档**: [docs/INTEGRATION_API.md](docs/INTEGRATION_API.md)
- **Integration API Key 管理**: `http://localhost:8000/admin/api-keys`

## 学员 Web 答题端（Flutter Web）

完整步骤见 **[docs/guides/FLUTTER_WEB_GUIDE.md](../docs/guides/FLUTTER_WEB_GUIDE.md)**。

**快速联调：**

```powershell
# 1. 构建并部署到 backend/web_app/
cd flutter_app
.\scripts\setup_flutter_env.ps1
.\scripts\build_web.ps1

# 2. 启动后端
cd ..\backend
python run.py

# 3. 浏览器打开
# http://127.0.0.1:8000/app-web
# 默认账号 admin / admin123
```

热重载开发：`flutter_app\scripts\run_web_dev.ps1`（Chrome `127.0.0.1:8080`，需后端已启动）。

Flutter SDK 默认路径：`D:\EXAM-MASTER\tools\flutter`（见 `.gitignore`，需本地 `git clone` 或自行安装 Flutter）。

## 学员 Web 考试端（Hero Web / React）

源码目录：`../hero_web/`。基于 React + HeroUI，专注考试/练习体验。

**快速联调：**

```powershell
# 1. 构建并部署到 backend/hero_web_app/
cd hero_web
npm install
.\scripts\build_deploy.ps1

# 2. 启动后端（若未启动）
cd ..\backend
python run.py

# 3. 浏览器打开
# http://127.0.0.1:8000/app-exam
```

热重载开发：`hero_web\scripts\run_dev.ps1`（Vite `127.0.0.1:5173`，API 代理到后端 8000）。

详细说明见 **[hero_web/README.md](../hero_web/README.md)**。

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users` - List users (admin)
- `GET /api/v1/users/{id}` - Get user details
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Question Banks
- `GET /api/v1/qbank/banks` - List question banks
- `POST /api/v1/qbank/banks` - Create question bank
- `GET /api/v1/qbank/banks/{id}` - Get bank details
- `PUT /api/v1/qbank/banks/{id}` - Update bank
- `DELETE /api/v1/qbank/banks/{id}` - Delete bank

### Questions
- `GET /api/v1/qbank/questions` - List questions
- `POST /api/v1/qbank/questions` - Create question
- `GET /api/v1/qbank/questions/{id}` - Get question
- `PUT /api/v1/qbank/questions/{id}` - Update question
- `DELETE /api/v1/qbank/questions/{id}` - Delete question

## Development

### Running Tests

#### GitHub CI（自动）

每次向 `main` / `dev_2.0` 推送或提交 PR（修改 `backend/`）时，GitHub Actions 会运行 `tests/test_ci_smoke.py`（约 50+ 条进程内用例：健康检查、OpenAPI、JWT 登录、题库序列化、逐条 public 接口）。

Live 测试（`@pytest.mark.live`）与慢速测试（`@pytest.mark.slow`）**不在 CI 中运行**，需在本地手动执行。

#### 进程内（无需启动服务）

```bash
pytest tests/test_ci_smoke.py -v
pytest tests/test_all_apis.py -q
pytest tests/test_all_apis.py::TestOpenAPIDocumentInProcess -v
```

#### Live：全接口 OpenAPI 冒烟（需先 `python run.py`）

每个 OpenAPI operation 一条用例，当前约 **230 条**（`-v` 逐条显示）：

```powershell
cd backend
$env:TEST_ADMIN_USER="admin"
$env:TEST_ADMIN_PASS="admin123"
$env:INTEGRATION_API_KEY="em_live_xxx"

# 全量
python -m pytest tests/test_openapi_full_live.py -v --tb=short -ra

# 统计用例数
python -m pytest tests/test_openapi_full_live.py --collect-only -q

# 只跑 Integration
python -m pytest tests/test_openapi_full_live.py -v -k "IntegrationSmoke"
```

#### Live：Integration API 专项（含 881 题性能）

```powershell
$env:INTEGRATION_API_KEY="em_live_xxx"
python -m pytest tests/test_integration_api_live.py -v -s
```

详细说明见 [docs/INTEGRATION_API.md](docs/INTEGRATION_API.md) §12。

耗时断言见 `tests/api_timing.py`。

### Code Formatting
```bash
black app/
```

### Linting
```bash
flake8 app/
```

## License

MIT
