"""Case file schema (PRD 7.1). Content team writes the YAML; these models are the contract.

Frozen + extra="forbid": a typo in a YAML key is an error with a path, not silently ignored.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Phase = Literal["INTRO", "INTERVIEW", "PRESSURE", "CLOSING", "COMPLETED"]
Status = Literal["Draft", "In Review", "Approved"]
VariantId = Literal["A", "B", "C"]


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class KnownFact(Model):
    id: str
    kind: Literal["known"]
    text_th: str
    source: str | None = None


class HiddenFact(Model):
    id: str
    kind: Literal["hidden"]
    text_th: str
    unlock_on: list[str]
    keywords_th: list[str] = []
    leak_terms_th: list[NonBlank] = Field(min_length=1)
    fallback_utterances_th: list[NonBlank] = Field(min_length=1)
    risk_relevance: Literal["critical", "contextual", "none"]
    source: str | None = None
    status: Status | None = None


Fact = Annotated[KnownFact | HiddenFact, Field(discriminator="kind")]


class PatientProfile(Model):
    display_th: str
    known_facts: list[str]


class Persona(Model):
    minimization: str
    family_pressure: bool = False
    style_th: str


class PressureLine(Model):
    speaker: str
    text_th: str


class Variant(Model):
    persona: Persona
    fact_set: str
    pressure_script: list[PressureLine] = []


class DecisionOption(Model):
    id: str
    label_th: str
    maps_to_actions: list[str]


class BranchRule(Model):
    from_: Phase = Field(alias="from")
    on_action_any: list[str] | None = None
    on_decision: str | None = None
    to: Phase | None = None
    if_variant: list[VariantId] | None = None
    set_risk_state: str | None = None
    mark_unsafe: bool = False


class OutcomeScript(Model):
    timeline_th: list[str]
    disclaimer_th: str


class Reference(Model):
    id: str
    title_th: str
    locator: str


class Case(Model):
    case_id: str
    version: str
    status: Status
    title_th: str
    learning_objectives: list[str]
    patient_profile: PatientProfile
    facts: list[Fact]
    variants: dict[VariantId, Variant]
    forbidden_terms_th: list[str] = []
    decision_options: list[DecisionOption]
    branch_rules: list[BranchRule]
    critical_facts_for_replay: list[str] = []
    outcome_scripts: dict[str, OutcomeScript] = {}
    references: list[Reference] = []
