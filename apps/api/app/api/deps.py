"""FastAPI dependencies: DB session per request, content store, learner auth."""

import hmac
import re
import uuid
from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.ai.llm_client import LLMClient, OnCall, Purpose, get_llm_client
from app.content.loader import ContentStore
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token
from app.db.models import LearnerSession
from app.db.repo import SessionRepo
from app.db.session import get_sessionmaker
from app.services.patient_voice import CannedGenerator, FloorValidator, Voice

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


LLMFactory = Callable[[Purpose, OnCall], LLMClient]


def get_llm_factory() -> LLMFactory:
    """Tests override this to script the mock provider."""
    return lambda purpose, on_call: get_llm_client(purpose, on_call=on_call)


def get_voice() -> Voice:
    """T-033/T-034 swap in the LLM generator and the full validator here."""
    return Voice(CannedGenerator(), FloorValidator())


Db = Annotated[Session, Depends(get_db)]
Store = Annotated[ContentStore, Depends(get_store)]
Llm = Annotated[LLMFactory, Depends(get_llm_factory)]
VoiceDep = Annotated[Voice, Depends(get_voice)]


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


def glassbox_caller(
    session_id: uuid.UUID,
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
    x_instructor_secret: Annotated[str | None, Header()] = None,
) -> tuple[LearnerSession, bool]:
    """The session plus whether the caller is an instructor (shared secret, API_DESIGN 3)."""
    if x_instructor_secret is None:
        return learner_session(session_id, db, authorization), False
    secret = get_settings().instructor_secret
    given = x_instructor_secret.encode()
    if secret is None or not hmac.compare_digest(given, secret.get_secret_value().encode()):
        raise ApiError("UNAUTHORIZED", "missing or invalid token")
    row = SessionRepo(db).get(session_id)
    if row is None:
        raise ApiError("NOT_FOUND", "session not found")
    return row, True


GlassboxCaller = Annotated[tuple[LearnerSession, bool], Depends(glassbox_caller)]
