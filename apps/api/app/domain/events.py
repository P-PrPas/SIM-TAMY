"""Event Log entries (PRD 7.5). The log is the single source of truth for scoring."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

EventType = Literal[
    "SESSION_STARTED",
    "LEARNER_MESSAGE",
    "ACTIONS_DETECTED",
    "ACTION_REPEATED",
    "CLARIFICATION_ASKED",
    "FACT_REVEALED",
    "RISK_STATE_CHANGED",
    "PHASE_CHANGED",
    "DECISION_COMMITTED",
    "UNSAFE_ACTION",
    "PRESSURE_STARTED",
    "PRESSURE_RESOLVED",
    "NOTE_SUBMITTED",
    "VALIDATOR_REJECTED",
    "LLM_FALLBACK_USED",
    "SESSION_COMPLETED",
]


class Event(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: EventType
    turn_idx: int
    payload: dict[str, Any] = {}


class LoggedEvent(Event):
    """An `Event` as stored in the Event Log: has its row id (the order scoring replays in)."""

    id: int
