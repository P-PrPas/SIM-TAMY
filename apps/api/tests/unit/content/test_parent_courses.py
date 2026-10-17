"""Parent and staff courses (research section 8): valid, still drafts, nothing leaks early."""

import re
from pathlib import Path

import pytest

from app.ai.validator import PatientValidator
from app.content.loader import load_case
from app.content.validate import check
from app.domain.case import HiddenFact
from app.domain.state import AllowedFact, AllowedFacts
from app.services.patient_voice import VoiceRequest

CASES = Path(__file__).resolve().parents[5] / "content" / "cases"
COURSES = {
    "DAD-001": "dad",
    "DAD-002": "dad",
    "MOM-001": "mom",
    "MOM-002": "mom",
    "STF-002": "staff",
}  # case id -> audience; add a course here when it is written


@pytest.mark.parametrize("case_id", COURSES)
def test_course_passes_strict_validation_and_stays_a_draft(case_id: str) -> None:
    loaded = load_case(CASES / case_id)
    assert check(loaded, strict=True) == []
    assert loaded.case.status == "Draft"  # only the Content team may promote it (AGENTS.md rule 9)
    assert loaded.case.audience == COURSES[case_id]


@pytest.mark.parametrize("case_id", COURSES)
def test_course_facts_are_traceable_and_hidden_ones_do_not_leak(case_id: str) -> None:
    case = load_case(CASES / case_id).case
    assert all(f.source for f in case.facts)
    hidden = [f for f in case.facts if f.kind == "hidden"]
    assert any(f.risk_relevance == "critical" for f in hidden)
    shown = [
        case.title_th,
        case.patient_profile.display_th,
        *case.learning_objectives,
        *(f.text_th for f in case.facts if f.kind == "known"),
        *(o.label_th for o in case.decision_options),
        *(v.persona.style_th for v in case.variants.values()),
    ]
    for fact in hidden:
        others = [o for o in hidden if o.id != fact.id]
        assert any(t in fact.text_th for t in fact.leak_terms_th), fact.id
        assert any(k in fact.text_th for k in fact.keywords_th), fact.id
        for line in fact.fallback_utterances_th:
            assert any(k in line for k in fact.keywords_th), (fact.id, line)
            assert not any(t in line for o in others for t in o.leak_terms_th), (fact.id, line)
        for text in shown:  # the CaseBrief shows these before the first question (rule 5)
            assert not any(t in text for t in (*fact.leak_terms_th, *fact.keywords_th)), (
                fact.id,
                text,
            )


@pytest.mark.parametrize("case_id", COURSES)
def test_course_every_fallback_passes_the_real_validator(case_id: str) -> None:
    """A fallback the Validator rejects would leave the learner with an empty reply."""
    case = load_case(CASES / case_id).case
    for fact in (f for f in case.facts if isinstance(f, HiddenFact)):
        request = VoiceRequest(
            persona_style_th=case.variants["A"].persona.style_th,
            allowed=AllowedFacts(
                facts=(AllowedFact(id=fact.id, text_th=fact.text_th),),
                must_convey_fact_ids=(fact.id,),
            ),
            directive="answer",
            learner_text="",
        )
        for line in fact.fallback_utterances_th:
            assert PatientValidator(request).check(line, case, [fact.id]) == [], (fact.id, line)


def _validator(case_persona: str) -> PatientValidator:
    request = VoiceRequest(
        persona_style_th=case_persona,
        allowed=AllowedFacts(facts=(), must_convey_fact_ids=()),
        directive="answer",
        learner_text="",
    )
    return PatientValidator(request)


@pytest.mark.parametrize("case_id", COURSES)
def test_course_no_clause_of_a_hidden_fact_slips_through_before_it_is_asked(case_id: str) -> None:
    """A reply that says only part of a hidden fact ("ไหลออกมา...") must be rejected too."""
    case = load_case(CASES / case_id).case
    validator = _validator(case.variants["A"].persona.style_th)
    for fact in (f for f in case.facts if isinstance(f, HiddenFact)):
        for clause in (c for c in re.split(r"\s+|และ", fact.text_th) if len(c) >= 5):
            reasons = validator.check(clause, case, [])
            assert reasons and reasons[0].startswith("leak_term"), (fact.id, clause)


@pytest.mark.parametrize("case_id", COURSES)
def test_course_scripted_relative_lines_do_not_state_a_hidden_fact(case_id: str) -> None:
    """The pressure script is shown without being asked for, so it must not give a fact away."""
    case = load_case(CASES / case_id).case
    hidden = [f for f in case.facts if isinstance(f, HiddenFact)]
    for variant in case.variants.values():
        for line in variant.pressure_script:
            for fact in hidden:
                assert not any(
                    t in line.text_th for t in (*fact.leak_terms_th, *fact.keywords_th)
                ), (
                    fact.id,
                    line.text_th,
                )


# Partial replies a model could produce before the fact is asked; the Validator must reject each.
PARTIAL_REPLIES = {
    "MOM-001": ["ปวดศีรษะมากไม่ยอมหาย กินยาแล้วก็ไม่ดีขึ้น"],
    "MOM-002": ["มีไข้ตั้งแต่เมื่อวาน", "แผลยังไม่หายสนิท", "น้ำคาวปลาเหม็น", "ยาต้มที่คุณยายให้"],
    "DAD-002": ["มีไข้ตั้งแต่เมื่อวาน", "ปวดศีรษะไม่หาย", "น้ำคาวปลาเหม็น", "ร้องไห้มาหลายวัน"],
}


@pytest.mark.parametrize("case_id", PARTIAL_REPLIES)
def test_course_partial_replies_are_rejected_before_the_fact_is_asked(case_id: str) -> None:
    case = load_case(CASES / case_id).case
    validator = _validator(case.variants["A"].persona.style_th)
    for reply in PARTIAL_REPLIES[case_id]:
        reasons = validator.check(reply, case, [])
        assert reasons and reasons[0].startswith("leak_term"), reply
