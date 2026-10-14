"""Confidence policy (FR-ACT-02) and the patient reply loop (FR-VAL-01/02), without a database."""

from pathlib import Path

import pytest

from app.ai.interpreter import DetectedAction, Interpretation
from app.ai.llm_client import LLMProviderError
from app.ai.policy import apply_policy
from app.content.loader import load_case
from app.domain.state import AllowedFact, AllowedFacts
from app.services.patient_voice import (
    CannedGenerator,
    FloorValidator,
    Voice,
    VoiceRequest,
    canned,
    speak,
)

CASE = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001").case
H1 = "ผู้รับบริการมีสัญญาณทดสอบก"
H2 = "ผู้รับบริการมีสัญญาณทดสอบข"


def found(*pairs: tuple[str, float]) -> Interpretation:
    return Interpretation(
        actions=tuple(DetectedAction(id=i, confidence=c, evidence_span="x") for i, c in pairs)
    )


@pytest.mark.parametrize(
    ("pairs", "accepted", "clarify"),
    [
        ([("A03", 0.75)], ["A03"], False),
        ([("A03", 0.7499)], [], True),
        ([("A03", 0.5)], [], True),
        ([("A03", 0.4999)], [], False),
        ([("A03", 0.9), ("A04", 0.6)], ["A03"], False),  # understood part wins, no clarification
        ([("A03", 0.6), ("A04", 0.55)], [], True),
        ([], [], False),
    ],
)
def test_policy_bands(pairs: list[tuple[str, float]], accepted: list[str], clarify: bool) -> None:
    d = apply_policy(found(*pairs))

    assert ([a.id for a in d.accepted], d.clarify) == (accepted, clarify)


def test_the_llm_asking_for_clarification_counts_when_nothing_was_accepted() -> None:
    ask = Interpretation(needs_clarification=True)
    assert apply_policy(ask).clarify is True
    ok = Interpretation(
        actions=(DetectedAction(id="A03", confidence=0.9, evidence_span="x"),),
        needs_clarification=True,
    )
    assert apply_policy(ok).clarify is False


def request(directive: str = "answer", *, facts: tuple[AllowedFact, ...] = ()) -> VoiceRequest:
    allowed = AllowedFacts(facts=facts, must_convey_fact_ids=tuple(f.id for f in facts))
    return VoiceRequest("style", allowed, directive, "text")  # type: ignore[arg-type]


H1_FACT = AllowedFact(id="H1", text_th=H1)


class Script:
    def __init__(self, *lines: str | Exception) -> None:
        self.lines, self.calls = list(lines), 0

    def generate(self, request: VoiceRequest, attempt: int) -> str:
        self.calls += 1
        line = self.lines[min(attempt, len(self.lines) - 1)]
        if isinstance(line, Exception):
            raise line
        return line


@pytest.mark.parametrize(
    ("text", "revealed", "failed"),
    [
        (H1, ["H1"], []),
        (H1, [], ["leak_term:H1"]),  # H1 not revealed yet
        (H1 + H2, ["H1"], ["leak_term:H2"]),
        ("คำต้องห้ามทดสอบ", [], ["forbidden_term"]),
        ("ก" * 301, ["H1", "H2", "H3"], ["length"]),
        ("ก" * 300, ["H1", "H2", "H3"], []),
        ("สัญญาณ​ทดสอบก", [], ["leak_term:H1"]),  # zero-width chars are stripped before matching
    ],
)
def test_floor_validator(text: str, revealed: list[str], failed: list[str]) -> None:
    assert FloorValidator().check(text, CASE, revealed) == failed


def test_speak_returns_the_first_clean_line() -> None:
    gen = Script(H1)

    spoken = speak(request(facts=(H1_FACT,)), CASE, ["H1"], Voice(gen, FloorValidator()))

    assert (spoken.text, spoken.rejected, spoken.fallback, gen.calls) == (H1, (), False, 1)


def test_speak_regenerates_twice_then_uses_the_canned_utterance() -> None:
    gen = Script(H2)  # always leaks H2, which is not revealed

    spoken = speak(request(facts=(H1_FACT,)), CASE, ["H1"], Voice(gen, FloorValidator()))

    assert gen.calls == 3 and spoken.fallback and not spoken.generator_failed
    assert spoken.rejected == (("leak_term:H2",),) * 3
    assert spoken.text == "ค่ะ มีสัญญาณทดสอบกค่ะ"  # H1's fallback_utterances_th[0]


def test_speak_recovers_on_the_third_attempt() -> None:
    gen = Script(H2, H2, H1)

    spoken = speak(request(facts=(H1_FACT,)), CASE, ["H1"], Voice(gen, FloorValidator()))

    assert (spoken.text, spoken.fallback, len(spoken.rejected)) == (H1, False, 2)


def test_speak_without_a_fact_to_convey_falls_back_to_generic_lines() -> None:
    bad = Script(H2)
    assert speak(request("answer"), CASE, [], Voice(bad, FloorValidator())).text == canned(
        "smalltalk"
    )
    assert speak(request("clarify"), CASE, [], Voice(bad, FloorValidator())).text == canned(
        "clarify"
    )


def test_speak_survives_a_generator_failure() -> None:
    gen = Script(LLMProviderError("boom"))

    spoken = speak(request(facts=(H1_FACT,)), CASE, ["H1"], Voice(gen, FloorValidator()))

    assert (spoken.fallback, spoken.generator_failed, spoken.rejected) == (True, True, ())
    assert gen.calls == 1  # a dead provider is not retried here (LLMClient already retried)


def test_the_canned_generator_uses_only_what_it_was_given() -> None:
    g = CannedGenerator()
    known = AllowedFact(id="K1", text_th="ข้อมูลตั้งต้น")
    req = VoiceRequest(
        "style",
        AllowedFacts(facts=(known, H1_FACT), must_convey_fact_ids=("H1",)),
        "answer",
        "text",
    )

    assert g.generate(req, 0) == H1  # the fact this turn is about, not everything allowed
    assert g.generate(request("clarify"), 0) == canned("clarify")
    assert g.generate(request("deflect_smalltalk"), 0) == canned("smalltalk")
