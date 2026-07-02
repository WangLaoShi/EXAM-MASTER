"""
Integration API - Question Banks
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_main_db, get_qbank_db
from app.core.integration_auth import IntegrationContext, require_scopes, assert_bank_access
from app.schemas.qbank_schemas_v2 import QuestionBankCreate, QuestionBankUpdate, QuestionBankResponse
from app.services.integration_service import IntegrationService
from app.services.question_bank_service import QuestionBankService


router = APIRouter(prefix="/banks", tags=["Integration - Banks"])


def _svc(main_db: Session, qbank_db: Session) -> IntegrationService:
    return IntegrationService(main_db, qbank_db)


@router.get("", response_model=List[QuestionBankResponse])
async def list_banks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    ctx: IntegrationContext = Depends(require_scopes("bank:read")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    banks = svc.list_accessible_banks(ctx.owner_user_id, ctx.allowed_bank_ids, skip, limit)
    svc.log_audit(ctx.api_key.id, "GET", str(request.url.path), 200, request.client.host if request.client else None)
    return banks


@router.post("", response_model=QuestionBankResponse, status_code=201)
async def create_bank(
    request: Request,
    data: QuestionBankCreate,
    ctx: IntegrationContext = Depends(require_scopes("bank:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    qbank_svc = QuestionBankService(qbank_db)
    bank = qbank_svc.create_question_bank(
        name=data.name,
        description=data.description,
        category=data.category,
        creator_id=ctx.owner_user_id,
        tags=data.tags,
        is_public=data.is_public,
        allow_download=data.allow_download,
        allow_fork=data.allow_fork,
    )
    if ctx.allowed_bank_ids is not None:
        allowed = list(ctx.allowed_bank_ids)
        if bank.id not in allowed:
            allowed.append(bank.id)
            ctx.api_key.allowed_bank_ids = allowed
            main_db.commit()
    svc.log_audit(
        ctx.api_key.id, "POST", str(request.url.path), 201,
        request.client.host if request.client else None,
        "bank", bank.id, f"Created bank: {bank.name}",
    )
    return bank


@router.get("/{bank_id}", response_model=QuestionBankResponse)
async def get_bank(
    request: Request,
    bank_id: str,
    ctx: IntegrationContext = Depends(require_scopes("bank:read")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    svc.log_audit(ctx.api_key.id, "GET", str(request.url.path), 200, request.client.host if request.client else None, "bank", bank_id)
    return bank


@router.put("/{bank_id}", response_model=QuestionBankResponse)
async def update_bank(
    request: Request,
    bank_id: str,
    data: QuestionBankUpdate,
    ctx: IntegrationContext = Depends(require_scopes("bank:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    qbank_svc = QuestionBankService(qbank_db)
    updated = qbank_svc.update_question_bank(bank_id, **data.model_dump(exclude_unset=True))
    svc.log_audit(ctx.api_key.id, "PUT", str(request.url.path), 200, request.client.host if request.client else None, "bank", bank_id)
    return updated


@router.delete("/{bank_id}")
async def delete_bank(
    request: Request,
    bank_id: str,
    ctx: IntegrationContext = Depends(require_scopes("bank:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    QuestionBankService(qbank_db).delete_question_bank(bank_id)
    svc.log_audit(ctx.api_key.id, "DELETE", str(request.url.path), 200, request.client.host if request.client else None, "bank", bank_id)
    return {"message": "Question bank deleted"}
