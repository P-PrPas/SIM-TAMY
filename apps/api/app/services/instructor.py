"""Instructor-only reads; cohort metrics use persisted deterministic scores (T-055/T-057)."""

import base64
import binascii
import json
import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.schemas import (
    CaseStatus,
    ClassAnalytics,
    ClassInfo,
    CompetencyAverage,
    CriticalItemFailRate,
    InstructorSessionList,
    SafetyStatus,
    SessionStatus,
    SessionSummary,
    Variant,
)
from app.content.loader import ContentStore
from app.core.errors import ApiError
from app.db.models import ClassRoom, LearnerSession, Report, Turn
from app.domain.scoring import Scoring
from app.services.briefs import status_label
from app.services.sessions import pinned_case

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass(frozen=True)
class CohortRecord:
    case_id: str
    scoring: Scoring
    turns: int
    item_labels: dict[str, str]


def analytics_from_records(
    class_code: str, records: list[CohortRecord], *, sessions_active: int
) -> ClassAnalytics:
    """Aggregate actual completed reports only; absent samples stay null, never zero."""
    count = len(records)
    competency: dict[str, list[float]] = defaultdict(list)
    competency_labels: dict[str, str] = {}
    critical: dict[str, list[bool]] = defaultdict(list)
    critical_labels: dict[str, str] = {}
    for record in records:
        for component in record.scoring.competencies:
            competency[component.id].append(component.score_pct)
            competency_labels[component.id] = component.name_th
        for item in record.scoring.items:
            if item.critical and item.result != "na":
                key = f"{record.case_id}:{item.id}"
                critical[key].append(item.result == "fail")
                critical_labels[key] = record.item_labels.get(item.id, item.id)
    return ClassAnalytics(
        class_code=class_code,
        sessions_completed=count,
        sessions_active=sessions_active,
        avg_total_score=round(sum(r.scoring.total_score for r in records) / count, 1)
        if count
        else None,
        safety_not_met_rate=(
            sum(r.scoring.safety_status == "SAFETY_NOT_MET" for r in records) / count
        )
        if count
        else None,
        avg_turns=sum(r.turns for r in records) / count if count else None,
        competency_avg=[
            CompetencyAverage(
                id=key, name_th=competency_labels[key], avg_pct=round(sum(values) / len(values), 1)
            )
            for key, values in sorted(competency.items())
        ],
        critical_item_fail_rates=[
            CriticalItemFailRate(
                item_id=key,
                label_th=critical_labels[key],
                fail_rate=sum(values) / len(values),
                n=len(values),
            )
            for key, values in sorted(critical.items())
        ],
    )


def _class_info(row: ClassRoom) -> ClassInfo:
    return ClassInfo(class_id=row.id, code=row.code, name=row.name or "", created_at=row.created_at)


def create_class(db: Session, name: str) -> ClassInfo:
    """Collision-safe random code; no predictable sequence and no schema migration."""
    for _ in range(12):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        row = db.execute(
            pg_insert(ClassRoom)
            .values(id=uuid.uuid4(), code=code, name=name)
            .on_conflict_do_nothing(index_elements=[ClassRoom.code])
            .returning(ClassRoom)
        ).scalar_one_or_none()
        if row is not None:
            return _class_info(row)
    raise ApiError("INTERNAL_ERROR", "could not allocate a class code")


def list_classes(db: Session) -> list[ClassInfo]:
    rows = db.scalars(select(ClassRoom).order_by(ClassRoom.created_at.desc(), ClassRoom.id.desc()))
    return [_class_info(row) for row in rows]


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        if len(cursor) > 256:
            raise ValueError("cursor too long")
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        when, ident = json.loads(raw)
        return datetime.fromisoformat(when), uuid.UUID(ident)
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError) as exc:
        raise ApiError("VALIDATION_ERROR", "invalid cursor") from exc


def _encode_cursor(row: LearnerSession) -> str:
    raw = json.dumps([row.started_at.isoformat(), str(row.id)], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _turn_count() -> ColumnElement[int]:
    return (
        select(func.count(Turn.id))
        .where(Turn.session_id == LearnerSession.id, Turn.speaker == "learner")
        .correlate(LearnerSession)
        .scalar_subquery()
    )


def list_sessions(
    db: Session,
    store: ContentStore,
    *,
    class_code: str | None,
    case_id: str | None,
    variant: Variant | None,
    status: SessionStatus | None,
    safety_status: SafetyStatus | None,
    limit: int,
    cursor: str | None,
) -> InstructorSessionList:
    count = _turn_count()
    stmt = select(LearnerSession, Report, count).outerjoin(
        Report, Report.session_id == LearnerSession.id
    )
    if class_code:
        stmt = stmt.join(ClassRoom, ClassRoom.id == LearnerSession.class_id).where(
            ClassRoom.code == class_code
        )
    if case_id:
        stmt = stmt.where(LearnerSession.case_id == case_id)
    if variant:
        stmt = stmt.where(LearnerSession.variant == variant.value)
    if status:
        stmt = stmt.where(LearnerSession.status == status.value)
    if safety_status:
        stmt = stmt.where(Report.scoring["safety_status"].as_string() == safety_status.value)
    if cursor:
        when, ident = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                LearnerSession.started_at < when,
                and_(LearnerSession.started_at == when, LearnerSession.id < ident),
            )
        )
    rows = db.execute(
        stmt.order_by(LearnerSession.started_at.desc(), LearnerSession.id.desc()).limit(limit + 1)
    ).all()
    items: list[SessionSummary] = []
    for row, saved, turns in rows[:limit]:
        loaded = pinned_case(store, row)
        scoring = (
            Scoring.model_validate(saved.scoring) if saved and row.status == "completed" else None
        )
        items.append(
            SessionSummary(
                session_id=row.id,
                learner_name=row.learner_name,
                case_id=row.case_id,
                case_version=row.case_version,
                case_status=CaseStatus(loaded.case.status),
                case_status_label_th=status_label(loaded.case.status),
                variant=Variant(row.variant),
                status=SessionStatus(row.status),
                started_at=row.started_at,
                ended_at=row.ended_at,
                turns=turns,
                safety_status=SafetyStatus(scoring.safety_status) if scoring else None,
                total_score=scoring.total_score if scoring else None,
                competency_pct={c.id: c.score_pct for c in scoring.competencies} if scoring else {},
            )
        )
    return InstructorSessionList(
        items=items, next_cursor=_encode_cursor(rows[limit - 1][0]) if len(rows) > limit else None
    )


def class_analytics(db: Session, store: ContentStore, class_code: str) -> ClassAnalytics:
    room = db.scalar(select(ClassRoom).where(ClassRoom.code == class_code))
    if room is None:
        raise ApiError("NOT_FOUND", "class not found")
    active = (
        db.scalar(
            select(func.count(LearnerSession.id)).where(
                LearnerSession.class_id == room.id, LearnerSession.status == "active"
            )
        )
        or 0
    )
    rows = db.execute(
        select(LearnerSession, Report, _turn_count())
        .join(Report, Report.session_id == LearnerSession.id)
        .where(LearnerSession.class_id == room.id, LearnerSession.status == "completed")
    ).all()
    records: list[CohortRecord] = []
    for row, saved, turns in rows:
        loaded = pinned_case(store, row)
        records.append(
            CohortRecord(
                case_id=row.case_id,
                scoring=Scoring.model_validate(saved.scoring),
                turns=turns,
                item_labels={
                    item.id: item.fail_finding.template_th for item in loaded.rubric.items
                },
            )
        )
    return analytics_from_records(class_code, records, sessions_active=active)
