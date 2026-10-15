from fastapi import APIRouter, Response

from app.api.deps import Db, Learner, Store
from app.api.v1.schemas import CreateSessionRequest, CreateSessionResponse, SessionView
from app.services import sessions

router = APIRouter(prefix="/v1", tags=["Sessions"])


@router.post(
    "/sessions", status_code=201, response_model=CreateSessionResponse, operation_id="createSession"
)
def create_session(
    body: CreateSessionRequest, response: Response, db: Db, store: Store
) -> CreateSessionResponse:
    created = sessions.create_session(db, store, body)
    response.headers["Location"] = f"/v1/sessions/{created.session_id}"
    return created


@router.get("/sessions/{session_id}", response_model=SessionView, operation_id="getSession")
def get_session(row: Learner, db: Db, store: Store) -> SessionView:
    sessions.ensure_alive(db, row)
    return sessions.view_session(db, store, row)
