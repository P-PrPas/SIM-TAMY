"""Mock and openai_like providers, and env-only provider/model switching."""

import json
from pathlib import Path

import httpx2
import pytest
from pydantic import BaseModel

from app.ai.llm_client import (
    LLMClient,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRequest,
    LLMTimeout,
    build_provider,
    get_llm_client,
    model_for,
)
from app.ai.providers.mock import MockProvider
from app.ai.providers.openai_like import OpenAILikeProvider
from app.core.config import Settings, get_settings
from app.services.patient_voice import canned

FAKE_KEY = "FAKE-KEY-FOR-TESTS"


class Actions(BaseModel):
    actions: list[dict] = []
    needs_clarification: bool = False
    clarification_hint: str | None = None


def req(prompt: str = "p", purpose: str = "interpreter", schema: bool = True) -> LLMRequest:
    return LLMRequest(
        purpose=purpose,
        model="m",
        system="sys",
        prompt=prompt,
        temperature=0.0,
        max_tokens=None,
        timeout_s=2,
        json_schema=Actions.model_json_schema() if schema else None,
    )


# ---- mock ----------------------------------------------------------------------------


def test_llm_client_mock_is_deterministic() -> None:
    mock = MockProvider()
    first = mock.complete(req("anything"))
    assert [mock.complete(req("anything")) for _ in range(5)] == [first] * 5


def test_llm_client_mock_builtin_interpreter_default_is_valid() -> None:
    client = LLMClient(MockProvider(), model="mock-model", timeout_s=1)
    out = client.complete_structured(Actions, purpose="interpreter", system="s", prompt="x")
    assert out == Actions()


def test_llm_client_mock_script_first_match_wins_then_default() -> None:
    mock = MockProvider(
        {
            "interpreter": [
                {"match_contains": "alpha", "return": {"actions": [{"id": "A1"}]}},
                {"match_contains": "alpha beta", "return": {"actions": [{"id": "never"}]}},
                {"default": {"actions": []}},
            ]
        }
    )
    assert json.loads(mock.complete(req("xx alpha beta")).text) == {"actions": [{"id": "A1"}]}
    assert json.loads(mock.complete(req("zzz")).text) == {"actions": []}


def test_llm_client_mock_text_purposes_get_plain_text() -> None:
    mock = MockProvider({"generator": [{"match_contains": "hi", "return": "scripted"}]})
    assert mock.complete(req("hi there", "generator", schema=False)).text == "scripted"
    assert mock.complete(req("other", "generator", schema=False)).text == canned("smalltalk")


def test_llm_client_mock_structured_without_rule_is_a_clear_error() -> None:
    with pytest.raises(LLMProviderError) as info:
        MockProvider().complete(req("x", "debrief"))
    assert info.value.code == "mock_no_rule" and not info.value.retryable


def test_llm_client_mock_script_loads_from_yaml(tmp_path: Path) -> None:
    script = tmp_path / "script.yaml"
    script.write_text(
        'interpreter:\n  - match_contains: "ping"\n    return: {actions: []}\n', encoding="utf-8"
    )
    mock = MockProvider.from_file(script)
    assert json.loads(mock.complete(req("ping")).text) == {"actions": []}


def test_llm_client_mock_rejects_malformed_script(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("interpreter: not-a-list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        MockProvider.from_file(bad)


# ---- openai_like ---------------------------------------------------------------------


def provider_with(handler) -> OpenAILikeProvider:
    return OpenAILikeProvider(
        base_url="https://llm.example/api/paas/v4",
        api_key=FAKE_KEY,
        reasoning_effort="low",
        transport=httpx2.MockTransport(handler),
    )


def ok_body(content: str) -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 4},
    }


def test_llm_client_openai_like_request_shape_and_parsing() -> None:
    seen: dict = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json=ok_body('{"actions": []}'))

    resp = provider_with(handler).complete(req("hello"))

    assert seen["url"] == "https://llm.example/api/paas/v4/chat/completions"
    assert seen["auth"] == f"Bearer {FAKE_KEY}"
    body = seen["body"]
    assert body["model"] == "m" and body["temperature"] == 0.0 and body["stream"] is False
    assert body["reasoning_effort"] == "low"
    assert body["response_format"] == {"type": "json_object"}
    assert "max_tokens" not in body
    system, user = body["messages"]
    assert (
        system["role"] == "system" and "needs_clarification" in system["content"]
    )  # schema inlined
    assert user == {"role": "user", "content": "hello"}
    assert resp.text == '{"actions": []}' and (resp.prompt_tokens, resp.completion_tokens) == (
        11,
        4,
    )


def test_llm_client_openai_like_text_call_has_no_response_format() -> None:
    bodies: list[dict] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(200, json=ok_body("hi"))

    provider_with(handler).complete(req(schema=False))
    assert "response_format" not in bodies[0] and bodies[0]["messages"][0]["content"] == "sys"


@pytest.mark.parametrize(
    ("status", "retryable"), [(401, False), (400, False), (429, True), (500, True), (503, True)]
)
def test_llm_client_openai_like_maps_http_errors(status: int, retryable: bool) -> None:
    provider = provider_with(lambda r: httpx2.Response(status, json={"error": "FAKE-DETAIL"}))
    with pytest.raises(LLMProviderError) as info:
        provider.complete(req())
    assert info.value.retryable is retryable and str(info.value) == f"http_{status}"


def test_llm_client_openai_like_maps_timeout_and_transport_errors() -> None:
    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    def down(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down", request=request)

    with pytest.raises(LLMTimeout):
        provider_with(slow).complete(req())
    with pytest.raises(LLMProviderError) as info:
        provider_with(down).complete(req())
    assert info.value.code == "transport_error"


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {}}]}, "oops"])
def test_llm_client_openai_like_odd_payloads(payload) -> None:
    provider = provider_with(lambda r: httpx2.Response(200, json=payload))
    try:
        resp = provider.complete(req())
    except LLMInvalidResponse:
        return
    assert resp.text == ""  # content missing -> empty text, which the client then rejects


@pytest.mark.parametrize(
    ("content", "usage"),
    [
        (None, {}),
        ("", {}),
        ("   ", {}),
        (["bad"], {}),
        ("ok", "bad"),
        ("ok", {"prompt_tokens": "bad"}),
        ("ok", {"completion_tokens": -1}),
    ],
)
def test_llm_client_malformed_envelope_retries_and_records(content, usage) -> None:
    attempts: list[int] = []
    records = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        attempts.append(1)
        return httpx2.Response(
            200, json={"choices": [{"message": {"content": content}}], "usage": usage}
        )

    client = LLMClient(provider_with(handler), model="m", timeout_s=2, on_call=records.append)
    with pytest.raises(LLMInvalidResponse):
        client.complete_text(purpose="generator", system="s", prompt="p")
    assert len(attempts) == len(records) == 2
    assert all(not record.ok and record.error == "invalid_response" for record in records)


def test_llm_client_openai_like_end_to_end_through_client() -> None:
    answers = iter(["garbage", '{"actions": [], "needs_clarification": true}'])
    provider = provider_with(lambda r: httpx2.Response(200, json=ok_body(next(answers))))
    client = LLMClient(provider, model="glm-test", timeout_s=2)

    out = client.complete_structured(Actions, purpose="interpreter", system="s", prompt="p")

    assert out.needs_clarification is True


# ---- env-only switching --------------------------------------------------------------


def test_llm_client_provider_is_chosen_by_env_only() -> None:
    assert isinstance(build_provider(Settings(llm_provider="mock")), MockProvider)
    real = build_provider(
        Settings(
            llm_provider="openai_like", llm_base_url="https://x.example/v4", llm_api_key=FAKE_KEY
        )
    )
    assert isinstance(real, OpenAILikeProvider)
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_provider(Settings(llm_provider="nope"))


def test_llm_client_openai_like_needs_url_and_key_without_leaking_them() -> None:
    with pytest.raises(ValueError) as info:
        build_provider(Settings(llm_provider="openai_like", llm_api_key=FAKE_KEY))
    assert FAKE_KEY not in str(info.value)


def test_llm_client_model_is_chosen_per_purpose_by_env() -> None:
    s = Settings(
        llm_provider="openai_like",
        llm_model_interpreter="fast",
        llm_model_generator="smart",
        llm_model_debrief=None,
    )
    assert model_for(s, "interpreter") == "fast" and model_for(s, "generator") == "smart"
    with pytest.raises(ValueError, match="LLM_MODEL_DEBRIEF"):
        model_for(s, "debrief")
    assert model_for(Settings(llm_provider="mock"), "debrief") == "mock-model"


def test_llm_client_backend_runs_offline_on_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ai import llm_client

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    llm_client._cached_provider.cache_clear()
    try:
        c = get_llm_client("interpreter")
        a = c.complete_structured(Actions, purpose="interpreter", system="s", prompt="same")
        b = get_llm_client("interpreter").complete_structured(
            Actions, purpose="interpreter", system="s", prompt="same"
        )
        assert a == b
    finally:
        get_settings.cache_clear()
        llm_client._cached_provider.cache_clear()


def test_llm_client_empty_env_values_mean_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "MOCK_LLM_SCRIPT", "LLM_REASONING_EFFORT"):
        monkeypatch.setenv(name, "")
    s = Settings()
    assert (s.llm_api_key, s.llm_base_url, s.mock_llm_script, s.llm_reasoning_effort) == (
        None,
        None,
        None,
        None,
    )
