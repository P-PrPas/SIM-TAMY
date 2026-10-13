"""The single door to any LLM (AGENTS.md: every call goes through `LLMClient`).

Providers live in `app/ai/providers/` and are the only place allowed to talk to a vendor.
Nothing here logs prompts, replies or keys: only purpose / model / latency / outcome.
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.ai.llm")

Purpose = Literal["interpreter", "generator", "debrief", "bench"]
MAX_ATTEMPTS = 2  # 1 retry, per PRD 9.1; callers fall back after the second failure

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


class LLMError(Exception):
    """Base class. Messages are short codes, never prompt/reply/key content."""


class LLMTimeout(LLMError):
    pass


class LLMProviderError(LLMError):
    def __init__(self, code: str, *, retryable: bool = True) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class LLMInvalidResponse(LLMError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    purpose: str
    model: str
    system: str
    prompt: str
    temperature: float
    max_tokens: int | None
    timeout_s: float
    json_schema: dict[str, Any] | None = None  # set for structured calls


@dataclass(frozen=True)
class LLMResponse:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(Protocol):
    name: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """One attempt. Raise LLMTimeout / LLMProviderError / LLMInvalidResponse."""
        ...


@dataclass(frozen=True)
class LLMCallRecord:
    """One attempt; mirrors the `llm_calls` columns (PRD 7.3). T-044 persists these."""

    purpose: str
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int
    ok: bool
    error: str | None


OnCall = Callable[[LLMCallRecord], None]

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class LLMClient:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str,
        timeout_s: float,
        on_call: OnCall | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.timeout_s = timeout_s
        self.on_call = on_call

    def complete_text(
        self,
        *,
        purpose: Purpose,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        request = self._request(purpose, system, prompt, temperature, max_tokens, None)
        return self._run(request, lambda text: text)

    def complete_structured(
        self,
        schema: type[T],
        *,
        purpose: Purpose,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> T:
        request = self._request(
            purpose, system, prompt, temperature, max_tokens, schema.model_json_schema()
        )

        def parse(text: str) -> T:
            fenced = _FENCE.match(text)
            try:
                return schema.model_validate_json(fenced.group(1) if fenced else text)
            except (ValidationError, ValueError) as exc:
                raise LLMInvalidResponse("invalid_response") from exc

        return self._run(request, parse)

    def _request(
        self,
        purpose: Purpose,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int | None,
        json_schema: dict[str, Any] | None,
    ) -> LLMRequest:
        return LLMRequest(
            purpose=purpose,
            model=self.model,
            system=system,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=self.timeout_s,
            json_schema=json_schema,
        )

    def _run(self, request: LLMRequest, parse: Callable[[str], R]) -> R:
        last: LLMError | None = None
        for _ in range(MAX_ATTEMPTS):
            start = time.perf_counter()
            response: LLMResponse | None = None
            try:
                response = self.provider.complete(request)
                result = parse(response.text)
            except LLMError as exc:
                last = exc
                self._record(request, response, start, ok=False, error=_code(exc))
                if isinstance(exc, LLMProviderError) and not exc.retryable:
                    raise
                continue
            self._record(request, response, start, ok=True, error=None)
            return result
        assert last is not None
        raise last

    def _record(
        self,
        request: LLMRequest,
        response: LLMResponse | None,
        start: float,
        *,
        ok: bool,
        error: str | None,
    ) -> None:
        record = LLMCallRecord(
            purpose=request.purpose,
            provider=self.provider.name,
            model=request.model,
            prompt_tokens=response.prompt_tokens if response else None,
            completion_tokens=response.completion_tokens if response else None,
            latency_ms=round((time.perf_counter() - start) * 1000),
            ok=ok,
            error=error,
        )
        logger.info(
            "llm_call purpose=%s provider=%s model=%s latency_ms=%d ok=%s error=%s",
            record.purpose,
            record.provider,
            record.model,
            record.latency_ms,
            record.ok,
            record.error,
        )
        if self.on_call is not None:
            self.on_call(record)


def _code(exc: LLMError) -> str:
    if isinstance(exc, LLMTimeout):
        return "timeout"
    if isinstance(exc, LLMProviderError):
        return exc.code
    return "invalid_response"


def build_provider(settings: Settings) -> LLMProvider:
    """Pick a provider by `LLM_PROVIDER`. SDK-free; vendors are imported only here, lazily."""
    name = settings.llm_provider
    if name == "mock":
        from app.ai.providers.mock import MockProvider

        return MockProvider.from_file(settings.mock_llm_script)
    if name == "openai_like":
        from app.ai.providers.openai_like import OpenAILikeProvider

        if not settings.llm_base_url or settings.llm_api_key is None:
            raise ValueError("LLM_BASE_URL and LLM_API_KEY are required for openai_like")
        return OpenAILikeProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            reasoning_effort=settings.llm_reasoning_effort,
        )
    raise ValueError(f"Unknown LLM_PROVIDER {name!r} (supported: mock, openai_like)")


def model_for(settings: Settings, purpose: Purpose) -> str:
    chosen = {
        "interpreter": settings.llm_model_interpreter,
        "generator": settings.llm_model_generator,
        "debrief": settings.llm_model_debrief,
        "bench": settings.llm_model_interpreter,
    }[purpose]
    if chosen:
        return chosen
    if settings.llm_provider == "mock":
        return "mock-model"
    raise ValueError(f"LLM_MODEL_{purpose.upper()} is not set")


@lru_cache
def _cached_provider() -> LLMProvider:
    # One provider (and its HTTP connection pool) per process.
    # Tests: `_cached_provider.cache_clear()`.
    return build_provider(get_settings())


def get_llm_client(
    purpose: Purpose, *, on_call: OnCall | None = None, model: str | None = None
) -> LLMClient:
    settings = get_settings()
    return LLMClient(
        _cached_provider(),
        model=model or model_for(settings, purpose),
        timeout_s=settings.llm_timeout_s,
        on_call=on_call,
    )


__all__ = [
    "LLMCallRecord",
    "LLMClient",
    "LLMError",
    "LLMInvalidResponse",
    "LLMProvider",
    "LLMProviderError",
    "LLMRequest",
    "LLMResponse",
    "LLMTimeout",
    "build_provider",
    "get_llm_client",
]
