"""Content-driven family choices replay deterministically, with an independent safety gate."""

from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.family import load_stories
from app.domain.family import FamilyStory
from app.engine.family import assess, choose, prompt, selections

ROOT = Path(__file__).resolve().parents[5]
STORY = load_stories(ROOT / "content")[0]


def test_every_authored_path_replays_and_gates_safety():
    for choices in product(*(tuple(c.id for c in s.choices) for s in STORY.steps)):
        log = []
        for step, choice_id in zip(STORY.steps, choices, strict=True):
            assert prompt(STORY, log)
            log = choose(STORY, log, step.role, choice_id)
        result = assess(STORY, log)
        assert result == assess(FamilyStory.model_validate(STORY.model_dump()), list(log))
        assert result.safety_met == all(
            not step.critical or choice.safe
            for step, choice in zip(STORY.steps, selections(STORY, log), strict=True)
        )
        assert prompt(STORY, log) == ""


def test_partial_invalid_and_out_of_turn_decisions_are_rejected():
    with pytest.raises(ValueError):
        assess(STORY, [])
    with pytest.raises(ValueError):
        choose(STORY, [], "father", STORY.steps[0].choices[0].id)
    with pytest.raises(ValueError):
        choose(STORY, [], "mother", "unknown")
    with pytest.raises(ValueError):
        selections(STORY, ["unknown"] * (len(STORY.steps) + 1))


def test_each_parent_can_respond_to_the_other_parents_actual_decision():
    shared = ["ask-rest", "share-load"]
    unshared = ["ask-rest", "wait-for-orders"]
    assert prompt(STORY, shared) != prompt(STORY, unshared)
    assert prompt(STORY, unshared) == STORY.steps[2].prompt_if["unshared-plan"]


@pytest.mark.parametrize("field", ["source_ids", "prompt_if", "id"])
def test_broken_content_references_fail_closed(field):
    raw = STORY.model_dump()
    if field == "source_ids":
        raw["steps"][0][field] = ["missing"]
    elif field == "prompt_if":
        raw["steps"][0][field] = {"future-flag": "invalid recall"}
    else:
        raw["steps"][1][field] = raw["steps"][0][field]
    with pytest.raises(ValidationError):
        FamilyStory.model_validate(raw)
