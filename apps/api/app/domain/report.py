"""Report parts that come straight from the Event Log (PRD 8.2 `glassbox`, `replay`, `timeline`)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.events import EventType
from app.domain.state import RiskState


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TimelineEntry(_Frozen):
    event_id: int
    turn_idx: int
    type: EventType
    summary_th: str


class GlassFact(_Frozen):
    id: str
    kind: Literal["known", "hidden"]
    text_th: str
    risk_relevance: Literal["critical", "contextual", "none"] | None
    revealed: bool
    revealed_at_idx: int | None


class RiskPoint(_Frozen):
    turn_idx: int
    risk_state: RiskState


class LearnerAction(_Frozen):
    turn_idx: int
    action_id: str
    label_th: str
    repeated: bool


class GlassBox(_Frozen):
    facts: tuple[GlassFact, ...]
    risk_state_timeline: tuple[RiskPoint, ...]
    learner_actions: tuple[LearnerAction, ...]


class MissedOpportunity(_Frozen):
    turn_idx: int
    fact_id: str
    note_th: str


class Replay(_Frozen):
    terminal_state: str
    timeline_th: tuple[str, ...]
    missed_opportunities: tuple[MissedOpportunity, ...]
    disclaimer_th: str
