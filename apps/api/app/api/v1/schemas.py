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


class DecisionRequest(BaseModel):
    option_id: str
    rationale_th: Annotated[str, StringConstraints(max_length=300)] | None = None


_DECISION_SCHEMA = {
    "type": "object",
    "required": ["option_id", "committed_at_idx"],
    "properties": {"option_id": {"type": "string"}, "committed_at_idx": {"type": "integer"}},
}


class DecisionRecord(BaseModel):
    option_id: str
    committed_at_idx: int


class DecisionResponse(BaseModel):
    phase: Phase
    decision: Annotated[DecisionRecord, WithJsonSchema(_DECISION_SCHEMA)]
    replies: list[Reply]
    pressure_turns_allowed: int | None = None


class CompleteRequest(BaseModel):
    note_th: Annotated[str, StringConstraints(max_length=500)] | None = None


class CompleteResponse(BaseModel):
    status: Annotated[
        Literal["completed"], WithJsonSchema({"type": "string", "enum": ["completed"]})
    ]
    report_ready: bool
    report_url: str


# ---------- Report ----------


class EventType(StrEnum):
    SESSION_STARTED = "SESSION_STARTED"
    LEARNER_MESSAGE = "LEARNER_MESSAGE"
    ACTIONS_DETECTED = "ACTIONS_DETECTED"
    ACTION_REPEATED = "ACTION_REPEATED"
    CLARIFICATION_ASKED = "CLARIFICATION_ASKED"
    FACT_REVEALED = "FACT_REVEALED"
    RISK_STATE_CHANGED = "RISK_STATE_CHANGED"
    PHASE_CHANGED = "PHASE_CHANGED"
    DECISION_COMMITTED = "DECISION_COMMITTED"
    UNSAFE_ACTION = "UNSAFE_ACTION"
    PRESSURE_STARTED = "PRESSURE_STARTED"
    PRESSURE_RESOLVED = "PRESSURE_RESOLVED"
    NOTE_SUBMITTED = "NOTE_SUBMITTED"
    VALIDATOR_REJECTED = "VALIDATOR_REJECTED"
    LLM_FALLBACK_USED = "LLM_FALLBACK_USED"
    SESSION_COMPLETED = "SESSION_COMPLETED"


class SafetyStatus(StrEnum):
    SAFETY_MET = "SAFETY_MET"
    SAFETY_NOT_MET = "SAFETY_NOT_MET"


class ItemResultValue(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NA = "na"


class Evidence(BaseModel):
    event_id: int
    turn_idx: int
    type: EventType


class CompetencyScore(BaseModel):
    id: Literal["HX", "RISK", "DEC", "ESC", "COMM", "DOC"]
    name_th: str
    weight: float
    score_pct: Annotated[float, Field(ge=0, le=100)]
    earned: float
    possible: float


class ItemResult(BaseModel):
    id: str
    competency: str
    label_th: str | None = None
    result: ItemResultValue
    points: float
    earned: float
    critical: bool
    evidence: list[Evidence]
    finding_id: str | None = None


class Finding(BaseModel):
    id: str
    polarity: Literal["strength", "improve"]
    rubric_item_id: str
    text_th: str
    evidence_refs: list[int]
    reference_ids: list[str] = []


class DebriefParagraph(BaseModel):
    finding_ids: list[str]
    text_th: str


class Debrief(BaseModel):
    source: Literal["llm", "template"]
    paragraphs: list[DebriefParagraph]


class TimelineEntry(BaseModel):
    event_id: int
    turn_idx: int
    type: EventType
    summary_th: str


_RISK_POINT_SCHEMA = {
    "type": "object",
    "required": ["turn_idx", "risk_state"],
    "properties": {
        "turn_idx": {"type": "integer"},
        "risk_state": {"$ref": "#/components/schemas/RiskState"},
    },
}
_LEARNER_ACTION_SCHEMA = {
    "type": "object",
    "required": ["turn_idx", "action_id", "label_th", "repeated"],
    "properties": {
        "turn_idx": {"type": "integer"},
        "action_id": {"type": "string"},
        "label_th": {"type": "string"},
        "repeated": {"type": "boolean"},
    },
}


class RiskPoint(BaseModel):
    turn_idx: int
    risk_state: RiskState


class LearnerAction(BaseModel):
    turn_idx: int
    action_id: str
    label_th: str
    repeated: bool


class GlassBoxReport(BaseModel):
    facts: list[Fact]
    risk_state_timeline: list[Annotated[RiskPoint, WithJsonSchema(_RISK_POINT_SCHEMA)]]
    learner_actions: list[Annotated[LearnerAction, WithJsonSchema(_LEARNER_ACTION_SCHEMA)]]


class MissedOpportunity(BaseModel):
    turn_idx: int
    fact_id: str
    note_th: str


class ReplayReport(BaseModel):
    terminal_state: str
    timeline_th: list[str]
    missed_opportunities: list[MissedOpportunity]
    disclaimer_th: str


class Reference(BaseModel):
    id: str
    title_th: str
    locator: str | None = None


class Override(BaseModel):
    id: int
    rubric_item_id: str
    original_result: ItemResultValue
    new_result: Literal["pass", "fail", "partial"]
    new_earned: float | None = None
    reason: str
    created_at: datetime


class EffectiveScore(BaseModel):
    safety_status: SafetyStatus
    total_score: float


class ReportCase(BaseModel):
    case_id: str
    version: str
    hash: str
    status: CaseStatus
    status_label_th: str
    title_th: str


_REPORT_CASE_SCHEMA = {
    "type": "object",
    "required": ["case_id", "version", "hash", "status", "status_label_th", "title_th"],
    "properties": {
        "case_id": {"type": "string"},
        "version": {"type": "string"},
        "hash": {"type": "string"},
        "status": {"$ref": "#/components/schemas/CaseStatus"},
        "status_label_th": {"type": "string"},
        "title_th": {"type": "string"},
    },
}


class ReportResponse(BaseModel):
    session_id: uuid.UUID
    generated_at: datetime
    engine_version: str
    rubric_version: str
    case: Annotated[ReportCase, WithJsonSchema(_REPORT_CASE_SCHEMA)]
    variant: Variant
    safety_status: SafetyStatus
    total_score: Annotated[float, Field(ge=0, le=100)]
    competencies: list[CompetencyScore]
    items: list[ItemResult]
    findings: list[Finding]
    debrief: Debrief
    timeline: list[TimelineEntry]
    glassbox: GlassBoxReport
    replay: ReplayReport
    references: list[Reference]
    overrides: list[Override]
    effective: EffectiveScore
    disclaimers: list[str]


# ---------- Offline Replay (T-073) ----------


class RecordingSummary(BaseModel):
    recording_id: str
    title_th: str
    case_id: str
    variant: Variant
    description_th: str | None = None
    steps_count: int | None = None


class RecordingStep(BaseModel):
    t_ms: Annotated[int, Field(ge=0)]
    type: Literal["learner", "reply", "decision", "phase_change", "complete"]
    speaker: Speaker | None = None
    text: str | None = None
    option_id: str | None = None
    phase: Phase | None = None


class Recording(RecordingSummary):
    case: CaseBrief
    steps: list[RecordingStep]
    report: ReportResponse


class RecordingListItem(RecordingSummary):
    """A list row also carries the snapshot's case status, so every row can show its badge."""

    status: CaseStatus
    status_label_th: str


class RecordingList(BaseModel):
    items: list[RecordingListItem]
