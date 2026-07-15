"""
练习模式（顺序 / 随机 / 错题 / 收藏 / 未做）API 与选题逻辑测试
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.core.database import get_main_db, get_qbank_db, BaseMain, BaseQBank
from app.core.security import get_password_hash
from app.models.user_models import User, UserRole
from app.models.question_models_v2 import QuestionBankV2, QuestionV2, QuestionType, StorageType
from app.models.user_practice import (
    PracticeMode,
    PracticeSession,
    SessionStatus,
    UserAnswerRecord,
    UserFavorite,
    UserWrongQuestion,
)
from app.schemas.practice_schemas import PracticeModeEnum
from app.api.v1.practice import (
    _coerce_practice_mode,
    _empty_mode_message,
    get_question_ids_for_session,
)

SQLALCHEMY_TEST_MAIN_URL = "sqlite:///./test_practice_modes_main.db"
SQLALCHEMY_TEST_QBANK_URL = "sqlite:///./test_practice_modes_qbank.db"

engine_main = create_engine(SQLALCHEMY_TEST_MAIN_URL, connect_args={"check_same_thread": False})
TestingSessionMain = sessionmaker(autocommit=False, autoflush=False, bind=engine_main)

engine_qbank = create_engine(SQLALCHEMY_TEST_QBANK_URL, connect_args={"check_same_thread": False})
TestingSessionQBank = sessionmaker(autocommit=False, autoflush=False, bind=engine_qbank)

BANK_ID = "00000000-0000-4000-8000-000000000101"
USER_ID = 1
QUESTION_IDS = [
    "00000000-0000-4000-8000-000000000201",
    "00000000-0000-4000-8000-000000000202",
    "00000000-0000-4000-8000-000000000203",
    "00000000-0000-4000-8000-000000000204",
    "00000000-0000-4000-8000-000000000205",
]

pytestmark = pytest.mark.ci


def _override_get_main_db():
    db = TestingSessionMain()
    try:
        yield db
    finally:
        db.close()


def _override_get_qbank_db():
    db = TestingSessionQBank()
    try:
        yield db
    finally:
        db.close()


def _seed_practice_data(main_db: Session, qbank_db: Session) -> None:
    if not main_db.query(User).filter(User.id == USER_ID).first():
        main_db.add(
            User(
                id=USER_ID,
                username="practice_modes_admin",
                email="practice_modes@example.com",
                password_hash=get_password_hash("admin123"),
                role=UserRole.admin,
                is_active=True,
            )
        )
        main_db.commit()

    if qbank_db.query(QuestionBankV2).filter(QuestionBankV2.id == BANK_ID).first():
        return

    qbank_db.add(
        QuestionBankV2(
            id=BANK_ID,
            name="Practice Modes Test Bank",
            description="for mode tests",
            version="1.0.0",
            category="test",
            tags=[],
            folder_path=None,
            storage_type=StorageType.local,
            total_questions=len(QUESTION_IDS),
            total_size_mb=0,
            has_images=False,
            has_audio=False,
            has_video=False,
            creator_id=USER_ID,
            is_public=True,
            is_published=True,
            allow_download=True,
            allow_fork=True,
            created_at=datetime.utcnow(),
        )
    )

    for index, question_id in enumerate(QUESTION_IDS, start=1):
        qbank_db.add(
            QuestionV2(
                id=question_id,
                bank_id=BANK_ID,
                question_number=index,
                stem=f"测试题 {index}",
                type=QuestionType.single,
                difficulty="medium",
                meta_data={"answer": "A"},
                created_at=datetime.utcnow(),
            )
        )

    # q1: 错题 + 已答
    qbank_db.add(
        UserWrongQuestion(
            id=str(uuid.uuid4()),
            user_id=USER_ID,
            question_id=QUESTION_IDS[0],
            bank_id=BANK_ID,
            error_count=1,
            corrected=False,
            first_error_at=datetime.utcnow(),
            last_error_at=datetime.utcnow(),
        )
    )
    qbank_db.add(
        UserAnswerRecord(
            id=str(uuid.uuid4()),
            user_id=USER_ID,
            question_id=QUESTION_IDS[0],
            bank_id=BANK_ID,
            user_answer={"answer": "B"},
            is_correct=False,
            created_at=datetime.utcnow(),
        )
    )

    # q2: 收藏 + 已答
    qbank_db.add(
        UserFavorite(
            id=str(uuid.uuid4()),
            user_id=USER_ID,
            question_id=QUESTION_IDS[1],
            bank_id=BANK_ID,
            created_at=datetime.utcnow(),
        )
    )
    qbank_db.add(
        UserAnswerRecord(
            id=str(uuid.uuid4()),
            user_id=USER_ID,
            question_id=QUESTION_IDS[1],
            bank_id=BANK_ID,
            user_answer={"answer": "A"},
            is_correct=True,
            created_at=datetime.utcnow(),
        )
    )

    qbank_db.commit()


@pytest.fixture(scope="module")
def practice_env():
    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_main_db] = _override_get_main_db
    app.dependency_overrides[get_qbank_db] = _override_get_qbank_db

    BaseMain.metadata.create_all(bind=engine_main)
    BaseQBank.metadata.create_all(bind=engine_qbank)

    main_db = TestingSessionMain()
    qbank_db = TestingSessionQBank()
    try:
        _seed_practice_data(main_db, qbank_db)
    finally:
        main_db.close()
        qbank_db.close()

    yield {"bank_id": BANK_ID, "user_id": USER_ID}

    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved_overrides)
    BaseMain.metadata.drop_all(bind=engine_main)
    BaseQBank.metadata.drop_all(bind=engine_qbank)


@pytest.fixture(scope="module")
def client(practice_env) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "practice_modes_admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPracticeModeHelpers:
    def test_coerce_practice_mode_from_schema_enum(self):
        assert _coerce_practice_mode(PracticeModeEnum.random) == PracticeMode.random
        assert _coerce_practice_mode("wrong_only") == PracticeMode.wrong_only

    def test_empty_mode_messages(self):
        assert "错题" in _empty_mode_message(PracticeMode.wrong_only)
        assert "收藏" in _empty_mode_message(PracticeMode.favorite_only)
        assert "练习过" in _empty_mode_message(PracticeMode.unpracticed)


class TestPracticeModeSelection:
    def test_get_question_ids_sequential(self, practice_env):
        db = TestingSessionQBank()
        try:
            ids = get_question_ids_for_session(
                db, practice_env["bank_id"], practice_env["user_id"], PracticeMode.sequential
            )
            assert ids == QUESTION_IDS
        finally:
            db.close()

    def test_get_question_ids_random_is_permutation(self, practice_env):
        db = TestingSessionQBank()
        try:
            ids = get_question_ids_for_session(
                db, practice_env["bank_id"], practice_env["user_id"], PracticeMode.random
            )
            assert sorted(ids) == sorted(QUESTION_IDS)
            assert set(ids) == set(QUESTION_IDS)
        finally:
            db.close()

    def test_get_question_ids_wrong_only(self, practice_env):
        db = TestingSessionQBank()
        try:
            ids = get_question_ids_for_session(
                db, practice_env["bank_id"], practice_env["user_id"], PracticeMode.wrong_only
            )
            assert ids == [QUESTION_IDS[0]]
        finally:
            db.close()

    def test_get_question_ids_favorite_only(self, practice_env):
        db = TestingSessionQBank()
        try:
            ids = get_question_ids_for_session(
                db, practice_env["bank_id"], practice_env["user_id"], PracticeMode.favorite_only
            )
            assert ids == [QUESTION_IDS[1]]
        finally:
            db.close()

    def test_get_question_ids_unpracticed(self, practice_env):
        db = TestingSessionQBank()
        try:
            ids = get_question_ids_for_session(
                db, practice_env["bank_id"], practice_env["user_id"], PracticeMode.unpracticed
            )
            assert set(ids) == set(QUESTION_IDS[2:])
        finally:
            db.close()


class TestPracticeModePreviewAPI:
    def test_preview_counts(self, client: TestClient, auth_headers: dict, practice_env):
        response = client.get(
            "/api/v1/practice/modes/preview",
            params={"bank_id": practice_env["bank_id"]},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["sequential"] == 5
        assert data["random"] == 5
        assert data["wrong_only"] == 1
        assert data["favorite_only"] == 1
        assert data["unpracticed"] == 3


class TestPracticeModeSessions:
    @pytest.mark.parametrize(
        "mode,expected_count",
        [
            ("sequential", 5),
            ("random", 5),
            ("wrong_only", 1),
            ("favorite_only", 1),
            ("unpracticed", 3),
        ],
    )
    def test_create_session_by_mode(
        self,
        client: TestClient,
        auth_headers: dict,
        practice_env,
        mode: str,
        expected_count: int,
    ):
        response = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": mode},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert response.status_code == 200, response.text
        session = response.json()
        assert session["mode"] == mode
        assert session["total_questions"] == expected_count
        assert len(session["question_ids"]) == expected_count
        assert session["current_index"] == 0

    def test_sequential_order_matches_question_list(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        response = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "sequential"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert response.status_code == 200
        assert response.json()["question_ids"] == QUESTION_IDS

    def test_random_order_differs_from_sequential(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        shuffled = None
        for _ in range(10):
            response = client.post(
                "/api/v1/practice/sessions",
                json={"bank_id": practice_env["bank_id"], "mode": "random"},
                headers=auth_headers,
                params={"resume_if_exists": False},
            )
            assert response.status_code == 200
            shuffled = response.json()["question_ids"]
            if shuffled != QUESTION_IDS:
                break
        assert shuffled is not None
        assert sorted(shuffled) == sorted(QUESTION_IDS)
        assert shuffled != QUESTION_IDS

    def test_wrong_only_empty_bank_returns_helpful_message(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        empty_bank_id = "00000000-0000-4000-8000-000000000999"
        qbank_db = TestingSessionQBank()
        try:
            if not qbank_db.query(QuestionBankV2).filter(QuestionBankV2.id == empty_bank_id).first():
                qbank_db.add(
                    QuestionBankV2(
                        id=empty_bank_id,
                        name="Empty Wrong Bank",
                        version="1.0.0",
                        tags=[],
                        storage_type=StorageType.local,
                        total_questions=1,
                        creator_id=USER_ID,
                        is_public=True,
                        is_published=True,
                        created_at=datetime.utcnow(),
                    )
                )
                qbank_db.add(
                    QuestionV2(
                        id="00000000-0000-4000-8000-000000000301",
                        bank_id=empty_bank_id,
                        stem="无错题",
                        type=QuestionType.single,
                        meta_data={"answer": "A"},
                        created_at=datetime.utcnow(),
                    )
                )
                qbank_db.commit()
        finally:
            qbank_db.close()

        response = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": empty_bank_id, "mode": "wrong_only"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert response.status_code == 404
        assert "错题" in response.json()["detail"]

    def test_resume_if_exists_returns_same_session(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        first = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "random"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert first.status_code == 200
        first_id = first.json()["id"]

        qbank_db = TestingSessionQBank()
        try:
            session = qbank_db.query(PracticeSession).filter(PracticeSession.id == first_id).one()
            session.current_index = 2
            qbank_db.commit()
        finally:
            qbank_db.close()

        second = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "random"},
            headers=auth_headers,
            params={"resume_if_exists": True},
        )
        assert second.status_code == 200
        assert second.json()["id"] == first_id
        assert second.json()["current_index"] == 2

    def test_resume_if_exists_false_creates_new_session(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        first = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "sequential"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert first.status_code == 200
        first_id = first.json()["id"]

        second = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "sequential"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert second.status_code == 200
        assert second.json()["id"] != first_id

    def test_different_modes_do_not_resume_each_other(
        self, client: TestClient, auth_headers: dict, practice_env
    ):
        sequential = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "sequential"},
            headers=auth_headers,
            params={"resume_if_exists": False},
        )
        assert sequential.status_code == 200
        sequential_id = sequential.json()["id"]

        wrong_only = client.post(
            "/api/v1/practice/sessions",
            json={"bank_id": practice_env["bank_id"], "mode": "wrong_only"},
            headers=auth_headers,
            params={"resume_if_exists": True},
        )
        assert wrong_only.status_code == 200
        assert wrong_only.json()["id"] != sequential_id
        assert wrong_only.json()["total_questions"] == 1
