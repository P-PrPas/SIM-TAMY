"""Pixel stage choice cards: display-only `short_th` and `icon` (contracts section 3, LP-01)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.v1.family_schemas import FamilyOption
from app.content.family import load_stories
from app.domain.family import SHORT_MAX, FamilyChoice

STORY = {s.id: s for s in load_stories(Path(__file__).resolve().parents[5] / "content")}[
    "thai-elements-family"
]
BASE = {"id": "x", "text_th": "ข้อความเต็ม", "reply_th": "ตอบ", "feedback_th": "ผล"}


def test_authored_cards_carry_short_label_and_icon() -> None:
    choices = [c for step in STORY.steps for c in step.choices]
    assert choices
    for choice in choices:
        assert choice.short_th and choice.icon
        assert len(choice.short_th) <= SHORT_MAX


def test_short_label_is_optional() -> None:
    choice = FamilyChoice.model_validate(BASE)
    assert choice.short_th is None and choice.icon is None


@pytest.mark.parametrize("short", ["", "   ", "ก" * (SHORT_MAX + 1)])
def test_short_label_rejects_empty_or_overlong(short: str) -> None:
    with pytest.raises(ValidationError):
        FamilyChoice.model_validate({**BASE, "short_th": short})


def test_unknown_icon_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FamilyChoice.model_validate({**BASE, "icon": "skull"})


def test_play_time_option_exposes_display_fields_only() -> None:
    assert set(FamilyOption.model_fields) == {"id", "text_th", "short_th", "icon"}
