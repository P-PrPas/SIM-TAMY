"""T-094: an image started after a rollback must not die on a database that is ahead of it."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine, inspect, text

from app.db.migrate import migrate

API_DIR = Path(__file__).resolve().parents[3]
FUTURE = '''"""a release newer than the image under test"""

import sqlalchemy as sa
from alembic import op

revision = "0099"
down_revision = "{parent}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("future_things", sa.Column("id", sa.Integer, primary_key=True))


def downgrade() -> None:
    op.drop_table("future_things")
'''


def config(location: Path, url: str) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(location))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def revision_of(url: str) -> str:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return str(conn.execute(text("select version_num from alembic_version")).scalar())
    finally:
        engine.dispose()


def test_a_database_ahead_of_the_image_is_served_not_migrated(
    make_db: Callable[[], str], tmp_path: Path
) -> None:
    url = make_db()
    old = config(API_DIR / "migrations", url)
    head = ScriptDirectory.from_config(old).get_current_head()
    newer_dir = tmp_path / "migrations"
    shutil.copytree(API_DIR / "migrations", newer_dir, ignore=shutil.ignore_patterns("__pycache__"))
    (newer_dir / "versions" / "0099_future.py").write_text(
        FUTURE.format(parent=head), encoding="utf-8"
    )
    newer = config(newer_dir, url)

    assert migrate(old) == "upgraded" and revision_of(url) == head  # empty database, old image
    assert migrate(newer) == "upgraded" and revision_of(url) == "0099"  # the newer release

    with pytest.raises(CommandError, match="Can't locate revision"):
        command.upgrade(old, "head")  # what the image used to do after a rollback

    assert migrate(old) == "ahead"  # the rolled-back image now starts
    assert revision_of(url) == "0099"  # and leaves the newer schema alone
    engine = create_engine(url)
    try:
        assert "future_things" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_an_older_database_is_still_upgraded(make_db: Callable[[], str]) -> None:
    url = make_db()
    cfg = config(API_DIR / "migrations", url)

    assert migrate(cfg) == "upgraded"
    assert migrate(cfg) == "upgraded"  # idempotent: a restart is safe
    assert revision_of(url) == ScriptDirectory.from_config(cfg).get_current_head()


def test_future_fixture_extends_the_current_image_head(tmp_path: Path) -> None:
    old = config(API_DIR / "migrations", "postgresql://unused")
    head = ScriptDirectory.from_config(old).get_current_head()
    newer_dir = tmp_path / "migrations"
    shutil.copytree(API_DIR / "migrations", newer_dir, ignore=shutil.ignore_patterns("__pycache__"))
    (newer_dir / "versions" / "0099_future.py").write_text(
        FUTURE.format(parent=head), encoding="utf-8"
    )
    assert ScriptDirectory.from_config(config(newer_dir, "postgresql://unused")).get_heads() == [
        "0099"
    ]
