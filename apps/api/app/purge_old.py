"""T-049 retention CLI: purge finished or abandoned sessions past retention.

Live event logs remain append-only. Deleting an eligible parent session cascades its
turns, events and report; metadata without foreign keys is removed explicitly.
"""

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.db.models import LearnerSession, LlmCall, ScoreOverride
from app.db.session import get_sessionmaker

FINISHED_STATUSES = ("completed", "expired")


def _eligible(cutoff: datetime) -> ColumnElement[bool]:
    return or_(
        and_(LearnerSession.status.in_(FINISHED_STATUSES), LearnerSession.ended_at < cutoff),
        and_(LearnerSession.status == "active", LearnerSession.last_activity_at < cutoff),
    )


def purge_expired(db: Session, *, retention_days: int, now: datetime) -> int:
    """Delete eligible sessions in the caller's transaction; return number deleted."""
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now - timedelta(days=retention_days)
    ids = list(
        db.scalars(
            select(LearnerSession.id).where(_eligible(cutoff)).with_for_update(skip_locked=True)
        )
    )
    if not ids:
        return 0
    db.execute(delete(LlmCall).where(LlmCall.session_id.in_(ids)))
    db.execute(delete(ScoreOverride).where(ScoreOverride.session_id.in_(ids)))
    deleted = (
        db.execute(
            delete(LearnerSession)
            .where(
                LearnerSession.id.in_(ids),
                _eligible(cutoff),
            )
            .returning(LearnerSession.id)
        )
        .scalars()
        .all()
    )
    return len(deleted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge sessions past retention")
    parser.add_argument(
        "--dry-run", action="store_true", help="show eligible count without deletion"
    )
    args = parser.parse_args()
    days = get_settings().log_retention_days
    with get_sessionmaker()() as db:
        if args.dry_run:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            count = db.scalar(select(func.count(LearnerSession.id)).where(_eligible(cutoff)))
            print(f"Eligible sessions: {count}")
            return
        with db.begin():
            count = purge_expired(db, retention_days=days, now=datetime.now(UTC))
    print(f"Purged sessions: {count}")


if __name__ == "__main__":
    main()
