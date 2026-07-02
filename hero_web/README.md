# EXAM-MASTER Hero Web

基于 **React 19 + Vite + HeroUI + TypeScript** 的独立 Web 考试端，对接后端 `/api/v1`。

## 功能状态

| 功能 | 状态 |
|------|------|
| 登录 / 注册 | ✅ |
| 题库列表 / 详情 | ✅ |
| 练习 / 模拟考试 | ✅ |
| 五种题型 + Markdown/KaTeX | ✅ |
| 题号导航 / 标记 / 收藏 | ✅ |
| 错题本 / 历史 | ✅ |
| 复合题 `composite` | ✅ |
| 模拟考「全部答完再交卷」 | ⏳ 当前逐题提交 |

## 功能（M1）

- 登录 / 注册
- 题库列表与详情
- 练习 / 模拟考试（倒计时、题号导航、标记、交卷）
- 五种题型渲染（单选、多选、判断、填空、简答）+ Markdown/KaTeX
- 错题本 / 收藏 / 答题历史（基础列表）

## 开发

```powershell
cd hero_web
npm install
npm run dev
```

默认 `http://127.0.0.1:5173`，API 通过 Vite 代理到 `http://127.0.0.1:8000`。

需先启动后端：

```powershell
cd backend
python run.py
```

## 环境变量

复制 `.env.example` 为 `.env.local`（可选）：

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE` | 生产环境 API 根地址，如 `https://exam.shaynechen.tech` |
| `VITE_BASE_PATH` | 静态资源 base path，部署到 `/app-exam` 时设为 `/app-exam/` |
| `VITE_APP_TITLE` | 页面标题 |

## 生产构建

```powershell
cd hero_web
npm run build
```

产物在 `hero_web/dist/`，可拷贝到 `backend/hero_web_app/` 并由后端挂载在 `/app-exam`。

## 目录结构

```
src/
  api/           # HTTP 客户端与接口
  components/
    exam/        # 考试壳（计时、导航、交卷）
    question/    # 题目渲染（核心）
    layout/
  pages/
  routes/
  stores/
  types/
```

## 与 Flutter Web 的关系

| 路径 | 客户端 |
|------|--------|
| `/app-web` | Flutter Web 全功能端 |
| `/app-exam` | Hero Web 考试专精端（本目录） |

两者共用同一套 JWT 与 `/api/v1` 后端。
