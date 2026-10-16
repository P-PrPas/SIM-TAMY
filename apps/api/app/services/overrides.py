"""Instructor score overrides (FR-INS-04, T-058): a separate record, never an edit.

`score_overrides` holds each override; the report's `scoring` stays what the engine produced, so
`make rescore` still equals it. `effective` is recomputed on read by `engine.overrides`.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import ItemResultValue, Override, OverrideRequest
from app.content.loader import ContentStore
from app.core.errors import ApiError
from app.db.models import Report, ScoreOverride
from app.db.repo import SessionRepo
from app.domain.scoring import Scoring
from app.engine.overrides import ItemOverride, OverrideRefused, check_override
from app.services.sessions import pinned_case


def stored(db: Session, session_id: uuid.UUID) -> list[ScoreOverride]:
    return list(
        db.scalars(
            select(ScoreOverride)
            .where(ScoreOverride.session_id == session_id)
            .order_by(ScoreOverride.id)
        )
    )


def as_item_override(row: ScoreOverride) -> ItemOverride:
    data: dict[str, Any] = row.new_result or {}
    return ItemOverride(row.rubric_item_id or "", data["result"], data.get("earned"))


def as_api(row: ScoreOverride) -> Override:
    data: dict[str, Any] = row.new_result or {}
    return Override(
        id=row.id,
        rubric_item_id=row.rubric_item_id or "",
        original_result=ItemResultValue(data["original_result"]),
        new_result=data["result"],
        new_earned=data.get("earned"),
        reason=row.reason or "",
        created_at=row.created_at,
    )


def create(
    db: Session, store: ContentStore, session_id: uuid.UUID, req: OverrideRequest
) -> Override:
    # row lock until commit: purge_old skips locked sessions, and waits out ours (then 404s)
    row = SessionRepo(db).get(session_id, for_update=True)
    if row is None:
        raise ApiError("NOT_FOUND", "session not found")
    report = db.get(Report, session_id)
    if report is None:
        raise ApiError("REPORT_NOT_READY", "the session is not completed yet")
    scoring = Scoring.model_validate(report.scoring)  # the engine's own result, never edited
    pinned_case(store, row)  # the case this session ran on must still load
    wanted = ItemOverride(req.rubric_item_id, req.new_result, req.new_earned)
    try:
        original = check_override(scoring, wanted)
    except OverrideRefused as exc:
        raise ApiError(
            "VALIDATION_ERROR", str(exc), {"fields": [{"loc": ["body", "rubric_item_id"]}]}
        ) from exc
    saved = ScoreOverride(
        session_id=session_id,
        rubric_item_id=req.rubric_item_id,
        new_result={
            "result": req.new_result,
            "earned": req.new_earned if req.new_result == "partial" else None,
            "original_result": original.result,
        },
        reason=req.reason,
    )
    db.add(saved)
    db.flush()
    db.refresh(saved)
    return as_api(saved)
