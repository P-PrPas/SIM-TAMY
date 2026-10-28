"""FastAPI dependencies: DB session per request, content store, learner auth."""

import hmac
import re
import uuid
from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.ai.llm_client import LLMClient, OnCall, Purpose, get_llm_client
from app.content.institution import DemoAccount
from app.content.loader import ContentStore
from app.core import ratelimit
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token
from app.db.models import LearnerSession
from app.db.repo import SessionRepo
from app.db.session import get_sessionmaker
from app.services import institution
from app.services.patient_voice import Voice

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


def get_voice() -> Voice | None:
    """None selects the production generator once the turn's LLM call sink is available."""
    return None


# scope="function": commit before the response is sent. The default (request scope) runs the code
# after `yield` once the client already has the response, so a follow-up request could miss it.
Db = Annotated[Session, Depends(get_db, scope="function")]
Store = Annotated[ContentStore, Depends(get_store)]
Llm = Annotated[LLMFactory, Depends(get_llm_factory)]
VoiceDep = Annotated[Voice | None, Depends(get_voice)]


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


def turn_rate_limit(request: Request, row: Learner) -> None:
    """10 turns a minute per session (API_DESIGN 8); HardeningMiddleware adds the headers."""
    limit = get_settings().rate_limit_per_min
    if not limit:
        return
    allowed, remaining, retry_after = ratelimit.hit(row.id, limit)
    request.state.rate_limit = (limit, remaining)
    if not allowed:
        raise ApiError(
            "RATE_LIMITED",
            "too many requests",
            {"retry_after_s": retry_after},
            {"Retry-After": str(retry_after)},
        )


def require_instructor_secret(
    x_instructor_secret: Annotated[str | None, Header(alias="X-Instructor-Secret")] = None,
) -> None:
    """Shared instructor secret is server-side only; never echo it in errors or logs."""
    configured = get_settings().instructor_secret
    if configured is None or not x_instructor_secret:
        raise ApiError("UNAUTHORIZED", "instructor secret required")
    if not hmac.compare_digest(
        x_instructor_secret.encode(), configured.get_secret_value().encode()
    ):
        raise ApiError("FORBIDDEN", "invalid instructor secret")


Instructor = Annotated[None, Depends(require_instructor_secret)]


def reader_session(
    session_id: uuid.UUID,
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
    x_instructor_secret: Annotated[str | None, Header(alias="X-Instructor-Secret")] = None,
) -> LearnerSession:
    """Read-only session routes allow its learner or a valid instructor (API_DESIGN 3)."""
    if x_instructor_secret is None:
        return learner_session(session_id, db, authorization)
    require_instructor_secret(x_instructor_secret)
    row = SessionRepo(db).get(session_id)
    if row is None:
        raise ApiError("NOT_FOUND", "session not found")
    return row


Reader = Annotated[LearnerSession, Depends(reader_session)]


def glassbox_caller(
    session_id: uuid.UUID,
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
    x_instructor_secret: Annotated[str | None, Header(alias="X-Instructor-Secret")] = None,
) -> tuple[LearnerSession, bool]:
    """The session plus whether the caller is an instructor (the live Glass Box gate)."""
    row = reader_session(session_id, db, authorization, x_instructor_secret)
    return row, x_instructor_secret is not None


GlassboxCaller = Annotated[tuple[LearnerSession, bool], Depends(glassbox_caller)]


def demo_account(
    x_demo_account: Annotated[str | None, Header(alias="X-Demo-Account")] = None,
) -> DemoAccount:
    """Mock identity (ADR-15 prototype): the picked account id is trusted, never authenticated."""
    account = institution.find_account(x_demo_account)
    if account is None:
        raise ApiError("UNAUTHORIZED", "pick a demo account (X-Demo-Account)")
    return account


Demo = Annotated[DemoAccount, Depends(demo_account)]
