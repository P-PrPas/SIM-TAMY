"""Rubric schema (PRD 10.1-10.2). Models only: evaluating the checks is T-060."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from app.domain.action import Category
from app.domain.case import Model, Phase, VariantId


class ActionPresentAny(Model):
    type: Literal["action_present_any"]
    actions: list[str]
    phase: Phase | None = None


class ActionPresentAll(Model):
    type: Literal["action_present_all"]
    actions: list[str]


class ActionAbsent(Model):
    type: Literal["action_absent"]
    actions: list[str]
    after_event: str | None = None


class ActionBefore(Model):
    type: Literal["action_before"]
    first: str
    then: str


class DecisionEquals(Model):
    type: Literal["decision_equals"]
    option: str


class DecisionNot(Model):
    type: Literal["decision_not"]
    option: str
    when_fact_revealed: str | None = None


class WithinTurnsAfterFact(Model):
    type: Literal["within_turns_after_fact"]
    decision: str
    fact_ids: list[str]
    max_turns: int = Field(ge=1)


class CountAtLeast(Model):
    type: Literal["count_at_least"]
    category: Category
    n: int = Field(ge=1)


class NoUnsafeAction(Model):
    type: Literal["no_unsafe_action"]


class NoteSubmitted(Model):
    type: Literal["note_submitted"]
    min_chars: int | None = None


Check = Annotated[
    ActionPresentAny
    | ActionPresentAll
    | ActionAbsent
    | ActionBefore
    | DecisionEquals
    | DecisionNot
    | WithinTurnsAfterFact
    | CountAtLeast
    | NoUnsafeAction
    | NoteSubmitted,
    Field(discriminator="type"),
]


class Finding(Model):
    id: str
    template_th: str
    references: list[str] = []


class Competency(Model):
    id: str
    name_th: str
    weight: int


class RubricItem(Model):
    id: str
    competency: str
    points: int = Field(ge=0)
    critical: bool = False
    applies_to_variants: list[VariantId] | None = None  # None = all variants
    check: Check
    pass_finding: Finding
    fail_finding: Finding
    source: str | None = None


class Rubric(Model):
    rubric_version: str
    competencies: list[Competency]
    items: list[RubricItem]

    @model_validator(mode="after")
    def _weights_sum_to_100(self) -> Self:
        total = sum(c.weight for c in self.competencies)
        if total != 100:
            raise ValueError(f"competency weights must sum to 100, got {total}")
        return self


def rubric_problems(rubric: Rubric) -> list[tuple[str, str]]:
    """(path, message) for every reason this rubric must not be scored or published.

    Shared by `validate-content` and by `engine.scoring.score`, so the checks cannot be skipped
    by loading a case without validating it. The Pydantic models stay as they are; these are
    value rules, not schema shape.
    """
    problems: list[tuple[str, str]] = []
    competency_ids: set[str] = set()
    for n, c in enumerate(rubric.competencies):
        if c.weight < 0:
            problems.append(
                (f"competencies.{n}.weight", f"weight must not be negative ({c.weight})")
            )
        if c.id in competency_ids:
            problems.append((f"competencies.{n}.id", f"duplicate competency id {c.id!r}"))
        competency_ids.add(c.id)
    item_ids: set[str] = set()
    for n, item in enumerate(rubric.items):
        if item.id in item_ids:
            problems.append((f"items.{n}.id", f"duplicate item id {item.id!r}"))
        item_ids.add(item.id)
        if item.competency not in competency_ids:
            problems.append((f"items.{n}.competency", f"unknown competency {item.competency!r}"))
        if item.critical and isinstance(item.check, ActionPresentAll | CountAtLeast):
            problems.append(
                (
                    f"items.{n}.check",
                    "a critical item cannot use a partial-credit check "
                    f"({item.check.type}): the Critical Safety gate only trips on fail",
                )
            )
    return problems
