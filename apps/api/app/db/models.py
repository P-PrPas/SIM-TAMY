"""SQLAlchemy models for PRD 7.3. `events` is append-only: see `app.db.repo.EventRepo`."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint/index names so Alembic downgrades and autogenerate are deterministic.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _now() -> Any:
    return func.now()


def _ts() -> Mapped[datetime]:
    return mapped_column(TIMESTAMP(timezone=True), server_default=_now())


class ClassRoom(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(CHAR(6), unique=True)
    name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    # 2.0 cohort (ADR-15): the mock organization from content/demo/institutions.yaml
    org_id: Mapped[str | None] = mapped_column(Text)


class Assignment(Base):
    """A story assigned to a cohort; learners reach it by the class code / QR (Blueprint §08)."""

    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    story_id: Mapped[str] = mapped_column(Text)
    story_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class PassportLesson(Base):
    """A knowledge lesson a mock account finished (LP-03). Not the append-only `events` log."""

    __tablename__ = "passport_lessons"

    account_id: Mapped[str] = mapped_column(Text, primary_key=True)
    unit_id: Mapped[str] = mapped_column(Text, primary_key=True)
    completed_at: Mapped[datetime] = _ts()


class LearnerSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("status IN ('active','completed','expired')", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(Text)
    case_version: Mapped[str] = mapped_column(Text)
    case_hash: Mapped[str] = mapped_column(Text)
    variant: Mapped[str] = mapped_column(CHAR(1))
    class_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classes.id"))
    learner_name: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text)  # hash only, never the token itself
    state: Mapped[dict[str, Any]] = mapped_column(JSONB)  # PRD 7.4
    state_version: Mapped[int] = mapped_column(Integer, server_default="0")  # optimistic lock
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = _ts()
    last_activity_at: Mapped[datetime] = _ts()
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


Index("ix_sessions_class_id_started_at", LearnerSession.class_id, LearnerSession.started_at.desc())


class PilotFeedback(Base):
    __tablename__ = "pilot_feedback"
    __table_args__ = (
        CheckConstraint("role IN ('learner','instructor','practitioner')", name="role"),
        CheckConstraint("usefulness BETWEEN 1 AND 5", name="usefulness"),
        CheckConstraint("realism BETWEEN 1 AND 5", name="realism"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(Text)
    usefulness: Mapped[int] = mapped_column(Integer)
    realism: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()


class Turn(Base):
    __tablename__ = "turns"
    __table_args__ = (
        CheckConstraint("speaker IN ('learner','patient','relative','system')", name="speaker"),
        UniqueConstraint("session_id", "client_turn_id", name="uq_turns_session_id_client_turn_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(Integer)  # learner turn index; system turns share it
    speaker: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    client_turn_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()


class Event(Base):
    """Append-only (AGENTS.md rule 8): no UPDATE/DELETE in application code."""

    __tablename__ = "events"
    __table_args__ = (Index("ix_events_session_id_id", "session_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    turn_idx: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = _ts()


class LlmCall(Base):
    """No raw prompt is stored (PRD 7.3 note)."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # no FK, per PRD 7.3
    turn_idx: Mapped[int | None] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(Text)  # interpreter|generator|debrief|bench
    provider: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool | None] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    # AICallTrace (Blueprint §09E): versions and outcome only, never raw text.
    capability: Mapped[str | None] = mapped_column(Text)  # ai01|ai02|ai03
    request_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str | None] = mapped_column(Text)  # valid|rejected|timeout
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    release_id: Mapped[str | None] = mapped_column(Text)
    room_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # family room; no FK, like session_id


class Report(Base):
    __tablename__ = "reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    rubric_version: Mapped[str] = mapped_column(Text)
    scoring: Mapped[dict[str, Any]] = mapped_column(JSONB)
    debrief: Mapped[dict[str, Any]] = mapped_column(JSONB)
    glassbox: Mapped[dict[str, Any]] = mapped_column(JSONB)
    replay: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts()


class ScoreOverride(Base):
    """Could-have (FR-INS-04). Table only; no repo yet."""

    __tablename__ = "score_overrides"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # no FK, per PRD 7.3
    rubric_item_id: Mapped[str | None] = mapped_column(Text)
    new_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
