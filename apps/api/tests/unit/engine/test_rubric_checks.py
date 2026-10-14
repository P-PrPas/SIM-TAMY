"""T-060: one test group per check type (PRD 10.2), plus evidence/determinism properties."""

import random
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.content.loader import LoadedCase, load_case
from app.domain.case import VariantId
from app.domain.events import LoggedEvent
from app.domain.rubric import RubricItem
from app.domain.scoring import ItemResult
from app.engine.scoring import MalformedEvent, View, evaluate_item
from tests.unit.engine.play import Play

NewPlay = Callable[[VariantId], Play]


def item(check: dict[str, Any], variants: list[str] | None = None, points: int = 10) -> RubricItem:
    finding = {"id": "F", "template_th": "t"}
    return RubricItem.model_validate(
        {
            "id": "R-T",
            "competency": "HX",
            "points": points,
            "critical": True,
            "applies_to_variants": variants,
            "check": check,
            "pass_finding": finding,
            "fail_finding": finding,
        }
    )


def run(p: Play, check: dict[str, Any], **kw: Any) -> ItemResult:
    return evaluate_item(item(check, **kw), View.build(p.events, p.loaded.actions), p.variant)


def types(r: ItemResult) -> list[str]:
    return [e.type for e in r.evidence]


# ---- action_present_any ----


def test_rubric_present_any_pass_and_fail(play: NewPlay) -> None:
    p = play("A").turn("A01").turn("A04")
    ok = run(p, {"type": "action_present_any", "actions": ["A03", "A04"]})
    assert ok.result == "pass" and ok.earned == 10 and types(ok) == ["ACTIONS_DETECTED"]
    assert ok.evidence[0].turn_idx == 2

    no = run(p, {"type": "action_present_any", "actions": ["A03"]})
    assert no.result == "fail" and no.earned == 0
    assert no.evidence[0].event_id == p.events[-1].id  # end of observation


def test_rubric_present_any_phase_filter(play: NewPlay) -> None:
    p = play("C").turn("A03").decide("refer").turn("C03")
    assert p.state.phase == "CLOSING"
    in_pressure = {"type": "action_present_any", "actions": ["C03"], "phase": "PRESSURE"}
    assert run(p, in_pressure).result == "pass"

    early = play("C").turn("C03")  # same action, asked during the interview
    assert run(early, in_pressure).result == "fail"
    first_turn = {"type": "action_present_any", "actions": ["A01"], "phase": "INTRO"}
    assert run(play("A").turn("A01"), first_turn).result == "pass"  # INTRO counts as INTERVIEW


# ---- action_present_all ----


def test_rubric_present_all_partial_credit(play: NewPlay) -> None:
    check = {"type": "action_present_all", "actions": ["A03", "A04"]}
    assert run(play("A").turn("A03", "A04"), check).result == "pass"

    half = run(play("A").turn("A03"), check)
    assert (half.result, half.earned) == ("partial", 5.0) and len(half.evidence) == 1

    none = run(play("A").turn("A01"), check)
    assert none.result == "fail" and none.earned == 0 and none.evidence


# ---- action_absent ----


def test_rubric_absent(play: NewPlay) -> None:
    check = {"type": "action_absent", "actions": ["C04"]}
    assert run(play("C").turn("A03"), check).result == "pass"
    bad = run(play("C").turn("C04"), check)
    assert bad.result == "fail" and types(bad) == ["ACTIONS_DETECTED"]


def test_rubric_absent_after_event(play: NewPlay) -> None:
    check = {"type": "action_absent", "actions": ["A05"], "after_event": "DECISION_COMMITTED"}
    before = play("A").turn("A03", "A05").decide("refer")
    assert run(before, check).result == "pass"  # asked, but before the decision
    after = play("A").turn("A03").decide("refer").turn("A05")
    assert run(after, check).result == "fail"
    never = play("A").turn("A05")
    assert run(never, check).result == "pass"  # the event never happened


# ---- action_before ----


def test_rubric_before(play: NewPlay) -> None:
    check = {"type": "action_before", "first": "A02", "then": "A03"}
    ordered = run(play("A").turn("A02").turn("A03"), check)
    assert ordered.result == "pass" and len(ordered.evidence) == 2
    assert run(play("A").turn("A03").turn("A02"), check).result == "fail"
    assert run(play("A").turn("A02", "A03"), check).result == "fail"  # same turn is not "before"
    assert run(play("A").turn("A02"), check).result == "fail"  # `then` never asked
    assert run(play("A").turn("A03"), check).result == "fail"  # `first` never asked


# ---- decision_equals / decision_not ----


def test_rubric_decision_equals(play: NewPlay) -> None:
    check = {"type": "decision_equals", "option": "refer"}
    ok = run(play("A").turn("A03").decide("refer"), check)
    assert ok.result == "pass" and types(ok) == ["DECISION_COMMITTED"]
    wrong = run(play("A").turn("A03").decide("proceed_service"), check)
    assert wrong.result == "fail" and types(wrong) == ["DECISION_COMMITTED"]
    nothing = run(play("A").turn("A03"), check)
    assert nothing.result == "fail" and nothing.evidence


def test_rubric_decision_not(play: NewPlay) -> None:
    plain = {"type": "decision_not", "option": "proceed_service"}
    assert run(play("A").turn("A03").decide("refer"), plain).result == "pass"
    assert run(play("A").turn("A03").decide("proceed_service"), plain).result == "fail"
    assert run(play("A").turn("A03"), plain).result == "pass"  # no decision, nothing committed

    cond = {**plain, "when_fact_revealed": "H1"}
    revealed = run(play("A").turn("A03").decide("proceed_service"), cond)
    assert revealed.result == "fail" and types(revealed) == ["FACT_REVEALED", "DECISION_COMMITTED"]
    not_yet = run(play("A").turn("A01").decide("proceed_service"), cond)
    assert not_yet.result == "pass"  # chose it, but the fact was never revealed


# ---- within_turns_after_fact ----


def _timing(max_turns: int = 3) -> dict[str, Any]:
    return {
        "type": "within_turns_after_fact",
        "decision": "refer",
        "fact_ids": ["H1", "H2"],
        "max_turns": max_turns,
    }


def test_rubric_within_turns(play: NewPlay) -> None:
    fast = play("A").turn("A03").turn("A04").decide("refer")
    ok = run(fast, _timing())
    assert ok.result == "pass" and types(ok) == [
        "FACT_REVEALED",
        "FACT_REVEALED",
        "DECISION_COMMITTED",
    ]

    slow = (
        play("A")
        .turn("A03")
        .turn("A04")
        .turn("A01")
        .turn("A02")
        .turn("A05")
        .turn("A06")
        .decide("refer")
    )
    assert run(slow, _timing(3)).result == "fail"  # 4 turns after the last reveal
    assert run(slow, _timing(4)).result == "pass"  # the bound is inclusive


def test_rubric_within_turns_missing_pieces_fail(play: NewPlay) -> None:
    only_one_fact = play("A").turn("A03").decide("refer")
    assert run(only_one_fact, _timing()).result == "fail"
    wrong_option = play("A").turn("A03").turn("A04").decide("proceed_service")
    assert run(wrong_option, _timing()).result == "fail"
    no_decision = play("A").turn("A03").turn("A04")
    out = run(no_decision, _timing())
    assert out.result == "fail" and out.evidence


# ---- count_at_least ----


def test_rubric_count_at_least(play: NewPlay) -> None:
    check = {"type": "count_at_least", "category": "COM", "n": 2}
    assert run(play("A").turn("C01").turn("C02"), check).result == "pass"
    one = run(play("A").turn("C01").turn("C01"), check)  # repeating does not count twice
    assert (one.result, one.earned) == ("partial", 5.0)
    zero = run(play("A").turn("A01"), check)
    assert zero.result == "fail" and zero.evidence
    more = run(play("A").turn("C01", "C02", "C03"), {**check, "n": 5})
    assert more.result == "partial" and more.earned == pytest.approx(6.0)


# ---- no_unsafe_action ----


def test_rubric_no_unsafe_action(play: NewPlay) -> None:
    check = {"type": "no_unsafe_action"}
    safe = run(play("A").turn("A03").decide("refer"), check)
    assert safe.result == "pass" and safe.evidence
    unsafe = run(play("A").turn("A03").decide("proceed_service"), check)
    assert unsafe.result == "fail" and types(unsafe) == ["UNSAFE_ACTION"]


# ---- note_submitted ----


def test_rubric_note_submitted(play: NewPlay) -> None:
    check = {"type": "note_submitted", "min_chars": 20}
    assert run(play("A").turn("A03").note(30), check).result == "pass"
    short = run(play("A").turn("A03").note(5), check)
    assert short.result == "fail" and types(short) == ["NOTE_SUBMITTED"]
    none = run(play("A").turn("A03"), check)
    assert none.result == "fail" and none.evidence
    assert run(play("A").note(1), {"type": "note_submitted"}).result == "pass"  # default min 1


# ---- actions linked to the Decision Panel option count like any other action ----


def test_rubric_decision_option_actions_are_evaluated(play: NewPlay) -> None:
    p = play("A").turn("A01").turn("A03").decide("refer").complete()
    assert {"B01", "B02"} <= set(p.state.fired_action_ids)  # the engine fired them

    both = run(p, {"type": "action_present_all", "actions": ["B01", "B02"]})
    assert both.result == "pass" and types(both) == ["DECISION_COMMITTED"]
    assert run(p, {"type": "action_present_any", "actions": ["B02"]}).result == "pass"
    assert run(p, {"type": "count_at_least", "category": "DEC", "n": 2}).result == "pass"
    assert run(p, {"type": "action_absent", "actions": ["B03"]}).result == "pass"
    assert run(p, {"type": "action_absent", "actions": ["B01"]}).result == "fail"
    # recorded in the phase the decision was taken in, before the phase moved on
    in_interview = {"type": "action_present_any", "actions": ["B01"], "phase": "INTERVIEW"}
    assert run(p, in_interview).result == "pass"


def test_rubric_action_before_a_decision_action_in_the_same_turn(play: NewPlay) -> None:
    p = play("A").turn("A03").decide("refer")  # A03 and B01 share turn 1, in different events
    assert run(p, {"type": "action_before", "first": "A03", "then": "B01"}).result == "pass"
    assert run(p, {"type": "action_before", "first": "B01", "then": "A03"}).result == "fail"


def test_rubric_proceed_option_action_is_seen_too(play: NewPlay) -> None:
    p = play("A").turn("A03").decide("proceed_service")
    assert run(p, {"type": "action_present_any", "actions": ["B03"]}).result == "pass"


# ---- within_turns_after_fact: reveals after the decision never count ----


def test_rubric_within_turns_rejects_a_fact_revealed_after_the_decision(play: NewPlay) -> None:
    late = play("A").turn("A03").decide("refer").turn("A04")  # H2 appears after the decision
    out = run(late, _timing())
    assert out.result == "fail"
    assert types(out) == ["FACT_REVEALED", "DECISION_COMMITTED", "FACT_REVEALED"]  # event order


def _log(*rows: tuple[int, str, int, dict[str, Any]]) -> list[LoggedEvent]:
    return [LoggedEvent(id=i, type=t, turn_idx=n, payload=pl) for i, t, n, pl in rows]  # type: ignore[arg-type]


def test_rubric_within_turns_hand_made_orderings(dev001: LoadedCase) -> None:
    item_ = item(_timing())
    decide = (5, "DECISION_COMMITTED", 2, {"option_id": "refer", "actions": []})

    def result(*rows: tuple[int, str, int, dict[str, Any]]) -> str:
        view = View.build(_log(*rows), dev001.actions)
        return evaluate_item(item_, view, "A").result

    h1 = (1, "FACT_REVEALED", 1, {"id": "H1"})
    h2_before = (4, "FACT_REVEALED", 2, {"id": "H2"})
    assert result(h1, h2_before, decide) == "pass"  # both before, gap 0
    h2_after_same_turn = (6, "FACT_REVEALED", 2, {"id": "H2"})  # same turn index, later event
    assert result(h1, decide, h2_after_same_turn) == "fail"
    h2_future_turn = (4, "FACT_REVEALED", 3, {"id": "H2"})  # inconsistent log: negative gap
    assert result(h1, h2_future_turn, decide) == "fail"


def test_rubric_within_turns_duplicate_fact_ids_do_not_double_count(dev001: LoadedCase) -> None:
    dup = item({**_timing(), "fact_ids": ["H1", "H1", "H2"]})
    h1 = (1, "FACT_REVEALED", 1, {"id": "H1"})
    decide = (5, "DECISION_COMMITTED", 2, {"option_id": "refer", "actions": []})
    only_h1 = View.build(_log(h1, decide), dev001.actions)
    assert evaluate_item(dup, only_h1, "A").result == "fail"  # H2 never revealed
    both = View.build(_log(h1, (4, "FACT_REVEALED", 2, {"id": "H2"}), decide), dev001.actions)
    assert evaluate_item(dup, both, "A").result == "pass"


# ---- malformed events are rejected loudly, never mis-scored ----


@pytest.mark.parametrize(
    "bad",
    [
        (1, "DECISION_COMMITTED", 1, {}),
        (1, "DECISION_COMMITTED", 1, {"option_id": "refer", "actions": None}),
        (1, "DECISION_COMMITTED", 1, {"option_id": "refer", "actions": "B01"}),
        (1, "DECISION_COMMITTED", 1, {"option_id": "refer", "actions": ["B01", 2]}),
        (1, "ACTIONS_DETECTED", 1, {"actions": "A03"}),
        (1, "ACTIONS_DETECTED", 1, {"actions": [{"confidence": 0.9}]}),
        (1, "PHASE_CHANGED", 1, {"from": "INTERVIEW"}),
        (1, "FACT_REVEALED", 1, {}),
        (1, "NOTE_SUBMITTED", 1, {"chars": "many"}),
        (1, "NOTE_SUBMITTED", 1, {"chars": True}),
    ],
)
def test_rubric_malformed_event_payloads_raise(
    dev001: LoadedCase, bad: tuple[int, str, int, dict[str, Any]]
) -> None:
    with pytest.raises(MalformedEvent):
        View.build(_log(bad), dev001.actions)


# ---- applicability ----


def test_rubric_a_later_malformed_decision_event_still_raises(dev001: LoadedCase) -> None:
    ok = (1, "DECISION_COMMITTED", 1, {"option_id": "refer", "actions": []})
    bad = (2, "DECISION_COMMITTED", 2, {"option_id": "refer", "actions": None})
    with pytest.raises(MalformedEvent):
        View.build(_log(ok, bad), dev001.actions)


def test_rubric_item_for_another_variant_is_not_applicable(play: NewPlay) -> None:
    r = run(
        play("A").turn("A03"), {"type": "action_present_any", "actions": ["A03"]}, variants=["C"]
    )
    assert (r.result, r.earned, r.evidence) == ("na", 0.0, ())


# ---- properties over the real DEV-001 rubric ----

STEPS = st.one_of(
    st.tuples(
        st.just("turn"),
        st.lists(
            st.sampled_from(["A01", "A02", "A03", "A04", "A05", "C01", "C02", "C03", "C04"]),
            max_size=4,
        ),
    ),
    st.tuples(st.just("decide"), st.sampled_from(["refer", "proceed_service"])),
    st.tuples(st.just("note"), st.integers(0, 60)),
)


def _play(loaded: LoadedCase, variant: VariantId, script: list[Any]) -> Play:
    p = Play(loaded, variant)
    for kind, arg in script:
        try:
            if kind == "turn":
                p.turn(*arg)
            elif kind == "decide":
                p.decide(arg)
            else:
                p.note(arg)
        except Exception:  # the engine refuses e.g. a second decision: skip that step
            continue
    return p


@settings(max_examples=100, deadline=None)
@given(st.sampled_from(["A", "C"]), st.lists(STEPS, min_size=1, max_size=15), st.randoms())
def test_rubric_results_always_have_evidence_and_ignore_log_order(
    variant: VariantId, script: list[Any], rnd: random.Random
) -> None:
    from tests.unit.engine.conftest import DEV_001

    loaded = load_case(DEV_001)
    p = _play(loaded, variant, script)
    view = View.build(p.events, loaded.actions)
    shuffled = list(p.events)
    rnd.shuffle(shuffled)
    other = View.build(shuffled, loaded.actions)

    for it in loaded.rubric.items:
        r = evaluate_item(it, view, variant)
        assert r == evaluate_item(
            it, other, variant
        )  # replay order is by event id, not input order
        assert r == evaluate_item(it, view, variant)  # deterministic
        if r.result != "na" and p.events:
            assert r.evidence, (it.id, r.result)  # FR-SCR-05
