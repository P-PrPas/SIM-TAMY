"""T-049: retention removes only sessions that are already expired and past cutoff."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event, LearnerSession, LlmCall, Report, ScoreOverride, Turn
from app.purge_old import purge_expired


def _session(db: Session, status: str, ended_at: datetime | None) -> uuid.UUID:
    row = LearnerSession(
        case_id="DEV-001",
        case_version="0.1",
        case_hash="synthetic-fixture",
        variant="A",
        learner_name="synthetic learner",
        token_hash="synthetic-token-hash",
        state={"phase": "INTERVIEW"},
        status=status,
        ended_at=ended_at,
    )
    db.add(row)
    db.flush()
    return row.id


def test_purge_only_old_expired_sessions_and_related_data(db: Session) -> None:
    now = datetime(2026, 10, 16, tzinfo=UTC)
    old = now - timedelta(days=31)
    recent = now - timedelta(days=29)
    expired_old = _session(db, "expired", old)
    expired_recent = _session(db, "expired", recent)
    active_old = _session(db, "active", old)
    completed_old = _session(db, "completed", old)
    expired_undated = _session(db, "expired", None)
    for session_id in (expired_old, expired_recent):
        db.add(Turn(session_id=session_id, idx=1, speaker="learner", text="synthetic private text"))
        db.add(Event(session_id=session_id, turn_idx=1, type="LEARNER_MESSAGE", payload={}))
        db.add(
            Report(
                session_id=session_id,
                rubric_version="fixture",
                scoring={},
                debrief={},
                glassbox={},
                replay={},
            )
        )
        db.add(LlmCall(session_id=session_id, purpose="interpreter"))
        db.add(ScoreOverride(session_id=session_id, reason="synthetic private reason"))
    db.flush()

    assert purge_expired(db, retention_days=30, now=now) == 1
    db.flush()
    assert db.get(LearnerSession, expired_old) is None
    for session_id in (expired_recent, active_old, completed_old, expired_undated):
        assert db.get(LearnerSession, session_id) is not None
    for model in (Turn, Event, Report, LlmCall, ScoreOverride):
        assert not db.scalars(select(model).where(model.session_id == expired_old)).all()
        assert db.scalars(select(model).where(model.session_id == expired_recent)).all()
    assert purge_expired(db, retention_days=30, now=now) == 0


def test_purge_rejects_invalid_retention(db: Session) -> None:
    try:
        purge_expired(db, retention_days=0, now=datetime(2026, 10, 16, tzinfo=UTC))
    except ValueError:
        pass
    else:
        raise AssertionError("retention must be positive")
