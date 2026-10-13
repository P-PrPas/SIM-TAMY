"""Integration fixtures: a throwaway Postgres database built by the real migrations.

Needs a reachable server (DATABASE_URL, default from settings). Locally the tests skip when it
is down (`docker compose up -d db`); in CI (CI=true) a missing server is a hard failure.
"""

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings

API_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(url: str) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _server_url() -> URL:
    return make_url(os.environ.get("DATABASE_URL") or get_settings().database_url)


@pytest.fixture
def alembic_config() -> Callable[[str], Config]:
    return _alembic_config


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    engine = create_engine(
        _server_url(), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 3}
    )
    try:
        engine.connect().close()
    except OperationalError as exc:
        if os.environ.get("CI"):
            pytest.fail(f"Postgres required in CI but unreachable: {exc.__class__.__name__}")
        pytest.skip("Postgres not reachable (run `docker compose up -d db`)")
    yield engine
    engine.dispose()


@pytest.fixture
def make_db(admin_engine: Engine) -> Iterator[object]:
    """Factory for empty throwaway databases; all are dropped at teardown."""
    created: list[str] = []

    def _make() -> str:
        name = f"simtamy_test_{uuid.uuid4().hex[:12]}"
        with admin_engine.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
        created.append(name)
        return admin_engine.url.set(database=name).render_as_string(hide_password=False)

    yield _make
    with admin_engine.connect() as conn:
        for name in created:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(scope="session")
def migrated_db_url(admin_engine: Engine) -> Iterator[str]:
    """One database migrated to head, shared by the repo tests (each test rolls back)."""
    name = f"simtamy_test_{uuid.uuid4().hex[:12]}"
    with admin_engine.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    url = admin_engine.url.set(database=name).render_as_string(hide_password=False)
    command.upgrade(_alembic_config(url), "head")
    yield url
    with admin_engine.connect() as conn:
        conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def db(migrated_db_url: str) -> Iterator[Session]:
    engine = create_engine(migrated_db_url)
    conn = engine.connect()
    outer = conn.begin()
    session = Session(conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    conn.close()
    engine.dispose()
