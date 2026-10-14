"""Scoring results (PRD 10, openapi ItemResult / Evidence). Frozen; produced by `engine.scoring`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.events import EventType

Result = Literal["pass", "fail", "partial", "na"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Evidence(_Frozen):
    event_id: int
    turn_idx: int
    type: EventType


class ItemResult(_Frozen):
    id: str
    competency: str
    result: Result
    points: int
    earned: float
    critical: bool
    evidence: tuple[Evidence, ...] = ()
