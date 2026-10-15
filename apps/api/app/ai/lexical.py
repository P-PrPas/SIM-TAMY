"""Conservative, deterministic Action matching from content-authored phrases (FR-ACT-03)."""

from collections.abc import Sequence
from typing import NamedTuple

from app.ai.interpreter import MAX_ACTIONS, OFFERED_CATEGORIES, DetectedAction
from app.ai.thai import normalize_th
from app.domain.action import Action


class _Match(NamedTuple):
    action_id: str
    start: int
    end: int
    is_example: bool

    @property
    def length(self) -> int:
        return self.end - self.start


def _hits(text: str, action_id: str, phrase: str, *, is_example: bool) -> list[_Match]:
    needle = normalize_th(phrase)
    if not needle:
        return []
    found: list[_Match] = []
    start = text.find(needle)
    while start != -1:
        found.append(_Match(action_id, start, start + len(needle), is_example))
        start = text.find(needle, start + 1)
    return found


def _overlaps(left: _Match, right: _Match) -> bool:
    return left.start < right.end and right.start < left.end


def match_actions(text: str, actions: Sequence[Action]) -> tuple[DetectedAction, ...]:
    """Match literal content phrases, dropping cross-action overlaps unless one is more specific.

    Ambiguous equal-length phrases do not fire either action. Full examples can suppress a
    shorter keyword of a different action, including a conflicting phrase in that example.
    """
    normalized = normalize_th(text)
    matches = [
        hit
        for action in actions
        if action.category in OFFERED_CATEGORIES
        for phrase, is_example in (
            *((example, True) for example in action.examples_th),
            *((keyword, False) for keyword in action.keywords_th),
        )
        for hit in _hits(normalized, action.id, phrase, is_example=is_example)
    ]
    unambiguous = [
        match
        for match in matches
        if not any(
            other.action_id != match.action_id
            and _overlaps(match, other)
            and other.length >= match.length
            for other in matches
        )
    ]
    best = {
        action.id: max(
            (match for match in unambiguous if match.action_id == action.id),
            key=lambda match: (match.length, match.is_example, -match.start),
            default=None,
        )
        for action in actions
        if action.category in OFFERED_CATEGORIES
    }
    return tuple(
        DetectedAction(
            id=action.id,
            confidence=1.0,
            evidence_span=normalized[match.start : match.end],
        )
        for action in actions
        if (match := best.get(action.id)) is not None
    )[:MAX_ACTIONS]
