"""Content-owned family exercises; separate from clinical Case/Rubric contracts."""

import re
from typing import Literal

from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

FamilyRole = Literal["mother", "father"]
FamilySkill = Literal["communication", "responsibility", "safety", "support", "shared_decision"]
EvidenceStatus = Literal[
    "traditional_practice", "supported_by_guidance", "insufficient_evidence", "caution"
]
# 2.0 rubric dimensions (contracts section 3; Blueprint 07 draft weights, test values only)
Dimension = Literal["discovery", "decision", "communication", "evidence_scope"]
DEFAULT_RUBRIC: dict[Dimension, int] = {
    "discovery": 25,
    "decision": 35,
    "communication": 25,
    "evidence_scope": 15,
}
UNIT_ID = r"^KB-[A-Z]+-[A-Z]+-\d{3}$"
OBJECTIVE_ID = r"^OBJ-\d-\d{2}$"
CONTINUE = "continue"  # the single choice that closes a discover step
# Pixel icon keys for choice cards (display only; the web draws them)
FamilyIcon = Literal["book", "notebook", "pot", "talk", "pause", "menu", "arrow"]
SHORT_MAX = 30  # card labels stay a glance long (about 25 Thai characters)


class FamilyChoice(Model):
    id: NonBlank
    text_th: NonBlank
    reply_th: NonBlank
    reply_alternatives_th: list[NonBlank] = []
    feedback_th: NonBlank
    skills: list[FamilySkill] = []
    safe: bool = True
    flags: list[str] = []
    dimension: Dimension | None = None  # credited when chosen (rubric); None = no credit
    short_th: NonBlank | None = Field(default=None, max_length=SHORT_MAX)  # card label
    icon: FamilyIcon | None = None  # card icon, display only


class FamilyLens(Model):
    """Thai Wisdom Lens: the three views a tradition card shows (Blueprint 01)."""

    wisdom_th: NonBlank  # the tradition and where it comes from
    safety_th: NonBlank  # safety and limits
    rights_th: NonBlank  # who may provide it, where to consult


class FamilyCard(Model):
    """Optional expandable knowledge card: separates a tradition from its evidence status."""

    tradition_th: NonBlank
    learning_point_th: NonBlank
    evidence_status: EvidenceStatus
    precautions_th: list[NonBlank] = []
    when_to_consult_th: NonBlank | None = None
    lens: FamilyLens | None = None
    source_ids: list[str] = Field(min_length=1)


class FamilyFact(Model):
    """A private-brief item one role may choose to share into the common timeline."""

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    role: FamilyRole
    text_th: NonBlank
    skills: list[FamilySkill] = []
    # Terms that must not appear in a generated reply unless this fact is allowed (AI-02 validator)
    leak_terms_th: list[NonBlank] = []


class FamilyIntent(Model):
    """One thing a learner can ask a character in a discover step (AI-01 allowlist entry)."""

    id: str = Field(pattern=r"^[A-Z_]+$")
    label_th: NonBlank
    examples_th: list[NonBlank] = Field(min_length=1)
    reveals: list[str] = []  # fact IDs of the asking role that this answer reveals
    unit_ids: list[str] = []  # knowledge units AI-02 may cite for this answer
    dimension: Dimension = "discovery"
    reply_th: NonBlank  # authored character reply: validator fallback and high-risk template
    high_risk: bool = False  # answered only from reply_th, never from generated text


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
    kind: Literal["choice", "discover"] = "choice"
    character_th: NonBlank | None = None  # discover: who the learner is questioning
    intents: list[FamilyIntent] = []
    min_reveals: int = Field(default=0, ge=0)  # discover: intents that reveal facts before continue
    abstain_th: NonBlank | None = None  # discover: when a question has no supported answer
    choices: list[FamilyChoice] = Field(min_length=1)

    @model_validator(mode="after")
    def kind_rules(self) -> "FamilyStep":
        if self.kind == "choice":
            if len(self.choices) < 2:
                raise ValueError("a choice step needs at least two choices")
            if self.intents or self.min_reveals or self.character_th:
                raise ValueError("intents belong to discover steps")
            return self
        if self.joint or self.critical:
            raise ValueError("a discover step is neither joint nor critical")
        if not self.character_th or not self.intents:
            raise ValueError("a discover step needs a character and intents")
        if [c.id for c in self.choices] != [CONTINUE]:
            raise ValueError("a discover step has exactly one choice, 'continue'")
        if len({i.id for i in self.intents}) != len(self.intents):
            raise ValueError("duplicate intent ID")
        if self.min_reveals > sum(bool(i.reveals) for i in self.intents):
            raise ValueError("min_reveals exceeds the intents that reveal facts")
        return self


class FamilySource(Model):
    id: NonBlank
    title_th: NonBlank
    url: str = Field(pattern=r"^https://")
    category: Literal["guidance", "culture", "limited_evidence"] = "guidance"
    summary_th: NonBlank


class RubricWeight(Model):
    id: Dimension
    weight: int = Field(ge=0, le=100)


class FamilyStory(Model):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    version: NonBlank
    status: Literal["Draft", "In Review", "Approved"]
    mode: Literal["coop", "solo"] = "coop"
    stage: int | None = Field(default=None, ge=1, le=4)
    objective_ids: list[str] = []
    knowledge_unit_ids: list[str] = []
    rubric: list[RubricWeight] | None = None
    boundary_th: NonBlank | None = None  # shown instead of a reply to a real-world health question
    voice_style_th: NonBlank | None = None
    title_th: NonBlank
    description_th: NonBlank
    roles: dict[FamilyRole, NonBlank]
    facts: list[FamilyFact] = []
    steps: list[FamilyStep] = Field(min_length=1)
    sources: list[FamilySource] = Field(min_length=1)

    @property
    def scored(self) -> bool:
        """2.0 stories (staged or with a discover step) report rubric dimension scores."""
        return self.stage is not None or any(s.kind == "discover" for s in self.steps)

    @property
    def weights(self) -> dict[Dimension, int]:
        return {r.id: r.weight for r in self.rubric} if self.rubric else dict(DEFAULT_RUBRIC)

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
        self._check_v2()
        return self

    def _check_v2(self) -> None:
        for ref, pattern in (
            (self.objective_ids, OBJECTIVE_ID),
            (self.knowledge_unit_ids, UNIT_ID),
        ):
            if any(not re.fullmatch(pattern, i) for i in ref):
                raise ValueError("malformed objective or knowledge unit ID")
        if self.rubric is not None:
            ids = [r.id for r in self.rubric]
            if len(set(ids)) != len(ids) or sum(r.weight for r in self.rubric) != 100:
                raise ValueError("rubric dimensions must be unique and weigh 100 in total")
        by_id = {f.id: f for f in self.facts}
        for step in self.steps:
            for intent in step.intents:
                for fact_id in intent.reveals:
                    fact = by_id.get(fact_id)
                    if fact is None or fact.role != step.role:
                        raise ValueError("an intent may reveal only a fact of the asking role")
                if not set(intent.unit_ids) <= set(self.knowledge_unit_ids):
                    raise ValueError("intent unit outside the story's knowledge_unit_ids")

    @property
    def discoverable(self) -> frozenset[str]:
        """Facts a role sees only after asking; all other facts are in its brief from the start."""
        return frozenset(f for step in self.steps for i in step.intents for f in i.reveals)
