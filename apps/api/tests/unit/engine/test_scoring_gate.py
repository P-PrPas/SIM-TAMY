"""T-061: Critical Safety gate, competency weights and renormalisation (PRD 10.3, AGENTS rule 7)."""

import random
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.content.loader import LoadedCase
from app.domain.case import VariantId
from app.domain.rubric import Rubric, rubric_problems
from app.engine.scoring import InvalidRubric
from app.engine.scoring import score as pure_score
from tests.unit.engine.play import Play

NewPlay = Callable[[VariantId], Play]


def score(events: Any, loaded: LoadedCase, variant: VariantId) -> Any:
    return pure_score(events, loaded.rubric, loaded.actions, variant)


COMPS = ["HX", "RISK", "DEC", "ESC", "COMM", "DOC"]
WEIGHTS = {"HX": 20, "RISK": 25, "DEC": 30, "ESC": 5, "COMM": 15, "DOC": 5}


def perfect_a(play: NewPlay) -> Play:
    p = play("A").turn("A01", "A02").turn("A03", "A04").turn("C01", "C02")
    return p.decide("refer").note(30).complete()


def rubric_with(dev001: LoadedCase, **changes: Any) -> LoadedCase:
    return LoadedCase(
        dev001.case, dev001.actions, dev001.rubric.model_copy(update=changes), dev001.case_hash
    )


NO_UNSAFE = {"type": "no_unsafe_action"}


def tiny(comps: dict[str, int], items: list[tuple[Any, ...]]) -> Rubric:
    """items: (id, competency, points, critical, variant it applies to[, check])."""
    finding = {"id": "F", "template_th": "t"}
    return Rubric.model_validate(
        {
            "rubric_version": "t",
            "competencies": [{"id": c, "name_th": c, "weight": w} for c, w in comps.items()],
            "items": [
                {
                    "id": i,
                    "competency": c,
                    "points": pts,
                    "critical": crit,
                    "applies_to_variants": [v],
                    "check": rest[0] if rest else NO_UNSAFE,
                    "pass_finding": finding,
                    "fail_finding": finding,
                }
                for i, c, pts, crit, v, *rest in items
            ],
        }
    )


def with_rubric(dev001: LoadedCase, rubric: Rubric) -> LoadedCase:
    return LoadedCase(dev001.case, dev001.actions, rubric, dev001.case_hash)


# ---- the gate ----


def test_scoring_perfect_path_is_full_marks_and_safe(play: NewPlay) -> None:
    p = perfect_a(play)
    s = score(p.events, p.loaded, "A")

    assert (s.total_score, s.safety_status) == (100.0, "SAFETY_MET")
    assert {c.id for c in s.competencies} == set(COMPS)
    assert sum(c.weight for c in s.competencies) == pytest.approx(100)


def test_scoring_found_but_proceeded_is_not_met_golden_t03(play: NewPlay) -> None:
    p = play("A").turn("A01", "A02").turn("A03", "A04").turn("C01", "C02")
    p.decide("proceed_service").note(30).complete()
    s = score(p.events, p.loaded, "A")

    assert s.safety_status == "SAFETY_NOT_MET"
    failed = {r.id for r in s.items if r.result == "fail"}
    assert {"R-DEC-01", "R-ESC-01"} <= failed  # the critical decision and the unsafe action
    assert (
        s.total_score > 50
    )  # the learner scored plenty elsewhere: the gate, not the total, decides


def test_scoring_pressure_fold_is_not_met_golden_t05(play: NewPlay) -> None:
    p = play("C").turn("A01", "A02").turn("A03", "A04").decide("refer").turn("C04").complete()
    s = score(p.events, p.loaded, "C")

    assert s.safety_status == "SAFETY_NOT_MET"
    assert {r.id: r.result for r in s.items}["R-COMM-03"] == "fail"


def test_scoring_pressure_hold_is_met_golden_t06(play: NewPlay) -> None:
    p = play("C").turn("A01", "A02").turn("A03", "A04").turn("C01", "C02")
    p.decide("refer").turn("C03").note(30).complete()
    s = score(p.events, p.loaded, "C")

    assert s.safety_status == "SAFETY_MET" and s.total_score > 90


def test_scoring_critical_failure_with_a_near_perfect_total_is_still_not_met(
    dev001: LoadedCase,
) -> None:
    rubric = tiny(
        {"HX": 95, "ESC": 5},
        [
            ("R1", "HX", 100, False, "A", {"type": "action_present_any", "actions": ["A01"]}),
            ("R2", "ESC", 1, True, "A"),
        ],
    )
    loaded = with_rubric(dev001, rubric)
    p = Play(loaded, "A").turn("A01").turn("A03").decide("proceed_service")  # unsafe: R2 fails

    s = score(p.events, loaded, "A")

    assert s.total_score == 95.0 and s.safety_status == "SAFETY_NOT_MET"


def test_scoring_a_non_critical_failure_never_trips_the_gate(dev001: LoadedCase) -> None:
    rubric = tiny({"HX": 100}, [("R1", "HX", 10, False, "A")])
    p = Play(with_rubric(dev001, rubric), "A").turn("A01").turn("A03").decide("proceed_service")
    s = score(p.events, with_rubric(dev001, rubric), "A")
    assert s.safety_status == "SAFETY_MET"  # no critical item exists


def test_scoring_na_critical_item_does_not_trip_the_gate(play: NewPlay) -> None:
    p = play("A").turn("A01").turn("A03").decide("proceed_service")
    results = {r.id: r for r in score(p.events, p.loaded, "A").items}
    assert results["R-COMM-03"].result == "na"  # a variant-C item, even though A folded elsewhere


# ---- weights ----


def test_scoring_competency_without_applicable_items_is_dropped_and_weights_renormalised(
    dev001: LoadedCase,
) -> None:
    rubric = tiny(
        {"HX": 20, "RISK": 25, "COMM": 55},
        [
            ("R1", "HX", 10, False, "A"),
            ("R2", "RISK", 10, False, "A"),
            ("R3", "COMM", 10, False, "C"),
        ],
    )
    loaded = with_rubric(dev001, rubric)
    p = Play(loaded, "A").turn("A01")
    s = score(p.events, loaded, "A")  # COMM only applies to variant C

    assert [c.id for c in s.competencies] == ["HX", "RISK"]
    assert [c.weight for c in s.competencies] == pytest.approx([20 * 100 / 45, 25 * 100 / 45])
    assert sum(c.weight for c in s.competencies) == pytest.approx(100)
    assert s.total_score == 100.0


def test_scoring_zero_point_competency_and_zero_weight_do_not_divide_by_zero(
    dev001: LoadedCase,
) -> None:
    zero_points = with_rubric(
        dev001,
        tiny({"HX": 50, "RISK": 50}, [("R1", "HX", 0, False, "A"), ("R2", "RISK", 10, False, "A")]),
    )
    p = Play(zero_points, "A").turn("A01")
    s = score(p.events, zero_points, "A")
    assert {c.id: c.score_pct for c in s.competencies} == {"HX": 0.0, "RISK": 100.0}

    zero_weight = tiny({"HX": 100, "RISK": 0}, [("R1", "RISK", 10, False, "A")])
    loaded = with_rubric(dev001, zero_weight)
    s2 = score(Play(loaded, "A").turn("A01").events, loaded, "A")
    assert s2.total_score == 0.0 and s2.competencies[0].weight == 0.0


@settings(max_examples=100, deadline=None)
@given(st.lists(st.sampled_from(["A", "C"]), min_size=6, max_size=6))
def test_scoring_weights_always_sum_to_100_whatever_competencies_apply(
    scopes: list[str],
) -> None:
    from app.content.loader import load_case
    from tests.unit.engine.play import DEV_001

    base = load_case(DEV_001)
    rubric = tiny(
        WEIGHTS,
        [(f"R-{c}", c, 10, False, scope) for c, scope in zip(COMPS, scopes, strict=True)],
    )
    loaded = with_rubric(base, rubric)
    s = score(Play(loaded, "A").turn("A01").events, loaded, "A")

    applicable = [c for c, scope in zip(COMPS, scopes, strict=True) if scope == "A"]
    assert [c.id for c in s.competencies] == applicable
    assert sum(c.weight for c in s.competencies) == pytest.approx(100 if applicable else 0)


# ---- determinism / shape ----


def test_scoring_is_deterministic_and_independent_of_log_order(play: NewPlay) -> None:
    p = perfect_a(play)
    first = score(p.events, p.loaded, "A").model_dump_json()
    shuffled = list(p.events)
    random.Random(7).shuffle(shuffled)

    assert {score(p.events, p.loaded, "A").model_dump_json() for _ in range(100)} == {first}
    assert score(shuffled, p.loaded, "A").model_dump_json() == first


def test_scoring_lists_every_rubric_item_in_rubric_order_and_rounds_the_total(
    play: NewPlay,
) -> None:
    p = play("A").turn("A01").turn("A03")
    s = score(p.events, p.loaded, "A")

    assert [r.id for r in s.items] == [i.id for i in p.loaded.rubric.items]
    assert s.total_score == round(s.total_score, 1)
    assert 0 <= s.total_score <= 100


def test_scoring_empty_log_does_not_crash(dev001: LoadedCase) -> None:
    s = score([], dev001, "A")
    assert s.safety_status == "SAFETY_NOT_MET"  # the critical "found the signal" item fails
    assert all(not r.evidence for r in s.items)  # nothing was logged, so there is nothing to cite


def test_scoring_partial_credit_flows_through_renormalised_weights_and_rounds_to_one_decimal(
    dev001: LoadedCase,
) -> None:
    rubric = tiny(
        {"HX": 20, "RISK": 25, "COMM": 55},
        [
            ("R1", "HX", 10, False, "A", {"type": "action_present_all", "actions": ["A01", "A02"]}),
            ("R2", "RISK", 10, False, "A", {"type": "action_present_any", "actions": ["A03"]}),
            ("R3", "COMM", 10, False, "C"),  # does not apply to variant A
        ],
    )
    loaded = with_rubric(dev001, rubric)
    s = score(Play(loaded, "A").turn("A01").turn("A03").events, loaded, "A")

    assert {c.id: c.score_pct for c in s.competencies} == {"HX": 50.0, "RISK": 100.0}
    # 50 * 20/45 + 100 * 25/45 = 77.777...
    assert s.total_score == 77.8


# ---- the rubric is checked at the scoring boundary, not only by validate-content ----


def test_scoring_negative_weights_are_refused_instead_of_scoring_above_100(
    dev001: LoadedCase,
) -> None:
    rubric = tiny(
        {"HX": 200, "RISK": -100},  # sums to 100, so the schema alone lets it through
        [
            ("R1", "HX", 10, False, "A", {"type": "action_present_any", "actions": ["A01"]}),
            ("R2", "RISK", 10, False, "A", {"type": "action_present_any", "actions": ["A03"]}),
        ],
    )
    loaded = with_rubric(dev001, rubric)
    log = Play(loaded, "A").turn("A01").events  # HX passes, RISK fails: the old code gave 200.0

    with pytest.raises(InvalidRubric, match=r"competencies\.1\.weight"):
        score(log, loaded, "A")


def test_scoring_duplicate_item_ids_are_refused(dev001: LoadedCase) -> None:
    rubric = tiny({"HX": 100}, [("R1", "HX", 10, False, "A"), ("R1", "HX", 10, True, "A")])
    loaded = with_rubric(dev001, rubric)
    with pytest.raises(InvalidRubric, match="duplicate item id 'R1'"):
        score(Play(loaded, "A").turn("A01").events, loaded, "A")


def test_scoring_critical_item_with_partial_credit_is_refused_at_runtime(
    dev001: LoadedCase,
) -> None:
    partial = {"type": "action_present_all", "actions": ["A03", "A04"]}
    rubric = tiny({"RISK": 100}, [("R1", "RISK", 10, True, "A", partial)])
    loaded = with_rubric(dev001, rubric)
    with pytest.raises(InvalidRubric, match="cannot use a partial-credit check"):
        score(Play(loaded, "A").turn("A03").events, loaded, "A")  # would have been partial/MET


def test_scoring_unknown_competency_and_duplicate_competency_are_refused(
    dev001: LoadedCase,
) -> None:
    orphan = with_rubric(dev001, tiny({"HX": 100}, [("R1", "RISK", 10, False, "A")]))
    with pytest.raises(InvalidRubric, match="unknown competency 'RISK'"):
        score([], orphan, "A")

    dup = dev001.rubric.model_copy(
        update={"competencies": (*dev001.rubric.competencies[:1], dev001.rubric.competencies[0])}
    )
    with pytest.raises(InvalidRubric, match="duplicate competency id"):
        score([], with_rubric(dev001, dup), "A")


def test_scoring_dev001_rubric_has_no_problems_and_zero_weights_are_allowed(
    dev001: LoadedCase,
) -> None:
    assert rubric_problems(dev001.rubric) == []
    zero = tiny({"HX": 100, "RISK": 0}, [("R1", "RISK", 10, False, "A")])
    assert rubric_problems(zero) == []  # zero weight is legitimate (see the earlier test)


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.sampled_from(["A", "C"]), min_size=6, max_size=6),
    st.lists(st.integers(0, 100), min_size=6, max_size=6),
    st.lists(st.booleans(), min_size=6, max_size=6),
)
def test_scoring_total_stays_within_0_and_100_for_any_valid_rubric(
    scopes: list[str], raw_weights: list[int], passes: list[bool]
) -> None:
    from app.content.loader import load_case
    from tests.unit.engine.play import DEV_001

    total = sum(raw_weights)
    weights = dict(zip(COMPS, raw_weights, strict=True))
    if total == 0:
        weights["HX"] = 100
    else:  # scale to sum 100 (non-negative integers, remainder on the first competency)
        weights = {c: w * 100 // total for c, w in weights.items()}
        weights["HX"] += 100 - sum(weights.values())
    items = [
        (
            f"R-{c}",
            c,
            10,
            False,
            scope,
            {"type": "action_present_any", "actions": ["A01"] if ok else ["A07"]},
        )
        for c, scope, ok in zip(COMPS, scopes, passes, strict=True)
    ]
    loaded = with_rubric(load_case(DEV_001), tiny(weights, items))
    s = score(Play(loaded, "A").turn("A01").events, loaded, "A")

    assert 0.0 <= s.total_score <= 100.0
