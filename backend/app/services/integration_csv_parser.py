"""
CSV row parsing for Integration API imports
"""

from typing import Any, Dict, Optional, Tuple

from app.schemas.integration_schemas import IntegrationQuestionCreate


QUESTION_TYPE_MAP = {
    "单选题": "single",
    "多选题": "multiple",
    "判断题": "judge",
    "填空题": "fill",
    "简答题": "essay",
    "问答题": "essay",
    "single": "single",
    "multiple": "multiple",
    "judge": "judge",
    "fill": "fill",
    "essay": "essay",
}

DIFFICULTY_MAP = {
    "无": "medium",
    "none": "medium",
    "": "medium",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
    "expert": "expert",
    "简单": "easy",
    "中等": "medium",
    "困难": "hard",
}


def _cell(row: dict, *keys: str) -> Optional[str]:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def map_question_type(raw_type: Optional[str], answer: str) -> str:
    if raw_type:
        normalized = raw_type.strip()
        if normalized in QUESTION_TYPE_MAP:
            return QUESTION_TYPE_MAP[normalized]
    return "multiple" if len(answer) > 1 else "single"


def map_difficulty(raw: Optional[str]) -> str:
    if not raw:
        return "medium"
    key = raw.strip().lower()
    return DIFFICULTY_MAP.get(raw.strip(), DIFFICULTY_MAP.get(key, "medium"))


def build_external_id(
    row: dict,
    prefix: str,
    row_index: int,
) -> Optional[str]:
    raw = _cell(row, "external_id", "id", "题号")
    if raw is None:
        return None
    raw = raw.strip().strip('"')
    if prefix:
        return f"{prefix}-{raw}"
    return raw


def parse_csv_row(
    row: dict,
    row_index: int,
    external_id_prefix: str = "import",
) -> Tuple[Optional[IntegrationQuestionCreate], Optional[str]]:
    """
    Parse one CSV row. Returns (question, skip_reason).
    skip_reason is set when row should be skipped (empty stem).
    Raises ValueError with human-readable message on invalid data.
    """
    stem = _cell(row, "stem", "question", "题干")
    if not stem:
        return None, "题干为空，已跳过"

    answer = (_cell(row, "答案", "correct_answer", "answer") or "").upper()

    options = []
    for label in ["A", "B", "C", "D", "E", "F"]:
        content = _cell(row, label, f"option_{label.lower()}")
        if content:
            options.append({
                "label": label,
                "content": content,
                "is_correct": label in answer,
            })

    if not options and answer:
        raise ValueError(f"第 {row_index} 行有答案「{answer}」但未找到选项列 A~F")

    raw_type = _cell(row, "type", "题型")
    qtype = map_question_type(raw_type, answer)
    external_id = build_external_id(row, external_id_prefix, row_index)

    question_number = None
    num_raw = _cell(row, "题号", "question_number", "number")
    if num_raw and num_raw.isdigit():
        question_number = int(num_raw)

    item = IntegrationQuestionCreate(
        stem=stem,
        type=qtype,
        external_id=external_id,
        options=options,
        explanation=_cell(row, "explanation", "解析"),
        difficulty=map_difficulty(_cell(row, "difficulty", "难度")),
        category=_cell(row, "category", "题型"),
        question_number=question_number,
    )
    return item, None


def build_external_id_safe(row: dict, prefix: str) -> Optional[str]:
    try:
        return build_external_id(row, prefix, 0)
    except Exception:
        return None
