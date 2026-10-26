"""T-081: the demo class holds real, rescore-able, synthetic sessions; seeding is idempotent."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import seed_demo
from app.api.deps import get_store
from app.core.config import get_settings
from app.db.models import ClassRoom, LearnerSession, Report
from app.rescore import rescore
from app.seed_demo import CLASS_CODE, SCENARIOS, main, seed

REPO = Path(__file__).resolve().parents[5]


@pytest.fixture
def database(make_db: Callable[[], str], monkeypatch: pytest.MonkeyPatch) -> str:
    url = make_db()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CONTENT_DIR", str(REPO / "content"))
    get_settings.cache_clear()
    get_store.cache_clear()
    monkeypatch.chdir(Path(__file__).resolve().parents[3])  # where alembic.ini is
    return url


def sessions_of(url: str) -> list[tuple[str, str]]:
    """(learner name, status) of every session in the demo class."""
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            room = db.scalar(select(ClassRoom).where(ClassRoom.code == CLASS_CODE))
            assert room is not None
            rows = db.scalars(select(LearnerSession).where(LearnerSession.class_id == room.id))
            return sorted((r.learner_name, r.status) for r in rows)
    finally:
        engine.dispose()


def test_seed_creates_a_synthetic_class_and_is_idempotent(database: str) -> None:
    labels: dict[str, Any] = yaml.safe_load(
        (REPO / "content" / "demo" / "demo_class_th.yaml").read_text(encoding="utf-8")
    )

    first = seed()
    again = seed()

    assert [o.status for o in first] == ["PASS"] * len(SCENARIOS)
    assert again == []  # the class is complete: nothing more is added
    engine = create_engine(database)
    try:
        with Session(engine) as db:
            room = db.scalar(select(ClassRoom).where(ClassRoom.code == CLASS_CODE))
            assert room is not None and room.name == labels["class_name_th"]
            rows = list(
                db.scalars(select(LearnerSession).where(LearnerSession.class_id == room.id))
            )
            expected = [labels["learner_name_template_th"].format(n=n) for n in (1, 2, 3, 4, 5)]
            assert sorted(r.learner_name for r in rows) == sorted(expected)
            assert all(r.status == "completed" for r in rows)
            assert db.scalar(select(func.count()).select_from(Report)) == len(SCENARIOS)
            assert {r.variant for r in rows} == {"A", "C"}  # a spread of outcomes
            for r in rows:
                assert rescore(db, get_store(), r.id).diffs == []  # genuine engine output
    finally:
        engine.dispose()


def test_a_run_that_stops_midway_is_completed_by_the_next(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = seed_demo.run_golden
    calls: list[str] = []

    def dies_on_the_third(g: Any, env: Any, session: Any = None) -> Any:
        calls.append(g.id)
        if len(calls) == 3:
            raise RuntimeError("the machine went to sleep")
        return real(g, env, session)

    monkeypatch.setattr(seed_demo, "run_golden", dies_on_the_third)
    with pytest.raises(RuntimeError):
        seed()
    assert len(sessions_of(database)) == 2  # two scenarios made it

    monkeypatch.setattr(seed_demo, "run_golden", real)
    rest = seed()

    assert [o.id for o in rest] == list(SCENARIOS[2:])  # only the three that were missing
    done = sessions_of(database)
    assert len(done) == len(SCENARIOS) and {status for _, status in done} == {"completed"}
    assert len({name for name, _ in done}) == len(SCENARIOS)  # nobody twice


def test_an_unfinished_session_does_not_count_as_seeded(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = seed_demo.run_golden
    calls: list[str] = []

    def stops_before_complete(g: Any, env: Any, session: Any = None) -> Any:
        calls.append(g.id)
        if len(calls) == 2:  # the second scenario is cut short: its session stays active
            g = g.model_copy(update={"steps": g.steps[:2]})
        return real(g, env, session)

    monkeypatch.setattr(seed_demo, "run_golden", stops_before_complete)
    seed()
    assert sorted(status for _, status in sessions_of(database)).count("active") == 1

    monkeypatch.setattr(seed_demo, "run_golden", real)
    again = seed()

    assert [o.id for o in again] == [SCENARIOS[1]]  # only the one that never finished
    final = sessions_of(database)
    assert sorted(name for name, status in final if status == "completed") == sorted(
        {name for name, _ in final}
    )  # every name has a completed session
    assert [status for _, status in final].count("completed") == len(SCENARIOS)


def test_no_database_is_a_quiet_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://sim:topsecret@127.0.0.1:1/simtamy")

    assert main() == 2

    err = capsys.readouterr().err
    assert "not reachable" in err and "topsecret" not in err


def test_reset_refuses_without_the_demo_flag_and_deletes_nothing(
    database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seed()
    monkeypatch.delenv("SIMTAMY_DEMO_DB", raising=False)

    assert main(["--reset"]) == 3

    assert "SIMTAMY_DEMO_DB=1" in capsys.readouterr().err
    assert len(sessions_of(database)) == len(SCENARIOS)


def test_reset_replaces_only_the_demo_class(database: str, monkeypatch: pytest.MonkeyPatch) -> None:
    seed()
    engine = create_engine(database)
    try:
        with Session(engine) as db, db.begin():
            db.add(ClassRoom(code="REAL01", name="not demo"))
            old_ids = set(db.scalars(select(LearnerSession.id)))
        monkeypatch.setenv("SIMTAMY_DEMO_DB", "1")

        assert main(["--reset"]) == 0

        with Session(engine) as db:
            assert db.scalar(select(ClassRoom).where(ClassRoom.code == "REAL01")) is not None
            new_ids = set(db.scalars(select(LearnerSession.id)))
            assert len(new_ids) == len(SCENARIOS) and not new_ids & old_ids  # re-seeded
    finally:
        engine.dispose()
