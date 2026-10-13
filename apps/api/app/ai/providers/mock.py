"""Offline, deterministic provider (PRD FR-OBS-02, Appendix A).

The reply is a pure function of (purpose, prompt) and the script: same input, same output.
Script shape, per purpose, first match wins:

    interpreter:
      - match_contains: "..."      # substring of the user prompt
        return: {...}              # dict/list -> JSON text, str -> as is
      - default: {...}
"""

import json
from pathlib import Path
from typing import Any

import yaml

from app.ai.llm_client import LLMProviderError, LLMRequest, LLMResponse

# Used when a script has no matching rule, so LLM_PROVIDER=mock works with no script at all.
_BUILTIN: dict[str, list[dict[str, Any]]] = {
    "interpreter": [
        {"default": {"actions": [], "needs_clarification": False, "clarification_hint": None}}
    ],
}
_FALLBACK_TEXT = "mock reply"


class MockProvider:
    name = "mock"

    def __init__(self, script: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.script = script or {}

    @classmethod
    def from_file(cls, path: Path | None) -> "MockProvider":
        if path is None:
            return cls()
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict) or not all(isinstance(v, list) for v in loaded.values()):
            raise ValueError("mock LLM script must map each purpose to a list of rules")
        return cls(loaded)

    def complete(self, request: LLMRequest) -> LLMResponse:
        rules = [*self.script.get(request.purpose, []), *_BUILTIN.get(request.purpose, [])]
        for rule in rules:
            if "default" in rule:
                return _reply(rule["default"])
            if "match_contains" in rule and rule["match_contains"] in request.prompt:
                return _reply(rule["return"])
        if request.json_schema is not None:
            raise LLMProviderError("mock_no_rule", retryable=False)
        return LLMResponse(text=_FALLBACK_TEXT, prompt_tokens=0, completion_tokens=0)


def _reply(value: Any) -> LLMResponse:
    text = (
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    )
    return LLMResponse(text=text, prompt_tokens=0, completion_tokens=0)
