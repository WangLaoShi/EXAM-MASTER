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

## Access Points

- Admin Panel: `http://localhost:8000/admin`
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- **Integration API 文档**: [docs/INTEGRATION_API.md](docs/INTEGRATION_API.md)
- **Integration API Key 管理**: `http://localhost:8000/admin/api-keys`

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
```bash
pytest
```

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
