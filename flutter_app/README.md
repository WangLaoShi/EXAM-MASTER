# EXAM MASTER 学员端（Flutter）

智能题库刷题客户端，支持 **Android / iOS / Web / 桌面**。与后端 `backend/` 的 REST API（`/api/v1`）对接。

> **Web 答题端安装与使用**（环境、构建、`/app-web`、热重载）请阅：  
> **[docs/guides/FLUTTER_WEB_GUIDE.md](../docs/guides/FLUTTER_WEB_GUIDE.md)**

## Web 答题端（摘要）

| 形态 | 地址 |
|------|------|
| 部署在后端 | `http://127.0.0.1:8000/app-web` |
| 热重载开发 | `http://127.0.0.1:8080`（`run_web_dev.ps1`） |

```powershell
.\scripts\build_web.ps1    # → backend/web_app/
.\scripts\run_web_dev.ps1    # 开发模式
```

## 目录结构（`lib/`）

```
lib/
├── main.dart              # 入口
├── app.dart               # 根 Widget
├── routes/app_router.dart # 路由
├── core/di/               # Provider 装配
├── data/                  # API、Repository、Model
└── presentation/          # Provider、Screen、Widget
```

## 架构

```
Screen / Provider  →  Repository  →  *Api (Dio)  →  Backend /api/v1
```

## 主要功能

| 模块 | 状态 |
|------|------|
| 登录 / 注册 / 改密 | ✅ |
| 题库、顺序/随机练习、错题、收藏、浏览 | ✅ |
| 统计 Tab、AI 对话、模拟考试 | ⏳ / ❌ |

## API 地址

编译时通过 `--dart-define` 配置（见 `lib/core/constants/api_constants.dart`）：

- 本地：`build_web.ps1`（默认 `API_BASE=http://127.0.0.1:8000`）
- 生产：`build_web.ps1 -Production`

## 脚本

| 脚本 | 说明 |
|------|------|
| `scripts/setup_flutter_env.ps1` | 加载项目内 Flutter PATH |
| `scripts/build_web.ps1` | 构建并部署 Web |
| `scripts/run_web_dev.ps1` | Chrome 热重载 |

## 移动端

```bash
flutter pub get
flutter run -d windows   # 或连接的手机/模拟器
```

SDK 路径：`D:\EXAM-MASTER\tools\flutter`（或系统已安装的 Flutter）。
