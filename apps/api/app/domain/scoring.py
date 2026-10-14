"""Scoring results (PRD 10, openapi ItemResult / Evidence). Frozen; produced by `engine.scoring`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.events import EventType

Result = Literal["pass", "fail", "partial", "na"]
SafetyStatus = Literal["SAFETY_MET", "SAFETY_NOT_MET"]


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


class CompetencyScore(_Frozen):
    id: str
    name_th: str
    weight: float  # normalised over the applicable competencies, sums to 100
    score_pct: float
    earned: float
    possible: float


class Scoring(_Frozen):
    """Everything the score is derived from the log; safety is a gate, not part of `total_score`."""

    safety_status: SafetyStatus
    total_score: float
    competencies: tuple[CompetencyScore, ...]
    items: tuple[ItemResult, ...]
