"""
复合题（composite）工具：练习态脱敏、标准答案提取、判分。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from app.models.question_models_v2 import QuestionType, QuestionV2

ANSWER_KEYS = {
    "answer",
    "answers",
    "blanks",
    "reference_answer",
    "keywords",
    "correct_answer",
    "is_correct",
}


def _normalize_options(options: Optional[List[Any]]) -> List[Dict[str, Any]]:
    if not options:
        return []
    normalized: List[Dict[str, Any]] = []
    for opt in options:
        if isinstance(opt, dict):
            normalized.append(
                {
                    "label": opt.get("label") or opt.get("option_label") or "",
                    "content": opt.get("content") or opt.get("option_content") or "",
                }
            )
    return normalized


def _sub_id(sub: Dict[str, Any], index: int) -> str:
    return str(sub.get("id") or sub.get("sub_id") or index + 1)


def sanitize_sub_questions(sub_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """移除子题中的正确答案，供练习/考试接口返回。"""
    sanitized: List[Dict[str, Any]] = []
    for index, sub in enumerate(sub_questions):
        if not isinstance(sub, dict):
            continue
        item = deepcopy(sub)
        item["id"] = _sub_id(item, index)
        for key in ANSWER_KEYS:
            item.pop(key, None)
        if item.get("options"):
            item["options"] = [
                {"label": opt.get("label") or opt.get("option_label"), "content": opt.get("content") or opt.get("option_content")}
                for opt in item["options"]
                if isinstance(opt, dict)
            ]
        if item.get("blanks"):
            item["blank_count"] = len(item["blanks"])
            item.pop("blanks", None)
        sanitized.append(item)
    return sanitized


def get_practice_meta_data(question: QuestionV2) -> Optional[Dict[str, Any]]:
    meta = deepcopy(question.meta_data) if question.meta_data else None
    if not meta or question.type != QuestionType.composite:
        return meta
    sub_questions = meta.get("sub_questions") or []
    if isinstance(sub_questions, list):
        meta["sub_questions"] = sanitize_sub_questions(sub_questions)
    return meta


def extract_sub_correct_answer(sub: Dict[str, Any]) -> Dict[str, Any]:
    sub_type = sub.get("type")
    if sub_type == QuestionType.single.value or sub_type == "single":
        for opt in sub.get("options") or []:
            if isinstance(opt, dict) and opt.get("is_correct"):
                return {"answer": opt.get("label") or opt.get("option_label")}
        if sub.get("answer") is not None:
            return {"answer": sub.get("answer")}
        return {"answer": None}

    if sub_type == QuestionType.multiple.value or sub_type == "multiple":
        labels = [
            opt.get("label") or opt.get("option_label")
            for opt in (sub.get("options") or [])
            if isinstance(opt, dict) and opt.get("is_correct")
        ]
        if labels:
            return {"answers": labels}
        if sub.get("answers") is not None:
            return {"answers": sub.get("answers")}
        return {"answers": []}

    if sub_type == QuestionType.judge.value or sub_type == "judge":
        answer_value = sub.get("answer")
        if answer_value is None and "correct_answer" in sub:
            answer_value = sub.get("correct_answer")
        if isinstance(answer_value, str):
            answer_value = answer_value.lower() in ["true", "正确", "对", "是", "yes", "t", "√"]
        return {"answer": bool(answer_value) if answer_value is not None else None}

    if sub_type == QuestionType.fill.value or sub_type == "fill":
        blanks = sub.get("blanks") or []
        return {"blanks": deepcopy(blanks)}

    if sub_type == QuestionType.essay.value or sub_type == "essay":
        return {
            "reference_answer": sub.get("reference_answer", ""),
            "keywords": sub.get("keywords") or [],
        }

    return {}


def get_composite_correct_answer(question: QuestionV2) -> Dict[str, Any]:
    sub_questions = (question.meta_data or {}).get("sub_questions") or []
    sub_answers: Dict[str, Any] = {}
    if isinstance(sub_questions, list):
        for index, sub in enumerate(sub_questions):
            if isinstance(sub, dict):
                sub_answers[_sub_id(sub, index)] = extract_sub_correct_answer(sub)
    return {"sub_answers": sub_answers}


def _grade_single(user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    return user.get("answer") == correct.get("answer")


def _grade_multiple(user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    return set(user.get("answers") or []) == set(correct.get("answers") or [])


def _grade_judge(user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    return user.get("answer") == correct.get("answer")


def _grade_fill(user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    blanks = correct.get("blanks") or []
    user_blanks = user.get("answers") or []
    if len(user_blanks) != len(blanks):
        return False
    for i, blank in enumerate(blanks):
        user_ans = str(user_blanks[i]).strip().lower()
        correct_ans = str(blank.get("answer", "")).strip().lower()
        alternatives = [str(alt).strip().lower() for alt in blank.get("alternatives", [])]
        if user_ans != correct_ans and user_ans not in alternatives:
            return False
    return True


def _grade_essay(user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    user_text = str(user.get("answer", "")).strip().lower()
    reference_answer = str(correct.get("reference_answer", "")).strip().lower()
    keywords = correct.get("keywords") or []
    if keywords:
        matched = sum(1 for keyword in keywords if str(keyword).lower() in user_text)
        return matched >= len(keywords) * 0.5
    if reference_answer and len(reference_answer) > 10:
        return reference_answer[:20] in user_text or len(user_text) >= len(reference_answer) * 0.5
    return len(user_text) > 0


def grade_sub_answer(sub_type: str, user: Dict[str, Any], correct: Dict[str, Any]) -> bool:
    if sub_type == "single":
        return _grade_single(user, correct)
    if sub_type == "multiple":
        return _grade_multiple(user, correct)
    if sub_type == "judge":
        return _grade_judge(user, correct)
    if sub_type == "fill":
        return _grade_fill(user, correct)
    if sub_type == "essay":
        return _grade_essay(user, correct)
    return False


def grade_composite_answer(question: QuestionV2, user_answer: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    correct = get_composite_correct_answer(question)
    user_sub = user_answer.get("sub_answers") or {}
    correct_sub = correct.get("sub_answers") or {}
    if not correct_sub:
        return False, correct

    sub_questions = (question.meta_data or {}).get("sub_questions") or []
    all_correct = True
    for index, sub in enumerate(sub_questions):
        if not isinstance(sub, dict):
            continue
        sid = _sub_id(sub, index)
        sub_type = sub.get("type")
        if sid not in user_sub:
            all_correct = False
            continue
        if not grade_sub_answer(str(sub_type), user_sub[sid], correct_sub.get(sid, {})):
            all_correct = False

    return all_correct, correct
