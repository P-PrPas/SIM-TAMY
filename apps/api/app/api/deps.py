"""FastAPI dependencies: DB session per request, content store, learner auth."""

import hmac
import re
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.content.loader import ContentStore
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token
from app.db.models import LearnerSession
from app.db.repo import SessionRepo
from app.db.session import get_sessionmaker

_CASE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def get_db() -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on any error."""
    with get_sessionmaker()() as db:
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


@lru_cache
def get_store() -> ContentStore:
    return ContentStore(get_settings().content_dir)


def safe_case_id(case_id: str) -> str:
    """Case ids become folder names: refuse anything that could leave `content/cases`."""
    if not _CASE_ID.fullmatch(case_id):
        raise ApiError("CASE_NOT_AVAILABLE", "case not available")
    return case_id


Db = Annotated[Session, Depends(get_db)]
Store = Annotated[ContentStore, Depends(get_store)]


def learner_session(
    session_id: uuid.UUID, db: Db, authorization: Annotated[str | None, Header()] = None
) -> LearnerSession:
    """The caller's own session (API_DESIGN 3). Another session's token is 404, junk is 401."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError("UNAUTHORIZED", "missing or invalid token")
    digest = hash_token(token.strip())
    repo = SessionRepo(db)
    row = repo.get(session_id)
    if row is not None and hmac.compare_digest(row.token_hash, digest):
        return row
    if repo.token_exists(digest):  # a valid token, but not for this session
        raise ApiError("NOT_FOUND", "session not found")
    raise ApiError("UNAUTHORIZED", "missing or invalid token")


Learner = Annotated[LearnerSession, Depends(learner_session)]
