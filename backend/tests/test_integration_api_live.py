"""
Integration API 实时测试（对接运行中的 localhost:8000）

用法:
    set INTEGRATION_API_KEY=em_live_xxx
    python -m pytest tests/test_integration_api_live.py -v -s

或:
    python tests/test_integration_api_live.py
"""

import csv
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest
import requests

from tests.api_timing import (
    LIMIT_LARGE_IMPORT,
    assert_response_time,
    time_limit_for_operation,
)

BASE_URL = os.environ.get("INTEGRATION_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("INTEGRATION_API_KEY", "")
BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_CSV = BACKEND_DIR / "sample_questions.csv"
SAMPLE_ZIP = BACKEND_DIR / "sample_questions.zip"
LARGE_CSV = BACKEND_DIR / "questions.csv"
LARGE_ZIP = BACKEND_DIR / "questions.zip"

pytestmark = pytest.mark.skipif(not API_KEY, reason="请设置环境变量 INTEGRATION_API_KEY")

HEADERS = {"Authorization": f"Bearer {API_KEY}"}
JSON_HEADERS = {**HEADERS, "Content-Type": "application/json"}


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _timed_request(method: str, path: str, max_seconds: float | None = None, **kwargs):
    """发起 HTTP 请求并断言响应时间在 OpenAPI 场景阈值内。"""
    limit = max_seconds or time_limit_for_operation(method, path)
    kwargs.pop("max_seconds", None)
    kwargs.setdefault("timeout", limit + 10)
    start = time.perf_counter()
    response = requests.request(method, _url(path), **kwargs)
    elapsed = time.perf_counter() - start
    assert_response_time(elapsed, limit, f"{method} {path}")
    return response


def _get(path: str, **kwargs):
    return _timed_request("GET", path, **kwargs)


def _post(path: str, **kwargs):
    return _timed_request("POST", path, **kwargs)


def _put(path: str, **kwargs):
    return _timed_request("PUT", path, **kwargs)


def _delete(path: str, **kwargs):
    return _timed_request("DELETE", path, **kwargs)


def _detail(response) -> dict:
    body = response.json()
    detail = body.get("detail")
    if isinstance(detail, dict):
        return detail
    return {"message": detail}


def _load_sample_rows(limit: int = 10) -> list[dict]:
    """从 sample_questions.csv 解析题目，转为 Integration API 格式"""
    rows = []
    with open(SAMPLE_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            answer = (row.get("答案") or "").strip().upper()
            options = []
            for label in ["A", "B", "C", "D", "E"]:
                content = (row.get(label) or "").strip()
                if content:
                    options.append({
                        "label": label,
                        "content": content,
                        "is_correct": label in answer,
                    })
            rows.append({
                "external_id": f"py-sample-{row['题号']}",
                "stem": row["题干"],
                "type": "multiple" if len(answer) > 1 else "single",
                "difficulty": row.get("难度") or "medium",
                "category": row.get("题型"),
                "explanation": row.get("解析"),
                "question_number": int(row["题号"]),
                "options": options,
            })
            if len(rows) >= limit:
                break
    return rows


def _count_csv_rows(path: Path) -> int:
    with open(path, encoding="utf-8-sig") as f:
        return sum(1 for _ in csv.DictReader(f))


@pytest.fixture(scope="module")
def bank_id():
    """创建测试题库，测试结束后删除"""
    payload = {
        "name": "Integration API 自动化测试题库",
        "description": "由 test_integration_api_live.py 创建，可安全删除",
        "category": "integration-test",
        "is_public": False,
    }
    r = _post("/api/integration/banks"), json=payload, headers=JSON_HEADERS, timeout=30)
    assert r.status_code == 201, f"创建题库失败: {r.status_code} {r.text}"
    bid = r.json()["id"]
    yield bid
    _delete(f"/api/integration/banks/{bid}"), headers=HEADERS, timeout=30)


@pytest.fixture(scope="module")
def large_bank_id():
    """881 题大文件导入专用题库"""
    payload = {
        "name": "Integration API 大文件导入测试题库",
        "description": "questions.csv / questions.zip 881 题",
        "category": "integration-test-large",
        "is_public": False,
    }
    r = _post("/api/integration/banks"), json=payload, headers=JSON_HEADERS, timeout=30)
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    yield bid
    _delete(f"/api/integration/banks/{bid}"), headers=HEADERS, timeout=120)


class TestIntegrationHealth:
    """TC-01: API Key 认证与健康检查"""

    def test_health_with_bearer(self):
        r = _get("/api/integration/health"), headers=HEADERS, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "scopes" in data
        assert "key_name" in data
        print(f"  Key: {data['key_name']}, Scopes: {data['scopes']}")

    def test_health_with_x_api_key_header(self):
        r = _get("/api/integration/health",headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        assert r.status_code == 200

    def test_missing_key_rejected(self):
        r = _get("/api/integration/health", timeout=10)
        assert r.status_code == 401
        detail = _detail(r)
        assert detail["code"] == "AUTH_MISSING"
        assert "suggestion" in detail

    def test_invalid_key_rejected(self):
        r = _get("/api/integration/health",headers={"Authorization": "Bearer em_live_invalid"},
            timeout=10,
        )
        assert r.status_code == 401
        detail = _detail(r)
        assert detail["code"] == "AUTH_INVALID"
        assert "suggestion" in detail


class TestIntegrationErrors:
    """TC-E01 ~ TC-E10: 常见错误场景"""

    def test_bank_not_found(self):
        r = _get("/api/integration/banks/non-existent-bank-id",headers=HEADERS,
            timeout=10,
        )
        assert r.status_code == 404
        detail = _detail(r)
        assert detail["code"] == "BANK_NOT_FOUND"

    def test_question_not_found_by_external_id(self, bank_id):
        r = _get("/api/integration/questions/by-external-id/does-not-exist",params={"bank_id": bank_id},
            headers=HEADERS,
            timeout=10,
        )
        assert r.status_code == 404
        assert _detail(r)["code"] == "QUESTION_NOT_FOUND"

    def test_duplicate_external_id_on_create(self, bank_id):
        q = _load_sample_rows(1)[0]
        _post(f"/api/integration/banks/{bank_id}/questions/upsert",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        r = _post(f"/api/integration/banks/{bank_id}/questions",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code == 409
        detail = _detail(r)
        assert detail["code"] == "QUESTION_DUPLICATE"
        assert detail.get("external_id") == q["external_id"]

    def test_upsert_requires_external_id(self, bank_id):
        r = _post(f"/api/integration/banks/{bank_id}/questions/upsert",json={"stem": "无 external_id", "type": "single"},
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "EXTERNAL_ID_REQUIRED"

    def test_import_empty_csv(self, bank_id):
        buf = io.BytesIO(b"")
        r = _post(f"/api/integration/banks/{bank_id}/import/csv",headers=HEADERS,
            files={"file": ("empty.csv", buf, "text/csv")},
            timeout=30,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "IMPORT_EMPTY_FILE"

    def test_import_wrong_extension(self, bank_id):
        buf = io.BytesIO(b"not csv")
        r = _post(f"/api/integration/banks/{bank_id}/import/csv",headers=HEADERS,
            files={"file": ("data.txt", buf, "text/plain")},
            timeout=30,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "IMPORT_INVALID_FORMAT"

    def test_import_invalid_zip(self, bank_id):
        buf = io.BytesIO(b"not a zip file")
        r = _post(f"/api/integration/banks/{bank_id}/import/zip",headers=HEADERS,
            files={"file": ("bad.zip", buf, "application/zip")},
            timeout=30,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "IMPORT_ZIP_INVALID"

    def test_import_empty_zip(self, bank_id):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass
        buf.seek(0)
        r = _post(f"/api/integration/banks/{bank_id}/import/zip",headers=HEADERS,
            files={"file": ("empty.zip", buf, "application/zip")},
            timeout=30,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "IMPORT_ZIP_EMPTY"

    def test_import_invalid_json(self, bank_id):
        buf = io.BytesIO(b"{not json")
        r = _post(f"/api/integration/banks/{bank_id}/import/json",headers=HEADERS,
            files={"file": ("bad.json", buf, "application/json")},
            timeout=30,
        )
        assert r.status_code == 400
        assert _detail(r)["code"] == "IMPORT_JSON_INVALID"

    def test_import_result_has_message_fields(self, bank_id):
        """成功导入响应应包含 message / duration_ms 等字段"""
        assert SAMPLE_CSV.exists()
        with open(SAMPLE_CSV, "rb") as f:
            r = _post(f"/api/integration/banks/{bank_id}/import/csv",params={"external_id_prefix": "py-sample"},
                headers=HEADERS,
                files={"file": ("sample_questions.csv", f, "text/csv")},
                timeout=60,
            )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["success"] is True
        assert result["message"]
        assert result["total_rows"] == 10
        assert result["duration_ms"] is not None
        assert "created_count" in result
        assert "updated_count" in result


class TestIntegrationBanks:
    """TC-02 ~ TC-06: 题库 CRUD"""

    def test_list_banks(self, bank_id):
        r = _get("/api/integration/banks"), headers=HEADERS, timeout=10)
        assert r.status_code == 200
        banks = r.json()
        assert isinstance(banks, list)
        assert any(b["id"] == bank_id for b in banks)

    def test_get_bank(self, bank_id):
        r = _get(f"/api/integration/banks/{bank_id}"), headers=HEADERS, timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == bank_id
        assert "Integration API" in r.json()["name"]

    def test_update_bank(self, bank_id):
        r = _put(f"/api/integration/banks/{bank_id}",json={"description": "已更新描述 - integration test"},
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code == 200
        assert "已更新描述" in r.json()["description"]


class TestIntegrationQuestions:
    """TC-07 ~ TC-14: 题目单条/批量/upsert/查询/修改/删除（基于 sample_questions.csv）"""

    def test_create_single_question(self, bank_id):
        """TC-07: 单题创建 — sample_questions.csv 第1题"""
        q = _load_sample_rows(1)[0]
        # 先 upsert 确保存在，再测 create 重复会 409（见 TestIntegrationErrors）
        _post(f"/api/integration/banks/{bank_id}/questions/upsert",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        r = _post(f"/api/integration/banks/{bank_id}/questions",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code in (201, 409)

    def test_get_question_by_external_id(self, bank_id):
        """TC-08: 按 external_id 查询"""
        external_id = "py-sample-1"
        r = _get(f"/api/integration/questions/by-external-id/{external_id}",params={"bank_id": bank_id},
            headers=HEADERS,
            timeout=10,
        )
        assert r.status_code == 200
        assert "Python" in r.json()["stem"]

    def test_update_question(self, bank_id):
        """TC-09: 修改题目"""
        external_id = "py-sample-1"
        get_r = _get(f"/api/integration/questions/by-external-id/{external_id}",params={"bank_id": bank_id},
            headers=HEADERS,
            timeout=10,
        )
        qid = get_r.json()["id"]
        r = _put(f"/api/integration/questions/{qid}",json={"explanation": "【已更新】Python是一种解释型的高级编程语言"},
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code == 200
        assert "【已更新】" in r.json()["explanation"]

    def test_batch_create_questions(self, bank_id):
        """TC-10: 批量创建 — csv 第2~5题"""
        questions = _load_sample_rows(5)[1:5]
        r = _post(f"/api/integration/banks/{bank_id}/questions/batch",json={"upsert": True, "questions": questions},
            headers=JSON_HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["success_count"] == 4
        assert result["failed_count"] == 0
        assert result["message"]

    def test_batch_upsert(self, bank_id):
        """TC-11: 批量 upsert — 更新第1题 + 新增第6题"""
        q1 = _load_sample_rows(1)[0]
        q1["explanation"] = "【upsert更新】解释型语言"
        q6 = _load_sample_rows(6)[5]
        r = _post(f"/api/integration/banks/{bank_id}/questions/batch",json={"upsert": True, "questions": [q1, q6]},
            headers=JSON_HEADERS,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["success_count"] == 2
        assert result["updated_count"] >= 1

    def test_upsert_single(self, bank_id):
        """TC-12: 单条 upsert"""
        q = _load_sample_rows(7)[6]
        r = _post(f"/api/integration/banks/{bank_id}/questions/upsert",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert "字符串" in r.json()["stem"]

    def test_list_questions(self, bank_id):
        """TC-13: 题目列表"""
        r = _get(f"/api/integration/banks/{bank_id}/questions",params={"limit": 100},
            headers=HEADERS,
            timeout=10,
        )
        assert r.status_code == 200
        questions = r.json()
        assert len(questions) >= 6

    def test_delete_question(self, bank_id):
        """TC-14: 删除题目"""
        external_id = "py-sample-10"
        q = _load_sample_rows(10)[9]
        _post(f"/api/integration/banks/{bank_id}/questions/upsert",json=q,
            headers=JSON_HEADERS,
            timeout=10,
        )
        get_r = _get(f"/api/integration/questions/by-external-id/{external_id}",params={"bank_id": bank_id},
            headers=HEADERS,
            timeout=10,
        )
        qid = get_r.json()["id"]
        r = _delete(f"/api/integration/questions/{qid}",headers=HEADERS,
            timeout=10,
        )
        assert r.status_code == 200


class TestIntegrationImport:
    """TC-15 ~ TC-17: CSV/JSON/ZIP 批量导入（小样本）"""

    def test_import_zip_sample_questions(self, bank_id):
        """TC-17: ZIP 压缩包导入 — sample_questions.zip（内含 CSV）"""
        assert SAMPLE_ZIP.exists(), f"缺少测试文件: {SAMPLE_ZIP}"
        with open(SAMPLE_ZIP, "rb") as f:
            r = _post(f"/api/integration/banks/{bank_id}/import/zip",params={"external_id_prefix": "py-sample"},
                headers=HEADERS,
                files={"file": ("sample_questions.zip", f, "application/zip")},
                timeout=60,
            )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["imported_count"] == 10, result
        assert result["failed_count"] == 0, result
        assert result["success"] is True
        print(f"  ZIP 导入: {result['message']}")

        check = _get("/api/integration/questions/by-external-id/py-sample-1",params={"bank_id": bank_id},
            headers=HEADERS,
            timeout=10,
        )
        assert check.status_code == 200

    def test_import_csv_sample_questions(self, bank_id):
        """TC-15: 直接导入 sample_questions.csv（中文列名）"""
        assert SAMPLE_CSV.exists()
        with open(SAMPLE_CSV, "rb") as f:
            r = _post(f"/api/integration/banks/{bank_id}/import/csv",params={"external_id_prefix": "py-sample"},
                headers=HEADERS,
                files={"file": ("sample_questions.csv", f, "text/csv")},
                timeout=60,
            )
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["imported_count"] == 10, result
        assert result["total_rows"] == 10
        print(f"  CSV 导入: {result['message']}")

    def test_import_json(self, bank_id):
        """TC-16: JSON 批量导入"""
        questions = _load_sample_rows(3)
        payload = {"questions": questions}
        buf = io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        r = _post(f"/api/integration/banks/{bank_id}/import/json",params={"external_id_prefix": "py-sample"},
            headers=HEADERS,
            files={"file": ("questions.json", buf, "application/json")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["imported_count"] >= 3


@pytest.mark.slow
class TestIntegrationLargeImport:
    """TC-L01 ~ TC-L03: questions.csv / questions.zip（881 题）"""

    @pytest.fixture(scope="class")
    def expected_rows(self):
        assert LARGE_CSV.exists(), f"缺少 {LARGE_CSV}"
        return _count_csv_rows(LARGE_CSV)

    def test_import_large_csv(self, large_bank_id, expected_rows):
        """TC-L01: 881 题 CSV 导入"""
        assert expected_rows >= 880, f"questions.csv 行数异常: {expected_rows}"
        with open(LARGE_CSV, "rb") as f:
            r = _post(
                f"/api/integration/banks/{large_bank_id}/import/csv",
                params={"external_id_prefix": "maoshi"},
                headers=HEADERS,
                files={"file": ("questions.csv", f, "text/csv")},
                max_seconds=LIMIT_LARGE_IMPORT,
            )
        assert r.status_code == 200, r.text[:500]
        result = r.json()
        assert result["failed_count"] == 0, result.get("errors", [])[:3]
        assert result["imported_count"] == expected_rows, result
        assert result["total_rows"] == expected_rows
        assert result["success"] is True
        assert result["duration_ms"] < LIMIT_LARGE_IMPORT * 1000, result
        print(f"  大 CSV: {result['message']}, duration={result['duration_ms']}ms")

        check = _get("/api/integration/questions/by-external-id/maoshi-1",params={"bank_id": large_bank_id},
            headers=HEADERS,
            timeout=10,
        )
        assert check.status_code == 200

    def test_import_large_zip(self, large_bank_id, expected_rows):
        """TC-L02: 881 题 ZIP 导入（upsert 幂等）"""
        assert LARGE_ZIP.exists(), f"缺少 {LARGE_ZIP}"
        with open(LARGE_ZIP, "rb") as f:
            r = _post(
                f"/api/integration/banks/{large_bank_id}/import/zip",
                params={"external_id_prefix": "maoshi"},
                headers=HEADERS,
                files={"file": ("questions.zip", f, "application/zip")},
                max_seconds=LIMIT_LARGE_IMPORT,
            )
        assert r.status_code == 200, r.text[:500]
        result = r.json()
        assert result["failed_count"] == 0, result.get("errors", [])[:3]
        assert result["imported_count"] == expected_rows
        assert result["updated_count"] >= expected_rows  # 第二次应为更新
        print(f"  大 ZIP upsert: {result['message']}")

    def test_large_bank_question_count(self, large_bank_id, expected_rows):
        """TC-L03: 列表抽样验证题目数量"""
        r = _get(f"/api/integration/banks/{large_bank_id}/questions",params={"limit": 500},
            headers=HEADERS,
            timeout=30,
        )
        assert r.status_code == 200
        # limit=500 时至少能拉到 500 题
        assert len(r.json()) >= min(500, expected_rows)


def run_standalone():
    """无 pytest 时直接运行并打印结果"""
    print(f"Base URL: {BASE_URL}")
    print(f"Sample CSV: {SAMPLE_CSV}")
    print(f"Large CSV: {LARGE_CSV} ({_count_csv_rows(LARGE_CSV) if LARGE_CSV.exists() else 'N/A'} rows)")
    exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    run_standalone()
