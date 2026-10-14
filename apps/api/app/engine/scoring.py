"""Rubric evaluator (PRD 10.2, FR-SCR-01/05). PURE: the Event Log is the only input.

Facts come from replaying the log in event-id order:
ACTIONS_DETECTED (accepted actions only, logged before the turn's engine events), FACT_REVEALED,
DECISION_COMMITTED, UNSAFE_ACTION, PHASE_CHANGED (running phase), NOTE_SUBMITTED {chars}.
Every pass/fail result carries evidence; when a result rests on something that did *not* happen
the evidence is the end of the observed log (the last event), so it is never empty.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

from app.domain.action import Action
from app.domain.case import VariantId
from app.domain.events import LoggedEvent
from app.domain.rubric import (
    ActionAbsent,
    ActionBefore,
    ActionPresentAll,
    ActionPresentAny,
    CountAtLeast,
    DecisionEquals,
    DecisionNot,
    NoteSubmitted,
    NoUnsafeAction,
    RubricItem,
    WithinTurnsAfterFact,
)
from app.domain.scoring import Evidence, ItemResult, Result


class Occurrence(NamedTuple):
    action_id: str
    event: LoggedEvent
    phase: str  # INTRO is reported as INTERVIEW (the public phase)


class Outcome(NamedTuple):
    result: Result
    ratio: float
    events: tuple[LoggedEvent, ...]


@dataclass(frozen=True)
class View:
    """The log, replayed once into the facts the checkers need."""

    events: tuple[LoggedEvent, ...]
    categories: dict[str, str]
    occurrences: tuple[Occurrence, ...]
    reveals: dict[str, LoggedEvent]  # first FACT_REVEALED per fact id
    decision: LoggedEvent | None

    @classmethod
    def build(cls, log: Sequence[LoggedEvent], actions: Sequence[Action]) -> "View":
        events = tuple(sorted(log, key=lambda e: e.id))
        phase = "INTERVIEW"
        occurrences: list[Occurrence] = []
        reveals: dict[str, LoggedEvent] = {}
        decision: LoggedEvent | None = None
        for e in events:
            if e.type == "PHASE_CHANGED":
                phase = "INTERVIEW" if e.payload["to"] == "INTRO" else e.payload["to"]
            elif e.type == "ACTIONS_DETECTED":
                occurrences += [Occurrence(a["id"], e, phase) for a in e.payload["actions"]]
            elif e.type == "FACT_REVEALED":
                reveals.setdefault(e.payload["id"], e)
            elif e.type == "DECISION_COMMITTED" and decision is None:
                decision = e
        return cls(
            events, {a.id: a.category for a in actions}, tuple(occurrences), reveals, decision
        )

    def first(self, action_id: str) -> Occurrence | None:
        return next((o for o in self.occurrences if o.action_id == action_id), None)

    def of(self, event_type: str) -> list[LoggedEvent]:
        return [e for e in self.events if e.type == event_type]

    def end(self) -> tuple[LoggedEvent, ...]:
        """End of the observed log: evidence when a result rests on something absent."""
        return self.events[-1:]


def _unique(events: Sequence[LoggedEvent]) -> tuple[LoggedEvent, ...]:
    return tuple({e.id: e for e in sorted(events, key=lambda e: e.id)}.values())


def _present_any(v: View, c: ActionPresentAny) -> Outcome:
    phase = None if c.phase is None else ("INTERVIEW" if c.phase == "INTRO" else c.phase)
    hits = [
        o.event
        for o in v.occurrences
        if o.action_id in c.actions and (phase is None or o.phase == phase)
    ]
    return Outcome("pass", 1.0, _unique(hits)) if hits else Outcome("fail", 0.0, v.end())


def _present_all(v: View, c: ActionPresentAll) -> Outcome:
    wanted = set(c.actions)
    found = [o for a in sorted(wanted) if (o := v.first(a))]
    ratio = len(found) / len(wanted) if wanted else 1.0
    result: Result = "pass" if ratio == 1 else "fail" if ratio == 0 else "partial"
    return Outcome(result, ratio, _unique([o.event for o in found]) or v.end())


def _absent(v: View, c: ActionAbsent) -> Outcome:
    marker = next(iter(v.of(c.after_event)), None) if c.after_event else None
    if c.after_event and marker is None:
        return Outcome("pass", 1.0, v.end())  # the event never happened, so nothing came after it
    floor = marker.id if marker else -1
    bad = [o.event for o in v.occurrences if o.action_id in c.actions and o.event.id > floor]
    if bad:
        return Outcome("fail", 0.0, _unique(bad))
    return Outcome("pass", 1.0, (marker,) if marker else v.end())


def _before(v: View, c: ActionBefore) -> Outcome:
    a, b = v.first(c.first), v.first(c.then)
    seen = _unique([o.event for o in (a, b) if o]) or v.end()
    if a and b and a.event.turn_idx < b.event.turn_idx:
        return Outcome("pass", 1.0, seen)
    return Outcome("fail", 0.0, seen)


def _decision_equals(v: View, c: DecisionEquals) -> Outcome:
    d = v.decision
    if d is not None and d.payload["option_id"] == c.option:
        return Outcome("pass", 1.0, (d,))
    return Outcome("fail", 0.0, (d,) if d else v.end())


def _decision_not(v: View, c: DecisionNot) -> Outcome:
    d = v.decision
    if d is None:
        return Outcome("pass", 1.0, v.end())  # nothing was committed, so it was not committed
    if d.payload["option_id"] != c.option:
        return Outcome("pass", 1.0, (d,))
    if c.when_fact_revealed is None:
        return Outcome("fail", 0.0, (d,))
    seen = v.reveals.get(c.when_fact_revealed)
    if seen is not None and seen.id < d.id:
        return Outcome("fail", 0.0, _unique([seen, d]))
    return Outcome("pass", 1.0, (d,))


def _within_turns(v: View, c: WithinTurnsAfterFact) -> Outcome:
    d = v.decision
    shown = [r for f in c.fact_ids if (r := v.reveals.get(f))]
    if d is None or d.payload["option_id"] != c.decision or len(shown) < len(set(c.fact_ids)):
        return Outcome("fail", 0.0, _unique([*shown, *([d] if d else [])]) or v.end())
    gap = d.turn_idx - max(r.turn_idx for r in shown)
    return Outcome(
        "pass" if gap <= c.max_turns else "fail", float(gap <= c.max_turns), _unique([*shown, d])
    )


def _count(v: View, c: CountAtLeast) -> Outcome:
    ids = sorted(
        {o.action_id for o in v.occurrences if v.categories.get(o.action_id) == c.category}
    )
    ratio = min(len(ids), c.n) / c.n
    result: Result = "pass" if ratio == 1 else "fail" if ratio == 0 else "partial"
    events = _unique([o.event for i in ids if (o := v.first(i))])
    return Outcome(result, ratio, events or v.end())


def _no_unsafe(v: View, c: NoUnsafeAction) -> Outcome:
    bad = v.of("UNSAFE_ACTION")
    return Outcome("fail", 0.0, _unique(bad)) if bad else Outcome("pass", 1.0, v.end())


def _note(v: View, c: NoteSubmitted) -> Outcome:
    notes = v.of("NOTE_SUBMITTED")
    good = [n for n in notes if n.payload.get("chars", 0) >= (c.min_chars or 1)]
    if good:
        return Outcome("pass", 1.0, (good[0],))
    return Outcome("fail", 0.0, tuple(notes[:1]) or v.end())


def _check(v: View, item: RubricItem) -> Outcome:
    c = item.check
    if isinstance(c, ActionPresentAny):
        return _present_any(v, c)
    if isinstance(c, ActionPresentAll):
        return _present_all(v, c)
    if isinstance(c, ActionAbsent):
        return _absent(v, c)
    if isinstance(c, ActionBefore):
        return _before(v, c)
    if isinstance(c, DecisionEquals):
        return _decision_equals(v, c)
    if isinstance(c, DecisionNot):
        return _decision_not(v, c)
    if isinstance(c, WithinTurnsAfterFact):
        return _within_turns(v, c)
    if isinstance(c, CountAtLeast):
        return _count(v, c)
    if isinstance(c, NoUnsafeAction):
        return _no_unsafe(v, c)
    return _note(v, c)


def evaluate_item(item: RubricItem, view: View, variant: VariantId) -> ItemResult:
    """Pure: same log, same item, same result."""
    if item.applies_to_variants is not None and variant not in item.applies_to_variants:
        return ItemResult(
            id=item.id,
            competency=item.competency,
            result="na",
            points=item.points,
            earned=0.0,
            critical=item.critical,
        )
    outcome = _check(view, item)
    return ItemResult(
        id=item.id,
        competency=item.competency,
        result=outcome.result,
        points=item.points,
        earned=item.points * outcome.ratio,
        critical=item.critical,
        evidence=tuple(
            Evidence(event_id=e.id, turn_idx=e.turn_idx, type=e.type) for e in outcome.events
        ),
    )
