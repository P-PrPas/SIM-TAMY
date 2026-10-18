from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.db import family  # noqa: F401 - register family tables with migration metadata
from app.db.models import Base

target_metadata = Base.metadata

# Tests override sqlalchemy.url to point at a throwaway database.
url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with create_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
