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
from app.domain.state import AllowedFacts

_FALLBACK_TEXT = "mock reply"
_CANNED = Path(__file__).resolve().parents[1] / "prompts" / "canned_th.yaml"


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
        rules = self.script.get(request.purpose, [])
        for rule in rules:
            if "default" in rule:
                return _reply(rule["default"])
            if "match_contains" in rule and rule["match_contains"] in request.prompt:
                return _reply(rule["return"])
        if request.json_schema is not None:
            # An empty success suppresses the real lexical fallback and loses every Action.
            raise LLMProviderError("mock_no_rule", retryable=False)
        if request.purpose == "generator":
            lines = yaml.safe_load(_CANNED.read_text(encoding="utf-8"))
            try:
                payload = json.loads(request.prompt)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                if payload.get("directive") == "clarify":
                    return _reply(lines["clarify"])
                if payload.get("directive") == "answer":
                    allowed = AllowedFacts.model_validate(
                        {
                            "facts": payload.get("allowed_facts", []),
                            "must_convey_fact_ids": payload.get("must_convey_fact_ids", []),
                        }
                    )
                    wanted = set(allowed.must_convey_fact_ids)
                    chosen = [fact for fact in allowed.facts if fact.id in wanted]
                    text = " ".join(fact.text_th for fact in chosen or allowed.facts)
                    if text:
                        return _reply(text)
            return _reply(lines["smalltalk"])
        return LLMResponse(text=_FALLBACK_TEXT, prompt_tokens=0, completion_tokens=0)


def _reply(value: Any) -> LLMResponse:
    text = (
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    )
    return LLMResponse(text=text, prompt_tokens=0, completion_tokens=0)
