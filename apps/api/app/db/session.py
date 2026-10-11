from functools import lru_cache

from sqlalchemy import Engine, create_engine, text

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def check_db() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
