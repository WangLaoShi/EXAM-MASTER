"""
CI 稳定冒烟测试（进程内 TestClient，无需 live 服务 / API Key）

由 GitHub Actions 在每次 push / PR 时自动运行。
"""

from __future__ import annotations

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_main_db, get_qbank_db, BaseMain, BaseQBank
from app.core.security import get_password_hash
from app.models.user_models import User, UserRole
from app.models.question_models_v2 import QuestionBankV2, StorageType
from app.schemas.qbank_schemas_v2 import question_bank_to_response
from tests.api_timing import LIMIT_DOCS, assert_elapsed
from tests.openapi_client import classify_operation, iter_operations, load_openapi_spec, smoke_call

SQLALCHEMY_TEST_MAIN_URL = "sqlite:///./test_ci_main.db"
SQLALCHEMY_TEST_QBANK_URL = "sqlite:///./test_ci_qbank.db"

engine_main = create_engine(SQLALCHEMY_TEST_MAIN_URL, connect_args={"check_same_thread": False})
TestingSessionMain = sessionmaker(autocommit=False, autoflush=False, bind=engine_main)

engine_qbank = create_engine(SQLALCHEMY_TEST_QBANK_URL, connect_args={"check_same_thread": False})
TestingSessionQBank = sessionmaker(autocommit=False, autoflush=False, bind=engine_qbank)


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


app.dependency_overrides[get_main_db] = _override_get_main_db
app.dependency_overrides[get_qbank_db] = _override_get_qbank_db

pytestmark = pytest.mark.ci


@pytest.fixture(scope="module", autouse=True)
def setup_ci_database():
    BaseMain.metadata.create_all(bind=engine_main)
    BaseQBank.metadata.create_all(bind=engine_qbank)

    db = TestingSessionMain()
    if not db.query(User).filter(User.username == "admin").first():
        db.add(
            User(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                role=UserRole.admin,
                is_active=True,
            )
        )
        db.commit()
    db.close()

    yield

    BaseMain.metadata.drop_all(bind=engine_main)
    BaseQBank.metadata.drop_all(bind=engine_qbank)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    r = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def openapi_spec(client: TestClient) -> dict:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    return load_openapi_spec(lambda: r.json())


@pytest.fixture(scope="module")
def public_operations(openapi_spec: dict):
    return [o for o in iter_operations(openapi_spec) if classify_operation(o) == "public"]


def _client_call(client: TestClient, method: str, path: str, **kwargs):
    return client.request(method, path, **kwargs)


def pytest_generate_tests(metafunc):
    if "public_op" not in metafunc.fixturenames:
        return
    if getattr(metafunc.cls, "__name__", "") != "TestCIPublicOperations":
        return
    # collection 时 client fixture 尚未就绪，从 app 直接拉 spec
    tc = TestClient(app)
    spec = load_openapi_spec(lambda: tc.get("/openapi.json").json())
    ops = [o for o in iter_operations(spec) if classify_operation(o) == "public"]
    ids = [f"{o.method.lower()}__{o.path.strip('/').replace('/', '_') or 'root'}"[:80] for o in ops]
    metafunc.parametrize("public_op", ops, ids=ids)


class TestCISystem:
    def test_root(self, client: TestClient):
        assert client.get("/").status_code == 200

    def test_health(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_openapi_json(self, client: TestClient):
        with assert_elapsed(LIMIT_DOCS, "GET /openapi.json"):
            r = client.get("/openapi.json")
        assert r.status_code == 200
        assert len(r.json().get("paths", {})) > 50

    def test_api_docs(self, client: TestClient):
        with assert_elapsed(LIMIT_DOCS, "GET /api/docs"):
            r = client.get("/api/docs")
        assert r.status_code == 200


class TestCIAuth:
    def test_v2_login_form(self, client: TestClient):
        r = client.post(
            "/api/v2/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_v2_me(self, client: TestClient, auth_headers: dict):
        r = client.get("/api/v2/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["username"] == "admin"


class TestCIQBankV2:
    def test_list_banks(self, client: TestClient, auth_headers: dict):
        r = client.get("/api/v2/qbank/banks", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)


class TestCISerialization:
    def test_question_bank_to_response(self):
        bank = QuestionBankV2(
            id="ci-bank-id",
            name="CI Bank",
            description="desc",
            category="test",
            tags=[],
            version="1.0.0",
            folder_path=None,
            storage_type=StorageType.local,
            total_questions=0,
            total_size_mb=0,
            has_images=False,
            has_audio=False,
            has_video=False,
            creator_id=1,
            is_public=False,
            is_published=False,
            allow_download=True,
            allow_fork=True,
            created_at=datetime.utcnow(),
            updated_at=None,
        )
        resp = question_bank_to_response(bank)
        assert resp.id == "ci-bank-id"
        assert resp.storage_type == "local"
        assert resp.folder_path == ""


class TestCIPublicOperations:
    """每个 public OpenAPI operation 一条用例（进程内）"""

    def test_operation(self, client: TestClient, public_op):
        def _call(method, path, **kwargs):
            return _client_call(client, method, path, **kwargs)

        result = smoke_call(_call, public_op)
        assert result.status_code < 500
