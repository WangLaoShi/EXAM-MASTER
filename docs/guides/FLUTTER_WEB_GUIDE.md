# Flutter Web 学员答题端 — 使用指南

学员刷题/练习的 Web 客户端，由 **Flutter Web** 编译，与移动端共用 `flutter_app/lib/` 源码。

| 项目 | 说明 |
|------|------|
| 源码 | `flutter_app/` |
| 构建产物 | `backend/web_app/` |
| 访问地址 | `http://127.0.0.1:8000/app-web`（需先启动后端） |
| API | `http://127.0.0.1:8000/api/v1`（本地默认同源） |

> 不是独立的 H5/React 项目；Admin 后台 `/admin` 仅用于管理，不能代替学员答题。

---

## 一、环境准备（Windows，首次）

### 1. Flutter SDK

项目内已支持将 SDK 放在仓库旁（无需管理员安装）：

```powershell
# 若尚未克隆（约 1GB）
git clone -b stable --depth 1 https://github.com/flutter/flutter.git D:\EXAM-MASTER\tools\flutter
```

当前终端加载 PATH：

```powershell
cd D:\EXAM-MASTER\flutter_app
.\scripts\setup_flutter_env.ps1
flutter doctor
```

**`flutter doctor` 期望（做 Web 即可）：**

| 项 | 要求 |
|----|------|
| Flutter | ✓ |
| Chrome | ✓（Web 调试） |
| Android SDK | 可选（仅做 App 时需要） |

可选：将 `D:\EXAM-MASTER\tools\flutter\bin` 加入系统 PATH，任意终端可用 `flutter`。

### 2. 开发人员模式（Windows 建议开启）

若 `flutter pub get` 提示 **symlink / Developer Mode**：

1. 运行 `start ms-settings:developers`
2. 打开 **开发人员模式**

### 3. 后端

```powershell
cd D:\EXAM-MASTER\backend
.\venv\Scripts\Activate.ps1
python run.py
python init_admin.py   # 仅首次，默认 admin / admin123
```

---

## 二、使用 Web 答题端（推荐流程）

### 方式 A：构建并挂到后端 `/app-web`（联调/演示）

与 API **同源**，无 CORS 问题。

```powershell
cd D:\EXAM-MASTER\flutter_app
.\scripts\build_web.ps1
```

脚本会：`flutter pub get` → `flutter build web --base-href=/app-web/` → 复制到 `backend/web_app/`。

另开终端启动后端后，浏览器访问：

**http://127.0.0.1:8000/app-web**

默认账号：`admin` / `admin123`（或自行注册的学员账号）。

### 方式 B：热重载开发（改 UI 时用）

```powershell
# 终端 1：后端
cd D:\EXAM-MASTER\backend
python run.py

# 终端 2：Flutter Web（Chrome :8080）
cd D:\EXAM-MASTER\flutter_app
.\scripts\run_web_dev.ps1
```

浏览器打开 **http://127.0.0.1:8080**。后端 CORS 已默认允许 `127.0.0.1:8080`。

---

## 三、API 地址配置

编译时通过 `--dart-define` 注入（见 `lib/core/constants/api_constants.dart`）：

| 场景 | 命令 |
|------|------|
| 本地（默认） | `.\scripts\build_web.ps1` → `API_BASE=http://127.0.0.1:8000` |
| 生产 | `.\scripts\build_web.ps1 -Production` → `https://exam.shaynechen.tech` |
| 自定义 | `.\scripts\build_web.ps1 -ApiBase "http://192.168.1.10:8000"` |

手动构建示例：

```powershell
flutter build web --base-href=/app-web/ `
  --dart-define=PRODUCTION=false `
  --dart-define=API_BASE=http://127.0.0.1:8000
```

---

## 四、脚本一览（`flutter_app/scripts/`）

| 脚本 | 作用 |
|------|------|
| `setup_flutter_env.ps1` | 当前终端加入 Flutter PATH |
| `build_web.ps1` | 构建 Web 并部署到 `backend/web_app/` |
| `run_web_dev.ps1` | Chrome 热重载开发（端口 8080） |

---

## 五、功能范围（Web 与 App 相同）

| 功能 | 状态 |
|------|------|
| 登录 / 注册 / 改密 | ✅ |
| 题库列表、激活码 | ✅ |
| 顺序 / 随机练习 | ✅ |
| 错题本、收藏、浏览题目 | ✅ |
| 统计 Tab、AI 对话 | ⏳ 未接入主导航 |
| 模拟考试 | ❌ 未实现 |

---

## 六、常见问题

### `/app-web` 白屏或 404

1. 确认 `backend/web_app/index.html` 存在（需先 `build_web.ps1`）
2. 确认后端已启动，且 `main.py` 已挂载 `/app-web`
3. 检查 `index.html` 中 `<base href="/app-web/">`

### 登录失败 / 连不上 API

1. 本地构建不要用 `-Production`，或确认 `API_BASE` 指向正在运行的后端
2. 方式 B 开发时确认后端已启动且 CORS 含 `127.0.0.1:8080`

### 修改 Dart 代码后页面未更新

重新执行 `.\scripts\build_web.ps1`，或用法 B 热重载。

### Windows 上后端行为异常（旧代码、500）

`python run.py` 的 `reload=True` 可能留下孤儿进程，重启前清理占用 8000 的 Python/uvicorn 进程（见 [backend/README.md](../backend/README.md) § Run）。

---

## 七、相关文档

- [flutter_app/README.md](../../flutter_app/README.md) — 客户端架构与目录
- [backend/README.md](../../backend/README.md) — 后端安装与测试
- [INTEGRATION_API.md](../../backend/docs/INTEGRATION_API.md) — 第三方题库对接（非学员 Web UI）
