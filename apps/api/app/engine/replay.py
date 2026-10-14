"""Consequence Replay (FR-REP-01): the case's own outcome script for how the session ended. PURE.

`terminal_state` is `UnsafeProceed` when the log has an UNSAFE_ACTION or the committed option's
branch rule is `mark_unsafe` (the case says proceeding there is unsafe), else `Referral`.
ponytail: T-064 refines the rule and fills `missed_opportunities`.
"""

from collections.abc import Sequence

from app.domain.case import Case
from app.domain.events import LoggedEvent
from app.domain.report import Replay


def terminal_state(log: Sequence[LoggedEvent], case: Case) -> str:
    decisions = [str(e.payload["option_id"]) for e in log if e.type == "DECISION_COMMITTED"]
    unsafe_option = any(
        r.mark_unsafe and r.on_decision in decisions for r in case.branch_rules if r.on_decision
    )
    if unsafe_option or any(e.type == "UNSAFE_ACTION" for e in log):
        return "UnsafeProceed"
    return "Referral"


def build_replay(log: Sequence[LoggedEvent], case: Case, disclaimer_th: str) -> Replay:
    state = terminal_state(log, case)
    script = case.outcome_scripts.get(state)
    return Replay(
        terminal_state=state,
        timeline_th=tuple(script.timeline_th) if script else (),
        missed_opportunities=(),
        disclaimer_th=script.disclaimer_th if script else disclaimer_th,
    )
