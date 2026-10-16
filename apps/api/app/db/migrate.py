"""Start-up migration: `python -m app.db.migrate` (T-091, T-094).

Upgrades the database to this image's head, with one exception. After a rollback the previous image
starts on a database a newer release already migrated, and `alembic upgrade head` would stop with
"Can't locate revision" before the API opens. Then we serve without migrating: that is safe only
while migrations stay additive (docs/RUNBOOK-deploy.md section 9).
"""

import sys

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.core.config import get_settings


def migrate(cfg: Config) -> str:
    """'upgraded', or 'ahead' when the database is at a revision this image does not have."""
    known = {r.revision for r in ScriptDirectory.from_config(cfg).walk_revisions()}
    url = cfg.get_main_option("sqlalchemy.url") or get_settings().database_url
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_heads()
    finally:
        engine.dispose()
    unknown = sorted(set(current) - known)
    if unknown:
        print(
            f"database is at revision {', '.join(unknown)}, newer than this image: "
            "serving without migrating (rollback)",
            file=sys.stderr,
        )
        return "ahead"
    command.upgrade(cfg, "head")
    return "upgraded"


if __name__ == "__main__":
    migrate(Config("alembic.ini"))  # relative to the working directory, like the alembic CLI
