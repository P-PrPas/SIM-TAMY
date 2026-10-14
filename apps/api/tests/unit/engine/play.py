"""Builds Event Logs the way the API (T-040) must: it is the contract scoring relies on."""

from pathlib import Path

from app.content.loader import LoadedCase
from app.domain.case import VariantId
from app.domain.events import Event, LoggedEvent
from app.domain.state import SessionState, initial_state
from app.engine.scenario import apply, commit_decision

DEV_001 = Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001"


class Play:
    """Drives the real engine and logs: LEARNER_MESSAGE, ACTIONS_DETECTED (accepted actions only),
    then the engine's own events, each with an increasing row id."""

    def __init__(self, loaded: LoadedCase, variant: VariantId) -> None:
        self.loaded, self.variant = loaded, variant
        self.state: SessionState = initial_state()
        self.events: list[LoggedEvent] = []

    def _log(self, type_: str, turn_idx: int, **payload: object) -> None:
        self.events.append(
            LoggedEvent(id=len(self.events) + 1, type=type_, turn_idx=turn_idx, payload=payload)  # type: ignore[arg-type]
        )

    def _log_all(self, events: tuple[Event, ...]) -> None:
        for e in events:
            self._log(e.type, e.turn_idx, **e.payload)

    def turn(self, *accepted: str) -> "Play":
        idx = self.state.turn_idx + 1
        self._log("LEARNER_MESSAGE", idx)
        self._log("ACTIONS_DETECTED", idx, actions=[{"id": a, "confidence": 0.9} for a in accepted])
        r = apply(self.state, list(accepted), self.loaded.case, self.variant)
        self.state = r.state
        self._log_all(r.events)
        return self

    def decide(self, option: str) -> "Play":
        d = commit_decision(self.state, option, self.loaded.case, self.variant)
        self.state = d.state
        self._log_all(d.events)
        return self

    def note(self, chars: int) -> "Play":
        self._log("NOTE_SUBMITTED", self.state.turn_idx, chars=chars)
        return self

    def complete(self) -> "Play":
        self._log("SESSION_COMPLETED", self.state.turn_idx)
        return self
