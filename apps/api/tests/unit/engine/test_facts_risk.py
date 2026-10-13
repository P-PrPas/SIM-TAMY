"""T-021: hidden-fact unlock, risk_state, and the allowed-facts contract (DEV-001 fixture)."""

from itertools import combinations
from pathlib import Path

from app.content.loader import load_case
from app.domain.case import BranchRule, Case
from app.domain.state import AllowedFacts, SessionState, initial_state
from app.engine.scenario import apply

ROOT = Path(__file__).resolve().parents[5]
LOADED = load_case(ROOT / "content" / "cases" / "DEV-001")
CASE = LOADED.case
ALL_ACTIONS = [a.id for a in LOADED.actions]
HIDDEN = {f.id for f in CASE.facts if f.kind == "hidden"}


def turn(state: SessionState, *ids: str, case: Case = CASE, variant: str = "A"):  # type: ignore[no-untyped-def]
    return apply(state, list(ids), case, variant)  # type: ignore[arg-type]


def ids(allowed: AllowedFacts) -> list[str]:
    return [f.id for f in allowed.facts]


def test_unlock_action_reveals_the_fact_and_sets_risk() -> None:
    r = turn(initial_state(), "A03")

    assert r.state.revealed_fact_ids == ("H1",) and r.state.risk_state == "recognized"
    assert [(e.type, e.payload) for e in r.events if e.type != "PHASE_CHANGED"] == [
        ("FACT_REVEALED", {"id": "H1", "unlocked_by": ["A03"]}),
        ("RISK_STATE_CHANGED", {"from": "unrecognized", "to": "recognized"}),
    ]
    assert ids(r.allowed) == ["K1", "H1"] and r.allowed.must_convey_fact_ids == ("H1",)


def test_repeating_the_action_does_not_reveal_again_but_stays_allowed() -> None:
    s = turn(initial_state(), "A03").state
    r = turn(s, "A03")

    assert [e.type for e in r.events] == ["ACTION_REPEATED"]  # no FACT_REVEALED, no risk event
    assert r.state.revealed_fact_ids == ("H1",)
    assert ids(r.allowed) == ["K1", "H1"] and r.allowed.must_convey_fact_ids == ()


def test_earlier_fact_is_not_passed_when_the_question_is_about_something_else() -> None:
    s = turn(initial_state(), "A03").state

    asked_other = turn(s, "A01")
    assert ids(asked_other.allowed) == ["K1"]

    asked_h2 = turn(s, "A04")
    assert ids(asked_h2.allowed) == ["K1", "H2"] and asked_h2.allowed.must_convey_fact_ids == (
        "H2",
    )


def test_two_unlocks_in_one_turn_keep_case_file_order() -> None:
    r = turn(initial_state(), "A04", "A03")

    assert r.state.revealed_fact_ids == ("H1", "H2")  # case order, not action order
    assert r.allowed.must_convey_fact_ids == ("H1", "H2")


def test_risk_event_only_fires_on_change() -> None:
    s = turn(initial_state(), "A03").state
    r = turn(s, "A04")
    assert (
        "RISK_STATE_CHANGED" not in [e.type for e in r.events]
        and r.state.risk_state == "recognized"
    )


def with_rules(*specs: dict[str, object]) -> Case:
    return CASE.model_copy(update={"branch_rules": [BranchRule.model_validate(s) for s in specs]})


def test_a_rule_can_set_risk_and_change_phase_together() -> None:
    case = with_rules(
        {
            "from": "INTERVIEW",
            "on_action_any": ["A03"],
            "to": "CLOSING",
            "set_risk_state": "escalated",
        }
    )
    r = turn(initial_state(), "A03", case=case)
    assert r.state.risk_state == "escalated" and r.state.phase == "CLOSING"


def test_rule_for_another_phase_or_variant_sets_nothing() -> None:
    case = with_rules(
        {"from": "PRESSURE", "on_action_any": ["A03"], "set_risk_state": "recognized"},
        {
            "from": "INTERVIEW",
            "on_action_any": ["A03"],
            "set_risk_state": "recognized",
            "if_variant": ["C"],
        },
    )
    assert turn(initial_state(), "A03", case=case, variant="A").state.risk_state == "unrecognized"
    assert turn(initial_state(), "A03", case=case, variant="C").state.risk_state == "recognized"


def test_no_leak_sweep_over_every_action_and_pair() -> None:
    """AGENTS.md rules 4/5: allowed facts are only known + revealed, and carry id + text only."""
    known = set(CASE.patient_profile.known_facts)
    starts = [
        initial_state(),
        turn(initial_state(), "A03").state,
        turn(initial_state(), "A03", "A04").state,
    ]
    combos = [(a,) for a in ALL_ACTIONS] + list(combinations(ALL_ACTIONS, 2))

    for start in starts:
        for combo in combos:
            r = turn(start, *combo)
            allowed = set(ids(r.allowed))
            assert allowed <= known | set(r.state.revealed_fact_ids), (start.phase, combo)
            assert set(r.allowed.must_convey_fact_ids) <= allowed
            assert set(r.state.revealed_fact_ids) & HIDDEN == set(r.state.revealed_fact_ids)
            for fact in r.allowed.model_dump()["facts"]:
                assert set(fact) == {"id", "text_th"}


def test_unrevealed_hidden_text_never_appears_in_allowed_facts() -> None:
    r = turn(initial_state(), "A01", "A02", "A05")  # unlocks only H3
    texts = " ".join(f.text_th for f in r.allowed.facts)
    for fact in CASE.facts:
        if fact.kind == "hidden" and fact.id != "H3":
            assert fact.text_th not in texts
