"""Session state (PRD 7.4). Frozen; sequences are tuples so nothing can be mutated in place."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.case import Phase

RiskState = Literal["unrecognized", "recognized", "escalated"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Pressure(_Frozen):
    started_at_idx: int | None = None
    resolved: bool | None = None


class Flags(_Frozen):
    unsafe_actions: tuple[str, ...] = ()
    clarifications: int = 0


class Directive(_Frozen):
    mood: str | None = None


class SessionState(_Frozen):
    phase: Phase = "INTRO"
    turn_idx: int = 0  # learner turn index; the unit of "time" in rubric checks
    risk_state: RiskState = "unrecognized"
    revealed_fact_ids: tuple[str, ...] = ()
    fired_action_ids: tuple[str, ...] = ()  # order matters (action_before)
    decision: str | None = None
    pressure: Pressure = Pressure()
    flags: Flags = Flags()
    last_directive: Directive = Directive()


def initial_state() -> SessionState:
    return SessionState()
