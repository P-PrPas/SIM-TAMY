"""Consented pilot feedback; independent from scoring and append-only events."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.v1.schemas import ClassPilotFeedback, PilotFeedback, PilotFeedbackRequest
from app.core.errors import ApiError
from app.db.models import ClassRoom, LearnerSession
from app.db.models import PilotFeedback as FeedbackRow


def submit(db: Session, row: LearnerSession, body: PilotFeedbackRequest) -> PilotFeedback:
    if row.status != "completed":
        raise ApiError("REPORT_NOT_READY", "complete the session before submitting feedback")
    values = body.model_dump(exclude={"consent"})
    saved = db.scalar(
        insert(FeedbackRow)
        .values(session_id=row.id, **values)
        .on_conflict_do_nothing()
        .returning(FeedbackRow)
    )
    if saved is None:
        saved = db.get(FeedbackRow, row.id)
        if saved is None or any(getattr(saved, key) != value for key, value in values.items()):
            raise ApiError("IDEMPOTENCY_CONFLICT", "feedback already submitted")
    return PilotFeedback.model_validate(saved)


def for_class(db: Session, code: str) -> ClassPilotFeedback:
    room = db.scalar(select(ClassRoom).where(ClassRoom.code == code))
    if room is None:
        raise ApiError("CLASS_NOT_FOUND", "class not found")
    selected = select(FeedbackRow).join(LearnerSession).where(LearnerSession.class_id == room.id)
    total, useful, realism = db.execute(
        select(func.count(), func.avg(FeedbackRow.usefulness), func.avg(FeedbackRow.realism))
        .select_from(FeedbackRow)
        .join(LearnerSession)
        .where(LearnerSession.class_id == room.id)
    ).one()
    rows = db.scalars(
        selected.order_by(FeedbackRow.created_at.desc(), FeedbackRow.session_id).limit(100)
    )
    return ClassPilotFeedback(
        total=total,
        usefulness_avg=float(useful) if useful is not None else None,
        realism_avg=float(realism) if realism is not None else None,
        items=[PilotFeedback.model_validate(row) for row in rows],
    )
