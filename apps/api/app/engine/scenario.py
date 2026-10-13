"""Scenario engine (PRD 4.5). PURE: no I/O, no clock, no randomness, no LLM (AGENTS.md rule 1).

`apply` handles one learner turn on the action path. Per turn, in order: start the interview,
fire/repeat actions, reveal hidden facts, set risk state, one phase step. Rules come from the
case's `branch_rules`; the first matching rule in file order wins.
`CLOSING -> COMPLETED` is session completion (FR-SES-04), not an engine step.
"""

from collections.abc import Sequence
from typing import NamedTuple, cast

from app.domain.case import BranchRule, Case, HiddenFact, Phase, VariantId
from app.domain.events import Event
from app.domain.state import AllowedFact, AllowedFacts, RiskState, SessionState


class ApplyResult(NamedTuple):
    state: SessionState
    events: tuple[Event, ...]
    allowed: AllowedFacts  # what the Generator may say this turn


def _rules(case: Case, variant: VariantId, phase: Phase) -> list[BranchRule]:
    """Rules that start in `phase` and apply to `variant` (no if_variant = every variant)."""
    return [
        r
        for r in case.branch_rules
        if r.from_ == phase and (r.if_variant is None or variant in r.if_variant)
    ]


def _hit(rule: BranchRule, actions: set[str], decision: str | None) -> bool:
    by_action = rule.on_action_any is not None and bool(actions.intersection(rule.on_action_any))
    return by_action or (rule.on_decision is not None and rule.on_decision == decision)


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
    for rule in _rules(case, variant, phase):
        if rule.to is not None and _hit(rule, fired, decision):
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
    asked = set(detected)

    revealed = list(state.revealed_fact_ids)
    new_facts: list[str] = []
    for fact in case.facts:
        if isinstance(fact, HiddenFact) and fact.id not in revealed and asked & set(fact.unlock_on):
            revealed.append(fact.id)
            new_facts.append(fact.id)
            by = [a for a in detected if a in fact.unlock_on]
            events.append(
                Event(
                    type="FACT_REVEALED", turn_idx=idx, payload={"id": fact.id, "unlocked_by": by}
                )
            )

    risk = state.risk_state
    for rule in _rules(case, variant, phase):  # phase the actions happened in
        if rule.set_risk_state and _hit(rule, asked, None):
            new_risk = cast(RiskState, rule.set_risk_state)  # values checked by validate-content
            if new_risk != risk:
                events.append(
                    Event(
                        type="RISK_STATE_CHANGED",
                        turn_idx=idx,
                        payload={"from": risk, "to": new_risk},
                    )
                )
                risk = new_risk
            break

    target = next_phase(case, variant, phase, actions=detected)
    if target is not None and target != phase:
        events.append(_phase_changed(idx, phase, target, "action"))
        phase = target

    new_state = state.model_copy(
        update={
            "turn_idx": idx,
            "phase": phase,
            "fired_action_ids": tuple(fired),
            "revealed_fact_ids": tuple(revealed),
            "risk_state": risk,
        }
    )
    allowed = _allowed_facts(case, revealed, asked, new_facts)
    return ApplyResult(new_state, tuple(events), allowed)


def _allowed_facts(
    case: Case, revealed: list[str], asked: set[str], new_facts: list[str]
) -> AllowedFacts:
    """Known facts + hidden facts that are revealed AND related to this turn's actions."""
    known = set(case.patient_profile.known_facts)
    facts = tuple(
        AllowedFact(id=f.id, text_th=f.text_th)
        for f in case.facts
        if f.id in known
        or (isinstance(f, HiddenFact) and f.id in revealed and asked & set(f.unlock_on))
    )
    return AllowedFacts(facts=facts, must_convey_fact_ids=tuple(new_facts))


def _phase_changed(idx: int, old: Phase, new: Phase, trigger: str) -> Event:
    return Event(
        type="PHASE_CHANGED",
        turn_idx=idx,
        payload={"from": old, "to": new, "trigger": trigger},
    )
