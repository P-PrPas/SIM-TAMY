"""T-024: property tests for the pure engine (FR-ENG-06) on DEV-001, random play-throughs."""

from pathlib import Path
from typing import Literal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.content.loader import load_case
from app.domain.case import HiddenFact, VariantId
from app.domain.events import Event
from app.domain.state import SessionState, initial_state
from app.engine.scenario import EngineError, apply, commit_decision

LOADED = load_case(Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001")
CASE = LOADED.case
ACTION_IDS = [a.id for a in LOADED.actions] + ["ZZ99"]  # an unknown id must be harmless too
OPTION_IDS = [o.id for o in CASE.decision_options] + ["nope"]
HIDDEN = {f.id: f for f in CASE.facts if isinstance(f, HiddenFact)}
CRITICAL = {i for i, f in HIDDEN.items() if f.risk_relevance == "critical"}
RANK = {"INTRO": 0, "INTERVIEW": 1, "PRESSURE": 2, "CLOSING": 3, "COMPLETED": 4}

Step = tuple[Literal["turn", "decision"], list[str] | str]
steps = st.one_of(
    st.tuples(st.just("turn"), st.lists(st.sampled_from(ACTION_IDS), max_size=6)),
    st.tuples(st.just("decision"), st.sampled_from(OPTION_IDS)),
)
plays = st.tuples(st.sampled_from(["A", "C"]), st.lists(steps, max_size=25))
PROPS = settings(max_examples=200, deadline=None)


def run(variant: VariantId, script: list[Step]):  # type: ignore[no-untyped-def]
    """Play the script; steps the engine refuses are skipped. Returns every transition."""
    state = initial_state()
    log: list[tuple[str, SessionState, SessionState, tuple[Event, ...], object]] = []
    for kind, arg in script:
        before = state
        try:
            if kind == "turn":
                assert isinstance(arg, list)
                r = apply(state, arg, CASE, variant)
                state, events, extra = r.state, r.events, r.allowed
            else:
                assert isinstance(arg, str)
                d = commit_decision(state, arg, CASE, variant)
                state, events, extra = d.state, d.events, d.replayed
        except EngineError:
            continue
        log.append((kind, before, state, events, extra))
    return state, log


@PROPS
@given(plays)
def test_same_play_gives_identical_results(play: tuple[VariantId, list[Step]]) -> None:
    variant, script = play
    first_state, first_log = run(variant, script)
    second_state, second_log = run(variant, script)

    assert first_state == second_state and first_log == second_log


@PROPS
@given(plays)
def test_phase_never_goes_backwards_and_changes_chain(play: tuple[VariantId, list[Step]]) -> None:
    variant, script = play
    _, log = run(variant, script)

    for _, before, after, events, _ in log:
        assert RANK[after.phase] >= RANK[before.phase]
        moves = [e.payload for e in events if e.type == "PHASE_CHANGED"]
        path = [before.phase, *[m["to"] for m in moves]]
        assert [m["from"] for m in moves] == path[:-1] and path[-1] == after.phase


@PROPS
@given(plays)
def test_progress_only_grows_without_duplicates(play: tuple[VariantId, list[Step]]) -> None:
    variant, script = play
    _, log = run(variant, script)

    for _, before, after, _, _ in log:
        for name in ("fired_action_ids", "revealed_fact_ids"):
            old, new = getattr(before, name), getattr(after, name)
            assert new[: len(old)] == old and len(set(new)) == len(new)


@PROPS
@given(plays)
def test_facts_are_only_revealed_by_their_unlock_actions(
    play: tuple[VariantId, list[Step]],
) -> None:
    variant, script = play
    final, log = run(variant, script)

    for fact_id in final.revealed_fact_ids:
        assert fact_id in HIDDEN and set(HIDDEN[fact_id].unlock_on) & set(final.fired_action_ids)
    events = [e for _, _, _, evs, _ in log for e in evs if e.type == "FACT_REVEALED"]
    assert [e.payload["id"] for e in events] == list(final.revealed_fact_ids)  # once each, in order


@PROPS
@given(plays)
def test_allowed_facts_never_exceed_known_plus_revealed(
    play: tuple[VariantId, list[Step]],
) -> None:
    variant, script = play
    _, log = run(variant, script)
    known = set(CASE.patient_profile.known_facts)

    for kind, _, after, _, extra in log:
        if kind == "turn":
            allowed = {f.id for f in extra.facts}  # type: ignore[attr-defined]
            assert allowed <= known | set(after.revealed_fact_ids)
            assert set(extra.must_convey_fact_ids) <= allowed  # type: ignore[attr-defined]


@PROPS
@given(plays)
def test_turn_counter_and_decision_are_consistent(play: tuple[VariantId, list[Step]]) -> None:
    variant, script = play
    _, log = run(variant, script)

    committed: str | None = None
    for kind, before, after, _, _ in log:
        if kind == "turn":
            assert after.turn_idx == before.turn_idx + 1
        else:
            assert after.turn_idx == before.turn_idx  # a decision costs no learner turn
            assert committed in (None, after.decision)  # final: never changes once committed
        committed = after.decision or committed


@PROPS
@given(plays)
def test_unsafe_only_after_a_critical_fact_was_revealed(
    play: tuple[VariantId, list[Step]],
) -> None:
    variant, script = play
    final, log = run(variant, script)

    for _, _, after, events, _ in log:
        if any(e.type == "UNSAFE_ACTION" for e in events):
            assert CRITICAL & set(after.revealed_fact_ids)
    unsafe_events = sum(e.type == "UNSAFE_ACTION" for _, _, _, evs, _ in log for e in evs)
    assert unsafe_events == len(final.flags.unsafe_actions)
