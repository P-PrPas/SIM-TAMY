"""T-022: Decision Panel commit and unsafe-action detection (DEV-001 fixture)."""

from pathlib import Path

import pytest

from app.content.loader import load_case
from app.domain.case import VariantId
from app.domain.state import SessionState, initial_state
from app.engine.scenario import (
    DecisionAlreadyCommitted,
    DecisionOptionInvalid,
    InvalidPhase,
    apply,
    commit_decision,
)

CASE = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001").case


def interviewing(*actions: str, variant: VariantId = "A") -> SessionState:
    return apply(initial_state(), list(actions), CASE, variant).state


def types(events: tuple) -> list[str]:  # type: ignore[type-arg]
    return [e.type for e in events]


def test_decision_proceed_after_critical_fact_is_unsafe() -> None:
    r = commit_decision(interviewing("A03"), "proceed_service", CASE, "A")

    assert types(r.events) == ["DECISION_COMMITTED", "PHASE_CHANGED", "UNSAFE_ACTION"]
    unsafe = r.events[-1].payload
    assert unsafe == {"trigger": "decision", "ids": ["proceed_service"], "fact_ids": ["H1"]}
    assert r.state.flags.unsafe_actions == ("proceed_service",) and r.state.phase == "CLOSING"


def test_decision_proceed_before_any_critical_fact_is_not_unsafe() -> None:
    r = commit_decision(interviewing("A01"), "proceed_service", CASE, "A")
    assert "UNSAFE_ACTION" not in types(r.events) and r.state.flags.unsafe_actions == ()


def test_decision_a_contextual_fact_alone_is_not_a_red_flag() -> None:
    r = commit_decision(interviewing("A05"), "proceed_service", CASE, "A")  # reveals H3 only
    assert r.state.revealed_fact_ids == ("H3",) and "UNSAFE_ACTION" not in types(r.events)


@pytest.mark.parametrize(("variant", "phase"), [("A", "CLOSING"), ("C", "PRESSURE")])
def test_decision_refer_moves_to_closing_or_pressure(variant: VariantId, phase: str) -> None:
    r = commit_decision(interviewing("A03", variant=variant), "refer", CASE, variant)

    assert r.state.phase == phase and r.state.decision == "refer"
    assert types(r.events) == ["DECISION_COMMITTED", "PHASE_CHANGED"]  # referring is not unsafe
    assert r.events[0].payload == {"option_id": "refer", "actions": ["B01", "B02"]}


def test_decision_records_linked_actions_and_keeps_the_turn_index() -> None:
    state = interviewing("A03")
    r = commit_decision(state, "refer", CASE, "A")

    assert r.state.fired_action_ids == ("A03", "B01", "B02")
    assert r.state.turn_idx == state.turn_idx and r.events[0].turn_idx == state.turn_idx


def test_decision_same_option_again_is_idempotent() -> None:
    first = commit_decision(interviewing("A03"), "proceed_service", CASE, "A")
    again = commit_decision(first.state, "proceed_service", CASE, "A")

    assert again.replayed and again.events == () and again.state == first.state
    assert not first.replayed


def test_decision_different_option_after_commit_is_an_error() -> None:
    done = commit_decision(interviewing("A03"), "refer", CASE, "A").state
    with pytest.raises(DecisionAlreadyCommitted) as info:
        commit_decision(done, "proceed_service", CASE, "A")
    assert info.value.code == "DECISION_ALREADY_COMMITTED"


def test_decision_rejects_wrong_phase_and_unknown_option() -> None:
    with pytest.raises(InvalidPhase) as wrong_phase:
        commit_decision(initial_state(), "refer", CASE, "A")  # still INTRO
    assert wrong_phase.value.code == "INVALID_PHASE"

    with pytest.raises(DecisionOptionInvalid) as unknown:
        commit_decision(interviewing("A03"), "nope", CASE, "A")
    assert unknown.value.code == "DECISION_OPTION_INVALID"


def test_decision_yielding_to_pressure_is_unsafe_too() -> None:
    """Same predicate on the action path: C04 in PRESSURE (mark_unsafe rule)."""
    pressure = commit_decision(interviewing("A03", variant="C"), "refer", CASE, "C").state

    held = apply(pressure, ["C03"], CASE, "C")
    assert held.state.phase == "CLOSING" and "UNSAFE_ACTION" not in types(held.events)

    folded = apply(pressure, ["C04"], CASE, "C")
    assert folded.state.phase == "CLOSING"
    assert folded.events[-1].type == "UNSAFE_ACTION"
    assert folded.events[-1].payload["ids"] == ["C04"] and folded.state.flags.unsafe_actions == (
        "C04",
    )


def test_decision_result_exposes_nothing_unsafe_to_the_learner_facing_fields() -> None:
    """The response fields (phase, decision) must not differ between safe and unsafe commits."""
    unsafe = commit_decision(interviewing("A03"), "proceed_service", CASE, "A").state
    safe = commit_decision(interviewing("A01"), "proceed_service", CASE, "A").state

    assert (unsafe.phase, unsafe.decision) == (safe.phase, safe.decision)


def test_decision_is_deterministic_and_does_not_mutate_its_input() -> None:
    state = interviewing("A03", "A04")
    before = state.model_dump()

    outputs = {
        commit_decision(state, "proceed_service", CASE, "A").state.model_dump_json()
        for _ in range(100)
    }

    assert len(outputs) == 1 and state.model_dump() == before
