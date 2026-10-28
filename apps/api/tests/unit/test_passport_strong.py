"""`strong` on a passport attempt is a display flag derived from the chosen options only."""

from pathlib import Path

import pytest

from app.content.family import load_stories
from app.domain.family import FamilyStory
from app.services.institution import _strong

CONTENT = Path(__file__).resolve().parents[4] / "content"
SAFE = ["ask-rest", "share-load", "trusted-backup", "contact-professional"]


def _story(story_id: str) -> FamilyStory:
    return next(s for s in load_stories(CONTENT) if s.id == story_id)


def test_strong_needs_a_skill_on_every_chosen_decision() -> None:
    story = _story("first-night")
    assert _strong(story, SAFE) is True
    assert _strong(story, [*SAFE[:2], "push-through", SAFE[3]]) is False
    assert _strong(story, [*SAFE[:3], "dismiss-concern"]) is False


def test_discover_steps_only_continue_so_they_do_not_count_as_decisions() -> None:
    story = _story("thai-elements-family")
    assert story.steps[0].kind == "discover"
    assert _strong(story, ["continue", "compare-sources", "plan-together"]) is True
    assert _strong(story, ["continue", "compare-sources", "keep-a-menu-list"]) is False


def test_an_unknown_choice_is_an_error_not_strong() -> None:
    with pytest.raises(ValueError):
        _strong(_story("first-night"), ["nope"])
