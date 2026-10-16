"""Public case reads and instructor authorization (T-043, T-045)."""

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.deps import get_db, get_store, reader_session, require_instructor_secret
from app.content.loader import ContentStore
from app.core.config import Settings
from app.core.errors import ApiError
from app.db.models import ClassRoom, LearnerSession
from app.main import create_app

CONTENT = Path(__file__).resolve().parents[4] / "content"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ALLOW_DRAFT_CASES", "true")
    app = create_app()
    app.dependency_overrides[get_store] = lambda: ContentStore(CONTENT)
    return TestClient(app)


def test_list_cases_exposes_status_but_no_hidden_content(client: TestClient) -> None:
    response = client.get("/v1/cases")

    assert response.status_code == 200
    item = next(x for x in response.json()["items"] if x["case_id"] == "DEV-001")
    assert item["status"] == "Draft" and item["status_label_th"]
    assert item["variants_available"] == ["A", "C"]
    assert not {"facts", "rubric", "branch_rules", "outcome_scripts"} & set(item)


def test_get_case_is_only_a_brief_and_rejects_unknown_id(client: TestClient) -> None:
    response = client.get("/v1/cases/DEV-001")

    assert response.status_code == 200
    brief = response.json()
    assert brief["status"] == "Draft" and brief["disclaimer_th"]
    assert "patient_display_th" in brief
    assert not {"facts", "rubric", "branch_rules", "outcome_scripts"} & set(brief)
    assert client.get("/v1/cases/does-not-exist").status_code == 404
    assert client.get("/v1/cases/..%2Fsecret").status_code == 404


def test_draft_case_is_hidden_when_not_allowed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALLOW_DRAFT_CASES", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert all(x["case_id"] != "DEV-001" for x in client.get("/v1/cases").json()["items"])
        assert client.get("/v1/cases/DEV-001").status_code == 404
    finally:
        get_settings.cache_clear()


def test_class_code_read_returns_only_name(client: TestClient) -> None:
    class FakeDb:
        def scalar(self, statement: Any) -> ClassRoom:
            return ClassRoom(code="ABC123", name="class")

    client.app.dependency_overrides[get_db] = lambda: FakeDb()  # type: ignore[attr-defined]

    response = client.get("/v1/classes/ABC123")

    assert response.status_code == 200 and response.json() == {"code": "ABC123", "name": "class"}


def test_instructor_secret_is_constant_time_checked_and_never_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: Settings(instructor_secret=SecretStr("test-secret")),
    )

    require_instructor_secret("test-secret")
    with pytest.raises(ApiError) as absent:
        require_instructor_secret(None)
    with pytest.raises(ApiError) as wrong:
        require_instructor_secret("wrong-secret")

    assert absent.value.code == "UNAUTHORIZED"
    assert wrong.value.code == "FORBIDDEN"
    assert "wrong-secret" not in str(wrong.value)


@pytest.mark.parametrize("header", ["ผิด", "café", "ÿ"])
def test_a_non_ascii_instructor_header_is_forbidden_not_a_500(
    monkeypatch: pytest.MonkeyPatch, header: str
) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: Settings(instructor_secret=SecretStr("test-secret")),
    )

    with pytest.raises(ApiError) as bad:
        require_instructor_secret(header)

    assert bad.value.code == "FORBIDDEN"


def test_instructor_can_read_any_session_but_missing_auth_cannot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = uuid.uuid4()
    row = LearnerSession(id=sid, token_hash="hash")

    class Repo:
        def __init__(self, db: Any) -> None:
            pass

        def get(self, session_id: uuid.UUID) -> LearnerSession | None:
            return row if session_id == sid else None

    monkeypatch.setattr("app.api.deps.SessionRepo", Repo)
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: Settings(instructor_secret=SecretStr("test-secret")),
    )

    assert (
        reader_session(sid, object(), authorization=None, x_instructor_secret="test-secret") is row
    )  # type: ignore[arg-type]
    with pytest.raises(ApiError) as missing:
        reader_session(sid, object(), authorization=None, x_instructor_secret=None)  # type: ignore[arg-type]
    assert missing.value.code == "UNAUTHORIZED"
