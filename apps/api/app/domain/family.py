"""Content-owned family exercises; separate from clinical Case/Rubric contracts."""

from typing import Literal

from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

FamilyRole = Literal["mother", "father"]
FamilySkill = Literal["communication", "responsibility", "safety", "support"]


class FamilyChoice(Model):
    id: NonBlank
    text_th: NonBlank
    reply_th: NonBlank
    feedback_th: NonBlank
    skills: list[FamilySkill] = []
    safe: bool = True
    flags: list[str] = []


class FamilyStep(Model):
    id: NonBlank
    chapter_th: NonBlank
    role: FamilyRole
    speaker_th: NonBlank
    prompt_th: NonBlank
    prompt_if: dict[str, str] = {}
    critical: bool = False
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
    title_th: NonBlank
    description_th: NonBlank
    roles: dict[FamilyRole, NonBlank]
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
        flags: set[str] = set()
        for step in self.steps:
            if not set(step.source_ids) <= source_ids:
                raise ValueError("unknown source reference")
            if not set(step.prompt_if) <= flags:
                raise ValueError("recall must reference a previous choice flag")
            if len({c.id for c in step.choices}) != len(step.choices):
                raise ValueError("duplicate choice ID")
            flags.update(flag for choice in step.choices for flag in choice.flags)
        return self
