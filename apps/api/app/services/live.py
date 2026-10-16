"""Live Glass Box (FR-GB-02): the session's hidden state, for demos and instructors only.

Built from the Event Log like the post-case Glass Box. Callers decide who may see it (the
`GLASS_BOX_LIVE` flag or the instructor secret); nothing here is sent to a learner by default.
"""

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy.orm import Session

from app.api.v1.schemas import Fact, LiveGlassBox
from app.content.loader import LoadedCase
from app.domain.events import LoggedEvent
from app.domain.state import SessionState
from app.engine.glassbox import build_glassbox
from app.services.closing import logged_events


def live_glassbox(
    db: Session, loaded: LoadedCase, session_id: uuid.UUID, state: SessionState
) -> LiveGlassBox:
    return _box(logged_events(db, session_id), loaded, state.risk_state, state.fired_action_ids)


def glassbox_after_turn(
    db: Session, loaded: LoadedCase, session_id: uuid.UUID, idx: int
) -> LiveGlassBox:
    """What `live_glassbox` returned when turn `idx` was answered (for idempotent retries)."""
    return glassbox_at(logged_events(db, session_id), loaded, idx)


def glassbox_at(log: Sequence[LoggedEvent], loaded: LoadedCase, idx: int) -> LiveGlassBox:
    """The Event Log up to the answer of turn `idx`: later turns, and a decision committed after
    it (same `turn_idx`, never before the turn's own events), are not part of that answer."""
    seen: list[LoggedEvent] = []
    for e in sorted(log, key=lambda e: e.id):
        if e.turn_idx > idx or (e.type == "DECISION_COMMITTED" and e.turn_idx == idx):
            break
        seen.append(e)
    risk = [e.payload["to"] for e in seen if e.type == "RISK_STATE_CHANGED"]
    fired = dict.fromkeys(  # a decision fires its mapped actions too (`state.fired_action_ids`)
        str(a["id"]) if isinstance(a, dict) else str(a)
        for e in seen
        if e.type in ("ACTIONS_DETECTED", "DECISION_COMMITTED")
        for a in e.payload["actions"]
    )
    return _box(seen, loaded, risk[-1] if risk else "unrecognized", fired)


def _box(
    log: list[LoggedEvent], loaded: LoadedCase, risk_state: str, fired: Iterable[str]
) -> LiveGlassBox:
    box = build_glassbox(log, loaded.case, loaded.actions)
    return LiveGlassBox(
        risk_state=risk_state,
        facts=[Fact(**f.model_dump()) for f in box.facts],
        fired_action_ids=list(fired),
    )
