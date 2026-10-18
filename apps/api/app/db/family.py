"""Pinned story and append-only family decisions; tokens are stored as hashes."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
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
    choice_id: Mapped[str] = mapped_column(Text)
    reply_th: Mapped[str | None] = mapped_column(Text)
    client_turn_id: Mapped[uuid.UUID] = mapped_column(Uuid)
