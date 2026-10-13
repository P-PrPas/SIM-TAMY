"""Acceptance criteria: keys never leak; no vendor SDK outside ai/providers/."""

import ast
import logging
from pathlib import Path

import httpx2
import pytest
from pydantic import BaseModel

from app.ai.llm_client import LLMCallRecord, LLMClient, LLMError
from app.ai.providers.openai_like import OpenAILikeProvider
from app.core.config import Settings

APP_DIR = Path(__file__).resolve().parents[3] / "app"
PROVIDERS_DIR = APP_DIR / "ai" / "providers"
FAKE_KEY = "FAKE-KEY-FOR-TESTS"
VENDOR_SDKS = {
    "openai",
    "anthropic",
    "zai",
    "zhipuai",
    "google",
    "cohere",
    "mistralai",
    "litellm",
    "langchain",
}


def sdk_imports(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots & VENDOR_SDKS


def test_llm_client_no_vendor_sdk_outside_providers() -> None:
    offenders = {
        str(p.relative_to(APP_DIR)): sdk_imports(p.read_text(encoding="utf-8"))
        for p in APP_DIR.rglob("*.py")
        if PROVIDERS_DIR not in p.parents and sdk_imports(p.read_text(encoding="utf-8"))
    }
    assert offenders == {}


def test_llm_client_sdk_scan_is_not_vacuous() -> None:
    assert sdk_imports("import openai") == {"openai"}
    assert sdk_imports("from anthropic import Anthropic") == {"anthropic"}
    assert sdk_imports("import httpx2\nfrom pathlib import Path") == set()


class Answer(BaseModel):
    value: int


@pytest.mark.parametrize(
    "handler_status",
    [200, 401, 500],
    ids=["ok", "unauthorized", "server_error"],
)
def test_llm_client_api_key_never_appears_in_logs_records_or_errors(
    handler_status: int, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if handler_status == 200:
            body = {"choices": [{"message": {"content": '{"value": 1}'}}], "usage": {}}
            return httpx2.Response(200, json=body)
        return httpx2.Response(handler_status, json={"message": "bad"})

    provider = OpenAILikeProvider(
        base_url="https://llm.example/v4",
        api_key=FAKE_KEY,
        transport=httpx2.MockTransport(handler),
    )
    records: list[LLMCallRecord] = []
    client = LLMClient(provider, model="m", timeout_s=1, on_call=records.append)

    caught = ""
    with caplog.at_level(logging.DEBUG):
        try:
            client.complete_structured(Answer, purpose="interpreter", system="s", prompt="p")
        except LLMError as exc:
            caught = f"{exc!r} {exc}"

    assert records  # something was recorded
    haystack = " ".join([caplog.text, caught, *map(repr, records)])
    assert FAKE_KEY not in haystack


def test_llm_client_settings_never_print_the_key() -> None:
    s = Settings(llm_api_key=FAKE_KEY)  # type: ignore[arg-type]
    assert FAKE_KEY not in repr(s) and FAKE_KEY not in str(s)
