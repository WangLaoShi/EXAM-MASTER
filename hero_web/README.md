# EXAM-MASTER Hero Web

基于 **React 19 + Vite + HeroUI + TypeScript** 的独立 Web 考试端，对接后端 `/api/v1`。

## 功能状态

| 功能 | 状态 |
|------|------|
| 登录 / 注册 | ✅ |
| 题库列表 / 详情 | ✅ |
| 五种练习模式 + 模式预览 | ✅ |
| 练习 / 模拟考试 | ✅ |
| 五种题型 + 复合题 + Markdown/KaTeX | ✅ |
| 题号导航（>60 题收缩）/ 标记 / 收藏 | ✅ |
| 考试页选项同行 / 工具栏左右布局 | ✅ |
| 错题本 / 历史 | ✅ |
| 模拟考「全部答完再交卷」 | ⏳ 当前逐题提交 |

## 练习模式

题库详情页支持五种模式，创建前调用 `GET /api/v1/practice/modes/preview` 显示「可用 N 题」；0 题模式置灰。

| 模式 | 说明 |
|------|------|
| 顺序练习 | 全库按序 |
| 随机练习 | 全库打乱 |
| 错题专练 | 需先有错题记录 |
| 收藏专练 | 需先有收藏 |
| 未做题 | 排除已作答题目 |

「开始练习」每次 **新建会话**（`resume_if_exists=false`）；「模拟考试」固定随机模式。  
后端与联调说明见 **[backend/docs/PRACTICE_MODES.md](../backend/docs/PRACTICE_MODES.md)**。

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

`run.py` 启动前会自动释放 8000 端口占用。

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
npm install
.\scripts\build_deploy.ps1
```

Linux / macOS：

```bash
cd hero_web
npm ci
VITE_BASE_PATH=/app-exam/ npm run build
mkdir -p ../backend/hero_web_app
cp -r dist/* ../backend/hero_web_app/
```

完整发布流程（含 Docker）见 **[docs/guides/INSTALLATION_AND_DEPLOYMENT.md](../docs/guides/INSTALLATION_AND_DEPLOYMENT.md)**。

## UI 说明（考试页）

- **选项行**：单选/多选/判断的圆圈/方框与 `A. 文字` 同一行（`index.css` 中 `.choice-option`，选项 Markdown 使用 `RichContent inline`）
- **底部栏**：上一题居左；下一题、标记、收藏、提交本题居右
- **题号导航**：≤60 题全部展开；>60 题默认收缩，可展开全部；三位数题号自适应字号

## 目录结构

```
src/
  api/           # HTTP 客户端与接口（practice.ts 含模式预览）
  components/
    exam/        # ExamToolbar、QuestionNavGrid、Timer、交卷
    question/    # 题型渲染、CompositeQuestion
    layout/      # ExamLayout、AppShell
  pages/         # BankDetailPage、ExamRoomPage 等
  routes/
  stores/        # examStore
  types/
```

## API 注意

- 题库列表：`GET /api/v1/qbank/banks/`（**尾斜杠**，避免 307 丢 Authorization）
- 当前题目：`GET /api/v1/practice/sessions/{id}/current`

## 与 Flutter Web 的关系

| 路径 | 客户端 |
|------|--------|
| `/app-web` | Flutter Web 全功能端 |
| `/app-exam` | Hero Web 考试专精端（本目录） |

两者共用同一套 JWT 与 `/api/v1` 后端。

## 测试

后端练习模式自动化测试（与 Hero Web 共用 API）：

```powershell
cd backend
pytest tests/test_practice_modes.py -v
python test_practice_api.py   # 需 run.py 已启动
```
