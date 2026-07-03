# 练习模式与 Hero Web 考试端

本文档记录 **练习会话 API**、**五种练习模式**、**Hero Web 前端行为**及 **2026-07 相关修复与测试**，供联调与回归参考。

---

## 1. 五种练习模式

| 模式值 | 名称 | 选题规则 |
|--------|------|----------|
| `sequential` | 顺序练习 | 题库内全部题目，按 `question_number` / 查询顺序 |
| `random` | 随机练习 | 全部题目，`random.shuffle` 打乱 |
| `wrong_only` | 错题专练 | 用户在本题库的 `user_wrong_questions` 记录（含已订正） |
| `favorite_only` | 收藏专练 | 用户在本题库的 `user_favorites` 记录 |
| `unpracticed` | 未做题 | 全部题目 − 用户在本题库已有 `user_answer_records` 的题 |

**前置条件（无题时返回 404）：**

- 错题专练：需先在本题库**答错**过题目（提交错误答案后写入错题本）
- 收藏专练：需先在本题库**收藏**过题目
- 未做题：需存在尚未产生答题记录的题目

404 响应 `detail` 为中文提示（非通用「没有找到符合条件的题目」），例如：

- 错题：`当前题库暂无错题，请先练习并答错后再使用错题专练`
- 收藏：`当前题库暂无收藏题目，请先在练习中收藏题目`
- 未做：`当前题库所有题目都已练习过`

---

## 2. API 端点

前缀：`/api/v1/practice`  
鉴权：`Authorization: Bearer <JWT>`

### 2.1 模式预览（新增）

```http
GET /api/v1/practice/modes/preview?bank_id={bank_id}
```

**响应示例：**

```json
{
  "bank_id": "f8f7f4cc-9753-4d76-a39a-522834f3a16f",
  "sequential": 863,
  "random": 863,
  "wrong_only": 3,
  "favorite_only": 1,
  "unpracticed": 860
}
```

`sequential` 与 `random` 题量相同（均为全库题数）；区别仅在创建会话时是否打乱顺序。

### 2.2 创建练习会话

```http
POST /api/v1/practice/sessions?resume_if_exists=false
Content-Type: application/json

{
  "bank_id": "uuid",
  "mode": "random",
  "question_types": null,
  "difficulty": null
}
```

| 查询参数 | 默认 | 说明 |
|----------|------|------|
| `resume_if_exists` | `false` | `true` 时若存在同用户、同题库、**同 mode** 且状态为 `in_progress` / `paused` 的会话，则恢复该会话而非新建 |

**Hero Web 行为（`BankDetailPage`）：**

- 「开始练习」：`resume_if_exists=false`，每次按所选模式**新建**会话
- 「模拟考试」：固定 `mode=random`，URL 带 `?mode=mock_exam&limit=秒数`

### 2.3 获取当前题目

```http
GET /api/v1/practice/sessions/{session_id}/current
```

**2026-07 修复：** `QuestionV2.difficulty` 在库中为字符串，不可调用 `.value`；选项需序列化为 `{label, content, is_correct}` 字典列表。见 `app/api/v1/practice.py` 中 `_enum_or_str`、`_serialize_question_options`。

### 2.4 提交答案

```http
POST /api/v1/practice/sessions/{session_id}/submit
```

复合题提交格式：`{ "sub_answers": { "1": {"answer": "A"}, "2": {"answer": true} } }`。判分与脱敏见 `app/utils/composite_question.py`。

---

## 3. Hero Web 前端（`hero_web/`）

开发：`http://127.0.0.1:5173`（Vite 代理 `/api` → `8000`）  
生产：`http://localhost:8000/app-exam`

### 3.1 题库详情页

- 调用 `GET /practice/modes/preview` 展示各模式「可用 N 题」
- 0 题模式 Radio **置灰**，并显示「暂不可用」
- 题库列表请求使用 **`/qbank/banks/`**（尾斜杠），避免 307 重定向丢失 `Authorization`

### 3.2 考试页 UI（2026-07）

| 区域 | 行为 |
|------|------|
| 单选/多选/判断 | 控件与选项文字**同一行**（覆盖 HeroUI 默认 `flex-col`；选项 Markdown 使用 `RichContent inline`） |
| 底部工具栏 | **上一题**居左；**下一题、标记、收藏、提交本题**居右 |
| 题号导航 | ≤60 题默认全部展开；>60 题默认收缩，可「展开全部 / 收起」；三位数题号自适应字号 |

样式类见 `hero_web/src/index.css`（`.choice-option`、`.question-nav-grid` 等）。

### 3.3 复合题

父题 `type: "composite"`，`meta_data.sub_questions` 为子题数组；练习接口返回已脱敏的 `meta_data`。

---

## 4. 开发服务：`run.py`

启动前自动检测 **8000** 端口：

1. 若端口可绑定 → 直接启动
2. 若被占用 → 结束占用进程（Windows：`taskkill /F /T`；Unix：`SIGTERM` → `SIGKILL`）
3. 仍无法释放 → 打印警告

```powershell
cd backend
python run.py
```

仍建议使用 `reload=True` 开发；若热重载异常，可手动结束 Python/uvicorn 进程后重启。

---

## 5. 测试

### 5.1 进程内 pytest（无需启动服务，CI 标记 `@pytest.mark.ci`）

```powershell
cd backend
pytest tests/test_practice_modes.py -v
pytest tests/test_composite_question.py -v
```

`tests/test_practice_modes.py` 覆盖：

- 五种模式选题逻辑（`get_question_ids_for_session`）
- 模式预览 API 题量
- 各模式创建会话（参数化 5 种 mode）
- 顺序 vs 随机顺序、空错题 404 文案
- `resume_if_exists` true/false、不同 mode 互不恢复

使用独立 SQLite：`test_practice_modes_main.db` / `test_practice_modes_qbank.db`（5 道种子题 + 错题/收藏/答题记录）。

### 5.2 Live 手动脚本（需 `python run.py`）

```powershell
cd backend
python test_practice_api.py
```

脚本流程：登录 → 题库列表 → **模式预览** → 五种模式逐个创建会话 → 顺序练习答题冒烟。

### 5.3 CI

GitHub Actions 在 `backend/` 变更时运行 `tests/test_ci_smoke.py`；可将 `tests/test_practice_modes.py` 一并纳入本地提交前检查：

```powershell
pytest tests/test_ci_smoke.py tests/test_practice_modes.py -v
```

---

## 6. 相关源码

| 路径 | 说明 |
|------|------|
| `app/api/v1/practice.py` | 练习 API、模式选题、预览、当前题 |
| `app/schemas/practice_schemas.py` | `PracticeModeEnum`、`PracticeModePreviewResponse` |
| `app/models/user_practice.py` | `PracticeMode`、`PracticeSession` |
| `app/utils/composite_question.py` | 复合题脱敏与判分 |
| `hero_web/src/pages/BankDetailPage.tsx` | 模式选择与预览 |
| `hero_web/src/pages/ExamRoomPage.tsx` | 考试主流程 |
| `hero_web/src/components/exam/QuestionNavGrid.tsx` | 题号导航 |
| `hero_web/src/components/exam/ExamToolbar.tsx` | 底部工具栏 |
| `tests/test_practice_modes.py` | 模式自动化测试 |
| `test_practice_api.py` | Live 冒烟脚本 |

---

## 7. 常见问题

**Q：随机练习和顺序一样？**  
A：确认创建会话时 `resume_if_exists=false`；旧会话会保留原 `question_ids` 顺序。

**Q：错题/收藏专练报 404？**  
A：本题库尚无错题或收藏；先在顺序练习中答错或收藏题目。

**Q：`GET .../current` 曾返回 500？**  
A：多为 `difficulty.value` 或 ORM `options` 序列化问题，已在 `get_current_question` 修复；重启 `run.py` 确保加载新代码。

**Q：Flutter 与 Hero Web 模式是否一致？**  
A：共用同一套 `/api/v1/practice`；Flutter 默认 `resumeIfExists=true`，Hero Web「开始练习」为 `false`。
