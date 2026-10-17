"""PP-001 (draft, from the curriculum document) is valid and honest about its own status."""

from pathlib import Path

from app.ai.validator import PatientValidator
from app.content.loader import load_case
from app.content.validate import check
from app.domain.case import HiddenFact
from app.domain.state import AllowedFact, AllowedFacts
from app.services.patient_voice import VoiceRequest

PP_001 = Path(__file__).resolve().parents[5] / "content" / "cases" / "PP-001"


def test_pp001_passes_strict_validation_and_stays_a_draft() -> None:
    loaded = load_case(PP_001)
    assert check(loaded, strict=True) == []
    assert loaded.case.status == "Draft"  # only the Content team may promote it (AGENTS.md rule 9)


def test_pp001_facts_are_traceable_and_hidden_ones_do_not_leak() -> None:
    case = load_case(PP_001).case
    assert all(f.source for f in case.facts)
    hidden = [f for f in case.facts if f.kind == "hidden"]
    visible = [
        case.patient_profile.display_th,
        *(f.text_th for f in case.facts if f.kind == "known"),
    ]
    for fact in hidden:
        others = [o for o in hidden if o.id != fact.id]
        assert any(t in fact.text_th for t in fact.leak_terms_th), fact.id
        assert any(k in fact.text_th for k in fact.keywords_th), fact.id
        for line in fact.fallback_utterances_th:
            assert any(k in line for k in fact.keywords_th), (fact.id, line)
            assert not any(t in line for o in others for t in o.leak_terms_th), (fact.id, line)
        # the briefing and the known facts must not give the hidden fact away
        assert not any(t in text for t in fact.leak_terms_th for text in visible), fact.id


def test_pp001_learner_visible_text_does_not_state_a_hidden_fact() -> None:
    """The CaseBrief shows these before the first question (AGENTS.md rule 5)."""
    case = load_case(PP_001).case
    shown = [
        case.title_th,
        case.patient_profile.display_th,
        *case.learning_objectives,
        *(o.label_th for o in case.decision_options),
        *(v.persona.style_th for v in case.variants.values()),
    ]
    for fact in (f for f in case.facts if f.kind == "hidden"):
        for text in shown:
            assert not any(t in text for t in (*fact.leak_terms_th, *fact.keywords_th)), (
                fact.id,
                text,
            )


def test_pp001_every_fallback_passes_the_real_validator() -> None:
    """A fallback the Validator rejects would leave the learner with an empty reply."""
    case = load_case(PP_001).case
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
