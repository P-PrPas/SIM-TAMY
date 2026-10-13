"""LLMClient behaviour with a scripted fake provider: retry, timeout, malformed JSON, records."""

import logging
from collections.abc import Callable

import pytest
from pydantic import BaseModel

from app.ai.llm_client import (
    LLMCallRecord,
    LLMClient,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMTimeout,
)

FAKE_KEY = "FAKE-KEY-FOR-TESTS"


class Answer(BaseModel):
    value: int


class ScriptedProvider:
    """Plays back outcomes in order: a str is a reply, an Exception is raised."""

    name = "scripted"

    def __init__(self, *outcomes: str | Exception) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return LLMResponse(text=outcome, prompt_tokens=7, completion_tokens=3)


def make_client(*outcomes: str | Exception) -> tuple[LLMClient, ScriptedProvider, list]:
    provider = ScriptedProvider(*outcomes)
    records: list[LLMCallRecord] = []
    client = LLMClient(provider, model="m1", timeout_s=5, on_call=records.append)
    return client, provider, records


def structured(client: LLMClient) -> Answer:
    return client.complete_structured(Answer, purpose="interpreter", system="s", prompt="p")


def test_llm_client_structured_success_records_usage() -> None:
    client, provider, records = make_client('{"value": 3}')

    assert structured(client) == Answer(value=3)

    (rec,) = records
    assert (rec.purpose, rec.provider, rec.model, rec.ok, rec.error) == (
        "interpreter",
        "scripted",
        "m1",
        True,
        None,
    )
    assert (rec.prompt_tokens, rec.completion_tokens) == (7, 3)
    assert rec.latency_ms >= 0
    req = provider.requests[0]
    assert req.json_schema == Answer.model_json_schema() and req.timeout_s == 5


def test_llm_client_retries_once_on_malformed_json() -> None:
    client, provider, records = make_client("not json {", '{"value": 1}')

    assert structured(client).value == 1
    assert len(provider.requests) == 2
    assert [(r.ok, r.error) for r in records] == [(False, "invalid_response"), (True, None)]


def test_llm_client_accepts_json_inside_code_fence() -> None:
    client, _, _ = make_client('```json\n{"value": 9}\n```')
    assert structured(client).value == 9


def test_llm_client_schema_invalid_twice_raises_invalid_response() -> None:
    client, provider, records = make_client('{"value": "x"}', '{"nope": 1}')

    with pytest.raises(LLMInvalidResponse):
        structured(client)
    assert len(provider.requests) == 2
    assert [r.ok for r in records] == [False, False]


def test_llm_client_timeout_twice_raises_timeout() -> None:
    client, provider, records = make_client(LLMTimeout("timeout"), LLMTimeout("timeout"))

    with pytest.raises(LLMTimeout):
        structured(client)
    assert len(provider.requests) == 2
    assert [(r.ok, r.error) for r in records] == [(False, "timeout")] * 2


def test_llm_client_timeout_then_success() -> None:
    client, _, records = make_client(LLMTimeout("timeout"), '{"value": 2}')

    assert structured(client).value == 2
    assert [r.ok for r in records] == [False, True]


def test_llm_client_does_not_retry_non_retryable_provider_error() -> None:
    client, provider, records = make_client(LLMProviderError("http_401", retryable=False), "x")

    with pytest.raises(LLMProviderError):
        structured(client)
    assert len(provider.requests) == 1
    assert records[0].error == "http_401"


def test_llm_client_retries_retryable_provider_error() -> None:
    client, _, records = make_client(LLMProviderError("http_503"), '{"value": 5}')

    assert structured(client).value == 5
    assert [r.error for r in records] == ["http_503", None]


def test_llm_client_complete_text_retries_on_timeout() -> None:
    client, _, records = make_client(LLMTimeout("timeout"), "hello")

    out = client.complete_text(purpose="generator", system="s", prompt="p", temperature=0.5)

    assert out == "hello"
    assert [r.ok for r in records] == [False, True]


def test_llm_client_works_without_a_hook() -> None:
    client = LLMClient(ScriptedProvider("ok"), model="m", timeout_s=1)
    assert client.complete_text(purpose="debrief", system="s", prompt="p") == "ok"


def test_llm_client_never_logs_prompt_or_reply(caplog: pytest.LogCaptureFixture) -> None:
    client, _, _ = make_client('{"value": 1}')
    with caplog.at_level(logging.DEBUG):
        client.complete_structured(
            Answer, purpose="interpreter", system="SECRET-SYSTEM", prompt="LEARNER-FREE-TEXT"
        )

    assert "llm_call" in caplog.text
    for forbidden in ("SECRET-SYSTEM", "LEARNER-FREE-TEXT", '{"value"'):
        assert forbidden not in caplog.text


@pytest.mark.parametrize("make_exc", [lambda: LLMTimeout("timeout"), lambda: LLMProviderError("x")])
def test_llm_client_error_messages_are_short_codes(make_exc: Callable[[], Exception]) -> None:
    client, _, _ = make_client(make_exc(), make_exc())
    with pytest.raises(Exception) as info:
        structured(client)
    assert FAKE_KEY not in str(info.value) and len(str(info.value)) < 40
