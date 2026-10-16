"""PP-001 (draft, from the curriculum document) is valid and honest about its own status."""

from pathlib import Path

from app.content.loader import load_case
from app.content.validate import check

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
