from app.utils.composite_question import (
    grade_composite_answer,
    get_composite_correct_answer,
    sanitize_sub_questions,
)


def test_sanitize_sub_questions_removes_answers():
    raw = [
        {
            "id": "1",
            "type": "single",
            "stem": "子题1",
            "options": [
                {"label": "A", "content": "选项A", "is_correct": True},
                {"label": "B", "content": "选项B", "is_correct": False},
            ],
        },
        {
            "id": "2",
            "type": "judge",
            "stem": "子题2",
            "answer": True,
        },
    ]
    sanitized = sanitize_sub_questions(raw)
    assert sanitized[0]["options"][0]["is_correct"] is None or "is_correct" not in sanitized[0]["options"][0]
    assert "answer" not in sanitized[1]


class DummyQuestion:
    type = type("T", (), {"value": "composite"})()
    meta_data = {
        "sub_questions": [
            {
                "id": "1",
                "type": "single",
                "options": [{"label": "A", "content": "A", "is_correct": True}],
            },
            {
                "id": "2",
                "type": "judge",
                "answer": True,
            },
        ]
    }


def test_grade_composite_all_correct():
    question = DummyQuestion()
    correct = get_composite_correct_answer(question)
    assert correct["sub_answers"]["1"]["answer"] == "A"

    is_correct, _ = grade_composite_answer(
        question,
        {"sub_answers": {"1": {"answer": "A"}, "2": {"answer": True}}},
    )
    assert is_correct is True


def test_grade_composite_partial_wrong():
    question = DummyQuestion()
    is_correct, _ = grade_composite_answer(
        question,
        {"sub_answers": {"1": {"answer": "B"}, "2": {"answer": True}}},
    )
    assert is_correct is False
