"""HTTP fixtures: the real app on a throwaway migrated Postgres, with the DEV-001 fixture."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_store
from app.content.loader import LoadedCase, load_case
from app.core.config import get_settings
from app.main import create_app

CONTENT_DIR = Path(__file__).resolve().parents[5] / "content"


@dataclass
class Api:
    client: TestClient
    db: Callable[[], AbstractContextManager[Session]]
    loaded: LoadedCase

    def create(self, **body: Any) -> dict[str, Any]:
        payload = {"case_id": "DEV-001", "variant": "A", "learner_name": "tester", **body}
        r = self.client.post("/v1/sessions", json=payload)
        assert r.status_code == 201, r.text
        return dict(r.json())

    def headers(self, created: dict[str, Any]) -> dict[str, str]:
        return {"Authorization": f"Bearer {created['token']}"}


@pytest.fixture
def api(
    make_db: Callable[[], str],
    alembic_config: Callable[[str], Config],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Api]:
    url = make_db()
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr("app.api.deps.get_sessionmaker", lambda: maker)
    monkeypatch.setenv("CONTENT_DIR", str(CONTENT_DIR))
    monkeypatch.setenv("ALLOW_DRAFT_CASES", "true")
    get_settings.cache_clear()
    get_store.cache_clear()
    client = TestClient(create_app(), raise_server_exceptions=False)
    yield Api(client, lambda: maker.begin(), load_case(CONTENT_DIR / "cases" / "DEV-001"))
    get_settings.cache_clear()
    get_store.cache_clear()
    engine.dispose()
