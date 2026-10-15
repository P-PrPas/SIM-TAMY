from fastapi import APIRouter, Response

from app.api.deps import Db, Learner, Llm, Reader, Store, VoiceDep
from app.api.v1.schemas import (
    CompleteRequest,
    CompleteResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    DecisionRequest,
    DecisionResponse,
    ReportResponse,
    SessionView,
    TurnRequest,
    TurnResponse,
)
from app.services import closing, sessions, turns

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
def get_session(row: Reader, db: Db, store: Store) -> SessionView:
    sessions.ensure_alive(db, row)
    return sessions.view_session(db, store, row)


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse, operation_id="sendTurn")
def send_turn(
    body: TurnRequest,
    response: Response,
    row: Learner,
    db: Db,
    store: Store,
    llm: Llm,
    voice: VoiceDep,
    stream: bool = False,  # accepted for the contract; SSE (T-042) is not built, JSON is returned
) -> TurnResponse:
    outcome = turns.send_turn(db, store, llm, voice, row, body)
    if outcome.replayed:
        response.headers["Idempotent-Replay"] = "true"
    return outcome.response


@router.post(
    "/sessions/{session_id}/decision",
    response_model=DecisionResponse,
    operation_id="commitDecision",
)
def commit_decision(body: DecisionRequest, row: Learner, db: Db, store: Store) -> DecisionResponse:
    return closing.commit(db, store, row, body)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=CompleteResponse,
    operation_id="completeSession",
)
def complete_session(
    row: Learner, db: Db, store: Store, body: CompleteRequest | None = None
) -> CompleteResponse:
    return closing.complete(db, store, row, body or CompleteRequest())


@router.get(
    "/sessions/{session_id}/report", response_model=ReportResponse, operation_id="getReport"
)
def get_report(row: Reader, db: Db, store: Store) -> ReportResponse:
    return closing.report(db, store, row)
