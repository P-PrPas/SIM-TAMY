import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "cases" / "DEV-001").mkdir(parents=True)
    monkeypatch.setenv("CONTENT_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.health.check_db", lambda: True)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "ok"
    assert body["content_loaded"] is True and body["cases_loaded"] == 1
    assert body["llm_provider"] == "mock"


def test_health_db_down_is_503(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.health.check_db", lambda: False)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["db"] == "error"


def test_settings_never_print_secrets():
    s = Settings(llm_api_key="sk-secret")  # type: ignore[arg-type]
    assert "sk-secret" not in repr(s)
