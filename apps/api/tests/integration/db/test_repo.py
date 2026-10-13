import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import LearnerSession
from app.db.repo import EventRepo, LlmCallRepo, SessionRepo, StaleStateError, TurnRepo


def _new_session(db: Session, **over: Any) -> LearnerSession:
    args: dict[str, Any] = {
        "case_id": "DEV-001",
        "case_version": "0.1",
        "case_hash": "abc123",
        "variant": "A",
        "learner_name": "nick",
        "token_hash": "hash-only",
        "state": {"phase": "INTERVIEW", "turn_idx": 0},
    }
    return SessionRepo(db).create(**{**args, **over})


def test_create_session_defaults(db: Session) -> None:
    s = _new_session(db)
    db.refresh(s)
    assert s.status == "active" and s.state_version == 0
    assert s.started_at is not None and s.ended_at is None


def test_save_state_bumps_version_and_rejects_stale(db: Session) -> None:
    s = _new_session(db)
    repo = SessionRepo(db)

    assert repo.save_state(s.id, {"phase": "DECISION"}, expected_version=0) == 1
    assert repo.save_state(s.id, {"phase": "CLOSING"}, expected_version=1) == 2

    with pytest.raises(StaleStateError):
        repo.save_state(s.id, {"phase": "X"}, expected_version=1)  # already moved on

    got = repo.get(s.id)
    assert got is not None
    db.refresh(got)
    assert got.state == {"phase": "CLOSING"} and got.state_version == 2


def test_get_missing_session_is_none(db: Session) -> None:
    assert SessionRepo(db).get(uuid.uuid4()) is None


def test_turn_add_is_idempotent_on_client_turn_id(db: Session) -> None:
    s = _new_session(db)
    turns = TurnRepo(db)

    first, created1 = turns.add(
        session_id=s.id, idx=1, speaker="learner", text="hi", client_turn_id="c1"
    )
    again, created2 = turns.add(
        session_id=s.id, idx=1, speaker="learner", text="hi", client_turn_id="c1"
    )

    assert created1 is True and created2 is False
    assert again.id == first.id
    assert len(turns.list_for_session(s.id)) == 1


def test_turns_without_client_turn_id_do_not_collide(db: Session) -> None:
    s = _new_session(db)
    turns = TurnRepo(db)
    turns.add(session_id=s.id, idx=1, speaker="patient", text="a")
    turns.add(session_id=s.id, idx=1, speaker="system", text="b")
    assert len(turns.list_for_session(s.id)) == 2


def test_events_append_and_read_in_order(db: Session) -> None:
    s = _new_session(db)
    events = EventRepo(db)
    events.append(session_id=s.id, turn_idx=0, type="SESSION_STARTED")
    events.append(session_id=s.id, turn_idx=1, type="LEARNER_MESSAGE", payload={"n": 1})

    got = events.list_for_session(s.id)
    assert [e.type for e in got] == ["SESSION_STARTED", "LEARNER_MESSAGE"]
    assert got[0].payload == {} and got[1].payload == {"n": 1}


def test_llm_call_is_recorded(db: Session) -> None:
    row = LlmCallRepo(db).record(
        purpose="interpreter", provider="mock", model="m", latency_ms=12, ok=True
    )
    assert row.id is not None and row.ok is True


def test_deleting_a_session_cascades_to_children(db: Session) -> None:
    s = _new_session(db)
    TurnRepo(db).add(session_id=s.id, idx=1, speaker="learner", text="hi")
    EventRepo(db).append(session_id=s.id, turn_idx=1, type="LEARNER_MESSAGE")

    db.execute(text("DELETE FROM sessions WHERE id = :id"), {"id": s.id})  # retention purge path

    for table in ("turns", "events"):
        n = db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        assert n == 0


def test_turn_speaker_check_constraint(db: Session) -> None:
    s = _new_session(db)
    with pytest.raises(IntegrityError):
        TurnRepo(db).add(session_id=s.id, idx=1, speaker="alien", text="x")


def test_session_status_check_constraint(db: Session) -> None:
    s = _new_session(db)
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE sessions SET status = 'bogus' WHERE id = :id"), {"id": s.id})
