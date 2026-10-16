"""Scenario engine (PRD 4.5). PURE: no I/O, no clock, no randomness, no LLM (AGENTS.md rule 1).

`apply` handles one learner turn on the action path. Per turn, in order: start the interview,
fire/repeat actions, reveal hidden facts, set risk state, one phase step. Rules come from the
case's `branch_rules`; the first matching rule in file order wins.
`CLOSING -> COMPLETED` is session completion (FR-SES-04), not an engine step.
`commit_decision` is the Decision Panel path (FR-ENG-03). Unsafe (FR-ENG-04): the rule that moves
the phase has `mark_unsafe` and a critical hidden fact was already revealed.
"""

from collections.abc import Sequence
from typing import NamedTuple, cast

from app.core.limits import PRESSURE_MAX_TURNS
from app.domain.case import BranchRule, Case, HiddenFact, Phase, PressureLine, VariantId
from app.domain.events import Event
from app.domain.state import AllowedFact, AllowedFacts, Pressure, RiskState, SessionState


class EngineError(Exception):
    code = "ENGINE_ERROR"  # API error code (API_DESIGN section 9); T-040 maps it


class InvalidPhase(EngineError):
    code = "INVALID_PHASE"


class DecisionAlreadyCommitted(EngineError):
    code = "DECISION_ALREADY_COMMITTED"


class DecisionOptionInvalid(EngineError):
    code = "DECISION_OPTION_INVALID"


class DecisionResult(NamedTuple):
    state: SessionState
    events: tuple[Event, ...]
    replayed: bool  # same option committed again: nothing changed
    pressure_line: PressureLine | None = None  # first scripted line, Variant C


class ApplyResult(NamedTuple):
    state: SessionState
    events: tuple[Event, ...]
    allowed: AllowedFacts  # what the Generator may say this turn
    pressure_line: PressureLine | None = None  # scripted reply in PRESSURE (ADR-11), no LLM


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


def _step(
    case: Case, variant: VariantId, phase: Phase, actions: set[str], decision: str | None
) -> BranchRule | None:
    """First matching rule that moves the phase."""
    for rule in _rules(case, variant, phase):
        if rule.to is not None and _hit(rule, actions, decision):
            return rule
    return None


def next_phase(
    case: Case,
    variant: VariantId,
    phase: Phase,
    *,
    actions: Sequence[str] = (),
    decision: str | None = None,
) -> Phase | None:
    """Target phase of the first matching rule, or None."""
    rule = _step(case, variant, phase, set(actions), decision)
    return rule.to if rule else None


def _risk(
    risk: RiskState,
    case: Case,
    variant: VariantId,
    phase: Phase,
    actions: set[str],
    decision: str | None,
    idx: int,
) -> tuple[RiskState, list[Event]]:
    """First matching rule with `set_risk_state` (action or decision path); event only on change."""
    for rule in _rules(case, variant, phase):  # the phase the trigger happened in
        if rule.set_risk_state and _hit(rule, actions, decision):
            new = cast(RiskState, rule.set_risk_state)  # values checked by validate-content
            if new == risk:
                return risk, []
            event = Event(
                type="RISK_STATE_CHANGED", turn_idx=idx, payload={"from": risk, "to": new}
            )
            return new, [event]
    return risk, []


def _unsafe(
    state: SessionState, case: Case, rule: BranchRule | None, trigger: str, ids: list[str], idx: int
) -> tuple[SessionState, list[Event]]:
    """UNSAFE_ACTION when `rule` is marked unsafe and a critical hidden fact is already revealed."""
    critical = [
        f.id
        for f in case.facts
        if isinstance(f, HiddenFact)
        and f.risk_relevance == "critical"
        and f.id in state.revealed_fact_ids
    ]
    if rule is None or not rule.mark_unsafe or not critical:
        return state, []
    flags = state.flags.model_copy(update={"unsafe_actions": (*state.flags.unsafe_actions, *ids)})
    event = Event(
        type="UNSAFE_ACTION",
        turn_idx=idx,
        payload={"trigger": trigger, "ids": ids, "fact_ids": critical},
    )
    return state.model_copy(update={"flags": flags}), [event]


def _pressure_turn(
    state: SessionState, case: Case, variant: VariantId, idx: int, phase: Phase, hit: list[str]
) -> tuple[Pressure, PressureLine | None, list[Event]]:
    """One learner turn spent in PRESSURE (FR-ENG-05): resolved by the case's rule, else the next
    scripted line, else closed unresolved after `PRESSURE_MAX_TURNS` (not counted as giving in)."""
    started = state.pressure.started_at_idx
    used = idx - (idx - 1 if started is None else started)
    if phase != "PRESSURE":  # a branch rule moved the phase: C03/C04
        resolved = Pressure(started_at_idx=started, resolved=True)
        return resolved, None, [_resolved(idx, True, hit)]
    if used >= PRESSURE_MAX_TURNS:
        events = [_phase_changed(idx, "PRESSURE", "CLOSING", "pressure_timeout")]
        unresolved = Pressure(started_at_idx=started, resolved=False)
        return unresolved, None, [*events, _resolved(idx, False, [])]
    script = case.variants[variant].pressure_script
    return state.pressure, (script[used] if used < len(script) else None), []


def _resolved(idx: int, resolved: bool, by: list[str]) -> Event:
    return Event(type="PRESSURE_RESOLVED", turn_idx=idx, payload={"resolved": resolved, "by": by})


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

    risk, risk_events = _risk(state.risk_state, case, variant, phase, asked, None, idx)
    events += risk_events

    step = _step(case, variant, phase, asked, None)
    target = step.to if step else None
    if target is not None and target != phase:
        events.append(_phase_changed(idx, phase, target, "action"))
        phase = target

    hit = [a for a in detected if step and step.on_action_any and a in step.on_action_any]
    pressure, line = state.pressure, None
    if state.phase == "PRESSURE":
        pressure, line, pressure_events = _pressure_turn(state, case, variant, idx, phase, hit)
        events += pressure_events
        if pressure.resolved is not None:
            phase = "CLOSING"
    new_state = state.model_copy(
        update={
            "turn_idx": idx,
            "phase": phase,
            "fired_action_ids": tuple(fired),
            "revealed_fact_ids": tuple(revealed),
            "risk_state": risk,
            "pressure": pressure,
        }
    )
    new_state, unsafe_events = _unsafe(new_state, case, step, "action", hit, idx)
    allowed = _allowed_facts(case, revealed, asked, new_facts)
    return ApplyResult(new_state, (*events, *unsafe_events), allowed, line)


def commit_decision(
    state: SessionState, option_id: str, case: Case, variant: VariantId
) -> DecisionResult:
    """Decision Panel commit (never inferred from chat text). Final; the same option is a no-op."""
    if state.decision is not None:
        if state.decision == option_id:
            return DecisionResult(state, (), True)
        raise DecisionAlreadyCommitted(state.decision)
    if state.phase != "INTERVIEW":
        raise InvalidPhase(state.phase)
    option = next((o for o in case.decision_options if o.id == option_id), None)
    if option is None:
        raise DecisionOptionInvalid(option_id)

    idx = state.turn_idx  # a decision does not consume a learner turn
    fired = tuple(dict.fromkeys((*state.fired_action_ids, *option.maps_to_actions)))
    events = [
        Event(
            type="DECISION_COMMITTED",
            turn_idx=idx,
            payload={"option_id": option_id, "actions": list(option.maps_to_actions)},
        )
    ]
    risk, risk_events = _risk(state.risk_state, case, variant, state.phase, set(), option_id, idx)
    events += risk_events
    rule = _step(case, variant, state.phase, set(), option_id)
    phase: Phase = state.phase
    if rule is not None and rule.to is not None and rule.to != phase:
        events.append(_phase_changed(idx, phase, rule.to, "decision"))
        phase = rule.to
    pressure, line = state.pressure, None
    if phase == "PRESSURE":  # Variant C: the relative speaks first, from the case's script
        pressure = Pressure(started_at_idx=idx)
        events.append(Event(type="PRESSURE_STARTED", turn_idx=idx, payload={"line": 0}))
        script = case.variants[variant].pressure_script
        line = script[0] if script else None
    new_state = state.model_copy(
        update={
            "decision": option_id,
            "fired_action_ids": fired,
            "phase": phase,
            "risk_state": risk,
            "pressure": pressure,
        }
    )
    new_state, unsafe_events = _unsafe(new_state, case, rule, "decision", [option_id], idx)
    return DecisionResult(new_state, (*events, *unsafe_events), False, line)


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
