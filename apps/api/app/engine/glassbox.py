"""Glass Box and timeline (FR-GB-01, PRD 8.2): derived from the Event Log only. PURE.

T-064 extends this (missed opportunities live in `replay.py`). Thai text comes from the case
(labels, fact text) or from `labels`, never from here.
"""

from collections.abc import Mapping, Sequence

from app.domain.action import Action
from app.domain.case import Case, HiddenFact
from app.domain.events import LoggedEvent
from app.domain.report import GlassBox, GlassFact, LearnerAction, RiskPoint, TimelineEntry


def _action_ids(event: LoggedEvent) -> list[str]:
    return [str(a["id"]) for a in event.payload["actions"]]


def build_glassbox(log: Sequence[LoggedEvent], case: Case, actions: Sequence[Action]) -> GlassBox:
    events = sorted(log, key=lambda e: e.id)
    revealed_at: dict[str, int] = {}
    for e in events:
        if e.type == "FACT_REVEALED":
            revealed_at.setdefault(str(e.payload["id"]), e.turn_idx)

    facts = tuple(
        GlassFact(
            id=f.id,
            kind=f.kind,
            text_th=f.text_th,
            risk_relevance=f.risk_relevance if isinstance(f, HiddenFact) else None,
            revealed=f.kind == "known" or f.id in revealed_at,
            revealed_at_idx=revealed_at.get(f.id),
        )
        for f in case.facts
    )
    risk = [RiskPoint(turn_idx=0, risk_state="unrecognized")] + [
        RiskPoint(turn_idx=e.turn_idx, risk_state=e.payload["to"])
        for e in events
        if e.type == "RISK_STATE_CHANGED"
    ]
    labels = {a.id: a.label_th for a in actions}
    repeated = {(e.turn_idx, str(e.payload["id"])) for e in events if e.type == "ACTION_REPEATED"}
    learner = tuple(
        LearnerAction(
            turn_idx=e.turn_idx,
            action_id=i,
            label_th=labels.get(i, i),
            repeated=(e.turn_idx, i) in repeated,
        )
        for e in events
        if e.type == "ACTIONS_DETECTED"
        for i in _action_ids(e)
    )
    return GlassBox(facts=facts, risk_state_timeline=tuple(risk), learner_actions=learner)


def build_timeline(
    log: Sequence[LoggedEvent], case: Case, actions: Sequence[Action], labels: Mapping[str, str]
) -> tuple[TimelineEntry, ...]:
    """One entry per event type named in `labels` (event type -> Thai heading)."""
    action_label = {a.id: a.label_th for a in actions}
    fact_text = {f.id: f.text_th for f in case.facts}
    option_label = {o.id: o.label_th for o in case.decision_options}
    out: list[TimelineEntry] = []
    for e in sorted(log, key=lambda e: e.id):
        if e.type not in labels:
            continue
        detail = ""
        if e.type == "ACTIONS_DETECTED":
            detail = ", ".join(action_label.get(i, i) for i in _action_ids(e))
        elif e.type == "FACT_REVEALED":
            detail = fact_text.get(str(e.payload["id"]), "")
        elif e.type == "DECISION_COMMITTED":
            detail = option_label.get(str(e.payload["option_id"]), "")
        heading = labels[e.type]
        summary = f"{heading}: {detail}" if detail else heading
        out.append(
            TimelineEntry(event_id=e.id, turn_idx=e.turn_idx, type=e.type, summary_th=summary)
        )
    return tuple(out)
