"""T-081: the demo class holds real, rescore-able, synthetic sessions; seeding is idempotent."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_store
from app.db.models import ClassRoom, LearnerSession, Report
from app.rescore import rescore
from app.seed_demo import CLASS_CODE, SCENARIOS, seed


def test_seed_creates_a_synthetic_class_and_is_idempotent(
    make_db: Callable[[], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    url = make_db()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.chdir(Path(__file__).resolve().parents[3])  # where alembic.ini is

    first = seed()
    again = seed()

    assert [o.status for o in first] == ["PASS"] * len(SCENARIOS)
    assert again == []  # the class has sessions: nothing more is added
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            room = db.scalar(select(ClassRoom).where(ClassRoom.code == CLASS_CODE))
            assert room is not None and "สังเคราะห์" in (room.name or "")
            rows = list(
                db.scalars(select(LearnerSession).where(LearnerSession.class_id == room.id))
            )
            assert len(rows) == len(SCENARIOS)
            assert all(r.status == "completed" and "สังเคราะห์" in r.learner_name for r in rows)
            assert db.scalar(select(func.count()).select_from(Report)) == len(SCENARIOS)
            assert {r.variant for r in rows} == {"A", "C"}  # a spread of outcomes
            for r in rows:
                assert (
                    rescore(db, get_store(), r.id).diffs == []
                )  # reports are genuine engine output
    finally:
        engine.dispose()
