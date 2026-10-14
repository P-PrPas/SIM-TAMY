"""Response/request models named exactly like docs/openapi.yaml components.

The spec is the contract (API_DESIGN 13): enums are `StrEnum` classes so they become `$ref`s like in
the spec, and inline objects use `WithJsonSchema` so the generated shape matches. The drift test
compares them.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, WithJsonSchema


class Variant(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class CaseStatus(StrEnum):
    DRAFT = "Draft"
    IN_REVIEW = "In Review"
    APPROVED = "Approved"


class Phase(StrEnum):
    INTERVIEW = "INTERVIEW"
    PRESSURE = "PRESSURE"
    CLOSING = "CLOSING"
    COMPLETED = "COMPLETED"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class Speaker(StrEnum):
    LEARNER = "learner"
    PATIENT = "patient"
    RELATIVE = "relative"
    SYSTEM = "system"


class LearningObjective(BaseModel):
    id: str
    label_th: str


class DecisionOption(BaseModel):
    id: str
    label_th: str


class CaseSummary(BaseModel):
    case_id: str
    version: str
    title_th: str
    status: CaseStatus
    status_label_th: str
    variants_available: list[Variant]


class CaseBrief(CaseSummary):
    patient_display_th: str
    learning_objectives: list[LearningObjective]
    decision_options: list[DecisionOption]
    disclaimer_th: str


class Limits(BaseModel):
    max_turns: int
    max_text_chars: int
    idle_timeout_s: int
    max_rationale_chars: int
    max_note_chars: int


class Notice(BaseModel):
    code: Literal["EDUCATION_ONLY", "CASE_STATUS", "PRIVACY_LLM", "NO_REAL_PII"]
    text_th: str


class CreateSessionRequest(BaseModel):
    case_id: str
    variant: Variant = Variant.A
    learner_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ]
    class_code: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{6}$")] | None = None


TokenType = Annotated[Literal["Bearer"], WithJsonSchema({"type": "string", "enum": ["Bearer"]})]


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    token: str
    token_type: TokenType
    created_at: datetime
    case: CaseBrief
    variant: Variant
    phase: Phase
    limits: Limits
    notices: list[Notice]


class RiskState(StrEnum):
    UNRECOGNIZED = "unrecognized"
    RECOGNIZED = "recognized"
    ESCALATED = "escalated"


class Message(BaseModel):
    idx: Annotated[int, Field(ge=0)]
    speaker: Speaker
    text: str
    created_at: datetime


class DecisionState(BaseModel):
    committed: bool
    option_id: str | None = None
    committed_at_idx: int | None = None


class SessionCase(BaseModel):
    case_id: str
    version: str
    status: CaseStatus
    status_label_th: str


_SESSION_CASE_SCHEMA = {
    "type": "object",
    "required": ["case_id", "version", "status", "status_label_th"],
    "properties": {
        "case_id": {"type": "string"},
        "version": {"type": "string"},
        "status": {"$ref": "#/components/schemas/CaseStatus"},
        "status_label_th": {"type": "string"},
    },
}


class SessionView(BaseModel):
    session_id: uuid.UUID
    case: Annotated[SessionCase, WithJsonSchema(_SESSION_CASE_SCHEMA)]
    variant: Variant
    status: SessionStatus
    phase: Phase
    turn_idx: int
    turns_remaining: int
    decision: DecisionState
    history: list[Message]
    limits: Limits
    created_at: datetime
    last_activity_at: datetime


class TurnRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    client_turn_id: Annotated[str, StringConstraints(min_length=8, max_length=64)] | None = None


class Reply(BaseModel):
    speaker: Literal["patient", "relative", "system"]
    text: str


class Fact(BaseModel):
    id: str
    kind: Literal["known", "hidden"]
    text_th: str
    risk_relevance: Literal["critical", "contextual", "none"] | None = None
    revealed: bool
    revealed_at_idx: int | None = None


class LiveGlassBox(BaseModel):
    risk_state: RiskState
    facts: list[Fact]
    fired_action_ids: list[str]


class TurnResponse(BaseModel):
    turn_idx: int
    replies: list[Reply]
    phase: Phase
    clarification: bool
    turns_remaining: int
    degraded: bool
    glassbox: LiveGlassBox | None = None
