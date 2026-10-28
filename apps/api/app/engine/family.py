"""Replayable, deterministic formative feedback. Never predicts family health."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import NamedTuple

from app.domain.family import (
    CONTINUE,
    Dimension,
    FamilyChoice,
    FamilyRole,
    FamilySkill,
    FamilyStep,
    FamilyStory,
)


class Assessment(NamedTuple):
    safety_met: bool
    competencies: dict[FamilySkill, tuple[int, int]]


def assess(story: FamilyStory, choices: list[str], shared: Iterable[str] = ()) -> Assessment:
    chosen = selections(story, choices)
    if len(chosen) != len(story.steps):
        raise ValueError("report is available only after completion")
    skills: tuple[FamilySkill, ...] = ("communication", "responsibility", "safety", "support")
    facts = [fact for fact in story.facts if fact.id in set(shared)]
    if story.facts or any(step.joint for step in story.steps):
        skills = (*skills, "shared_decision")
    return Assessment(
        safety_met=not any(
            step.critical and not choice.safe
            for step, choice in zip(story.steps, chosen, strict=True)
        ),
        competencies={
            skill: (
                sum(skill in choice.skills for choice in chosen)
                + sum(skill in fact.skills for fact in facts),
                sum(any(skill in c.skills for c in step.choices) for step in story.steps)
                + sum(skill in fact.skills for fact in story.facts),
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
    if len(choices) >= len(story.steps) or (
        story.mode == "coop" and story.steps[len(choices)].role != role
    ):
        raise ValueError("not this role's turn")
    if choice_id == CONTINUE and story.steps[len(choices)].kind != "discover":
        raise ValueError("unknown decision")
    updated = [*choices, choice_id]
    selections(story, updated)
    return updated


def prompt(story: FamilyStory, choices: list[str], facts: Iterable[str] = ()) -> str:
    """Prompt for the step after `choices`; `facts` are fact IDs shared when it began."""
    chosen = selections(story, choices)
    if len(chosen) == len(story.steps):
        return ""
    flags = {flag for choice in chosen for flag in choice.flags}
    flags.update(f"fact:{fact}" for fact in facts)
    step = story.steps[len(chosen)]
    return next((line for flag, line in step.prompt_if.items() if flag in flags), step.prompt_th)


def revealing(step: "FamilyStep", asked: Iterable[str]) -> int:
    """Distinct asked intents that reveal facts: the count a discover step's min_reveals needs."""
    return sum(1 for i in step.intents if i.reveals and i.id in set(asked))


class FamilyEventRecord(NamedTuple):
    """The replay-relevant part of a stored event: decision, joint vote, fact share or ask."""

    kind: str
    role: FamilyRole
    choice_id: str
    reply_th: str | None = None


@dataclass
class Progress:
    choices: list[str] = field(default_factory=list)
    replies: list[str | None] = field(default_factory=list)
    step_facts: list[frozenset[str]] = field(default_factory=list)  # shared when step i locked
    shared: list[tuple[FamilyRole, str]] = field(default_factory=list)
    votes: dict[str, str] = field(default_factory=dict)  # open round, role -> choice
    split: dict[str, str] | None = None  # last round that disagreed
    events: int = 0
    asks: list[tuple[int, str, str | None]] = field(default_factory=list)  # step, intent, reply
    revealed: set[str] = field(default_factory=set)  # discoverable facts unlocked by asking
    locked_at: list[int] = field(default_factory=list)  # 1-based event idx that locked each step

    @property
    def version(self) -> int:
        """Optimistic-lock version: a lone pending vote does not invalidate the partner's view."""
        return self.events - (1 if len(self.votes) == 1 else 0)

    @property
    def facts(self) -> frozenset[str]:
        return frozenset(fact for _, fact in self.shared)

    def asked(self, step_index: int) -> list[str]:
        """Intent IDs asked in a step, in order, repeats kept (they are logged, not re-revealed)."""
        return [intent for i, intent, _ in self.asks if i == step_index]

    def reply_for(self, step_index: int, intent_id: str) -> str | None:
        return next((r for i, n, r in self.asks if (i, n) == (step_index, intent_id)), None)


def replay(story: FamilyStory, events: Iterable[FamilyEventRecord]) -> Progress:
    """Rebuild room state purely from the append-only events (deterministic, no clock)."""
    done = Progress()
    for event in events:
        done.events += 1
        if event.kind == "share":
            fact = next((f for f in story.facts if f.id == event.choice_id), None)
            if fact is None or fact.role != event.role:
                raise ValueError("unknown or foreign fact")
            if fact.id in story.discoverable and fact.id not in done.revealed:
                raise ValueError("fact is not revealed yet")
            if event.choice_id not in done.facts:
                done.shared.append((event.role, event.choice_id))
            continue
        index = len(done.choices)
        if index >= len(story.steps):
            raise ValueError("too many decisions")
        step = story.steps[index]
        if event.kind == "ask":
            intent = next((i for i in step.intents if i.id == event.choice_id), None)
            if intent is None or (story.mode == "coop" and step.role != event.role):
                raise ValueError("unknown intent or not this role's turn")
            done.asks.append((index, intent.id, event.reply_th))
            done.revealed.update(intent.reveals)
            continue
        if not any(c.id == event.choice_id for c in step.choices):
            raise ValueError("unknown decision")
        if event.kind == "decision":
            if step.joint or (story.mode == "coop" and step.role != event.role):
                raise ValueError("not this role's turn")
            if step.kind == "discover" and revealing(step, done.asked(index)) < step.min_reveals:
                raise ValueError("not enough answers yet")
            done.choices.append(event.choice_id)
            done.replies.append(event.reply_th)
            done.step_facts.append(done.facts)
            done.locked_at.append(done.events)
        elif event.kind == "vote":
            if not step.joint or event.role in done.votes:
                raise ValueError("not a joint step or already voted")
            done.votes[event.role] = event.choice_id
            if len(done.votes) == 2:
                if len(set(done.votes.values())) == 1:
                    done.choices.append(event.choice_id)
                    done.replies.append(None)
                    done.step_facts.append(done.facts)
                    done.locked_at.append(done.events)
                    done.split = None
                else:
                    done.split = dict(done.votes)
                done.votes = {}
        else:
            raise ValueError("unknown event kind")
    return done


class DimensionScore(NamedTuple):
    id: Dimension
    weight: int
    earned: int
    possible: int
    score: int  # 0-100


class RubricScore(NamedTuple):
    total: int  # 0-100, weighted over the dimensions that had opportunities
    dimensions: tuple[DimensionScore, ...]


def rubric_score(story: FamilyStory, state: Progress) -> RubricScore | None:
    """Weighted dimension scores from the replayed state alone. Not a pass mark and never mixed
    with the Critical Safety gate (`assess().safety_met`), which stays a separate result."""
    if not story.scored:
        return None
    earned: dict[Dimension, int] = {}
    possible: dict[Dimension, int] = {}

    def opportunity(dimension: Dimension, got: bool) -> None:
        possible[dimension] = possible.get(dimension, 0) + 1
        earned[dimension] = earned.get(dimension, 0) + int(got)

    chosen = selections(story, state.choices)
    for index, step in enumerate(story.steps):
        asked = set(state.asked(index))
        for intent in step.intents:
            opportunity(intent.dimension, intent.id in asked)
        if step.kind == "choice":
            picked = chosen[index].dimension if index < len(chosen) else None
            for dimension in dict.fromkeys(c.dimension for c in step.choices if c.dimension):
                opportunity(dimension, picked == dimension)
    for fact_id in sorted(story.discoverable):
        opportunity("communication", fact_id in state.facts)
    weights = story.weights
    scored = [d for d in weights if possible.get(d)]
    parts = tuple(
        DimensionScore(
            d,
            weights[d],
            earned.get(d, 0),
            possible[d],
            round(100 * earned.get(d, 0) / possible[d]),
        )
        for d in scored
    )
    weight = sum(p.weight for p in parts)
    mass = sum(p.weight * p.earned / p.possible for p in parts)
    return RubricScore(round(100 * mass / weight) if weight else 0, parts)
