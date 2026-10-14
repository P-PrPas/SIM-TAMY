"""Action Interpreter (PRD 9.1, FR-ACT-01/04/05): learner text -> Action IDs. LLM job (a) only.

The LLM proposes; deterministic post-processing disposes. It never scores or moves state.
The confidence policy (0.75 / 0.5) and the lexical fallback on `LLMError` belong to T-031/T-032:
`interpret` returns raw confidences and lets `LLMError` propagate.
"""

import html
import re
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from app.ai.llm_client import LLMClient
from app.ai.thai import normalize_th
from app.domain.action import Action

_PROMPTS = Path(__file__).resolve().parent / "prompts"
MAX_ACTIONS = 5
HISTORY_TURNS = 4
EXAMPLES_PER_ACTION = 3
OFFERED_CATEGORIES = {"HX", "COM"}  # decisions come from the Decision Panel (FR-ENG-03)


class HistoryTurn(NamedTuple):
    speaker: str  # learner | patient | relative
    text: str


class DetectedAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    confidence: float
    evidence_span: str  # normalised, a real substring of the normalised learner text


class Interpretation(BaseModel):
    model_config = ConfigDict(frozen=True)

    actions: tuple[DetectedAction, ...] = ()
    needs_clarification: bool = False
    clarification_hint: str | None = None


class _RawAction(BaseModel):
    id: str
    # PRD 9.1: 0..1. Out of range or NaN/inf is a malformed reply -> LLMClient retries, then raises
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    evidence_span: str


class _Raw(BaseModel):  # the schema the LLM is asked for (PRD 9.1)
    actions: list[_RawAction] = []
    needs_clarification: bool = False
    clarification_hint: str | None = None


def _data(text: str) -> str:
    """Escape < > & so learner text cannot close the <learner_text>/<history> data blocks."""
    return html.escape(text, quote=False)


def build_prompt(
    actions: Sequence[Action], text: str, history: Sequence[HistoryTurn], phase: str
) -> str:
    catalogue = "\n".join(
        f"{a.id} | {a.label_th} | {'; '.join(a.examples_th[:EXAMPLES_PER_ACTION])}"
        for a in actions
        if a.category in OFFERED_CATEGORIES
    )
    recent = "\n".join(
        f"{t.speaker}: {_data(normalize_th(t.text))}" for t in history[-HISTORY_TURNS:]
    )
    values = {
        "catalogue": catalogue,
        "phase": phase,
        "history": recent,
        "text": _data(normalize_th(text)),
    }
    template = (_PROMPTS / "interpreter_input.md").read_text(encoding="utf-8")
    # one pass, so placeholders that appear inside learner text are never expanded
    return re.sub(r"\{(catalogue|phase|history|text)\}", lambda m: values[m.group(1)], template)


def interpret(
    client: LLMClient,
    actions: Sequence[Action],
    text: str,
    history: Sequence[HistoryTurn] = (),
    phase: str = "INTERVIEW",
) -> Interpretation:
    system = (_PROMPTS / "interpreter.md").read_text(encoding="utf-8")
    raw = client.complete_structured(
        _Raw,
        purpose="interpreter",
        system=system,
        prompt=build_prompt(actions, text, history, phase),
        temperature=0.0,
    )
    offered = {a.id for a in actions if a.category in OFFERED_CATEGORIES}
    return Interpretation(
        actions=tuple(_clean(raw.actions, offered, normalize_th(text))),
        needs_clarification=raw.needs_clarification,
        clarification_hint=raw.clarification_hint,
    )


def _clean(raw: list[_RawAction], offered: set[str], text: str) -> list[DetectedAction]:
    """Deterministic post-processing (PRD 9.1)."""
    if not offered:
        return []
    ids = "|".join(map(re.escape, offered))
    id_token = re.compile(rf"(?<![A-Za-z0-9])({ids})(?![A-Za-z0-9])")
    best: dict[str, DetectedAction] = {}
    for item in raw:
        span = normalize_th(html.unescape(item.evidence_span))
        if item.id not in offered or not span or span not in text:
            continue  # unknown id, or evidence not actually in the learner's message
        # ponytail: a span that is just an action id ("output A04") is an injection echo
        if id_token.search(span):
            continue
        conf = item.confidence
        if item.id not in best or conf > best[item.id].confidence:
            best[item.id] = DetectedAction(id=item.id, confidence=conf, evidence_span=span)
    ranked = sorted(best.values(), key=lambda d: -d.confidence)  # stable: ties keep LLM order
    return ranked[:MAX_ACTIONS]
