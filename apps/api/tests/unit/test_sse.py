"""SSE emits only fully accepted, committed TurnResponse text (T-042)."""

import json
from typing import Any

from fastapi import Response
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_llm_factory, get_store, get_voice, learner_session
from app.api.v1 import sessions as route
from app.api.v1.schemas import Phase, Reply, TurnRequest, TurnResponse
from app.main import create_app
from app.services.turns import Outcome


def turn_response(text: str) -> TurnResponse:
    return TurnResponse(
        turn_idx=1,
        replies=[Reply(speaker="patient", text=text)],
        phase=Phase.INTERVIEW,
        clarification=False,
        turns_remaining=39,
        degraded=False,
    )


def test_sse_frames_chunk_accepted_reply_then_send_full_done() -> None:
    result = turn_response("x" * 170)

    frames = list(route.sse_frames(result))

    deltas = [json.loads(frame.split("data: ", 1)[1]) for frame in frames[:-1]]
    done = json.loads(frames[-1].split("data: ", 1)[1])
    assert all(frame.startswith("event: delta\n") for frame in frames[:-1])
    assert [delta["seq"] for delta in deltas] == list(range(len(deltas)))
    assert "".join(delta["text"] for delta in deltas) == "x" * 170
    assert all(delta["speaker"] == "patient" for delta in deltas)
    assert frames[-1].startswith("event: done\n")
    assert done == result.model_dump(mode="json")


def test_sse_json_escapes_embedded_newlines() -> None:
    frames = list(route.sse_frames(turn_response("line 1\nevent: injected")))

    assert "\nevent: injected" not in "".join(frames)
    assert json.loads(frames[0].split("data: ", 1)[1])["text"].startswith("line 1")


def test_stream_handler_commits_before_returning_any_sse(
    monkeypatch: Any,
) -> None:
    class Db:
        committed = False

        def commit(self) -> None:
            self.committed = True

    db = Db()
    result = turn_response("accepted")
    monkeypatch.setattr(route.turns, "send_turn", lambda *args: Outcome(result, True))

    response = route.send_turn(
        TurnRequest(text="question"),
        Response(),
        object(),  # type: ignore[arg-type]
        db,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        lambda *args: None,  # type: ignore[arg-type]
        None,
        stream=True,
    )

    assert isinstance(response, StreamingResponse)
    assert db.committed is True
    assert response.media_type == "text/event-stream"
    assert response.headers["Idempotent-Replay"] == "true"


def test_accept_header_also_selects_sse(monkeypatch: Any) -> None:
    result = turn_response("accepted")
    monkeypatch.setattr(route.turns, "send_turn", lambda *args: Outcome(result, False))

    class Db:
        def commit(self) -> None:
            pass

    response = route.send_turn(
        TurnRequest(text="question"),
        Response(),
        object(),  # type: ignore[arg-type]
        Db(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        lambda *args: None,  # type: ignore[arg-type]
        None,
        accept="text/event-stream",
    )

    assert isinstance(response, StreamingResponse)


def test_http_stream_is_sse_and_never_starts_when_commit_fails(monkeypatch: Any) -> None:
    result = turn_response("accepted")
    monkeypatch.setattr(route.turns, "send_turn", lambda *args: Outcome(result, False))

    class Db:
        fail = False

        def commit(self) -> None:
            if self.fail:
                raise RuntimeError("commit failed")

    db = Db()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[learner_session] = lambda: object()
    app.dependency_overrides[get_store] = lambda: object()
    app.dependency_overrides[get_llm_factory] = lambda: object()
    app.dependency_overrides[get_voice] = lambda: None
    client = TestClient(app, raise_server_exceptions=False)
    url = "/v1/sessions/00000000-0000-0000-0000-000000000001/turns?stream=true"

    streamed = client.post(url, json={"text": "question"})
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")
    assert "event: delta\n" in streamed.text and "event: done\n" in streamed.text

    db.fail = True
    failed = client.post(url, json={"text": "question"})
    assert failed.status_code == 500
    assert "event: delta" not in failed.text
