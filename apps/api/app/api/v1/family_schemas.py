"""Public family contracts deliberately omit private partner briefs and live feedback."""

import uuid
from typing import Literal

from pydantic import Field

from app.core.limits import MAX_TEXT_CHARS
from app.domain.case import Model
from app.domain.family import EvidenceStatus, FamilyRole, FamilySkill, FamilySource


class FamilyCreate(Model):
    story_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)
    role: FamilyRole
    assignment_id: uuid.UUID | None = None  # cohort assignment this room belongs to (2.0)


class FamilyJoin(Model):
    invite: str = Field(min_length=32, max_length=128)
    participant_token: str = Field(min_length=32, max_length=128)


class FamilyDecision(Model):
    choice_id: str = Field(min_length=1, max_length=64)
    state_version: int = Field(ge=0)
    client_turn_id: uuid.UUID


class FamilyMessage(Model):
    """Typed learner text (AI-01). Never commits a critical or joint decision by itself."""

    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    state_version: int = Field(ge=0)
    client_turn_id: uuid.UUID


class FamilyShare(Model):
    fact_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)
    client_turn_id: uuid.UUID


class FamilyCardSource(Model):
    id: str
    title_th: str
    url: str


class FamilyLensView(Model):
    wisdom_th: str
    safety_th: str
    rights_th: str


class FamilyKnowledgeCard(Model):
    lens: FamilyLensView | None = None
    tradition_th: str
    learning_point_th: str
    evidence_status: EvidenceStatus
    precautions_th: list[str]
    when_to_consult_th: str | None
    sources: list[FamilyCardSource]


class FamilyVoteChoice(Model):
    role: FamilyRole
    choice_id: str
    text_th: str


class FamilyVote(Model):
    """Joint-step state. The partner's choice appears only once both have voted (disagreement)."""

    my_choice_id: str | None
    waiting_for_partner: bool
    disagreement: list[FamilyVoteChoice] | None


class FamilyFactView(Model):
    id: str
    role: FamilyRole
    text_th: str
    shared: bool


class FamilyOption(Model):
    id: str
    text_th: str


class FamilyScene(Model):
    id: str
    chapter_th: str
    role: FamilyRole
    speaker_th: str
    prompt_th: str
    choices: list[FamilyOption]
    joint: bool = False
    vote: FamilyVote | None = None
    card: FamilyKnowledgeCard | None = None
    kind: Literal["choice", "discover"] = "choice"
    character_th: str | None = None  # discover: whom the learner is questioning
    accepts_text: bool = False  # typed chat is available on this step for the caller
    can_continue: bool = True  # discover: enough answers gathered to press continue
    examples_th: list[str] = []  # discover: sample questions only (no intent ids or labels)


class FamilyExchange(Model):
    idx: int
    role: FamilyRole
    speaker_th: str
    prompt_th: str
    text_th: str
    reply_th: str
    mood: Literal["warm", "open"] | None = None  # coarse character reaction to the committed choice


class FamilyEvidence(Model):
    idx: int
    text_th: str
    feedback_th: str
    source_ids: list[str]
    safe: bool
    # Finished-report only: lets the end-of-chapter reveal replay each choice (LP-03).
    skills: list[FamilySkill] = []
    dimension: str | None = None
    critical: bool = False
    kind: Literal["choice", "discover"] = "choice"


class FamilyCompetency(Model):
    skill: FamilySkill
    observed: int
    opportunities: int


class FamilyDimension(Model):
    id: str
    weight: int
    earned: int
    possible: int
    score: int


class FamilyDialogueTurn(Model):
    """One typed question and the character's validated answer, visible to the asker only."""

    step_id: str
    speaker_th: str
    text_th: str
    reply_th: str


class FamilyReport(Model):
    safety_status: str
    score_total: int | None = None  # rubric dimensions, 2.0 stories only; never replaces the gate
    dimensions: list[FamilyDimension] = []
    competencies: list[FamilyCompetency]
    evidence: list[FamilyEvidence]
    sources: list[FamilySource]


class FamilyView(Model):
    room_id: uuid.UUID
    story_id: str
    title_th: str
    role: FamilyRole
    private_brief_th: str
    partner_joined: bool
    state_version: int
    completed_steps: int = 0
    total_steps: int
    partner_online: bool = False
    my_facts: list[FamilyFactView] = []
    shared_facts: list[FamilyFactView] = []
    scene: FamilyScene | None
    transcript: list[FamilyExchange]
    report: FamilyReport | None
    dialogue: list[FamilyDialogueTurn] = []
    assignment_id: uuid.UUID | None = None


class FamilyCreated(Model):
    room_id: uuid.UUID
    token: str
    invite: str


class FamilyStoryCard(Model):
    id: str
    title_th: str
    description_th: str
    mode: Literal["coop", "solo"]
    chapters_th: list[str]


class FamilyCitation(Model):
    knowledge_id: str
    claim_id: str
    source_id: str
    title: str
    locator: str


class FamilyReply(Model):
    speaker_th: str
    text_th: str
    citations: list[FamilyCitation]


class FamilyClarification(Model):
    """Allowed options as buttons. Discover options are re-sent as text; choice options vote."""

    options: list[FamilyOption]


class FamilyMessageResult(Model):
    view: FamilyView
    reply: FamilyReply | None
    clarification: FamilyClarification | None
