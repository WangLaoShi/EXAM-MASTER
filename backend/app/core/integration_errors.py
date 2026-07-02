"""
Structured errors for Integration API
"""

from typing import Any, Optional

from fastapi import HTTPException


class ErrorCode:
    AUTH_MISSING = "AUTH_MISSING"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_IP_DENIED = "AUTH_IP_DENIED"
    RATE_LIMIT = "RATE_LIMIT"
    SCOPE_DENIED = "SCOPE_DENIED"
    BANK_NOT_FOUND = "BANK_NOT_FOUND"
    BANK_ACCESS_DENIED = "BANK_ACCESS_DENIED"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    QUESTION_DUPLICATE = "QUESTION_DUPLICATE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    IMPORT_EMPTY_FILE = "IMPORT_EMPTY_FILE"
    IMPORT_FILE_TOO_LARGE = "IMPORT_FILE_TOO_LARGE"
    IMPORT_INVALID_FORMAT = "IMPORT_INVALID_FORMAT"
    IMPORT_ZIP_EMPTY = "IMPORT_ZIP_EMPTY"
    IMPORT_ZIP_INVALID = "IMPORT_ZIP_INVALID"
    IMPORT_JSON_INVALID = "IMPORT_JSON_INVALID"
    IMPORT_CSV_INVALID = "IMPORT_CSV_INVALID"
    IMPORT_ROW_ERROR = "IMPORT_ROW_ERROR"
    BATCH_ROW_ERROR = "BATCH_ROW_ERROR"
    EXTERNAL_ID_REQUIRED = "EXTERNAL_ID_REQUIRED"


def error_detail(
    code: str,
    message: str,
    suggestion: Optional[str] = None,
    **extra: Any,
) -> dict:
    detail = {"code": code, "message": message}
    if suggestion:
        detail["suggestion"] = suggestion
    if extra:
        detail.update({k: v for k, v in extra.items() if v is not None})
    return detail


def raise_integration_error(
    status_code: int,
    code: str,
    message: str,
    suggestion: Optional[str] = None,
    **extra: Any,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=error_detail(code, message, suggestion, **extra),
    )
