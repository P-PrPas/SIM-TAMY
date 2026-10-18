"""Three authored chapters carry earlier family decisions forward deterministically."""

from itertools import product
from pathlib import Path

from app.content.family import load_stories
from app.engine.family import assess, choose, prompt

STORY = next(
    s for s in load_stories(Path(__file__).resolve().parents[5] / "content") if s.id == "parenthood"
)


def test_three_chapters_recall_the_actual_previous_choices_and_repair():
    assert len({step.chapter_th for step in STORY.steps}) == 3
    assert prompt(STORY, ["postpone-plan", "keep-private"]) == STORY.steps[2].prompt_if["no-plan"]
    assert prompt(STORY, ["plan-together", "name-support"]) == STORY.steps[2].prompt_th
    repaired = ["postpone-plan", "keep-private", "adjust-plan", "request-relief"]
    assert prompt(STORY, repaired) == STORY.steps[4].prompt_if["plan-repaired"]
    unresolved = ["postpone-plan", "keep-private", "blame-partner", "conceal-strain"]
    assert prompt(STORY, unresolved) == STORY.steps[4].prompt_if["no-plan"]


def test_all_solo_paths_finish_for_either_parent_and_keep_safety_gate():
    for role in ("mother", "father"):
        for path in product(*(tuple(c.id for c in step.choices) for step in STORY.steps)):
            log = []
            for choice in path:
                log = choose(STORY, log, role, choice)
            result = assess(STORY, log)
            assert result == assess(STORY, list(path))
            assert result.safety_met == (path[-1] == "verify-together")
