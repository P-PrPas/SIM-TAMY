import json
import unicodedata
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Header, Response
from fastapi.responses import StreamingResponse

from app.api.deps import Db, Learner, Llm, Store, VoiceDep
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
_CHUNK_CHARS = 80


def _chunks(text: str) -> Iterator[str]:
    """Split accepted text without starting a chunk on a combining mark."""
    start = 0
    while start < len(text):
        end = min(start + _CHUNK_CHARS, len(text))
        while end < len(text) and unicodedata.combining(text[end]):
            end += 1
        yield text[start:end]
        start = end


def _frame(event: str, data: dict[str, object]) -> str:
    # JSON escapes embedded newlines, so patient text cannot inject an SSE frame.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def sse_frames(result: TurnResponse) -> Iterator[str]:
    """Called only after the full turn is validated and committed."""
    seq = 0
    for reply in result.replies:
        for chunk in _chunks(reply.text):
            yield _frame("delta", {"seq": seq, "speaker": reply.speaker, "text": chunk})
            seq += 1
    yield _frame("done", result.model_dump(mode="json"))


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


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse, operation_id="sendTurn")
def send_turn(
    body: TurnRequest,
    response: Response,
    row: Learner,
    db: Db,
    store: Store,
    llm: Llm,
    voice: VoiceDep,
    stream: bool = False,
    accept: Annotated[str | None, Header()] = None,
) -> TurnResponse | StreamingResponse:
    outcome = turns.send_turn(db, store, llm, voice, row, body)
    if stream or (accept is not None and "text/event-stream" in accept.lower()):
        # A StreamingResponse is sent after yield dependencies unwind, so explicitly commit here.
        # No event, including the first delta, can escape before persistence succeeds.
        db.commit()
        headers = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
        if outcome.replayed:
            headers["Idempotent-Replay"] = "true"
        return StreamingResponse(
            sse_frames(outcome.response), media_type="text/event-stream", headers=headers
        )
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
def get_report(row: Learner, db: Db, store: Store) -> ReportResponse:
    return closing.report(db, store, row)
