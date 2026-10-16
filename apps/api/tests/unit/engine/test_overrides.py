"""T-058: an override is a second scoring by the same arithmetic; the original is untouched."""

import pytest

from app.content.loader import LoadedCase
from app.domain.scoring import Scoring
from app.engine.overrides import ItemOverride, OverrideRefused, apply_overrides, check_override
from app.engine.scoring import aggregate, score
from tests.unit.engine.play import Play


def finished(dev001: LoadedCase) -> tuple[Play, Scoring]:
    p = Play(dev001, "A").turn("A01", "A02").turn("A03", "A04").decide("refer").complete()
    return p, score(p.events, dev001.rubric, dev001.actions, "A")


def test_no_overrides_is_the_original_and_aggregate_is_the_engine_arithmetic(
    dev001: LoadedCase,
) -> None:
    _, original = finished(dev001)

    assert apply_overrides(original, dev001.rubric, []) == original
    assert aggregate(original.items, dev001.rubric) == original


def test_an_override_changes_the_effective_score_only(dev001: LoadedCase) -> None:
    _, original = finished(dev001)
    before = original.model_copy()
    item = next(i for i in original.items if i.result == "fail" and not i.critical)

    effective = apply_overrides(
        original,
        dev001.rubric,
        [ItemOverride(item.id, "pass")],
    )

    assert effective.total_score > original.total_score
    assert original == before  # the engine's result was not touched
    assert effective.safety_status == original.safety_status
    changed = next(i for i in effective.items if i.id == item.id)
    assert (changed.result, changed.earned) == ("pass", float(item.points))


def test_the_latest_override_of_an_item_wins_and_a_partial_scores_its_earned(
    dev001: LoadedCase,
) -> None:
    _, original = finished(dev001)
    item = next(i for i in original.items if i.result == "fail" and not i.critical)

    pass_then_fail = apply_overrides(
        original,
        dev001.rubric,
        [ItemOverride(item.id, "pass"), ItemOverride(item.id, "fail")],
    )
    partial = apply_overrides(
        original,
        dev001.rubric,
        [ItemOverride(item.id, "partial", item.points / 2)],
    )

    assert pass_then_fail == original
    mid = next(i for i in partial.items if i.id == item.id)
    assert (mid.result, mid.earned) == ("partial", item.points / 2)
    assert original.total_score < partial.total_score


@pytest.mark.parametrize(
    ("override", "why"),
    [
        (ItemOverride("R-RISK-01", "pass"), "critical"),  # Critical Safety stays the engine's
        (ItemOverride("NOPE", "pass"), "no such"),
        (ItemOverride("R-HX-01", "partial"), "partial"),
        (ItemOverride("R-HX-01", "partial", 0.0), "partial"),
        (ItemOverride("R-HX-01", "partial", 10.0), "partial"),  # full marks is a pass
        (ItemOverride("R-COMM-02", "pass"), "does not apply"),  # Variant C only
    ],
)
def test_what_cannot_be_overridden(dev001: LoadedCase, override: ItemOverride, why: str) -> None:
    _, original = finished(dev001)

    with pytest.raises(OverrideRefused, match=why):
        check_override(original, override)
