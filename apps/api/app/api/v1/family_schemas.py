"""Public family contracts deliberately omit private partner briefs and live feedback."""

import uuid
from typing import Literal

from pydantic import Field

from app.domain.case import Model
from app.domain.family import EvidenceStatus, FamilyRole, FamilySkill, FamilySource


class FamilyCreate(Model):
    story_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)
    role: FamilyRole


class FamilyJoin(Model):
    invite: str = Field(min_length=32, max_length=128)
    participant_token: str = Field(min_length=32, max_length=128)


class FamilyDecision(Model):
    choice_id: str = Field(min_length=1, max_length=64)
    state_version: int = Field(ge=0)
    client_turn_id: uuid.UUID


class FamilyShare(Model):
    fact_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)
    client_turn_id: uuid.UUID


class FamilyCardSource(Model):
    id: str
    title_th: str
    url: str


class FamilyKnowledgeCard(Model):
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


class FamilyExchange(Model):
    idx: int
    role: FamilyRole
    speaker_th: str
    prompt_th: str
    text_th: str
    reply_th: str


class FamilyEvidence(Model):
    idx: int
    text_th: str
    feedback_th: str
    source_ids: list[str]
    safe: bool


class FamilyCompetency(Model):
    skill: FamilySkill
    observed: int
    opportunities: int


class FamilyReport(Model):
    safety_status: str
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
