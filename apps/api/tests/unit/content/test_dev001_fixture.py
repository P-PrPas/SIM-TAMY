"""DEV-001 is the engineering fixture the whole pipeline runs on until PP-001 arrives (T-011)."""

from pathlib import Path

from app.content.loader import load_case
from app.content.validate import check

DEV_001 = Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001"
MIN_ACTIONS = {
    *(f"A0{i}" for i in range(1, 8)),
    *(f"B0{i}" for i in range(1, 4)),
    *(f"C0{i}" for i in range(1, 5)),
    "D01",
}


def test_dev001_passes_strict_validation() -> None:
    assert check(load_case(DEV_001), strict=True) == []


def test_dev001_covers_the_minimum_contract() -> None:
    loaded = load_case(DEV_001)
    case = loaded.case
    assert case.status == "Draft" and "DEV-001" in case.title_th
    assert {a.id for a in loaded.actions} >= MIN_ACTIONS
    assert set(case.variants) == {"A", "C"} and case.variants["C"].pressure_script
    assert {"Referral", "UnsafeProceed"} <= set(case.outcome_scripts)
    # all 10 rubric check types are exercised, so T-060 can build its tests on this fixture
    assert len({i.check.type for i in loaded.rubric.items}) == 10
    assert any(i.critical for i in loaded.rubric.items)


def test_dev001_hidden_facts_are_consistent_with_the_validator_rules() -> None:
    """PRD 9.3 rules 3 and 6, applied to the fixture itself (substring probes, no pipeline yet)."""
    case = load_case(DEV_001).case
    hidden = [f for f in case.facts if f.kind == "hidden"]
    assert len(hidden) == 3

    for fact in hidden:
        others = [o for o in hidden if o.id != fact.id]
        # rule 3: stating the fact before unlock must trip its own leak terms
        assert any(t in fact.text_th for t in fact.leak_terms_th), fact.id
        # rule 6: the fact text and every canned fallback must carry a keyword
        assert any(k in fact.text_th for k in fact.keywords_th), fact.id
        for line in fact.fallback_utterances_th:
            assert any(k in line for k in fact.keywords_th), (fact.id, line)
            # a fallback may only reveal its own fact, never another locked one
            assert not any(t in line for o in others for t in o.leak_terms_th), (fact.id, line)

    # known facts and the briefing text must not leak any hidden fact
    leaks = [t for f in hidden for t in f.leak_terms_th]
    visible = [f.text_th for f in case.facts if f.kind == "known"] + [
        case.patient_profile.display_th
    ]
    assert not any(t in text for t in leaks for text in visible)
