"""T-065: a retried turn rebuilds the Glass Box exactly as that turn's answer showed it."""

from pathlib import Path

from app.content.loader import load_case
from app.domain.events import LoggedEvent
from app.services.live import glassbox_at

LOADED = load_case(Path(__file__).resolve().parents[4] / "content" / "cases" / "DEV-001")


def ev(id: int, type: str, turn_idx: int, **payload: object) -> LoggedEvent:
    return LoggedEvent(id=id, type=type, turn_idx=turn_idx, payload=payload)  # type: ignore[arg-type]


LOG = [
    ev(1, "ACTIONS_DETECTED", 1, actions=[{"id": "A01"}]),
    ev(2, "ACTIONS_DETECTED", 2, actions=[{"id": "A03"}]),
    ev(3, "RISK_STATE_CHANGED", 2, **{"from": "unrecognized", "to": "recognized"}),
    # the decision follows turn 2 and shares its turn_idx
    ev(4, "DECISION_COMMITTED", 2, option_id="refer", actions=["B01", "B02"]),
    ev(5, "RISK_STATE_CHANGED", 2, **{"from": "recognized", "to": "escalated"}),
    ev(6, "ACTIONS_DETECTED", 3, actions=[{"id": "C01"}]),
]


def test_the_answer_before_a_decision_excludes_what_the_decision_did() -> None:
    box = glassbox_at(LOG, LOADED, 2)

    assert box.risk_state == "recognized"
    assert box.fired_action_ids == ["A01", "A03"]


def test_a_later_turn_includes_the_decision_and_its_mapped_actions() -> None:
    box = glassbox_at(LOG, LOADED, 3)

    assert box.risk_state == "escalated"
    assert box.fired_action_ids == ["A01", "A03", "B01", "B02", "C01"]


def test_an_early_turn_ignores_everything_after_it() -> None:
    box = glassbox_at(LOG, LOADED, 1)

    assert box.risk_state == "unrecognized" and box.fired_action_ids == ["A01"]
