"""
Integration API 导入结果汇总

负责：
- 构造结构化错误项（含 suggestion）
- 截断 errors 列表（避免响应过大）
- 生成人类可读的 message / duration_ms
"""

import time
from typing import List

from fastapi import HTTPException

from app.core.integration_errors import ErrorCode
from app.schemas.integration_schemas import (
    IntegrationImportResult,
    IntegrationBatchResult,
    IntegrationErrorDetail,
)

# 响应中最多返回的错误条数，超出时 errors_truncated=True
MAX_ERRORS_IN_RESPONSE = 50


def make_error(
    code: str,
    message: str,
    row: int = None,
    external_id: str = None,
    field: str = None,
    suggestion: str = None,
) -> IntegrationErrorDetail:
    """构造单条导入/批量错误详情。"""
    return IntegrationErrorDetail(
        code=code,
        message=message,
        row=row,
        external_id=external_id,
        field=field,
        suggestion=suggestion,
    )


def error_from_exception(exc: Exception, row: int = None, external_id: str = None) -> IntegrationErrorDetail:
    """将异常转为 IntegrationErrorDetail，保留 HTTPException 中的 code/suggestion。"""
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            return IntegrationErrorDetail(
                code=detail.get("code", ErrorCode.IMPORT_ROW_ERROR),
                message=detail.get("message", str(detail)),
                suggestion=detail.get("suggestion"),
                row=row,
                external_id=external_id or detail.get("external_id"),
                field=detail.get("field"),
            )
        return make_error(ErrorCode.IMPORT_ROW_ERROR, str(detail), row=row, external_id=external_id)
    return make_error(ErrorCode.IMPORT_ROW_ERROR, str(exc), row=row, external_id=external_id)


def truncate_errors(errors: list) -> tuple[list, bool]:
    """截断错误列表，返回 (截断后列表, 是否被截断)。"""
    if len(errors) <= MAX_ERRORS_IN_RESPONSE:
        return errors, False
    return errors[:MAX_ERRORS_IN_RESPONSE], True


def finalize_import_result(
    result: IntegrationImportResult,
    start_time: float,
    total_rows: int,
) -> IntegrationImportResult:
    """汇总导入结果：success/partial/message/duration_ms。"""
    result.total_rows = total_rows
    result.duration_ms = int((time.time() - start_time) * 1000)
    result.errors, result.errors_truncated = truncate_errors(result.errors)

    if result.failed_count == 0:
        result.success = True
        result.partial = False
        if result.imported_count == 0 and result.skipped_count > 0:
            result.message = f"未导入任何题目，跳过 {result.skipped_count} 行空数据"
        else:
            result.message = (
                f"导入完成：成功 {result.imported_count} 题"
                f"（新建 {result.created_count}，更新 {result.updated_count}）"
                f"，跳过 {result.skipped_count} 行，耗时 {result.duration_ms}ms"
            )
    elif result.imported_count > 0:
        result.success = False
        result.partial = True
        result.message = (
            f"部分成功：成功 {result.imported_count} 题，失败 {result.failed_count} 行，"
            f"跳过 {result.skipped_count} 行"
        )
    else:
        result.success = False
        result.partial = False
        result.message = f"导入失败：{result.failed_count} 行错误，跳过 {result.skipped_count} 行"

    if result.errors_truncated:
        result.message += f"（仅返回前 {MAX_ERRORS_IN_RESPONSE} 条错误详情）"

    return result


def finalize_batch_result(result: IntegrationBatchResult, total: int) -> IntegrationBatchResult:
    """汇总 JSON batch 结果。"""
    result.total = total
    result.errors, result.errors_truncated = truncate_errors(result.errors)

    if result.failed_count == 0:
        result.success = True
        result.partial = False
        result.message = (
            f"批量处理完成：成功 {result.success_count} 题"
            f"（新建 {result.created_count}，更新 {result.updated_count}）"
        )
    elif result.success_count > 0:
        result.success = False
        result.partial = True
        result.message = (
            f"部分成功：成功 {result.success_count} 题，失败 {result.failed_count} 题"
        )
    else:
        result.success = False
        result.partial = False
        result.message = f"批量处理失败：全部 {result.failed_count} 题均未成功"

    if result.errors_truncated:
        result.message += f"（仅返回前 {MAX_ERRORS_IN_RESPONSE} 条错误详情）"

    return result
