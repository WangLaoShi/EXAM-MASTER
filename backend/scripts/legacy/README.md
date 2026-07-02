# 历史维护脚本（Legacy Maintenance Scripts）

本目录存放**一次性数据修复工具**，用于迁移旧数据或排查问题。

> **正常开发/部署不需要运行这些脚本。** 应用启动时 `init_databases()` 会自动建表；新数据库无需手动迁移。

在 `backend` 目录下、已激活 venv 后执行，例如：

```bash
python scripts/legacy/fix_question_types.py
```

---

## SQL 脚本（`sql/`）

| 文件 | 用途 | 是否还需要 |
|------|------|-----------|
| `add_agent_fields_migration.sql` | 为旧版 `ai_configs` 表添加 `enable_agent`、`max_tool_iterations` 字段 | 仅**升级旧库**时需要；新库由模型自动创建 |
| `check_duplicate_question_numbers.sql` | 查询重复题号（只读诊断） | 排查题号问题时可用 |
| `fix_empty_question_types.sql` | 将空 `type` 批量改为 `single` | 与 `fix_question_types.py` 重复，优先用 Python 版 |
| `fix_question_numbers.sql` | 重排题号 | **PostgreSQL 语法**，本项目用 SQLite，请用 `fix_question_numbers.py` |

---

## Python 脚本

### 数据库修复（直接改 SQLite）

| 文件 | 修复内容 | 何时使用 |
|------|---------|---------|
| `fix_question_types.py` | 空/无效 `type` → 默认 `single` | 导入后题目类型为空 |
| `fix_question_type.py` | `question`→`essay`，`true_false`→`judge` | 旧版枚举名残留 |
| `fix_enum_values.py` | 去掉 `QuestionType.` 前缀 | 类型字段含枚举类名 |
| `fix_question_numbers.py` | 重排各题库连续题号 | 题号重复或缺失 |
| `fix_judge_meta_data.py` | 修正判断题 `meta_data` 格式 | 判断题答案格式错误 |

### JSON 导入修复（改题库 JSON 文件）

| 文件 | 修复内容 | 用法 |
|------|---------|------|
| `fix_judge_answer_format.py` | 判断题答案 `"正确"` → `{"answer": true}` | `python fix_judge_answer_format.py input.json [output.json]` |
| `fix_fill_answer_format.py` | 填空题答案 → `blanks` 数组格式 | 同上 |
| `fix_essay_answer_format.py` | 问答题答案 → `reference_answer` 格式 | 同上 |

---

## 与正式流程的关系

| 场景 | 正确做法 |
|------|---------|
| 全新安装 | `python run.py`（自动建表）→ `python init_admin.py` |
| AI Agent 字段 | 已包含在 `app/models/ai_models.py`，新库无需跑 SQL |
| 数据问题 | 按需选用上表中的诊断/修复脚本 |
