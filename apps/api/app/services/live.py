"""Live Glass Box (FR-GB-02): the session's hidden state, for demos and instructors only.

Built from the Event Log like the post-case Glass Box. Callers decide who may see it (the
`GLASS_BOX_LIVE` flag or the instructor secret); nothing here is sent to a learner by default.
"""

import uuid

from sqlalchemy.orm import Session

from app.api.v1.schemas import Fact, LiveGlassBox
from app.content.loader import LoadedCase
from app.domain.state import SessionState
from app.engine.glassbox import build_glassbox
from app.services.closing import logged_events


def live_glassbox(
    db: Session, loaded: LoadedCase, session_id: uuid.UUID, state: SessionState
) -> LiveGlassBox:
    box = build_glassbox(logged_events(db, session_id), loaded.case, loaded.actions)
    return LiveGlassBox(
        risk_state=state.risk_state,
        facts=[Fact(**f.model_dump()) for f in box.facts],
        fired_action_ids=list(state.fired_action_ids),
    )
