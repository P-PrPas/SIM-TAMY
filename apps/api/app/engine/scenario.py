"""Scenario engine (PRD 4.5). PURE: no I/O, no clock, no randomness, no LLM (AGENTS.md rule 1).

`apply` handles one learner turn on the action path. Phase moves follow the case's
`branch_rules`; the first matching rule in file order wins, one step per turn.
`CLOSING -> COMPLETED` is session completion (FR-SES-04), not an engine step.
"""

from collections.abc import Sequence
from typing import NamedTuple

from app.domain.case import Case, Phase, VariantId
from app.domain.events import Event
from app.domain.state import SessionState


class ApplyResult(NamedTuple):
    state: SessionState
    events: tuple[Event, ...]


def next_phase(
    case: Case,
    variant: VariantId,
    phase: Phase,
    *,
    actions: Sequence[str] = (),
    decision: str | None = None,
) -> Phase | None:
    """Target phase of the first matching rule, or None. Shared with the decision path (T-022)."""
    fired = set(actions)
    for rule in case.branch_rules:
        if rule.from_ != phase or rule.to is None:
            continue
        if rule.if_variant is not None and variant not in rule.if_variant:
            continue
        by_action = rule.on_action_any is not None and fired.intersection(rule.on_action_any)
        by_decision = rule.on_decision is not None and rule.on_decision == decision
        if by_action or by_decision:
            return rule.to
    return None


def apply(
    state: SessionState, action_ids: Sequence[str], case: Case, variant: VariantId
) -> ApplyResult:
    """One learner turn. Unknown action ids are the Interpreter's job to drop (T-030)."""
    idx = state.turn_idx + 1
    events: list[Event] = []
    phase = state.phase

    if phase == "INTRO":  # first learner message starts the interview
        events.append(_phase_changed(idx, "INTRO", "INTERVIEW", "first_turn"))
        phase = "INTERVIEW"

    fired = list(state.fired_action_ids)
    detected = list(dict.fromkeys(action_ids))  # de-dup, keep order
    for action_id in detected:
        if action_id in fired:
            events.append(Event(type="ACTION_REPEATED", turn_idx=idx, payload={"id": action_id}))
        else:
            fired.append(action_id)

    target = next_phase(case, variant, phase, actions=detected)
    if target is not None and target != phase:
        events.append(_phase_changed(idx, phase, target, "action"))
        phase = target

    new_state = state.model_copy(
        update={"turn_idx": idx, "phase": phase, "fired_action_ids": tuple(fired)}
    )
    return ApplyResult(new_state, tuple(events))


def _phase_changed(idx: int, old: Phase, new: Phase, trigger: str) -> Event:
    return Event(
        type="PHASE_CHANGED",
        turn_idx=idx,
        payload={"from": old, "to": new, "trigger": trigger},
    )
