"""Replayable, deterministic formative feedback. Never predicts family health."""

from typing import NamedTuple

from app.domain.family import FamilyChoice, FamilyRole, FamilySkill, FamilyStory


class Assessment(NamedTuple):
    safety_met: bool
    competencies: dict[FamilySkill, tuple[int, int]]


def assess(story: FamilyStory, choices: list[str]) -> Assessment:
    chosen = selections(story, choices)
    if len(chosen) != len(story.steps):
        raise ValueError("report is available only after completion")
    skills: tuple[FamilySkill, ...] = ("communication", "responsibility", "safety", "support")
    return Assessment(
        safety_met=not any(
            step.critical and not choice.safe
            for step, choice in zip(story.steps, chosen, strict=True)
        ),
        competencies={
            skill: (
                sum(skill in choice.skills for choice in chosen),
                sum(any(skill in c.skills for c in step.choices) for step in story.steps),
            )
            for skill in skills
        },
    )


def selections(story: FamilyStory, choices: list[str]) -> list[FamilyChoice]:
    if len(choices) > len(story.steps):
        raise ValueError("too many decisions")
    result = []
    for step, choice_id in zip(story.steps, choices, strict=False):
        choice = next((choice for choice in step.choices if choice.id == choice_id), None)
        if choice is None:
            raise ValueError("unknown decision")
        result.append(choice)
    return result


def choose(story: FamilyStory, choices: list[str], role: FamilyRole, choice_id: str) -> list[str]:
    if len(choices) >= len(story.steps) or story.steps[len(choices)].role != role:
        raise ValueError("not this role's turn")
    updated = [*choices, choice_id]
    selections(story, updated)
    return updated


def prompt(story: FamilyStory, choices: list[str]) -> str:
    chosen = selections(story, choices)
    if len(chosen) == len(story.steps):
        return ""
    flags = {flag for choice in chosen for flag in choice.flags}
    step = story.steps[len(chosen)]
    return next((line for flag, line in step.prompt_if.items() if flag in flags), step.prompt_th)
