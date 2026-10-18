"""Each cultural scenario finishes on every authored path without clinical predictions."""

from itertools import product
from pathlib import Path

import pytest

from app.content.family import load_stories
from app.engine.family import assess, choose

STORIES = [
    s
    for s in load_stories(Path(__file__).resolve().parents[5] / "content")
    if s.id.startswith("bridge-")
]


@pytest.mark.parametrize("story", STORIES, ids=lambda s: s.id)
def test_bridge_paths_have_sources_natural_replies_and_independent_safety(story):
    assert story.status == "Draft"
    assert story.mode == "solo"
    assert story.voice_style_th
    replies = [c.reply_th for step in story.steps for c in step.choices]
    assert len(replies) == len(set(replies))
    assert all(len(line) <= 300 for line in replies)
    assert all(step.source_ids for step in story.steps)
    for path in product(*(tuple(c.id for c in step.choices) for step in story.steps)):
        log = []
        for choice_id in path:
            log = choose(story, log, "mother", choice_id)
        result = assess(story, log)
        assert result == assess(story, list(path))
        assert result.safety_met == (path[-1] == story.steps[-1].choices[0].id)
