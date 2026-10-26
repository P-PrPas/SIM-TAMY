"""Content-owned family exercises; separate from clinical Case/Rubric contracts."""

from typing import Literal

from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

FamilyRole = Literal["mother", "father"]
FamilySkill = Literal["communication", "responsibility", "safety", "support", "shared_decision"]
EvidenceStatus = Literal[
    "traditional_practice", "supported_by_guidance", "insufficient_evidence", "caution"
]


class FamilyChoice(Model):
    id: NonBlank
    text_th: NonBlank
    reply_th: NonBlank
    reply_alternatives_th: list[NonBlank] = []
    feedback_th: NonBlank
    skills: list[FamilySkill] = []
    safe: bool = True
    flags: list[str] = []


class FamilyCard(Model):
    """Optional expandable knowledge card: separates a tradition from its evidence status."""

    tradition_th: NonBlank
    learning_point_th: NonBlank
    evidence_status: EvidenceStatus
    precautions_th: list[NonBlank] = []
    when_to_consult_th: NonBlank | None = None
    source_ids: list[str] = Field(min_length=1)


class FamilyFact(Model):
    """A private-brief item one role may choose to share into the common timeline."""

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    role: FamilyRole
    text_th: NonBlank
    skills: list[FamilySkill] = []


class FamilyStep(Model):
    id: NonBlank
    chapter_th: NonBlank
    role: FamilyRole
    speaker_th: NonBlank
    prompt_th: NonBlank
    prompt_if: dict[str, str] = {}
    critical: bool = False
    joint: bool = False
    card: FamilyCard | None = None
    source_ids: list[str] = Field(min_length=1)
    choices: list[FamilyChoice] = Field(min_length=2)


class FamilySource(Model):
    id: NonBlank
    title_th: NonBlank
    url: str = Field(pattern=r"^https://")
    category: Literal["guidance", "culture", "limited_evidence"] = "guidance"
    summary_th: NonBlank


class FamilyStory(Model):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    version: NonBlank
    status: Literal["Draft", "In Review", "Approved"]
    mode: Literal["coop", "solo"] = "coop"
    voice_style_th: NonBlank | None = None
    title_th: NonBlank
    description_th: NonBlank
    roles: dict[FamilyRole, NonBlank]
    facts: list[FamilyFact] = []
    steps: list[FamilyStep] = Field(min_length=1)
    sources: list[FamilySource] = Field(min_length=1)

    @model_validator(mode="after")
    def references(self) -> "FamilyStory":
        if set(self.roles) != {"mother", "father"}:
            raise ValueError("both private role briefs are required")
        if len({s.id for s in self.steps}) != len(self.steps):
            raise ValueError("duplicate step ID")
        source_ids = {source.id for source in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("duplicate source ID")
        fact_ids = {fact.id for fact in self.facts}
        if len(fact_ids) != len(self.facts):
            raise ValueError("duplicate fact ID")
        if (self.facts or any(step.joint for step in self.steps)) and self.mode != "coop":
            raise ValueError("shared facts and joint decisions need a co-op story")
        flags: set[str] = set()
        for step in self.steps:
            if not set(step.source_ids) <= source_ids:
                raise ValueError("unknown source reference")
            if step.card and not set(step.card.source_ids) <= source_ids:
                raise ValueError("unknown card source reference")
            recalled = {k for k in step.prompt_if if not k.startswith("fact:")}
            if (
                not recalled <= flags
                or not {k[5:] for k in step.prompt_if if k.startswith("fact:")} <= fact_ids
            ):
                raise ValueError("recall must reference a previous choice flag or a fact")
            if len({c.id for c in step.choices}) != len(step.choices):
                raise ValueError("duplicate choice ID")
            flags.update(flag for choice in step.choices for flag in choice.flags)
        return self
