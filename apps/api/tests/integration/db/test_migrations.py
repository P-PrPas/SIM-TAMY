from collections.abc import Callable

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.db.models import Base

EXPECTED_TABLES = {
    "classes",
    "sessions",
    "turns",
    "events",
    "llm_calls",
    "reports",
    "score_overrides",
}


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_then_downgrade_cleanly(
    make_db: Callable[[], str], alembic_config: Callable[[str], Config]
) -> None:
    url = make_db()
    cfg = alembic_config(url)

    command.upgrade(cfg, "head")
    assert _tables(url) == EXPECTED_TABLES

    command.downgrade(cfg, "base")
    assert _tables(url) == set()

    command.upgrade(cfg, "head")  # and back up again
    assert _tables(url) == EXPECTED_TABLES


def test_models_and_migration_do_not_drift(migrated_db_url: str) -> None:
    engine = create_engine(migrated_db_url)
    try:
        with engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    assert diffs == []
