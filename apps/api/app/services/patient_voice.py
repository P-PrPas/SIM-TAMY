"""The patient's reply path: Generator -> Validator -> regenerate (<= 2) -> canned fallback.

PRD 9.2/9.3, FR-GEN-01, FR-VAL-01/02. `Generator` and `Validator` are seams: T-033/T-034 plug in the
LLM generator and the full validator. The defaults here are deterministic. The default validator
is a fail-closed floor (length, forbidden terms, leak terms of facts not yet revealed), never a
pass-through, so a rejected line is never shown even before T-034 lands (AGENTS.md rule 6).
The Generator only receives allowed facts: id + text (rule 4).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, NamedTuple, Protocol

import yaml

from app.ai.interpreter import HistoryTurn
from app.ai.llm_client import LLMError
from app.ai.thai import normalize_th
from app.domain.case import Case, HiddenFact
from app.domain.state import AllowedFacts

MAX_REGENERATIONS = 2
MAX_CHARS = 300  # PRD 9.3 rule 1 (the sentence count needs a Thai splitter; T-034)

Directive = Literal["answer", "clarify", "deflect_smalltalk"]
_CANNED = Path(__file__).resolve().parents[1] / "ai" / "prompts" / "canned_th.yaml"


@dataclass(frozen=True)
class VoiceRequest:
    """Everything a Generator may see. No hidden facts, risk state or rubric."""

    persona_style_th: str
    allowed: AllowedFacts
    directive: Directive
    learner_text: str
    history: tuple[HistoryTurn, ...] = ()


class Generator(Protocol):
    def generate(self, request: VoiceRequest, attempt: int) -> str: ...


class Validator(Protocol):
    def check(self, text: str, case: Case, revealed: Sequence[str]) -> list[str]:
        """Rule names that failed (e.g. `leak_term:H1`); empty means the line may be shown."""
        ...


@lru_cache
def canned(key: str) -> str:
    loaded = yaml.safe_load(_CANNED.read_text("utf-8"))
    return str(loaded[key])


class CannedGenerator:
    """Deterministic default: say the facts this turn is about, in the case's own words."""

    def generate(self, request: VoiceRequest, attempt: int) -> str:
        if request.directive == "clarify":
            return canned("clarify")
        if request.directive == "deflect_smalltalk":
            return canned("smalltalk")
        facts = request.allowed.facts
        wanted = set(request.allowed.must_convey_fact_ids)
        chosen = [f for f in facts if f.id in wanted] or list(facts)
        return " ".join(f.text_th for f in chosen) or canned("smalltalk")


class FloorValidator:
    def check(self, text: str, case: Case, revealed: Sequence[str]) -> list[str]:
        flat = normalize_th(text)
        failed = ["length"] if len(flat) > MAX_CHARS else []
        if any(normalize_th(term) in flat for term in case.forbidden_terms_th):
            failed.append("forbidden_term")
        for fact in case.facts:
            if not isinstance(fact, HiddenFact) or fact.id in revealed:
                continue
            if any(normalize_th(term) in flat for term in fact.leak_terms_th):
                failed.append(f"leak_term:{fact.id}")
        return failed


@dataclass(frozen=True)
class Voice:
    generator: Generator
    validator: Validator


class Spoken(NamedTuple):
    text: str  # empty: nothing safe to say, so no reply is stored or shown
    rejected: tuple[tuple[str, ...], ...]  # rules failed per rejected attempt (never the text)
    fallback: bool  # the canned line was used
    generator_failed: bool  # the Generator raised LLMError


def fallback_line(request: VoiceRequest, case: Case, revealed: Sequence[str], voice: Voice) -> str:
    """The first canned line the Validator accepts: the facts' own lines, then a generic one.

    Empty when none is safe: the patient then says nothing (AGENTS.md rule 6).
    """

    def clean(text: str) -> bool:
        return not voice.validator.check(text, case, revealed)

    candidates: list[str] = []
    if request.directive == "answer":
        by_id = {f.id: f for f in case.facts if isinstance(f, HiddenFact)}
        lines = [
            line
            for i in request.allowed.must_convey_fact_ids
            if i in by_id
            if (line := next((u for u in by_id[i].fallback_utterances_th if clean(u)), None))
        ]
        candidates += [" ".join(lines), *lines]  # all of them, else the first that fits
    candidates.append(canned("clarify" if request.directive == "clarify" else "smalltalk"))
    return next((c for c in candidates if c and clean(c)), "")


def speak(request: VoiceRequest, case: Case, revealed: Sequence[str], voice: Voice) -> Spoken:
    rejected: list[tuple[str, ...]] = []
    for attempt in range(1 + MAX_REGENERATIONS):
        try:
            text = voice.generator.generate(request, attempt)
        except LLMError:
            line = fallback_line(request, case, revealed, voice)
            return Spoken(line, tuple(rejected), True, True)
        failed = voice.validator.check(text, case, revealed)
        if not failed:
            return Spoken(text, tuple(rejected), False, False)
        rejected.append(tuple(failed))
    return Spoken(fallback_line(request, case, revealed, voice), tuple(rejected), True, False)
