"""OpenAI-compatible chat/completions over plain HTTP (no vendor SDK).

First real provider is Z.ai GLM (docs.z.ai API reference, verified 2026-10-14):
POST {LLM_BASE_URL}/chat/completions with `Authorization: Bearer <key>`, base URL
https://api.z.ai/api/paas/v4. `response_format` accepts `text` and `json_object` only
(no json_schema), so the schema is embedded in the system message and the caller validates it.
Reasoning models return the answer in `choices[0].message.content`; that is all we read.

DeepSeek (api-docs.deepseek.com, 2026-10-27) is the same wire format: LLM_BASE_URL=https://api.deepseek.com,
model `deepseek-flash` (V4.1-Flash). Thinking mode ignores temperature: set LLM_THINKING=disabled.
"""

import json
from pathlib import Path
from typing import Any

import httpx2

from app.ai.llm_client import (
    LLMInvalidResponse,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMTimeout,
)

_SCHEMA_PROMPT = Path(__file__).resolve().parents[1] / "prompts" / "structured_output.md"


class OpenAILikeProvider:
    name = "openai_like"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        reasoning_effort: str | None = None,
        thinking: str | None = None,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self.reasoning_effort = reasoning_effort
        self.thinking = thinking
        self._client = httpx2.Client(
            base_url=base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            resp = self._client.post(
                "chat/completions",
                json=self._body(request),
                timeout=httpx2.Timeout(request.timeout_s),
            )
        except httpx2.TimeoutException as exc:
            raise LLMTimeout("timeout") from exc
        except httpx2.HTTPError as exc:
            raise LLMProviderError("transport_error") from exc

        if resp.status_code >= 400:
            status = resp.status_code
            raise LLMProviderError(f"http_{status}", retryable=status == 429 or status >= 500)
        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("invalid content")
            usage = data.get("usage")
            if usage is None:
                usage = {}
            if not isinstance(usage, dict):
                raise ValueError("invalid usage")
            for field in ("prompt_tokens", "completion_tokens"):
                value = usage.get(field)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("invalid token count")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMInvalidResponse("invalid_response") from exc
        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        system = request.system
        body: dict[str, Any] = {
            "model": request.model,
            "temperature": request.temperature,
            "stream": False,
        }
        if request.json_schema is not None:
            template = _SCHEMA_PROMPT.read_text(encoding="utf-8")
            schema_json = json.dumps(request.json_schema, ensure_ascii=False)
            system = f"{system}\n\n{template.replace('{schema}', schema_json)}"
            body["response_format"] = {"type": "json_object"}
        body["messages"] = [
            {"role": "system", "content": system},
            {"role": "user", "content": request.prompt},
        ]
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if self.thinking:
            body["thinking"] = {"type": self.thinking}  # DeepSeek: disabled honours temperature
        return body
