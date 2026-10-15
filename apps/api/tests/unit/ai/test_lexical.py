"""Deterministic lexical fallback for interpreter outages (FR-ACT-03, T-032)."""

from pathlib import Path

from app.ai.lexical import match_actions
from app.content.loader import load_case
from app.domain.action import Action

ACTIONS = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001").actions


def action(action_id: str) -> Action:
    return next(item for item in ACTIONS if item.id == action_id)


def test_known_keyword_fires_only_its_action() -> None:
    keyword = action("A03").keywords_th[0]

    detected = match_actions(keyword, ACTIONS)

    assert [(item.id, item.confidence, item.evidence_span) for item in detected] == [
        ("A03", 1.0, keyword)
    ]


def test_unrelated_text_does_not_fire_any_action() -> None:
    assert match_actions("unrelated", ACTIONS) == ()


def test_normalization_applies_to_both_text_and_content_keywords() -> None:
    keyword = action("A03").keywords_th[0]

    detected = match_actions(keyword[:2] + "\u200b" + keyword[2:], ACTIONS)

    assert [item.id for item in detected] == ["A03"]
    assert detected[0].evidence_span == keyword


def test_exact_example_matches_when_the_short_keyword_is_absent() -> None:
    candidate = action("C01")
    example = next(text for text in candidate.examples_th if candidate.keywords_th[0] not in text)

    assert [item.id for item in match_actions(example, ACTIONS)] == ["C01"]


def test_specific_example_suppresses_another_actions_nested_keyword() -> None:
    negative_example = next(
        text for text in action("C04").examples_th if action("C03").keywords_th[0] in text
    )

    assert [item.id for item in match_actions(negative_example, ACTIONS)] == ["C04"]


def test_only_chat_actions_are_eligible_and_multiple_matches_are_bounded() -> None:
    assert match_actions(action("B01").label_th, (action("B01"), action("D01"))) == ()
    text = " ".join(action(f"A{idx:02d}").keywords_th[0] for idx in range(1, 8))

    detected = match_actions(text, ACTIONS)

    assert [item.id for item in detected] == [f"A{idx:02d}" for idx in range(1, 6)]
