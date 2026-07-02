"""Serialize ORM objects for Integration API responses."""

from app.models.question_models_v2 import QuestionV2
from app.schemas.qbank_schemas_v2 import (
    QuestionResponse,
    question_bank_to_response as to_bank_response,
    OptionData,
    QuestionTypeEnum,
    DifficultyEnum,
)


def to_question_response(question: QuestionV2) -> QuestionResponse:
    qtype = question.type.value if hasattr(question.type, "value") else question.type
    try:
        difficulty = DifficultyEnum(question.difficulty)
    except ValueError:
        difficulty = DifficultyEnum.medium

    options = [
        OptionData(
            label=opt.option_label,
            content=opt.option_content,
            is_correct=opt.is_correct,
            explanation=getattr(opt, "explanation", None),
        )
        for opt in (question.options or [])
    ]

    return QuestionResponse(
        id=question.id,
        bank_id=question.bank_id,
        question_number=question.question_number,
        question_code=question.question_code,
        stem=question.stem,
        stem_format=question.stem_format or "text",
        type=QuestionTypeEnum(qtype),
        difficulty=difficulty,
        score=question.score or 1.0,
        category=question.category,
        sub_category=question.sub_category,
        tags=question.tags or [],
        explanation=question.explanation,
        explanation_format=question.explanation_format or "text",
        hint=question.hint,
        source=question.source,
        has_images=question.has_images or False,
        has_audio=question.has_audio or False,
        has_video=question.has_video or False,
        has_formula=question.has_formula or False,
        usage_count=question.usage_count or 0,
        error_count=question.error_count or 0,
        avg_score=question.avg_score,
        avg_time=question.avg_time,
        meta_data=question.meta_data,
        created_at=question.created_at,
        updated_at=question.updated_at,
        options=options,
    )
