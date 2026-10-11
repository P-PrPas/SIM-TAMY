from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings
from app.db.session import check_db

router = APIRouter(tags=["System"])


class Health(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    time: datetime
    db: Literal["ok", "error"]
    content_loaded: bool
    cases_loaded: int
    llm_provider: str  # name only, never keys


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health(response: Response) -> Health:
    settings = get_settings()
    cases_dir = settings.content_dir / "cases"
    # ponytail: counts case folders only; the real loader (T-010) replaces this.
    cases = [p for p in cases_dir.iterdir() if p.is_dir()] if cases_dir.is_dir() else []
    db_ok = check_db()
    if not db_ok:
        response.status_code = 503
    return Health(
        status="ok" if db_ok else "down",
        version=__version__,
        time=datetime.now(UTC),
        db="ok" if db_ok else "error",
        content_loaded=bool(cases),
        cases_loaded=len(cases),
        llm_provider=settings.llm_provider,
    )
