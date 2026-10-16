"""T-049 retention CLI: purge completed or expired sessions past retention.

Live event logs remain append-only. Deleting a finished parent session cascades its
turns, events and report; metadata without foreign keys is removed explicitly.
"""

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LearnerSession, LlmCall, ScoreOverride
from app.db.session import get_sessionmaker

FINISHED_STATUSES = ("completed", "expired")


def purge_expired(db: Session, *, retention_days: int, now: datetime) -> int:
    """Delete eligible sessions in the caller's transaction; return number deleted."""
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    cutoff = now - timedelta(days=retention_days)
    ids = list(
        db.scalars(
            select(LearnerSession.id)
            .where(LearnerSession.status.in_(FINISHED_STATUSES), LearnerSession.ended_at < cutoff)
            .with_for_update(skip_locked=True)
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
                LearnerSession.status.in_(FINISHED_STATUSES),
                LearnerSession.ended_at < cutoff,
            )
            .returning(LearnerSession.id)
        )
        .scalars()
        .all()
    )
    return len(deleted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge finished sessions past retention")
    parser.add_argument(
        "--dry-run", action="store_true", help="show eligible count without deletion"
    )
    args = parser.parse_args()
    days = get_settings().log_retention_days
    with get_sessionmaker()() as db:
        if args.dry_run:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            count = db.scalar(
                select(func.count(LearnerSession.id)).where(
                    LearnerSession.status.in_(FINISHED_STATUSES),
                    LearnerSession.ended_at < cutoff,
                )
            )
            print(f"Eligible finished sessions: {count}")
            return
        with db.begin():
            count = purge_expired(db, retention_days=days, now=datetime.now(UTC))
    print(f"Purged finished sessions: {count}")


if __name__ == "__main__":
    main()
