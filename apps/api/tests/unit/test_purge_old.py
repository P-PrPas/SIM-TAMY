"""T-049 query safety checks independent of a running Postgres server."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.purge_old import purge_expired


def _sql(statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]


def test_purge_selects_old_finished_or_abandoned_active_sessions() -> None:
    db = MagicMock()
    db.scalars.return_value = []

    assert purge_expired(db, retention_days=30, now=datetime(2026, 10, 16, tzinfo=UTC)) == 0

    statement = db.scalars.call_args.args[0]
    sql = _sql(statement)
    assert "sessions.status IN" in sql
    assert "sessions.ended_at <" in sql
    assert "sessions.status =" in sql
    assert "sessions.last_activity_at <" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    params = list(statement.compile(dialect=postgresql.dialect()).params.values())
    assert any(
        isinstance(value, (list, tuple)) and set(value) == {"completed", "expired"}
        for value in params
    )
    assert "active" in params
    assert params.count(datetime(2026, 9, 16, tzinfo=UTC)) == 2
    db.execute.assert_not_called()


def test_purge_deletes_unlinked_metadata_then_eligible_parent_not_events_directly() -> None:
    db = MagicMock()
    session_id = uuid.uuid4()
    db.scalars.return_value = [session_id]
    db.execute.return_value.scalars.return_value.all.return_value = [session_id]

    assert purge_expired(db, retention_days=30, now=datetime(2026, 10, 16, tzinfo=UTC)) == 1

    statements = [_sql(call.args[0]) for call in db.execute.call_args_list]
    assert len(statements) == 3
    assert statements[0].startswith("DELETE FROM llm_calls")
    assert statements[1].startswith("DELETE FROM score_overrides")
    assert statements[2].startswith("DELETE FROM sessions")
    assert "sessions.status IN" in statements[2] and "sessions.ended_at <" in statements[2]
    assert "sessions.last_activity_at <" in statements[2]
    assert not any("DELETE FROM events" in statement for statement in statements)


@pytest.mark.parametrize("days", [0, -1])
def test_purge_rejects_nonpositive_retention(days: int) -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="positive"):
        purge_expired(db, retention_days=days, now=datetime(2026, 10, 16, tzinfo=UTC))
    db.scalars.assert_not_called()


def test_purge_rejects_naive_clock() -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="timezone-aware"):
        purge_expired(db, retention_days=30, now=datetime(2026, 10, 16))
    db.scalars.assert_not_called()
