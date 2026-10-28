"""Thin repositories over a caller-owned SQLAlchemy `Session`.

The caller owns the transaction (a turn is atomic: PRD / AGENTS.md), so nothing here commits.
`EventRepo` deliberately has no update/delete method (AGENTS.md rule 8).
"""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.db.models import Event, LearnerSession, LlmCall, Turn


class StaleStateError(Exception):
    """`state_version` moved since the caller loaded the session (optimistic lock)."""


class SessionRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        case_id: str,
        case_version: str,
        case_hash: str,
        variant: str,
        learner_name: str,
        token_hash: str,
        state: dict[str, Any],
        class_id: uuid.UUID | None = None,
    ) -> LearnerSession:
        row = LearnerSession(
            case_id=case_id,
            case_version=case_version,
            case_hash=case_hash,
            variant=variant,
            class_id=class_id,
            learner_name=learner_name,
            token_hash=token_hash,
            state=state,
            state_version=0,
            status="active",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get(
        self, session_id: uuid.UUID, *, for_update: bool = False, nowait: bool = False
    ) -> LearnerSession | None:
        """`nowait`: raise OperationalError (lock not available) instead of waiting."""
        stmt = select(LearnerSession).where(LearnerSession.id == session_id)
        if for_update:
            stmt = stmt.with_for_update(nowait=nowait).execution_options(populate_existing=True)
        return self.db.execute(stmt).scalar_one_or_none()

    def token_exists(self, token_hash: str) -> bool:
        # ponytail: unindexed scan of a small table; add an index on token_hash if it ever grows
        stmt = select(LearnerSession.id).where(LearnerSession.token_hash == token_hash).limit(1)
        return self.db.execute(stmt).first() is not None

    def save_state(
        self, session_id: uuid.UUID, state: dict[str, Any], *, expected_version: int
    ) -> int:
        """Compare-and-swap on `state_version`; returns the new version."""
        new_version = self.db.execute(
            update(LearnerSession)
            .where(
                LearnerSession.id == session_id,
                LearnerSession.state_version == expected_version,
            )
            .values(
                state=state,
                state_version=expected_version + 1,
                last_activity_at=func.now(),
            )
            .returning(LearnerSession.state_version)
        ).scalar_one_or_none()
        if new_version is None:
            raise StaleStateError(f"session {session_id}: state_version != {expected_version}")
        return new_version


class TurnRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        session_id: uuid.UUID,
        idx: int,
        speaker: str,
        text: str,
        client_turn_id: str | None = None,
    ) -> tuple[Turn, bool]:
        """Idempotent on (session_id, client_turn_id). Returns (turn, created)."""
        stmt = (
            pg_insert(Turn)
            .values(
                session_id=session_id,
                idx=idx,
                speaker=speaker,
                text=text,
                client_turn_id=client_turn_id,
            )
            .on_conflict_do_nothing(index_elements=["session_id", "client_turn_id"])
            .returning(Turn)
        )
        turn = self.db.execute(stmt).scalar_one_or_none()
        if turn is not None:
            return turn, True
        existing = self.db.execute(
            select(Turn).where(Turn.session_id == session_id, Turn.client_turn_id == client_turn_id)
        ).scalar_one()
        return existing, False

    def find_by_client_id(self, session_id: uuid.UUID, client_turn_id: str) -> Turn | None:
        stmt = select(Turn).where(
            Turn.session_id == session_id, Turn.client_turn_id == client_turn_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_session(self, session_id: uuid.UUID) -> list[Turn]:
        stmt = select(Turn).where(Turn.session_id == session_id).order_by(Turn.id)
        return list(self.db.execute(stmt).scalars())


class EventRepo:
    """Append-only access to `events`. Do not add update/delete methods."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def append(
        self,
        *,
        session_id: uuid.UUID,
        turn_idx: int,
        type: str,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        row = Event(session_id=session_id, turn_idx=turn_idx, type=type, payload=payload or {})
        self.db.add(row)
        self.db.flush()
        return row

    def list_for_session(self, session_id: uuid.UUID) -> list[Event]:
        stmt = select(Event).where(Event.session_id == session_id).order_by(Event.id)
        return list(self.db.execute(stmt).scalars())


class LlmCallRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        purpose: str,
        session_id: uuid.UUID | None = None,
        turn_idx: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_ms: int | None = None,
        ok: bool | None = None,
        error: str | None = None,
        room_id: uuid.UUID | None = None,
        capability: str | None = None,
        prompt_version: str | None = None,
        schema_version: str | None = None,
        validation_status: str | None = None,
        fallback_reason: str | None = None,
        release_id: str | None = None,
    ) -> LlmCall:
        row = LlmCall(
            room_id=room_id,
            capability=capability,
            prompt_version=prompt_version,
            schema_version=schema_version,
            validation_status=validation_status,
            fallback_reason=fallback_reason,
            release_id=release_id,
            purpose=purpose,
            session_id=session_id,
            turn_idx=turn_idx,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            ok=ok,
            error=error,
        )
        self.db.add(row)
        self.db.flush()
        return row
