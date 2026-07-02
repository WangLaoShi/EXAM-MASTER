"""
OpenAPI 全接口冒烟测试（对齐 /api/docs 中全部 operation）

每个 OpenAPI operation 对应一条独立 pytest 用例，`-v` 下可看到逐条 PASS/FAIL。

依赖运行中的服务：http://localhost:8000

环境变量:
    LIVE_BASE_URL          默认 http://localhost:8000
    TEST_ADMIN_USER        JWT / Admin 登录用户名，默认 admin
    TEST_ADMIN_PASS        密码，默认 admin123
    INTEGRATION_API_KEY    Integration 接口（/api/integration/*）

用法:
    cd backend
    $env:TEST_ADMIN_USER="admin"
    $env:TEST_ADMIN_PASS="admin123"
    $env:INTEGRATION_API_KEY="em_live_xxx"
    python -m pytest tests/test_openapi_full_live.py -v --tb=short -ra
    python -m pytest tests/test_openapi_full_live.py -v -k "integration" --tb=long
"""

from __future__ import annotations

import os
from typing import Callable

import pytest
import requests

from tests.api_timing import LIMIT_DOCS, assert_elapsed
from tests.openapi_client import (
    OpenAPIOperation,
    classify_operation,
    iter_operations,
    load_openapi_spec,
    smoke_call,
)

BASE_URL = os.environ.get("LIVE_BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_USER = os.environ.get("TEST_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("TEST_ADMIN_PASS", "admin123")
INTEGRATION_KEY = os.environ.get("INTEGRATION_API_KEY", "")

_OPS_BY_KIND: dict[str, list[OpenAPIOperation]] | None = None


def _server_up() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _load_operations_by_kind() -> dict[str, list[OpenAPIOperation]]:
    global _OPS_BY_KIND
    if _OPS_BY_KIND is not None:
        return _OPS_BY_KIND

    by_kind: dict[str, list[OpenAPIOperation]] = {
        "public": [],
        "jwt": [],
        "admin": [],
        "integration": [],
    }
    if not _server_up():
        _OPS_BY_KIND = by_kind
        return by_kind

    try:
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=LIMIT_DOCS + 5)
        r.raise_for_status()
        spec = load_openapi_spec(lambda: r.json())
        for op in iter_operations(spec):
            by_kind[classify_operation(op)].append(op)
    except requests.RequestException:
        pass

    _OPS_BY_KIND = by_kind
    return by_kind


def _op_test_id(op: OpenAPIOperation) -> str:
    path_part = op.path.strip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"
    return f"{op.method.lower()}__{path_part}"[:100]


def pytest_generate_tests(metafunc):
    """按 OpenAPI operation 逐条生成测试用例。"""
    if "operation" not in metafunc.fixturenames:
        return

    kind = getattr(metafunc.cls, "openapi_kind", None)
    if not kind:
        return

    ops = _load_operations_by_kind().get(kind, [])
    metafunc.parametrize("operation", ops, ids=[_op_test_id(o) for o in ops])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """在 verbose 报告中附加 HTTP 状态与耗时。"""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    props = dict(item.user_properties)
    status = props.get("http_status")
    elapsed = props.get("elapsed_ms")
    if status is not None:
        report.sections.append(
            ("smoke", f"HTTP {status} | {elapsed}ms | {props.get('operation', '')}")
        )


def _record_result(request: pytest.FixtureRequest, result) -> None:
    request.node.user_properties.append(("http_status", result.status_code))
    request.node.user_properties.append(("elapsed_ms", result.elapsed_ms))
    request.node.user_properties.append(("operation", result.operation.display_name))


pytestmark = pytest.mark.skipif(not _server_up(), reason=f"服务未启动: {BASE_URL}")


@pytest.fixture(scope="module")
def openapi_spec():
    def fetch():
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=LIMIT_DOCS + 2)
        r.raise_for_status()
        return r.json()

    return load_openapi_spec(fetch)


@pytest.fixture(scope="module")
def all_operations(openapi_spec):
    ops = iter_operations(openapi_spec)
    assert len(ops) > 50, f"OpenAPI operation 数量异常: {len(ops)}"
    return ops


@pytest.fixture(scope="module")
def jwt_headers():
    r = requests.post(
        f"{BASE_URL}/api/v2/auth/login",
        data={"username": ADMIN_USER, "password": ADMIN_PASS},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(f"JWT 登录失败: {r.status_code} {r.text[:200]}")
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_session():
    session = requests.Session()
    r = session.post(
        f"{BASE_URL}/admin/login",
        data={"username": ADMIN_USER, "password": ADMIN_PASS},
        timeout=10,
        allow_redirects=True,
    )
    if r.status_code not in (200, 303):
        pytest.skip(f"Admin Session 登录失败: {r.status_code}")
    return session


@pytest.fixture(scope="module")
def integration_headers():
    if not INTEGRATION_KEY:
        pytest.skip("未设置 INTEGRATION_API_KEY")
    return {"Authorization": f"Bearer {INTEGRATION_KEY}"}


def _requests_call(method, path, headers=None, cookies=None, timeout=30, **kwargs):
    url = f"{BASE_URL}{path}"
    return requests.request(
        method, url, headers=headers or {}, cookies=cookies or {}, timeout=timeout, **kwargs
    )


def _run_smoke(
    request: pytest.FixtureRequest,
    call_fn: Callable,
    operation: OpenAPIOperation,
    **kwargs,
) -> None:
    result = smoke_call(call_fn, operation, **kwargs)
    _record_result(request, result)


class TestOpenAPIMeta:
    """文档与规范元数据（3 条）"""

    def test_openapi_json(self):
        with assert_elapsed(LIMIT_DOCS, "GET /openapi.json"):
            r = requests.get(f"{BASE_URL}/openapi.json", timeout=LIMIT_DOCS + 2)
        assert r.status_code == 200
        assert "paths" in r.json()

    def test_api_docs(self):
        with assert_elapsed(LIMIT_DOCS, "GET /api/docs"):
            r = requests.get(f"{BASE_URL}/api/docs", timeout=LIMIT_DOCS + 2)
        assert r.status_code == 200
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower()

    def test_api_redoc(self):
        with assert_elapsed(LIMIT_DOCS, "GET /api/redoc"):
            r = requests.get(f"{BASE_URL}/api/redoc", timeout=LIMIT_DOCS + 2)
        assert r.status_code == 200


class TestOpenAPIPublicSmoke:
    """无需鉴权的 OpenAPI operation（逐条）"""

    openapi_kind = "public"

    def test_operation(self, request, operation: OpenAPIOperation):
        _run_smoke(request, _requests_call, operation)


class TestOpenAPIJWTSmoke:
    """需要 JWT Bearer 的 operation（逐条）"""

    openapi_kind = "jwt"

    def test_operation(self, request, operation: OpenAPIOperation, jwt_headers):
        _run_smoke(request, _requests_call, operation, headers=jwt_headers)


class TestOpenAPIAdminSmoke:
    """Admin 面板 HTML / 表单路由（Session Cookie，逐条）"""

    openapi_kind = "admin"

    def test_operation(self, request, operation: OpenAPIOperation, admin_session):
        def _admin_call(method, path, headers=None, cookies=None, timeout=30, **kwargs):
            url = f"{BASE_URL}{path}"
            return admin_session.request(method, url, timeout=timeout, **kwargs)

        _run_smoke(request, _admin_call, operation)


class TestOpenAPIIntegrationSmoke:
    """Integration API operation（逐条）"""

    openapi_kind = "integration"

    def test_operation(self, request, operation: OpenAPIOperation, integration_headers):
        _run_smoke(request, _requests_call, operation, headers=integration_headers)


class TestOpenAPICoverageSummary:
    """统计 OpenAPI 覆盖范围（1 条）"""

    def test_operation_counts(self, all_operations):
        by_kind = {"public": 0, "jwt": 0, "admin": 0, "integration": 0}
        for op in all_operations:
            by_kind[classify_operation(op)] += 1
        total = sum(by_kind.values())
        print(f"\n  OpenAPI 冒烟覆盖: total={total}, {by_kind}")
        assert total > 100, f"operation 总数过少: {total}"
        assert by_kind["jwt"] > 30
        assert by_kind["admin"] > 10
        assert by_kind["integration"] >= 5
