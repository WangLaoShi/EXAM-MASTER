"""
OpenAPI 规范解析与冒烟请求构造

从 /openapi.json 读取全部 operation，用于全接口覆盖测试。
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from dataclasses import dataclass
from typing import Any, Callable, Optional

from tests.api_timing import (
    SERVER_ERROR_STATUSES,
    assert_response_time,
    time_limit_for_operation,
)

# 占位 ID：用于路径参数，预期 404/403 亦可，但不能 5xx
PLACEHOLDER_IDS = {
    "bank_id": "00000000-0000-4000-8000-000000000001",
    "question_id": "00000000-0000-4000-8000-000000000002",
    "user_id": "1",
    "external_id": "openapi-smoke-test",
    "resource_id": "00000000-0000-4000-8000-000000000003",
    "session_id": "00000000-0000-4000-8000-000000000004",
    "interface_id": "1",
    "template_id": "1",
    "config_id": "1",
    "code_id": "1",
    "access_id": "1",
    "favorite_id": "1",
    "wrong_question_id": "1",
    "option_id": "1",
    "tool_name": "list_tools",
    "key_id": "00000000-0000-4000-8000-000000000099",
}

# 需要真实文件或副作用过大，跳过自动冒烟（由专项测试覆盖）
SKIP_PATH_PATTERNS = [
    re.compile(r"/import/(csv|json|zip)$"),
    re.compile(r"/upload"),
    re.compile(r"/batch-upload"),
    re.compile(r"/admin/imports/csv$"),
    re.compile(r"/admin/v2/imports/"),
    re.compile(r"/admin/agent-test/chat$"),
    re.compile(r"/llm/parse$"),
    re.compile(r"/llm/import$"),
    re.compile(r"/llm/interfaces/.+/test$"),
    re.compile(r"/admin/ai-configs/test-"),
    re.compile(r"/mcp/execute$"),
    re.compile(r"/mcp/batch$"),
    re.compile(r"/questions/.+/images$"),
    re.compile(r"/export/"),
]

# 可接受的非成功状态（路由存在、鉴权/校验生效）
ACCEPTABLE_STATUSES = {
    200, 201, 204,
    301, 302, 303, 307, 308,
    400, 401, 403, 404, 405, 409, 413, 422, 429,
}


@dataclass(frozen=True)
class OpenAPIOperation:
    """单个 OpenAPI operation 描述。"""

    operation_id: str
    method: str
    path: str
    tags: tuple[str, ...]
    requires_auth: bool
    security_schemes: tuple[str, ...]
    summary: str

    @property
    def display_name(self) -> str:
        return f"{self.method.upper()} {self.path}"


def load_openapi_spec(fetch_json: Callable[[], dict]) -> dict:
    """拉取并返回 OpenAPI JSON。"""
    spec = fetch_json()
    assert "paths" in spec, "OpenAPI 缺少 paths"
    return spec


def _resolve_path(path: str) -> str:
    """将 {param} 替换为占位值。"""

    def replacer(match: re.Match) -> str:
        name = match.group(1)
        return PLACEHOLDER_IDS.get(name, str(uuid.uuid4()))

    return re.sub(r"\{([^}]+)\}", replacer, path)


def _should_skip(path: str, method: str) -> bool:
    for pattern in SKIP_PATH_PATTERNS:
        if pattern.search(path):
            return True
    # POST /admin/login 由专项测试处理
    if path == "/admin/login" and method.upper() == "POST":
        return True
    return False


def _parse_security(operation: dict, spec: dict) -> tuple[bool, tuple[str, ...]]:
    security = operation.get("security")
    if security is None:
        # 全局 security
        security = spec.get("security", [])
    if not security:
        return False, ()
    schemes = []
    for item in security:
        schemes.extend(item.keys())
    return True, tuple(schemes)


def iter_operations(spec: dict) -> list[OpenAPIOperation]:
    """从 OpenAPI spec 解析全部 operation。"""
    ops: list[OpenAPIOperation] = []
    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                continue
            if not isinstance(operation, dict):
                continue
            if _should_skip(path, method):
                continue
            requires_auth, schemes = _parse_security(operation, spec)
            tags = tuple(operation.get("tags") or ("default",))
            op_id = operation.get("operationId") or f"{method}_{path}"
            ops.append(
                OpenAPIOperation(
                    operation_id=op_id,
                    method=method.upper(),
                    path=path,
                    tags=tags,
                    requires_auth=requires_auth,
                    security_schemes=schemes,
                    summary=operation.get("summary") or "",
                )
            )
    return ops


def classify_operation(op: OpenAPIOperation) -> str:
    """分类：public / jwt / integration / admin。"""
    if op.path.startswith("/api/integration"):
        return "integration"
    if op.path.startswith("/admin"):
        return "admin"
    if not op.requires_auth:
        return "public"
    return "jwt"


def build_request_kwargs(op: OpenAPIOperation) -> dict[str, Any]:
    """构造 requests/TestClient 的 kwargs（最小 body/query）。"""
    kwargs: dict[str, Any] = {}
    path = _resolve_path(op.path)

    if op.method in ("POST", "PUT", "PATCH"):
        if "/auth/login" in op.path:
            kwargs["data"] = {"username": "openapi-smoke", "password": "openapi-smoke"}
        # 表单类 admin 路由
        elif op.path.startswith("/admin") and "login" not in op.path:
            if "password" in op.path or op.path.endswith("/login"):
                kwargs["data"] = {}
            else:
                kwargs["data"] = {}
        elif "application/json" in _guess_content_type(op):
            kwargs["json"] = {}
        elif op.path.startswith("/admin"):
            kwargs["data"] = {}

    if "by-external-id" in op.path:
        kwargs["params"] = {"bank_id": PLACEHOLDER_IDS["bank_id"]}

    return {"path": path, **kwargs}


def _guess_content_type(op: OpenAPIOperation) -> str:
    if op.path.startswith("/admin"):
        return "form"
    return "application/json"


@dataclass(frozen=True)
class SmokeResult:
    """单次冒烟请求结果，便于 pytest 逐条报告。"""

    operation: OpenAPIOperation
    status_code: int
    elapsed: float

    @property
    def elapsed_ms(self) -> float:
        return round(self.elapsed * 1000, 1)

    def summary(self) -> str:
        return (
            f"{self.operation.display_name} → HTTP {self.status_code} "
            f"({self.elapsed_ms}ms, limit={time_limit_for_operation(self.operation.method, self.operation.path)}s)"
        )


def smoke_call(
    request_fn: Callable,
    op: OpenAPIOperation,
    headers: Optional[dict] = None,
    cookies: Optional[dict] = None,
) -> SmokeResult:
    """
    执行单次冒烟请求。
    request_fn(method, url, headers=, cookies=, json=, ...) -> response-like with .status_code
    """
    req = build_request_kwargs(op)
    path = req.pop("path")
    limit = time_limit_for_operation(op.method, op.path)

    start = time.perf_counter()
    response = request_fn(
        op.method,
        path,
        headers=headers or {},
        cookies=cookies or {},
        timeout=limit + 5,
        **{k: v for k, v in req.items() if k not in ("path",)},
    )
    elapsed = time.perf_counter() - start

    if response.status_code in SERVER_ERROR_STATUSES:
        body = ""
        if hasattr(response, "text"):
            body = (response.text or "")[:400].replace("\n", " ")
        raise AssertionError(
            f"{op.display_name} 返回服务端错误 {response.status_code}"
            + (f" | body={body!r}" if body else "")
        )
    assert response.status_code in ACCEPTABLE_STATUSES, (
        f"{op.display_name} 返回意外状态 {response.status_code}"
        + (f" | body={(getattr(response, 'text', '') or '')[:200]}" if hasattr(response, "text") else "")
    )
    assert_response_time(elapsed, limit, op.display_name)
    return SmokeResult(operation=op, status_code=response.status_code, elapsed=elapsed)
