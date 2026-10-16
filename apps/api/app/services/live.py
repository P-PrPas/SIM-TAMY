"""Live Glass Box (FR-GB-02): the session's hidden state, for demos and instructors only.

Built from the Event Log like the post-case Glass Box. Callers decide who may see it (the
`GLASS_BOX_LIVE` flag or the instructor secret); nothing here is sent to a learner by default.
"""

import uuid
from collections.abc import Iterable

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
    log: list[LoggedEvent] = []
    for e in logged_events(db, session_id):
        if e.turn_idx > idx:
            break  # only a turn's own events change risk state and facts
        log.append(e)
    risk = [e.payload["to"] for e in log if e.type == "RISK_STATE_CHANGED"]
    fired = dict.fromkeys(
        str(a["id"]) for e in log if e.type == "ACTIONS_DETECTED" for a in e.payload["actions"]
    )
    return _box(log, loaded, risk[-1] if risk else "unrecognized", fired)


def _box(
    log: list[LoggedEvent], loaded: LoadedCase, risk_state: str, fired: Iterable[str]
) -> LiveGlassBox:
    box = build_glassbox(log, loaded.case, loaded.actions)
    return LiveGlassBox(
        risk_state=risk_state,
        facts=[Fact(**f.model_dump()) for f in box.facts],
        fired_action_ids=list(fired),
    )
