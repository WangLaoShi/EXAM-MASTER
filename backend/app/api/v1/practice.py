"""
Practice Session API - 答题会话管理
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime
import uuid
import random
import json

from app.core.database import get_qbank_db, get_main_db
from app.core.security import get_current_user
from app.models.user_models import User, UserBankPermission
from app.models.user_practice import (
    PracticeSession, UserAnswerRecord, UserFavorite, UserWrongQuestion,
    PracticeMode, SessionStatus
)
from app.models.user_statistics import UserBankStatistics
from app.models.question_models_v2 import QuestionV2, QuestionType
from app.utils.composite_question import get_practice_meta_data, grade_composite_answer
from app.models.activation import UserBankAccess
from app.schemas.practice_schemas import (
    PracticeSessionCreate,
    PracticeSessionUpdate,
    PracticeSessionResponse,
    PracticeSessionListResponse,
    AnswerSubmit,
    AnswerResult,
    UserAnswerRecordResponse,
    AnswerHistoryResponse,
    PracticeQuestionWithProgress,
    SessionStatistics,
    PracticeModePreviewResponse,
)

router = APIRouter()


# ==================== Helper Functions ====================

def _enum_or_str(value):
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    return value


def _serialize_question_options(question) -> Optional[List[Dict[str, Any]]]:
    if not question.options:
        return None
    return [
        {
            "label": opt.option_label,
            "content": opt.option_content,
            "is_correct": opt.is_correct,
        }
        for opt in question.options
    ]


def _coerce_practice_mode(mode) -> PracticeMode:
    if isinstance(mode, PracticeMode):
        return mode
    if hasattr(mode, "value"):
        return PracticeMode(mode.value)
    return PracticeMode(mode)


def _empty_mode_message(mode: PracticeMode) -> str:
    messages = {
        PracticeMode.wrong_only: "当前题库暂无错题，请先练习并答错后再使用错题专练",
        PracticeMode.favorite_only: "当前题库暂无收藏题目，请先在练习中收藏题目",
        PracticeMode.unpracticed: "当前题库所有题目都已练习过",
    }
    return messages.get(mode, "没有找到符合条件的题目")


def check_bank_access(main_db: Session, qbank_db: Session, user: User, bank_id: str) -> bool:
    """检查用户是否有权限访问题库"""
    # Admin users have access to all banks
    if user.role == "admin":
        return True

    # Check if bank is public
    from app.models.question_models_v2 import QuestionBankV2
    bank = qbank_db.query(QuestionBankV2).filter(QuestionBankV2.id == bank_id).first()
    if bank and bank.is_public:
        return True

    # Check UserBankPermission (legacy system) - in main_db
    perm = main_db.query(UserBankPermission).filter(
        and_(
            UserBankPermission.user_id == user.id,
            UserBankPermission.bank_id == bank_id
        )
    ).first()

    if perm and perm.permission in ["read", "write", "admin"]:
        return True

    # Check UserBankAccess (new activation system) - in qbank_db
    access = qbank_db.query(UserBankAccess).filter(
        and_(
            UserBankAccess.user_id == user.id,
            UserBankAccess.bank_id == bank_id,
            UserBankAccess.is_active == True
        )
    ).first()

    if access:
        # Check if not expired
        if access.expire_at is None or access.expire_at > datetime.utcnow():
            return True

    return False


def _update_bank_statistics(
    db: Session,
    user_id: int,
    bank_id: str,
    question_id: str,
    is_correct: bool,
    time_spent: int
):
    """更新题库统计数据"""

    # 查找或创建统计记录
    stats = db.query(UserBankStatistics).filter(
        and_(
            UserBankStatistics.user_id == user_id,
            UserBankStatistics.bank_id == bank_id
        )
    ).first()

    if not stats:
        # 获取题库总题数
        total_questions = db.query(func.count(QuestionV2.id)).filter(
            QuestionV2.bank_id == bank_id
        ).scalar() or 0

        stats = UserBankStatistics(
            id=str(uuid.uuid4()),
            user_id=user_id,
            bank_id=bank_id,
            total_questions=total_questions,
            practiced_questions=0,
            correct_count=0,
            wrong_count=0,
            accuracy_rate=0.0,
            favorite_count=0,
            wrong_questions_count=0,
            total_time_spent=0,
            first_practiced_at=datetime.utcnow()
        )
        db.add(stats)

    # 检查这道题之前做过几次（统计不重复的题目数）
    previous_answer_count = db.query(func.count(UserAnswerRecord.id)).filter(
        and_(
            UserAnswerRecord.user_id == user_id,
            UserAnswerRecord.question_id == question_id,
            UserAnswerRecord.bank_id == bank_id
        )
    ).scalar() or 0

    # 如果是第一次做这道题（包括本次），增加已练习题目数
    if previous_answer_count == 1:
        stats.practiced_questions += 1

    # 更新正确/错误统计
    if is_correct:
        stats.correct_count += 1
    else:
        stats.wrong_count += 1

    # 更新正确率
    total_answered = stats.correct_count + stats.wrong_count
    if total_answered > 0:
        stats.accuracy_rate = (stats.correct_count / total_answered) * 100

    # 更新总用时
    stats.total_time_spent += (time_spent or 0)

    # 更新最后练习时间
    stats.last_practiced_at = datetime.utcnow()

    # 更新收藏数量
    favorite_count = db.query(func.count(UserFavorite.id)).filter(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.bank_id == bank_id
        )
    ).scalar() or 0
    stats.favorite_count = favorite_count

    # 更新错题数量（未订正的）
    wrong_questions_count = db.query(func.count(UserWrongQuestion.id)).filter(
        and_(
            UserWrongQuestion.user_id == user_id,
            UserWrongQuestion.bank_id == bank_id,
            UserWrongQuestion.corrected == False
        )
    ).scalar() or 0
    stats.wrong_questions_count = wrong_questions_count

    db.commit()


def get_question_ids_for_session(
    db: Session,
    bank_id: str,
    user_id: int,
    mode: PracticeMode,
    question_types: Optional[List[str]] = None,
    difficulty: Optional[str] = None
) -> List[str]:
    """根据模式和筛选条件获取题目ID列表"""
    mode = _coerce_practice_mode(mode)

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting question IDs: mode={mode}, user_id={user_id}, bank_id={bank_id}")

    if mode == PracticeMode.wrong_only:
        # 错题模式：获取所有错题（包括已订正和未订正）
        query = db.query(UserWrongQuestion.question_id).filter(
            and_(
                UserWrongQuestion.user_id == user_id,
                UserWrongQuestion.bank_id == bank_id
            )
        )
        question_ids = [q[0] for q in query.all()]
        logger.info(f"Wrong questions mode: found {len(question_ids)} questions")

    elif mode == PracticeMode.favorite_only:
        # 收藏模式：只获取收藏题目
        query = db.query(UserFavorite.question_id).filter(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.bank_id == bank_id
            )
        )
        question_ids = [q[0] for q in query.all()]
        logger.info(f"Favorite mode: found {len(question_ids)} questions")

        # 如果没有找到收藏，记录详细信息
        if not question_ids:
            total_favorites = db.query(UserFavorite).filter(UserFavorite.user_id == user_id).count()
            logger.warning(f"No favorites found for bank_id={bank_id}, but user has {total_favorites} total favorites")

    elif mode == PracticeMode.unpracticed:
        # 未练习模式：获取用户从未答过的题目
        # 先获取所有题目ID
        all_questions_query = db.query(QuestionV2.id).filter(
            QuestionV2.bank_id == bank_id
        )

        # 应用筛选条件
        if question_types:
            all_questions_query = all_questions_query.filter(QuestionV2.type.in_(question_types))
        if difficulty:
            all_questions_query = all_questions_query.filter(QuestionV2.difficulty == difficulty)

        all_question_ids = set(q[0] for q in all_questions_query.all())

        # 获取用户已答过的题目ID
        answered_query = db.query(UserAnswerRecord.question_id).filter(
            and_(
                UserAnswerRecord.user_id == user_id,
                UserAnswerRecord.bank_id == bank_id
            )
        ).distinct()
        answered_ids = set(q[0] for q in answered_query.all())

        # 未练习的题目 = 所有题目 - 已答过的题目
        question_ids = list(all_question_ids - answered_ids)

    else:
        # 顺序或随机模式：获取所有符合条件的题目
        query = db.query(QuestionV2.id).filter(
            QuestionV2.bank_id == bank_id
        )

        # 应用筛选条件
        if question_types:
            query = query.filter(QuestionV2.type.in_(question_types))
        if difficulty:
            query = query.filter(QuestionV2.difficulty == difficulty)

        question_ids = [q[0] for q in query.all()]

    # 随机模式：打乱顺序
    if mode == PracticeMode.random:
        random.shuffle(question_ids)

    return question_ids


@router.get("/modes/preview", response_model=PracticeModePreviewResponse, tags=["📝 Practice"])
async def preview_practice_modes(
    bank_id: str = Query(..., description="题库ID"),
    current_user: User = Depends(get_current_user),
    qbank_db: Session = Depends(get_qbank_db),
    main_db: Session = Depends(get_main_db),
):
    """预览各练习模式在本题库下可用的题目数量"""
    if not check_bank_access(main_db, qbank_db, current_user, bank_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有访问该题库的权限",
        )

    total = get_question_ids_for_session(qbank_db, bank_id, current_user.id, PracticeMode.sequential)
    wrong = get_question_ids_for_session(qbank_db, bank_id, current_user.id, PracticeMode.wrong_only)
    favorite = get_question_ids_for_session(qbank_db, bank_id, current_user.id, PracticeMode.favorite_only)
    unpracticed = get_question_ids_for_session(qbank_db, bank_id, current_user.id, PracticeMode.unpracticed)

    count = len(total)
    return PracticeModePreviewResponse(
        bank_id=bank_id,
        sequential=count,
        random=count,
        wrong_only=len(wrong),
        favorite_only=len(favorite),
        unpracticed=len(unpracticed),
    )


# ==================== Practice Session Endpoints ====================

@router.post("/sessions", response_model=PracticeSessionResponse, tags=["📝 Practice"])
async def create_practice_session(
    session_data: PracticeSessionCreate,
    resume_if_exists: bool = Query(False, description="如果存在未完成的会话，是否继续该会话"),
    current_user: User = Depends(get_current_user),
    qbank_db: Session = Depends(get_qbank_db),
    main_db: Session = Depends(get_main_db)
):
    """创建答题会话"""
    coerced_mode = _coerce_practice_mode(session_data.mode)

    # 检查题库访问权限
    if not check_bank_access(main_db, qbank_db, current_user, session_data.bank_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有访问该题库的权限"
        )

    # Check for existing unfinished session if resume_if_exists is True
    if resume_if_exists:
        existing_session = qbank_db.query(PracticeSession).filter(
            and_(
                PracticeSession.user_id == current_user.id,
                PracticeSession.bank_id == session_data.bank_id,
                PracticeSession.mode == coerced_mode,
                PracticeSession.status.in_([SessionStatus.in_progress, SessionStatus.paused])
            )
        ).order_by(PracticeSession.last_activity_at.desc()).first()

        if existing_session:
            # Resume existing session
            existing_session.status = SessionStatus.in_progress
            existing_session.last_activity_at = datetime.utcnow()
            qbank_db.commit()
            qbank_db.refresh(existing_session)
            return existing_session

    # 获取题目列表
    question_ids = get_question_ids_for_session(
        db=qbank_db,
        bank_id=session_data.bank_id,
        user_id=current_user.id,
        mode=coerced_mode,
        question_types=session_data.question_types,
        difficulty=session_data.difficulty
    )

    if not question_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_empty_mode_message(coerced_mode)
        )

    # 创建会话
    session = PracticeSession(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        bank_id=session_data.bank_id,
        mode=coerced_mode,
        question_types=session_data.question_types,
        difficulty=session_data.difficulty,
        total_questions=len(question_ids),
        question_ids=question_ids,
        current_index=0,
        completed_count=0,
        correct_count=0,
        status=SessionStatus.in_progress,
        started_at=datetime.utcnow()
    )

    qbank_db.add(session)
    qbank_db.commit()
    qbank_db.refresh(session)

    return session


@router.get("/sessions", response_model=PracticeSessionListResponse, tags=["📝 Practice"])
async def list_practice_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=10000),
    bank_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """获取用户的答题会话列表"""

    query = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id
    )

    # 筛选条件
    if bank_id:
        query = query.filter(PracticeSession.bank_id == bank_id)
    if status_filter:
        query = query.filter(PracticeSession.status == status_filter)

    # 按最后活动时间倒序
    query = query.order_by(PracticeSession.last_activity_at.desc())

    total = query.count()
    sessions = query.offset(skip).limit(limit).all()

    return PracticeSessionListResponse(sessions=sessions, total=total)


@router.get("/sessions/{session_id}", response_model=PracticeSessionResponse, tags=["📝 Practice"])
async def get_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """获取答题会话详情"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    return session


@router.put("/sessions/{session_id}", response_model=PracticeSessionResponse, tags=["📝 Practice"])
async def update_practice_session(
    session_id: str,
    session_update: PracticeSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """更新答题会话进度"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 更新字段
    if session_update.current_index is not None:
        session.current_index = session_update.current_index
    if session_update.status is not None:
        session.status = session_update.status
        if session_update.status == SessionStatus.completed:
            session.completed_at = datetime.utcnow()

    session.last_activity_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return session


@router.delete("/sessions/{session_id}", tags=["📝 Practice"])
async def delete_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """删除答题会话"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    db.delete(session)
    db.commit()

    return {"success": True, "message": "会话已删除"}


@router.post("/sessions/{session_id}/pause", tags=["📝 Practice"])
async def pause_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """暂停答题会话"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 只有进行中的会话才能暂停
    if session.status != SessionStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会话状态为 {session.status.value}，无法暂停"
        )

    session.status = SessionStatus.paused
    session.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": "会话已暂停",
        "session_id": session.id,
        "status": session.status.value
    }


@router.post("/sessions/{session_id}/resume", tags=["📝 Practice"])
async def resume_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """恢复答题会话"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 只有暂停的会话才能恢复
    if session.status != SessionStatus.paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会话状态为 {session.status.value}，无法恢复"
        )

    session.status = SessionStatus.in_progress
    session.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": "会话已恢复",
        "session_id": session.id,
        "status": session.status.value
    }


# ==================== Answer Submission Endpoints ====================

@router.post("/sessions/{session_id}/submit", response_model=AnswerResult, tags=["📝 Practice"])
async def submit_answer(
    session_id: str,
    answer_data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """提交答案"""

    # 获取会话
    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 获取题目
    question = db.query(QuestionV2).filter(
        QuestionV2.id == answer_data.question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在"
        )

    # 判断答案是否正确
    is_correct = False
    # 确保correct_answer是纯字典，避免包含ORM对象
    correct_answer_raw = question.correct_answer or {}
    # 深拷贝，保持原始数据类型（尤其是bool类型）
    import copy
    correct_answer = copy.deepcopy(correct_answer_raw)
    user_answer = answer_data.user_answer

    # 根据题型判断正确性
    if question.type == QuestionType.single:
        is_correct = user_answer.get("answer") == correct_answer.get("answer")
    elif question.type == QuestionType.multiple:
        user_ans = set(user_answer.get("answers", []))
        correct_ans = set(correct_answer.get("answers", []))
        is_correct = user_ans == correct_ans
    elif question.type == QuestionType.judge:
        is_correct = user_answer.get("answer") == correct_answer.get("answer")
    elif question.type == QuestionType.fill:
        # 填空题答案校验 - 支持多个空格和备选答案
        blanks = correct_answer.get("blanks", [])
        user_blanks = user_answer.get("answers", [])

        # 逐个比对填空答案（忽略大小写和首尾空格）
        is_correct = True
        if len(user_blanks) != len(blanks):
            is_correct = False
        else:
            for i, blank in enumerate(blanks):
                if i >= len(user_blanks):
                    is_correct = False
                    break
                user_ans = str(user_blanks[i]).strip().lower()
                correct_ans = str(blank.get("answer", "")).strip().lower()
                alternatives = [str(alt).strip().lower() for alt in blank.get("alternatives", [])]

                # 检查是否匹配标准答案或任一备选答案
                if user_ans != correct_ans and user_ans not in alternatives:
                    is_correct = False
                    break
    elif question.type == QuestionType.essay:
        # 问答题基于关键词匹配评判
        user_text = str(user_answer.get("answer", "")).strip().lower()
        reference_answer = str(correct_answer.get("reference_answer", "")).strip().lower()
        keywords = correct_answer.get("keywords", [])

        # 如果有关键词，检查关键词匹配度
        if keywords and len(keywords) > 0:
            matched_keywords = sum(1 for keyword in keywords if keyword.lower() in user_text)
            # 如果匹配50%以上关键词，视为正确
            is_correct = matched_keywords >= len(keywords) * 0.5
        else:
            # 没有关键词时，进行简单的相似度判断
            # 如果用户答案包含参考答案的主要内容，视为正确
            if reference_answer and len(reference_answer) > 10:
                # 检查用户答案是否包含参考答案的关键部分
                is_correct = reference_answer[:20] in user_text or len(user_text) >= len(reference_answer) * 0.5
            else:
                # 如果没有参考答案或关键词，只要有作答就给分
                is_correct = len(user_text) > 0
    elif question.type == QuestionType.composite:
        is_correct, correct_answer = grade_composite_answer(question, user_answer)

    # 创建答题记录
    # 序列化选项为字典列表
    options_snapshot = []
    if question.options:
        for opt in question.options:
            options_snapshot.append({
                "label": opt.option_label,
                "content": opt.option_content,
                "is_correct": opt.is_correct
            })

    record = UserAnswerRecord(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        question_id=answer_data.question_id,
        session_id=session_id,
        bank_id=session.bank_id,
        user_answer=user_answer,
        is_correct=is_correct,
        time_spent=answer_data.time_spent,
        question_snapshot={
            "type": _enum_or_str(question.type),
            "stem": question.stem,
            "options": options_snapshot
        },
        correct_answer=correct_answer,
        created_at=datetime.utcnow()
    )

    db.add(record)

    # 更新会话统计
    session.completed_count += 1
    if is_correct:
        session.correct_count += 1
    session.last_activity_at = datetime.utcnow()

    # 自动推进到下一题
    # 找到当前题目在question_ids中的位置
    try:
        current_question_idx = session.question_ids.index(answer_data.question_id)
        # 如果不是最后一题，则推进索引
        if current_question_idx < len(session.question_ids) - 1:
            session.current_index = current_question_idx + 1
    except ValueError:
        # 如果题目不在列表中，不更新索引
        pass

    # 如果答错，加入错题本
    if not is_correct:
        wrong_q = db.query(UserWrongQuestion).filter(
            and_(
                UserWrongQuestion.user_id == current_user.id,
                UserWrongQuestion.question_id == answer_data.question_id,
                UserWrongQuestion.bank_id == session.bank_id
            )
        ).first()

        if wrong_q:
            # 更新错误次数
            wrong_q.error_count += 1
            wrong_q.last_error_answer = user_answer
            wrong_q.last_error_at = datetime.utcnow()
            wrong_q.corrected = False
        else:
            # 创建新的错题记录
            wrong_q = UserWrongQuestion(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                question_id=answer_data.question_id,
                bank_id=session.bank_id,
                error_count=1,
                last_error_answer=user_answer,
                corrected=False,
                first_error_at=datetime.utcnow(),
                last_error_at=datetime.utcnow()
            )
            db.add(wrong_q)
    else:
        # 如果答对了，检查是否在错题本中，如果在则标记为已订正
        wrong_q = db.query(UserWrongQuestion).filter(
            and_(
                UserWrongQuestion.user_id == current_user.id,
                UserWrongQuestion.question_id == answer_data.question_id,
                UserWrongQuestion.bank_id == session.bank_id
            )
        ).first()

        if wrong_q and not wrong_q.corrected:
            wrong_q.corrected = True
            wrong_q.corrected_at = datetime.utcnow()

    db.commit()
    db.refresh(record)

    # 更新题库统计
    _update_bank_statistics(db, current_user.id, session.bank_id, answer_data.question_id, is_correct, answer_data.time_spent)

    # 构造选项信息（包含label和content）
    options_data = []
    if question.options:
        for opt in question.options:
            options_data.append({
                "label": opt.option_label,
                "content": opt.option_content,
                "is_correct": opt.is_correct
            })

    return AnswerResult(
        record_id=record.id,
        question_id=record.question_id,
        is_correct=is_correct,
        correct_answer=correct_answer,
        user_answer=user_answer,
        explanation=question.explanation,
        time_spent=answer_data.time_spent,
        created_at=record.created_at,
        # 新增返回字段
        options=options_data if options_data else None,
        question_type=question.type.value if hasattr(question.type, 'value') else str(question.type),
        question_stem=question.stem
    )


# ==================== Practice Question Endpoints ====================

@router.get("/sessions/{session_id}/current", response_model=PracticeQuestionWithProgress, tags=["📝 Practice"])
async def get_current_question(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """获取当前题目（带进度信息）"""

    # 获取会话
    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 检查是否还有题目
    if session.current_index >= len(session.question_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="已完成所有题目"
        )

    # 获取当前题目ID
    current_question_id = session.question_ids[session.current_index]

    # 获取题目
    question = db.query(QuestionV2).filter(
        QuestionV2.id == current_question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在"
        )

    # 检查是否已收藏
    is_favorite = db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == current_user.id,
            UserFavorite.question_id == current_question_id
        )
    ).first() is not None

    # 检查是否曾经做错
    is_wrong_before = db.query(UserWrongQuestion).filter(
        and_(
            UserWrongQuestion.user_id == current_user.id,
            UserWrongQuestion.question_id == current_question_id
        )
    ).first() is not None

    # 获取之前的答案（如果有）
    previous_record = db.query(UserAnswerRecord).filter(
        and_(
            UserAnswerRecord.user_id == current_user.id,
            UserAnswerRecord.question_id == current_question_id
        )
    ).order_by(UserAnswerRecord.created_at.desc()).first()

    previous_answer = previous_record.user_answer if previous_record else None

    # 构造响应（不包含正确答案）
    return PracticeQuestionWithProgress(
        id=question.id,
        bank_id=question.bank_id,
        type=_enum_or_str(question.type),
        stem=question.stem,
        options=_serialize_question_options(question),
        difficulty=_enum_or_str(question.difficulty),
        tags=question.tags,
        has_image=getattr(question, "has_images", False) or getattr(question, "has_image", False),
        has_video=question.has_video or False,
        has_audio=question.has_audio or False,
        meta_data=get_practice_meta_data(question),
        created_at=question.created_at,
        current_index=session.current_index + 1,  # 从1开始
        total_questions=session.total_questions,
        is_favorite=is_favorite,
        is_wrong_before=is_wrong_before,
        previous_answer=previous_answer
    )


# ==================== Session Statistics Endpoints ====================

@router.get("/sessions/{session_id}/statistics", response_model=SessionStatistics, tags=["📝 Practice"])
async def get_session_statistics(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """获取会话统计信息"""

    session = db.query(PracticeSession).filter(
        and_(
            PracticeSession.id == session_id,
            PracticeSession.user_id == current_user.id
        )
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 计算统计数据
    wrong_count = session.completed_count - session.correct_count
    accuracy_rate = (session.correct_count / session.completed_count * 100) if session.completed_count > 0 else 0.0

    # 计算总用时和平均用时
    total_time = db.query(func.sum(UserAnswerRecord.time_spent)).filter(
        UserAnswerRecord.session_id == session_id
    ).scalar() or 0

    avg_time = (total_time / session.completed_count) if session.completed_count > 0 else 0.0

    return SessionStatistics(
        session_id=session.id,
        total_questions=session.total_questions,
        completed_count=session.completed_count,
        correct_count=session.correct_count,
        wrong_count=wrong_count,
        accuracy_rate=accuracy_rate,
        total_time_spent=total_time,
        avg_time_per_question=avg_time,
        started_at=session.started_at,
        completed_at=session.completed_at
    )


# ==================== Answer History Endpoints ====================

@router.get("/history", response_model=AnswerHistoryResponse, tags=["📝 Practice"])
async def get_answer_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=10000),
    bank_id: Optional[str] = None,
    question_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_qbank_db)
):
    """获取答题历史"""

    query = db.query(UserAnswerRecord).filter(
        UserAnswerRecord.user_id == current_user.id
    )

    # 筛选条件
    if bank_id:
        query = query.filter(UserAnswerRecord.bank_id == bank_id)
    if question_id:
        query = query.filter(UserAnswerRecord.question_id == question_id)

    # 按时间倒序
    query = query.order_by(UserAnswerRecord.created_at.desc())

    total = query.count()
    records = query.offset(skip).limit(limit).all()

    # 计算正确率
    correct_count = db.query(func.count(UserAnswerRecord.id)).filter(
        and_(
            UserAnswerRecord.user_id == current_user.id,
            UserAnswerRecord.is_correct == True
        )
    ).scalar() or 0

    accuracy_rate = (correct_count / total * 100) if total > 0 else 0.0

    return AnswerHistoryResponse(
        records=records,
        total=total,
        correct_count=correct_count,
        accuracy_rate=accuracy_rate
    )
