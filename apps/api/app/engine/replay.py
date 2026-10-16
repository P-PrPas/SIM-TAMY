"""Consequence Replay (FR-REP-01): the case's own outcome script for how the session ended. PURE.

`terminal_state` is `UnsafeProceed` when the log has an UNSAFE_ACTION or the committed option's
branch rule is `mark_unsafe` (the case says proceeding there is unsafe), else `Referral`.
Missed opportunities (every UnsafeProceed has at least one):
- proceeded by decision: each of the case's `critical_facts_for_replay` is a moment they could have
  stopped: the turn the fact reached them, or the decision turn when they never asked;
- gave in after referring (UNSAFE_ACTION from an action, e.g. C04 under pressure): the critical
  facts they already had, at the turn they gave in.
Thai wording comes from `notes`, never from here.
"""

from collections.abc import Mapping, Sequence

from app.domain.case import Case
from app.domain.events import LoggedEvent
from app.domain.report import MissedOpportunity, Replay


def _decisions(log: Sequence[LoggedEvent]) -> list[LoggedEvent]:
    return [e for e in log if e.type == "DECISION_COMMITTED"]


def _proceeded_by_decision(log: Sequence[LoggedEvent], case: Case) -> bool:
    chosen = {str(e.payload["option_id"]) for e in _decisions(log)}
    return any(
        r.mark_unsafe and r.on_decision in chosen for r in case.branch_rules if r.on_decision
    )


def terminal_state(log: Sequence[LoggedEvent], case: Case) -> str:
    if _proceeded_by_decision(log, case) or any(e.type == "UNSAFE_ACTION" for e in log):
        return "UnsafeProceed"
    return "Referral"


def missed_opportunities(
    log: Sequence[LoggedEvent], case: Case, notes: Mapping[str, str]
) -> tuple[MissedOpportunity, ...]:
    """`notes`: `revealed`, `never_asked` and `gave_in` templates with a `{fact}` placeholder."""
    text = {f.id: f.text_th for f in case.facts}
    gave_in = tuple(
        MissedOpportunity(
            turn_idx=e.turn_idx,
            fact_id=str(fact_id),
            note_th=notes["gave_in"].format(fact=text[str(fact_id)]),
        )
        for e in sorted(log, key=lambda e: e.id)
        if e.type == "UNSAFE_ACTION" and e.payload.get("trigger") == "action"
        for fact_id in e.payload["fact_ids"]
    )
    if not _proceeded_by_decision(log, case):
        return gave_in
    decision_turn = _decisions(log)[0].turn_idx
    revealed_at: dict[str, int] = {}
    for e in sorted(log, key=lambda e: e.id):
        if e.type == "FACT_REVEALED":
            revealed_at.setdefault(str(e.payload["id"]), e.turn_idx)
    return gave_in + tuple(
        MissedOpportunity(
            turn_idx=revealed_at.get(fact_id, decision_turn),
            fact_id=fact_id,
            note_th=notes["revealed" if fact_id in revealed_at else "never_asked"].format(
                fact=text[fact_id]
            ),
        )
        for fact_id in case.critical_facts_for_replay
    )


def build_replay(
    log: Sequence[LoggedEvent], case: Case, disclaimer_th: str, notes: Mapping[str, str]
) -> Replay:
    state = terminal_state(log, case)
    script = case.outcome_scripts.get(state)
    return Replay(
        terminal_state=state,
        timeline_th=tuple(script.timeline_th) if script else (),
        missed_opportunities=missed_opportunities(log, case, notes),
        disclaimer_th=script.disclaimer_th if script else disclaimer_th,
    )
