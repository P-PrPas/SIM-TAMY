"""Consequence Replay markers (FR-REP-01, T-064): derived from the log + the case, pure."""

from pathlib import Path

import pytest

from app.content.loader import load_case
from app.engine.replay import build_replay, missed_opportunities
from tests.unit.engine.play import Play

LOADED = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001")
CASE = LOADED.case
NOTES = {"revealed": "R:{fact}", "never_asked": "N:{fact}"}
TEXT = {f.id: f.text_th for f in CASE.facts}


def marks(play: Play) -> list[tuple[int, str, str]]:
    return [
        (m.turn_idx, m.fact_id, m.note_th) for m in missed_opportunities(play.events, CASE, NOTES)
    ]


def test_the_critical_facts_were_never_asked_so_the_marker_is_the_decision_turn() -> None:
    play = Play(LOADED, "A").turn("A01").turn("A02").decide("proceed_service")

    assert marks(play) == [(2, "H1", "N:" + TEXT["H1"]), (2, "H2", "N:" + TEXT["H2"])]


def test_found_then_proceeded_marks_the_turn_the_fact_reached_the_learner() -> None:
    play = Play(LOADED, "A").turn("A03").turn("A04").decide("proceed_service")

    assert marks(play) == [(1, "H1", "R:" + TEXT["H1"]), (2, "H2", "R:" + TEXT["H2"])]


def test_a_mix_of_found_and_never_asked() -> None:
    play = Play(LOADED, "A").turn("A03").turn("A01").decide("proceed_service")

    assert [(m[0], m[1], m[2][0]) for m in marks(play)] == [(1, "H1", "R"), (2, "H2", "N")]


def test_referring_leaves_no_missed_opportunity() -> None:
    play = Play(LOADED, "A").turn("A03").turn("A04").decide("refer")

    assert marks(play) == []
    assert build_replay(play.events, CASE, "d", NOTES).terminal_state == "Referral"


def test_the_replay_is_a_pure_function_of_the_log() -> None:
    play = Play(LOADED, "A").turn("A03").decide("proceed_service")

    a = build_replay(play.events, CASE, "d", NOTES)
    assert a == build_replay(list(reversed(play.events)), CASE, "d", NOTES)  # order of rows moot
    assert a.terminal_state == "UnsafeProceed" and a.timeline_th


@pytest.mark.parametrize("facts", [[], ["H1"]])
def test_only_the_cases_listed_facts_are_marked(facts: list[str]) -> None:
    case = CASE.model_copy(update={"critical_facts_for_replay": facts})
    play = Play(LOADED, "A").turn("A03").decide("proceed_service")

    assert [m.fact_id for m in missed_opportunities(play.events, case, NOTES)] == facts
