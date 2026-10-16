"""Instructor overrides (FR-INS-04, T-058). PURE: an override never edits the engine's result.

`apply_overrides` returns a second `Scoring` (the report's `effective` block) computed with the same
`aggregate` as the original, so the arithmetic is not duplicated. Critical items cannot be
overridden (docs/API_DESIGN.md section 14, Q1): the Critical Safety gate stays the engine's.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.rubric import Rubric
from app.domain.scoring import ItemResult, Scoring
from app.engine.scoring import aggregate

OverrideResult = Literal["pass", "fail", "partial"]


class OverrideRefused(ValueError):
    """The override cannot be applied to this item (unknown, not applicable, critical, bad score)"""


@dataclass(frozen=True)
class ItemOverride:
    rubric_item_id: str
    result: OverrideResult
    earned: float | None = None  # only for `partial`


def _earned(item: ItemResult, o: ItemOverride) -> float:
    if o.result == "pass":
        return float(item.points)
    if o.result == "fail":
        return 0.0
    if o.earned is None or not 0 < o.earned < item.points:
        raise OverrideRefused(f"a partial result needs 0 < earned < {item.points}")
    return o.earned


def _overridden(item: ItemResult | None, o: ItemOverride) -> ItemResult:
    if item is None:
        raise OverrideRefused("no such rubric item")
    if item.result == "na":
        raise OverrideRefused("the item does not apply to this variant")
    if item.critical:
        raise OverrideRefused("critical items cannot be overridden")
    return item.model_copy(update={"result": o.result, "earned": _earned(item, o)})


def check_override(scoring: Scoring, o: ItemOverride) -> ItemResult:
    """The engine's original result for the item, or why it cannot be overridden."""
    item = next((i for i in scoring.items if i.id == o.rubric_item_id), None)
    _overridden(item, o)  # raises when it cannot be applied
    if item is None:  # unreachable: _overridden refuses a missing item
        raise OverrideRefused("no such rubric item")
    return item


def apply_overrides(scoring: Scoring, rubric: Rubric, overrides: Sequence[ItemOverride]) -> Scoring:
    """`scoring` with the overrides applied, oldest first, so the latest one per item wins."""
    items = {i.id: i for i in scoring.items}
    for o in overrides:
        items[o.rubric_item_id] = _overridden(items.get(o.rubric_item_id), o)
    return aggregate(tuple(items.values()), rubric)
