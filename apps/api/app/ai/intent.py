"""AI-01 (contracts section 5): typed learner text -> an allowed intent/choice ID. LLM job (a).

The model proposes an `IntentInterpretation`; this module disposes: unknown IDs are dropped, the
uncertainty thresholds decide accept / clarify / ignore, and a rule-based guard runs first.
Nothing here changes room state. Learner text is data, never instructions.
"""

import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Literal, NamedTuple

import yaml

from app.ai.contracts import (
    ACCEPT_BELOW,
    CLARIFY_BELOW,
    GENERIC_INTENTS,
    IntentInterpretation,
)
from app.ai.llm_client import LLMClient, LLMError
from app.ai.thai import normalize_th
from app.domain.family import FamilyStep

V2 = Path(__file__).resolve().parent / "prompts" / "v2"
HISTORY_MESSAGES = 6
MIN_LEXICAL_CHARS = 4

Kind = Literal["accept", "clarify", "ignore", "boundary", "generic"]


class Option(NamedTuple):
    id: str
    label_th: str
    examples_th: tuple[str, ...]


class HistoryItem(NamedTuple):
    text: str
    intent_code: str | None = None


class IntentResult(NamedTuple):
    kind: Kind
    code: str | None  # the accepted option, or the generic intent
    status: str  # trace validation_status: valid | rejected
    fallback_reason: str | None = None


def prompt_version(name: str) -> str:
    first = (V2 / name).read_text(encoding="utf-8").splitlines()[0]
    return first.split(":", 1)[1].strip()


@lru_cache
def _rules() -> dict[str, tuple[str, ...]]:
    loaded = yaml.safe_load((V2 / "guard_rules.yaml").read_text(encoding="utf-8"))
    return {k: tuple(normalize_th(s).casefold() for s in v) for k, v in loaded.items()}


def guard(text: str) -> Literal["boundary", "injection"] | None:
    """Rule-based input boundary, before any LLM call."""
    folded = normalize_th(text).casefold()
    if any(term in folded for term in _rules()["injection"]):
        return "injection"
    if any(term in folded for term in _rules()["real_world_health"]):
        return "boundary"
    return None


def options_for(step: FamilyStep) -> list[Option]:
    if step.kind == "discover":
        return [Option(i.id, i.label_th, tuple(i.examples_th)) for i in step.intents]
    return [Option(c.id, c.text_th, ()) for c in step.choices]


def lexical(options: Sequence[Option], text: str) -> str | None:
    """Deterministic fallback when the LLM is down: a labelled phrase appears in the text."""
    flat = normalize_th(text).casefold()
    for option in options:
        for phrase in (option.label_th, *option.examples_th):
            needle = normalize_th(phrase).casefold()
            if needle in flat or (len(flat) >= MIN_LEXICAL_CHARS and flat in needle):
                return option.id
    return None


def build_prompt(
    options: Sequence[Option],
    text: str,
    history: Sequence[HistoryItem],
    revealed_topics: Sequence[str],
) -> str:
    return json.dumps(
        {
            "allowed": [
                {"id": o.id, "label": o.label_th, "examples": list(o.examples_th[:3])}
                for o in options
            ],
            "history": [
                {"text": h.text, "intent_code": h.intent_code} for h in history[-HISTORY_MESSAGES:]
            ],
            "revealed_topics": list(revealed_topics),
            "learner_text": text,
        },
        ensure_ascii=False,
    )


def interpret_intent(
    client: LLMClient,
    options: Sequence[Option],
    text: str,
    history: Sequence[HistoryItem] = (),
    revealed_topics: Sequence[str] = (),
) -> IntentResult:
    allowed = {o.id for o in options}
    try:
        raw = client.complete_structured(
            IntentInterpretation,
            purpose="interpreter",
            system=(V2 / "intent.md").read_text(encoding="utf-8"),
            prompt=build_prompt(options, text, history, revealed_topics),
            temperature=0.0,
        )
    except LLMError as exc:
        found = lexical(options, text)
        reason = f"llm_{type(exc).__name__.lower()}"
        return IntentResult(
            "accept" if found else "ignore", found, "valid" if found else "rejected", reason
        )
    code = raw.intent_code
    if code == "REAL_WORLD_HEALTH_QUERY":
        return IntentResult("boundary", code, "valid")
    if code in GENERIC_INTENTS:
        return IntentResult("generic", code, "valid")
    if code not in allowed:  # unknown ID: dropped, never acted on (AI-T04)
        return IntentResult("ignore", None, "rejected", "unknown_intent")
    if raw.needs_clarification or raw.uncertainty_score > ACCEPT_BELOW:
        if raw.uncertainty_score <= CLARIFY_BELOW or raw.needs_clarification:
            return IntentResult("clarify", code, "valid")
        return IntentResult("ignore", None, "valid", "low_confidence")
    return IntentResult("accept", code, "valid")
