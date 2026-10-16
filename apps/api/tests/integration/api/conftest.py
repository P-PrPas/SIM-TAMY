"""HTTP fixtures: the real app on a throwaway migrated Postgres, with the DEV-001 fixture."""

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai.llm_client import LLMClient, LLMRequest, LLMResponse, LLMTimeout
from app.api.deps import get_llm_factory, get_store, get_voice
from app.content.loader import LoadedCase, load_case
from app.core.config import get_settings
from app.main import create_app
from app.services.patient_voice import CannedGenerator, FloorValidator, Voice

CONTENT_DIR = Path(__file__).resolve().parents[5] / "content"


FORBIDDEN_KEYS = {"revealed_fact_ids", "risk_state", "actions", "fired_action_ids", "items"}
FORBIDDEN_KEYS |= {"total_score", "safety_status", "findings", "unlock_on", "leak_terms_th"}


def keys_of(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in keys_of(v)}
    if isinstance(node, list):
        return {k for v in node for k in keys_of(v)}
    return set()


class ScriptedProvider:
    """Mock LLM keyed on the learner's latest message (`<learner_text>`), so multi-turn tests
    are not confused by the history in the prompt. `None` = no actions, `"down"` = LLM failure."""

    name = "scripted"

    def __init__(self) -> None:
        self.by_text: dict[str, Any] = {}
        self.generator_reply: str | None = None
        self.calls = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if request.purpose == "generator" and self.generator_reply is not None:
            return LLMResponse(self.generator_reply, prompt_tokens=1, completion_tokens=1)
        text = request.prompt.split("<learner_text>" + chr(10))[-1].split(
            chr(10) + "</learner_text>"
        )[0]
        rule = self.by_text.get(text)
        if rule == "down":
            raise LLMTimeout("timeout")
        body = {"actions": [], "needs_clarification": False} if rule is None else rule
        return LLMResponse(json.dumps(body), prompt_tokens=1, completion_tokens=1)


def ask(action_id: str, span: str, confidence: float = 0.9) -> dict[str, Any]:
    return {"actions": [{"id": action_id, "confidence": confidence, "evidence_span": span}]}


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

    llm: ScriptedProvider = field(default_factory=ScriptedProvider)

    def use_voice(self, voice: Voice) -> None:
        self.client.app.dependency_overrides[get_voice] = lambda: voice  # type: ignore[attr-defined]

    def assert_no_leak(self, body: Any, revealed: tuple[str, ...] = ()) -> None:
        """No hidden facts, risk state, actions or scores in a play-time response (rule 5)."""
        text = str(body)
        assert not keys_of(body) & FORBIDDEN_KEYS
        hidden = [f for f in self.loaded.case.facts if f.kind == "hidden"]
        assert hidden
        for fact in hidden:
            if fact.id not in revealed:
                assert fact.text_th not in text
                assert not any(term in text for term in fact.leak_terms_th)  # type: ignore[union-attr]


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
    monkeypatch.setenv(
        "RATE_LIMIT_PER_MIN", "0"
    )  # tests play many turns; test_security_api turns it on
    get_settings.cache_clear()
    get_store.cache_clear()
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    provider = ScriptedProvider()
    app.dependency_overrides[get_llm_factory] = lambda: (
        lambda purpose, on_call: LLMClient(
            provider, model="scripted-model", timeout_s=1, on_call=on_call
        )
    )
    # Existing API contract tests use a deterministic canned voice. Tests of the production
    # LLM/validator path explicitly remove this override.
    app.dependency_overrides[get_voice] = lambda: Voice(CannedGenerator(), FloorValidator())
    yield Api(client, lambda: maker.begin(), load_case(CONTENT_DIR / "cases" / "DEV-001"), provider)
    get_settings.cache_clear()
    get_store.cache_clear()
    engine.dispose()
