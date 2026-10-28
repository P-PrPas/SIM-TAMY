"""Pinned story and append-only family decisions; tokens are stored as hashes."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class FamilyRoom(Base):
    __tablename__ = "family_rooms"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    story: Mapped[dict[str, Any]] = mapped_column(JSONB)
    host_role: Mapped[str] = mapped_column(Text)
    host_hash: Mapped[str] = mapped_column(Text)
    partner_hash: Mapped[str | None] = mapped_column(Text)
    invite_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    # Presence only: last poll per role. Never exposes timestamps, just an online boolean.
    host_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    partner_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # 2.0 (ADR-15): cohort link, mock accounts per role, and the pinned knowledge release.
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="SET NULL")
    )
    host_account_id: Mapped[str | None] = mapped_column(Text)
    partner_account_id: Mapped[str | None] = mapped_column(Text)
    release_id: Mapped[str | None] = mapped_column(Text)


class FamilyEvent(Base):
    __tablename__ = "family_events"
    __table_args__ = (
        UniqueConstraint("room_id", "client_turn_id", name="uq_family_events_client_turn_id"),
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_rooms.id", ondelete="CASCADE"), primary_key=True
    )
    idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(Text)
    # decision (one turn), vote (joint step) or share (private fact -> shared timeline)
    kind: Mapped[str] = mapped_column(Text, server_default="decision")
    choice_id: Mapped[str] = mapped_column(Text)
    reply_th: Mapped[str | None] = mapped_column(Text)
    client_turn_id: Mapped[uuid.UUID] = mapped_column(Uuid)


class FamilyMessage(Base):
    """Typed learner text in a family room (AI-01). Kept apart from events for retention purges."""

    __tablename__ = "family_messages"
    __table_args__ = (
        UniqueConstraint("room_id", "client_turn_id", name="uq_family_messages_client_turn_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("family_rooms.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Text)
    step_id: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    intent_code: Mapped[str | None] = mapped_column(Text)
    client_turn_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class FamilyDebrief(Base):
    """AI-03 output per finished room and debrief version; regenerating is idempotent."""

    __tablename__ = "family_debriefs"
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_rooms.id", ondelete="CASCADE"), primary_key=True
    )
    debrief_version: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fallback_used: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
