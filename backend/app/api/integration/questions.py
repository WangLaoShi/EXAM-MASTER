"""
Integration API - Questions
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_main_db, get_qbank_db
from app.core.integration_auth import IntegrationContext, require_scopes, assert_bank_access
from app.models.question_models_v2 import QuestionV2, QuestionType
from app.api.integration.serializers import to_question_response
from app.schemas.integration_schemas import (
    IntegrationQuestionCreate,
    IntegrationQuestionUpdate,
    IntegrationQuestionBatchRequest,
    IntegrationBatchResult,
)
from app.schemas.qbank_schemas_v2 import QuestionResponse
from app.services.integration_service import IntegrationService


router = APIRouter(tags=["Integration - Questions"])


def _svc(main_db: Session, qbank_db: Session) -> IntegrationService:
    return IntegrationService(main_db, qbank_db)


def _load_question(qbank_db: Session, question_id: str) -> Optional[QuestionV2]:
    return qbank_db.query(QuestionV2).options(
        joinedload(QuestionV2.options)
    ).filter(QuestionV2.id == question_id).first()


@router.get("/banks/{bank_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    request: Request,
    bank_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    type: Optional[QuestionType] = None,
    ctx: IntegrationContext = Depends(require_scopes("question:read")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)

    query = qbank_db.query(QuestionV2).options(joinedload(QuestionV2.options)).filter(
        QuestionV2.bank_id == bank_id
    )
    if type:
        query = query.filter(QuestionV2.type == type)
    questions = query.order_by(QuestionV2.question_number).offset(skip).limit(limit).all()
    svc.log_audit(ctx.api_key.id, "GET", str(request.url.path), 200, request.client.host if request.client else None, "bank", bank_id)
    return [to_question_response(q) for q in questions]


@router.post("/banks/{bank_id}/questions", response_model=QuestionResponse, status_code=201)
async def create_question(
    request: Request,
    bank_id: str,
    data: IntegrationQuestionCreate,
    ctx: IntegrationContext = Depends(require_scopes("question:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    question = svc.create_question(bank_id, data, ctx.owner_user_id)
    question = _load_question(qbank_db, question.id)
    svc.log_audit(
        ctx.api_key.id, "POST", str(request.url.path), 201,
        request.client.host if request.client else None, "question", question.id,
        f"external_id={data.external_id}",
    )
    return to_question_response(question)


@router.post("/banks/{bank_id}/questions/batch", response_model=IntegrationBatchResult)
async def batch_create_questions(
    request: Request,
    bank_id: str,
    data: IntegrationQuestionBatchRequest,
    ctx: IntegrationContext = Depends(require_scopes("question:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    result = svc.batch_questions(bank_id, data.questions, ctx.owner_user_id, upsert=data.upsert)
    svc.log_audit(
        ctx.api_key.id, "POST", str(request.url.path), 200,
        request.client.host if request.client else None, "bank", bank_id,
        f"batch upsert={data.upsert} success={result.success_count} failed={result.failed_count}",
    )
    return result


@router.post("/banks/{bank_id}/questions/upsert", response_model=QuestionResponse)
async def upsert_question(
    request: Request,
    bank_id: str,
    data: IntegrationQuestionCreate,
    ctx: IntegrationContext = Depends(require_scopes("question:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    question, created = svc.upsert_question(bank_id, data, ctx.owner_user_id)
    question = _load_question(qbank_db, question.id)
    svc.log_audit(
        ctx.api_key.id, "POST", str(request.url.path), 200 if not created else 201,
        request.client.host if request.client else None, "question", question.id,
        f"upsert created={created} external_id={data.external_id}",
    )
    return to_question_response(question)


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    request: Request,
    question_id: str,
    ctx: IntegrationContext = Depends(require_scopes("question:read")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    question = qbank_db.query(QuestionV2).options(joinedload(QuestionV2.options)).filter(
        QuestionV2.id == question_id
    ).first()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")
    assert_bank_access(ctx, question.bank_id, question.bank.creator_id)
    svc.log_audit(ctx.api_key.id, "GET", str(request.url.path), 200, request.client.host if request.client else None, "question", question_id)
    return to_question_response(question)


@router.get("/questions/by-external-id/{external_id}", response_model=QuestionResponse)
async def get_question_by_external_id(
    request: Request,
    external_id: str,
    bank_id: str = Query(...),
    ctx: IntegrationContext = Depends(require_scopes("question:read")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    bank = svc.get_bank_or_404(bank_id)
    assert_bank_access(ctx, bank_id, bank.creator_id)
    question = svc.get_by_external_id(bank_id, external_id)
    question = _load_question(qbank_db, question.id)
    svc.log_audit(ctx.api_key.id, "GET", str(request.url.path), 200, request.client.host if request.client else None, "question", question.id)
    return to_question_response(question)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    request: Request,
    question_id: str,
    data: IntegrationQuestionUpdate,
    ctx: IntegrationContext = Depends(require_scopes("question:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    question = qbank_db.query(QuestionV2).filter(QuestionV2.id == question_id).first()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")
    assert_bank_access(ctx, question.bank_id, question.bank.creator_id)
    updated = svc.update_question(question_id, data, ctx.owner_user_id)
    updated = _load_question(qbank_db, updated.id)
    svc.log_audit(ctx.api_key.id, "PUT", str(request.url.path), 200, request.client.host if request.client else None, "question", question_id)
    return to_question_response(updated)


@router.delete("/questions/{question_id}")
async def delete_question(
    request: Request,
    question_id: str,
    ctx: IntegrationContext = Depends(require_scopes("question:write")),
    main_db: Session = Depends(get_main_db),
    qbank_db: Session = Depends(get_qbank_db),
):
    svc = _svc(main_db, qbank_db)
    question = qbank_db.query(QuestionV2).filter(QuestionV2.id == question_id).first()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")
    assert_bank_access(ctx, question.bank_id, question.bank.creator_id)
    svc.delete_question(question_id)
    svc.log_audit(ctx.api_key.id, "DELETE", str(request.url.path), 200, request.client.host if request.client else None, "question", question_id)
    return {"message": "Question deleted"}
