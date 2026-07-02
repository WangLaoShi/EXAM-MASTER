"""
测试耗时断言工具

用于 live 测试与 TestClient 测试，确保接口在预期时间内响应。
阈值可按路径/场景调整，见 `time_limit_for_operation`。
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)

# 默认上限（秒）
LIMIT_PUBLIC = 3.0
LIMIT_AUTH = 5.0
LIMIT_ADMIN_HTML = 3.0
LIMIT_DOCS = 3.0
LIMIT_INTEGRATION = 10.0
LIMIT_IMPORT = 60.0
LIMIT_LARGE_IMPORT = 15.0
LIMIT_DEFAULT = 5.0

# 不可接受的 HTTP 状态（服务端异常）
SERVER_ERROR_STATUSES = {500, 502, 503, 504}


def time_limit_for_operation(method: str, path: str) -> float:
    """根据 HTTP 方法与路径返回耗时上限（秒）。"""
    path_lower = path.lower()
    method_upper = method.upper()

    if path in ("/api/docs", "/openapi.json", "/api/redoc", "/docs", "/redoc"):
        return LIMIT_DOCS
    if path in ("/", "/health", "/api/v2/", "/api/v2/health"):
        return LIMIT_PUBLIC
    if "/import/" in path_lower and method_upper == "POST":
        return LIMIT_IMPORT
    if path_lower.startswith("/admin") and method_upper == "GET":
        return LIMIT_ADMIN_HTML
    if "/api/integration/" in path_lower:
        if "/import/" in path_lower:
            return LIMIT_LARGE_IMPORT
        return LIMIT_INTEGRATION
    if method_upper == "GET":
        return LIMIT_AUTH
    return LIMIT_DEFAULT


@contextmanager
def assert_elapsed(max_seconds: float, label: str = "操作"):
    """上下文管理器：块内代码执行时间不得超过 max_seconds。"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    assert elapsed <= max_seconds, (
        f"{label} 耗时 {elapsed:.3f}s，超过上限 {max_seconds}s"
    )


def assert_response_time(elapsed: float, max_seconds: float, label: str = "请求") -> None:
    """断言单次请求耗时。"""
    assert elapsed <= max_seconds, (
        f"{label} 耗时 {elapsed:.3f}s，超过上限 {max_seconds}s"
    )


def assert_not_server_error(status_code: int, context: str = "") -> None:
    """冒烟测试：不允许 5xx。"""
    assert status_code not in SERVER_ERROR_STATUSES, (
        f"{context} 返回服务端错误 {status_code}"
    )


def time_limit(seconds: float):
    """装饰器：整个测试函数耗时上限。"""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - start
            assert elapsed <= seconds, (
                f"{fn.__name__} 总耗时 {elapsed:.3f}s，超过上限 {seconds}s"
            )
            return result

        return wrapper  # type: ignore

    return decorator


def timed_request(request_fn: Callable, *args, max_seconds: float | None = None, label: str = "请求", **kwargs):
    """
    执行 request_fn(*args, **kwargs)，返回 (result, elapsed)。
    若提供 max_seconds 则断言耗时。
    """
    start = time.perf_counter()
    result = request_fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    if max_seconds is not None:
        assert_response_time(elapsed, max_seconds, label)
    return result, elapsed
