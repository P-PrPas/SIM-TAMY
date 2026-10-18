"""Public family contracts deliberately omit private partner briefs and live feedback."""

import uuid
from typing import Literal

from pydantic import Field

from app.domain.case import Model
from app.domain.family import FamilyRole, FamilySkill, FamilySource


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
    total_steps: int
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
