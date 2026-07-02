"""
Integration API - Import 路由

上传校验（空文件/扩展名/大小）→ IntegrationService 导入 → 审计日志。
Query 参数 external_id_prefix 控制 CSV 题号列生成的 external_id。
"""

import io

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_main_db, get_qbank_db
from app.core.integration_auth import IntegrationContext, require_scopes, assert_bank_access
from app.core.integration_errors import ErrorCode, raise_integration_error
from app.schemas.integration_schemas import IntegrationImportResult
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/banks/{bank_id}/import", tags=["Integration - Import"])

MAX_IMPORT_BYTES = getattr(settings, "max_upload_size", 52_428_800)


async def _read_upload(file: UploadFile, allowed_extensions: tuple[str, ...]) -> bytes:
    if not file.filename:
        raise_integration_error(
            400, ErrorCode.IMPORT_INVALID_FORMAT, "未收到文件名",
            suggestion="multipart 字段名应为 file",
        )
    if not file.filename.lower().endswith(allowed_extensions):
        raise_integration_error(
            400, ErrorCode.IMPORT_INVALID_FORMAT,
            f"不支持的文件类型：{file.filename}",
            suggestion=f"仅支持：{', '.join(allowed_extensions)}",
        )
    content = await file.read()
    if not content:
        raise_integration_error(
            400, ErrorCode.IMPORT_EMPTY_FILE, "上传文件为空",
            suggestion="请确认文件有内容且未损坏",
        )
    if len(content) > MAX_IMPORT_BYTES:
        raise_integration_error(
            413, ErrorCode.IMPORT_FILE_TOO_LARGE,
            f"文件过大（{len(content)} 字节），上限 {MAX_IMPORT_BYTES} 字节",
            suggestion="请拆分批量导入，或联系管理员提高上传限制",
        )
    return content


def _wrap_upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


def _audit_import(svc, ctx, request, bank_id, result, fmt: str):
    status = 200 if result.success else (207 if result.partial else 422)
    svc.log_audit(
        ctx.api_key.id, "POST", str(request.url.path), status,
        request.client.host if request.client else None, "bank", bank_id,
        f"{fmt} imported={result.imported_count} failed={result.failed_count} partial={result.partial}",
    )


@router.post("/json", response_model=IntegrationImportResult)
async def import_json(
    request: Request,
    bank_id: str,
    file: UploadFile = File(...),
    external_id_prefix: str = Query(
        "import",
        description="远端题目 ID 前缀，最终 external_id 为 {prefix}-{题号或id}",
    ),
    ctx: IntegrationContext = Depends(require_scopes("question:import")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    content = await _read_upload(file, (".json",))
    svc = IntegrationService(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    result = await svc.import_json_to_bank(
        bank_id, _wrap_upload(file.filename, content), ctx.owner_user_id, external_id_prefix,
    )
    _audit_import(svc, ctx, request, bank_id, result, "json")
    return result


@router.post("/csv", response_model=IntegrationImportResult)
async def import_csv(
    request: Request,
    bank_id: str,
    file: UploadFile = File(...),
    external_id_prefix: str = Query("import", description="external_id 前缀，如 maoshi → maoshi-1"),
    ctx: IntegrationContext = Depends(require_scopes("question:import")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    content = await _read_upload(file, (".csv",))
    svc = IntegrationService(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    result = await svc.import_csv_to_bank(
        bank_id, _wrap_upload(file.filename, content), ctx.owner_user_id, external_id_prefix,
    )
    _audit_import(svc, ctx, request, bank_id, result, "csv")
    return result


@router.post("/zip", response_model=IntegrationImportResult)
async def import_zip(
    request: Request,
    bank_id: str,
    file: UploadFile = File(...),
    external_id_prefix: str = Query("import", description="external_id 前缀"),
    ctx: IntegrationContext = Depends(require_scopes("question:import")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    content = await _read_upload(file, (".zip",))
    svc = IntegrationService(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    result = await svc.import_zip_to_bank(
        bank_id, _wrap_upload(file.filename, content), ctx.owner_user_id, external_id_prefix,
    )
    _audit_import(svc, ctx, request, bank_id, result, "zip")
    return result
