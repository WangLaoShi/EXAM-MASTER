# Integration API 对接手册

远端业务系统通过 **Integration API Key** 调用 `/api/integration/` 接口，完成题库创建、题目同步与批量导入。该通道与面向终端用户的 JWT API、Admin Cookie 登录相互隔离。

---

## 目录

1. [快速开始](#1-快速开始)
2. [认证与安全](#2-认证与安全)
3. [权限范围（Scopes）](#3-权限范围scopes)
4. [统一错误格式](#4-统一错误格式)
5. [API 端点一览](#5-api-端点一览)
6. [题库接口](#6-题库接口)
7. [题目接口](#7-题目接口)
8. [批量导入](#8-批量导入)
9. [CSV 格式说明](#9-csv-格式说明)
10. [external_id 与幂等](#10-external_id-与幂等)
11. [对接建议与重试策略](#11-对接建议与重试策略)
12. [自动化测试](#12-自动化测试)

---

## 1. 快速开始

### 1.1 申请 API Key

1. 登录管理后台：`http://<host>:8000/admin`
2. 进入 **集成 API Key**
3. 填写名称、勾选权限范围，点击「生成 API Key」
4. **立即复制**完整 Key（仅显示一次）

Key 格式示例：`em_live_YdB2EgyL0vFzgVwESnb6qtbat-7YqMdHrZWzB0MORSo`

### 1.2 验证连通性

```bash
curl -s -H "Authorization: Bearer em_live_你的key" \
  http://localhost:8000/api/integration/health | jq
```

成功响应示例：

```json
{
  "status": "ok",
  "key_name": "教务系统-生产",
  "scopes": ["bank:write", "question:write", "question:import"],
  "owner_user_id": 1
}
```

### 1.3 最小对接流程

```
申请 Key → health 自检 → POST 创建题库 → CSV/ZIP 导入或 JSON 批量 upsert → 按 external_id 查询校验
```

---

## 2. 认证与安全

### 2.1 认证方式（二选一）

```http
Authorization: Bearer em_live_xxxxxxxx
```

```http
X-API-Key: em_live_xxxxxxxx
```

### 2.2 安全机制

| 机制 | 说明 |
|------|------|
| Key 哈希存储 | 服务端只存 hash，明文 Key 丢失后需重新申请 |
| 吊销 | Admin 后台吊销后立即失效 |
| IP 白名单 | 可选，未在白名单内返回 `AUTH_IP_DENIED` |
| 速率限制 | 默认 120 次/分钟，超出返回 `RATE_LIMIT` |
| 题库隔离 | Key 可限定 `allowed_bank_ids`；未限定时仅可操作 Key 归属账号创建的题库 |
| 审计日志 | 每次调用写入 Admin → 集成 API Key → 日志 |

### 2.3 Base URL

| 环境 | 地址 |
|------|------|
| 本地开发 | `http://localhost:8000` |
| 生产 | 由运维提供，建议使用 HTTPS |

OpenAPI 交互文档：`http://<host>:8000/api/docs`（标签 **Integration**）

---

## 3. 权限范围（Scopes）

| Scope | 说明 |
|-------|------|
| `bank:read` | 读取题库列表与详情 |
| `bank:write` | 创建 / 修改 / 删除题库 |
| `question:read` | 读取题目 |
| `question:write` | 单题增删改、批量、upsert |
| `question:import` | CSV / JSON / ZIP 文件导入 |
| `resource:write` | 上传资源（预留） |

缺少 scope 时 HTTP **403**，`detail.code = SCOPE_DENIED`，并返回 `required_scope` 与 `your_scopes`。

---

## 4. 统一错误格式

HTTP 4xx/5xx 时，响应体一般为：

```json
{
  "detail": {
    "code": "BANK_NOT_FOUND",
    "message": "题库不存在：abc-123",
    "suggestion": "请调用 GET /api/integration/banks 确认可用题库 ID",
    "bank_id": "abc-123"
  }
}
```

### 4.1 错误码一览

| code | HTTP | 含义 | 处理建议 |
|------|------|------|----------|
| `AUTH_MISSING` | 401 | 未携带 Key | 检查 Header |
| `AUTH_INVALID` | 401 | Key 无效或已吊销 | 重新申请 Key |
| `AUTH_EXPIRED` | 401 | Key 已过期 | 联系管理员续期 |
| `AUTH_IP_DENIED` | 403 | IP 不在白名单 | 添加 IP 或换出口 |
| `RATE_LIMIT` | 429 | 请求过于频繁 | 降频或提高限额 |
| `SCOPE_DENIED` | 403 | 权限不足 | 勾选对应 scope |
| `BANK_NOT_FOUND` | 404 | 题库不存在 | 确认 bank_id |
| `BANK_ACCESS_DENIED` | 403 | 无权访问该题库 | 检查 Key 归属与限定题库 |
| `QUESTION_NOT_FOUND` | 404 | 题目不存在 | 确认 id / external_id |
| `QUESTION_DUPLICATE` | 409 | external_id 重复（create 模式） | 改用 upsert |
| `EXTERNAL_ID_REQUIRED` | 400 | upsert 缺少 external_id | 补充 external_id |
| `VALIDATION_ERROR` | 422 | 请求体校验失败 | 对照 OpenAPI 修正字段 |
| `IMPORT_EMPTY_FILE` | 400 | 上传文件为空 | 检查文件内容 |
| `IMPORT_FILE_TOO_LARGE` | 413 | 超过上传大小限制 | 拆分文件 |
| `IMPORT_INVALID_FORMAT` | 400 | 扩展名不支持 | 使用 .csv / .json / .zip |
| `IMPORT_ZIP_EMPTY` | 400 | ZIP 内无可识别文件 | 放入 CSV 或 questions.json |
| `IMPORT_ZIP_INVALID` | 400 | ZIP 损坏 | 重新打包 |
| `IMPORT_JSON_INVALID` | 400 | JSON 无法解析 | 检查 UTF-8 与结构 |
| `IMPORT_CSV_INVALID` | 400 | CSV 无表头 | 补充表头行 |
| `IMPORT_ROW_ERROR` | — | 某行数据错误 | 见 errors 数组 |
| `BATCH_ROW_ERROR` | — | 批量 JSON 某条失败 | 见 errors 数组 |

### 4.2 导入 / 批量部分成功

导入与 batch 接口在**部分行失败**时仍返回 HTTP **200**，响应体中：

| 字段 | 说明 |
|------|------|
| `success` | 是否全部成功 |
| `partial` | 是否部分成功 |
| `message` | 人类可读摘要 |
| `errors` | 错误明细数组（最多 50 条） |
| `errors_truncated` | 是否截断 |

单条错误结构：

```json
{
  "code": "IMPORT_ROW_ERROR",
  "message": "第 12 行有答案「AB」但未找到选项列 A~F",
  "row": 12,
  "external_id": "maoshi-12",
  "suggestion": "检查该行选项列与答案列是否匹配"
}
```

---

## 5. API 端点一览

### 健康检查

| 方法 | 路径 | Scope |
|------|------|-------|
| GET | `/api/integration/health` | 任意有效 Key |

### 题库

| 方法 | 路径 | Scope |
|------|------|-------|
| GET | `/api/integration/banks` | bank:read |
| POST | `/api/integration/banks` | bank:write |
| GET | `/api/integration/banks/{bank_id}` | bank:read |
| PUT | `/api/integration/banks/{bank_id}` | bank:write |
| DELETE | `/api/integration/banks/{bank_id}` | bank:write |

### 题目

| 方法 | 路径 | Scope |
|------|------|-------|
| GET | `/api/integration/banks/{bank_id}/questions` | question:read |
| POST | `/api/integration/banks/{bank_id}/questions` | question:write |
| POST | `/api/integration/banks/{bank_id}/questions/batch` | question:write |
| POST | `/api/integration/banks/{bank_id}/questions/upsert` | question:write |
| GET | `/api/integration/questions/{question_id}` | question:read |
| GET | `/api/integration/questions/by-external-id/{external_id}?bank_id=` | question:read |
| PUT | `/api/integration/questions/{question_id}` | question:write |
| DELETE | `/api/integration/questions/{question_id}` | question:write |

### 批量导入

| 方法 | 路径 | Scope |
|------|------|-------|
| POST | `/api/integration/banks/{bank_id}/import/json` | question:import |
| POST | `/api/integration/banks/{bank_id}/import/csv` | question:import |
| POST | `/api/integration/banks/{bank_id}/import/zip` | question:import |

---

## 6. 题库接口

### 6.1 创建题库

```bash
curl -X POST http://localhost:8000/api/integration/banks \
  -H "Authorization: Bearer em_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "2026春季期末考试",
    "description": "远端同步",
    "category": "exam",
    "is_public": false
  }'
```

响应 **201**，返回 `id`（即后续路径中的 `bank_id`）。

### 6.2 查询题库

```bash
curl -H "Authorization: Bearer em_live_xxx" \
  http://localhost:8000/api/integration/banks
```

---

## 7. 题目接口

### 7.1 单题创建

`external_id` 在同一题库内唯一；重复创建返回 **409** `QUESTION_DUPLICATE`。

```bash
curl -X POST http://localhost:8000/api/integration/banks/{bank_id}/questions \
  -H "Authorization: Bearer em_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "remote-q-001",
    "stem": "1+1=?",
    "type": "single",
    "difficulty": "medium",
    "options": [
      {"label": "A", "content": "1", "is_correct": false},
      {"label": "B", "content": "2", "is_correct": true}
    ]
  }'
```

### 7.2 单题 upsert（推荐）

按 `external_id` 存在则更新，不存在则创建：

```bash
curl -X POST http://localhost:8000/api/integration/banks/{bank_id}/questions/upsert \
  -H "Authorization: Bearer em_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{ "external_id": "remote-q-001", "stem": "更新后的题干", "type": "single" }'
```

### 7.3 批量 upsert

```bash
curl -X POST http://localhost:8000/api/integration/banks/{bank_id}/questions/batch \
  -H "Authorization: Bearer em_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "upsert": true,
    "questions": [
      {
        "external_id": "q1",
        "stem": "题目1",
        "type": "single",
        "options": [
          {"label": "A", "content": "对", "is_correct": true},
          {"label": "B", "content": "错", "is_correct": false}
        ]
      }
    ]
  }'
```

批量响应字段：`success_count`、`created_count`、`updated_count`、`failed_count`、`message`、`errors`。

### 7.4 按 external_id 查询

```bash
curl -H "Authorization: Bearer em_live_xxx" \
  "http://localhost:8000/api/integration/questions/by-external-id/maoshi-1?bank_id={bank_id}"
```

响应中 `question_code` 即导入时的 `external_id`。

### 7.5 题型枚举

| type 值 | 说明 |
|---------|------|
| `single` | 单选题 |
| `multiple` | 多选题 |
| `judge` | 判断题 |
| `fill` | 填空题 |
| `essay` | 简答 / 问答 |

---

## 8. 批量导入

三种导入方式均支持 Query 参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `external_id_prefix` | `import` | 远端 ID 前缀，最终 `external_id = {prefix}-{题号}` |

> **重要**：若 CSV 使用「题号」列而非独立 `external_id` 列，务必设置正确前缀，否则默认生成 `import-1`、`import-2`…

### 8.1 CSV 导入

```bash
curl -X POST "http://localhost:8000/api/integration/banks/{bank_id}/import/csv?external_id_prefix=maoshi" \
  -H "Authorization: Bearer em_live_xxx" \
  -F "file=@questions.csv"
```

### 8.2 ZIP 导入

ZIP 内可包含：

- 一个或多个 `.csv` 文件
- 或 `questions.json`（标准 JSON 题库）

```bash
curl -X POST "http://localhost:8000/api/integration/banks/{bank_id}/import/zip?external_id_prefix=maoshi" \
  -H "Authorization: Bearer em_live_xxx" \
  -F "file=@questions.zip"
```

### 8.3 JSON 导入

文件结构：

```json
{
  "questions": [
    {
      "external_id": "q001",
      "stem": "题干",
      "type": "single",
      "options": [
        {"label": "A", "content": "选项A", "is_correct": true}
      ]
    }
  ]
}
```

根节点也可直接为数组 `[{...}, {...}]`。

### 8.4 导入成功响应示例

```json
{
  "success": true,
  "partial": false,
  "message": "导入完成：成功 881 题（新建 881，更新 0），跳过 0 行，耗时 45230ms",
  "bank_id": "xxx",
  "total_rows": 881,
  "imported_count": 881,
  "created_count": 881,
  "updated_count": 0,
  "skipped_count": 0,
  "failed_count": 0,
  "errors": [],
  "errors_truncated": false,
  "duration_ms": 45230,
  "source_files": ["questions.csv"]
}
```

### 8.5 导入前校验清单

| 检查项 | 失败 code |
|--------|-----------|
| 文件为空 | `IMPORT_EMPTY_FILE` |
| 扩展名错误（如 .txt 传 csv 接口） | `IMPORT_INVALID_FORMAT` |
| 超过大小限制（默认约 50MB） | `IMPORT_FILE_TOO_LARGE` |
| ZIP 损坏 | `IMPORT_ZIP_INVALID` |
| ZIP 内无 CSV/JSON | `IMPORT_ZIP_EMPTY` |
| JSON 语法错误 | `IMPORT_JSON_INVALID` |
| CSV 无表头 | `IMPORT_CSV_INVALID` |
| 某行题干为空 | 跳过，`skipped_count++` |
| 某行有答案无选项 | `IMPORT_ROW_ERROR` |

---

## 9. CSV 格式说明

### 9.1 中文列名（推荐，与 `questions.csv` 一致）

| 列名 | 必填 | 说明 |
|------|------|------|
| 题号 | 建议 | 用于生成 external_id |
| 题干 | 是 | 题目正文 |
| A ~ F | 视题型 | 选项内容 |
| 答案 | 建议 | 如 `A` 或 `ABC`（多选） |
| 难度 | 否 | `无` → medium；也支持 easy/medium/hard |
| 题型 | 否 | `单选题`/`多选题` 等；缺省按答案长度推断 |

示例（`questions.csv`，共 881 题）：

```csv
题号,题干,A,B,C,D,E,答案,难度,题型
1,下列关于…,选项A,选项B,选项C,选项D,,A,无,单选题
2,以下哪些…,…,…,…,…,,ABC,无,多选题
```

### 9.2 英文列名（兼容）

`stem`、`option_a`~`option_f`、`correct_answer`、`type`、`external_id`、`explanation`、`difficulty`、`category`

### 9.3 题型映射

| CSV 题型 | API type |
|----------|----------|
| 单选题 | single |
| 多选题 | multiple |
| 判断题 | judge |
| 填空题 | fill |
| 简答题 / 问答题 | essay |

---

## 10. external_id 与幂等

- 请求字段 `external_id` 映射到数据库 `question_code`
- 导入时：`external_id = {external_id_prefix}-{题号}`（若 CSV 无独立 external_id 列）
- **create** 模式：重复 external_id → 409
- **upsert** 模式（import / batch upsert / questions/upsert）：重复则更新

对接方应保证：

1. 同一远端题目始终使用同一 `external_id`
2. 不同业务线使用不同 `external_id_prefix`（如 `maoshi`、`course-2026`）
3. 全量同步时使用 import（内部 upsert），可安全重复执行

---

## 11. 对接建议与重试策略

### 11.1 推荐同步方案

| 场景 | 方案 |
|------|------|
| 首次全量（800+ 题） | ZIP 或 CSV + `external_id_prefix` |
| 增量更新 | `POST .../questions/upsert` 或 batch upsert |
| 校验 | `GET .../by-external-id/{id}?bank_id=` |

### 11.2 重试策略

| HTTP | 是否重试 |
|------|----------|
| 401 / 403 | 否，修正 Key 或权限 |
| 404 | 否，修正 bank_id / external_id |
| 409 | 否，改用 upsert |
| 429 | 是，指数退避 |
| 5xx / 超时 | 是，有限次重试；import 可幂等重跑 |

### 11.3 性能参考

- 881 题 CSV 导入：约 30~90 秒（视硬件而定）
- 建议单次 import 不超过数千题；更大体量拆分多个 ZIP

### 11.4 常见问题

**Q: 导入成功但查不到题？**  
A: 检查 `external_id_prefix` 是否与查询一致（如导入用 `maoshi` 则查 `maoshi-1`）。

**Q: 重复导入会 duplicate 吗？**  
A: import 内部走 upsert，相同 external_id 会更新，`updated_count` 增加。

**Q: CSV 中文乱码？**  
A: 使用 UTF-8（带 BOM 也可），服务端按 `utf-8-sig` 解码。

**Q: multipart 字段名？**  
A: 必须为 `file`。

---

## 12. 自动化测试

测试文件：`tests/test_integration_api_live.py`

数据文件：

| 文件 | 题数 | 用途 |
|------|------|------|
| `sample_questions.csv` / `.zip` | 10 | 功能回归 |
| `questions.csv` / `.zip` | 881 | 大文件与性能 |

```powershell
cd backend
$env:INTEGRATION_API_KEY = "em_live_你的key"
python -m pytest tests/test_integration_api_live.py -v -s
```

### 测试用例矩阵

| 编号 | 类别 | 用例 | 说明 |
|------|------|------|------|
| TC-01 | Health | Bearer / X-API-Key / 缺 Key / 非法 Key | 结构化错误码 |
| TC-E01~E10 | Errors | 404 题库、404 题目、409 重复、空文件、错误扩展名、坏 ZIP 等 | 错误提示覆盖 |
| TC-02~04 | Banks | 列表 / 详情 / 更新 | 题库 CRUD |
| TC-07~14 | Questions | 单题 / 查询 / 修改 / batch / upsert / 删除 | sample 10 题 |
| TC-15~17 | Import | CSV / JSON / ZIP 小样本 | `external_id_prefix=py-sample` |
| TC-L01~L03 | Large | 881 题 CSV / ZIP upsert / 列表抽样 | `external_id_prefix=maoshi` |

---

## 附录：联系与支持

- OpenAPI：`/api/docs`
- Admin 审计：Admin → 集成 API Key → 操作日志
- 问题排查顺序：health → bank 列表 → 单题 upsert → 小 CSV → 大文件
