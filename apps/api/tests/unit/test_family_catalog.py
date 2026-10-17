"""The public catalogue respects review visibility and contains no lesson internals."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_family_catalogue_respects_draft_visibility(monkeypatch):
    monkeypatch.setenv("CONTENT_DIR", str(Path(__file__).resolve().parents[4] / "content"))
    try:
        monkeypatch.setenv("ALLOW_DRAFT_CASES", "false")
        get_settings.cache_clear()
        client = TestClient(create_app())
        assert client.get("/v1/family/stories").json() == []
        monkeypatch.setenv("ALLOW_DRAFT_CASES", "true")
        get_settings.cache_clear()
        cards = client.get("/v1/family/stories").json()
        assert cards
        assert all(
            set(card) == {"id", "title_th", "description_th", "mode", "chapters_th"}
            for card in cards
        )
    finally:
        get_settings.cache_clear()
