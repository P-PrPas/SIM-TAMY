"""Pressure phase, Variant C (FR-ENG-05, ADR-11): scripted lines, at most 2 learner turns."""

from pathlib import Path

from app.content.loader import load_case
from app.core.limits import PRESSURE_MAX_TURNS
from app.domain.case import VariantId
from app.engine.scenario import DecisionResult, apply, commit_decision
from tests.unit.engine.play import Play

LOADED = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001")
CASE = LOADED.case
SCRIPT = [line.text_th for line in CASE.variants["C"].pressure_script]


def referred(variant: VariantId = "C") -> tuple[Play, DecisionResult]:
    play = Play(LOADED, variant).turn("A03").turn("A04")
    result = commit_decision(play.state, "refer", CASE, variant)
    play.state = result.state
    play._log_all(result.events)
    return play, result


def test_referring_in_variant_c_starts_the_pressure_with_the_first_scripted_line() -> None:
    play, result = referred()

    assert play.state.phase == "PRESSURE" and play.state.pressure.started_at_idx == 2
    assert result.pressure_line is not None and result.pressure_line.text_th == SCRIPT[0]
    assert result.pressure_line.speaker == "relative"
    assert [e.type for e in result.events].count("PRESSURE_STARTED") == 1


def test_variant_a_has_no_pressure() -> None:
    play, result = referred("A")

    assert play.state.phase == "CLOSING" and result.pressure_line is None
    assert "PRESSURE_STARTED" not in [e.type for e in result.events]


def test_an_unrelated_turn_gets_the_next_scripted_line_and_stays_in_pressure() -> None:
    play, _ = referred()
    result = apply(play.state, [], CASE, "C")

    assert result.state.phase == "PRESSURE" and result.pressure_line is not None
    assert result.pressure_line.text_th == SCRIPT[1] and result.events == ()


def test_confirming_the_referral_resolves_the_pressure() -> None:
    play, _ = referred()
    result = apply(play.state, ["C03"], CASE, "C")

    assert result.state.phase == "CLOSING" and result.state.pressure.resolved is True
    assert result.pressure_line is None and result.state.flags.unsafe_actions == ()
    resolved = [e for e in result.events if e.type == "PRESSURE_RESOLVED"]
    assert resolved[0].payload == {"resolved": True, "by": ["C03"]}


def test_giving_in_resolves_it_and_is_marked_unsafe_when_a_critical_fact_was_found() -> None:
    play, _ = referred()
    result = apply(play.state, ["C04"], CASE, "C")

    assert result.state.phase == "CLOSING" and result.state.pressure.resolved is True
    assert "UNSAFE_ACTION" in [e.type for e in result.events]


def test_two_turns_without_an_answer_close_the_phase_unresolved_and_not_unsafe() -> None:
    play, _ = referred()
    for _ in range(PRESSURE_MAX_TURNS - 1):
        play.turn()
        assert play.state.phase == "PRESSURE"
    last = apply(play.state, [], CASE, "C")

    assert last.state.phase == "CLOSING" and last.state.pressure.resolved is False
    assert last.pressure_line is None and last.state.flags.unsafe_actions == ()
    types = [(e.type, e.payload.get("trigger", e.payload.get("resolved"))) for e in last.events]
    assert types == [("PHASE_CHANGED", "pressure_timeout"), ("PRESSURE_RESOLVED", False)]


def test_a_confirmation_on_the_last_pressure_turn_still_counts() -> None:
    play, _ = referred()
    play.turn()
    result = apply(play.state, ["C03"], CASE, "C")

    assert result.state.pressure.resolved is True
