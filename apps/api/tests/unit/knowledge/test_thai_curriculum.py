"""The expanded curriculum keeps cultural explanations sourced and exercises replayable."""

from itertools import product
from pathlib import Path

import pytest

from app.ai.intent import lexical, options_for
from app.content.family import load_stories
from app.content.knowledge import load_knowledge
from app.engine.family import assess, replay, rubric_score
from tests.unit.engine.test_family_v2 import full_log

CONTENT = Path(__file__).resolve().parents[5] / "content"
KB = load_knowledge(CONTENT)
STORIES = {s.id: s for s in load_stories(CONTENT)}
NEW_STORIES = [sid for sid in STORIES if sid.startswith("thai-")]


def test_new_objectives_link_to_playable_stories_and_back():
    assert NEW_STORIES
    objectives = {o.id: o for stage in KB.paths.stages for o in stage.objectives}
    for sid in [*NEW_STORIES, "gs-b-thai-recovery"]:
        story = STORIES[sid]
        assert story.status == "Draft"
        for oid in story.objective_ids:
            assert sid in objectives[oid].story_ids
        assert all(KB.release.unit(uid) for uid in story.knowledge_unit_ids)


@pytest.mark.parametrize("sid", NEW_STORIES)
def test_every_authored_branch_finishes_with_identical_replayed_assessment(sid: str):
    story = STORIES[sid]
    scores = set()
    for path in product(*[[c.id for c in step.choices] for step in story.steps]):
        events = full_log(story, dict(enumerate(path)))
        state, again = replay(story, events), replay(story, list(events))
        assert state == again and state.choices == list(path)
        assert assess(story, state.choices, state.facts) == assess(
            story, again.choices, again.facts
        )
        rubric = rubric_score(story, state)
        assert rubric is not None and rubric == rubric_score(story, again)
        scores.add(rubric.total)
    assert len(scores) > 1


def test_new_authored_questions_map_to_their_intents_and_only_story_units():
    for sid in [*NEW_STORIES, "gs-b-thai-recovery"]:
        story = STORIES[sid]
        for step in story.steps:
            for intent in step.intents:
                assert set(intent.unit_ids) <= set(story.knowledge_unit_ids)
                assert lexical(options_for(step), intent.examples_th[0]) == intent.id
