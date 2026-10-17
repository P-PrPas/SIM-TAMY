"""The transaction commits before the client gets the response, not after.

FastAPI runs the code after `yield` of a request-scoped dependency once the response has been sent.
`get_db` commits there, so a learner could receive "report_ready" and ask for the report before the
row existed (a 409 REPORT_NOT_READY, seen in CI and in a load run). `Db` must close the dependency
right after the endpoint returns (`scope="function"`).
"""

import asyncio
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI

from app.api.deps import Db, get_db


def test_the_commit_happens_before_the_response_is_sent() -> None:
    events: list[str] = []

    def fake_db() -> Iterator[object]:
        yield object()
        events.append("commit")  # what get_db does after its yield

    app = FastAPI()

    @app.post("/x")
    def endpoint(db: Db) -> dict[str, bool]:
        return {"ok": True}

    app.dependency_overrides[get_db] = fake_db

    async def call() -> None:
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/x",
            "raw_path": b"/x",
            "root_path": "",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1),
            "server": ("127.0.0.1", 80),
        }

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                events.append("response sent")

        await app(scope, receive, send)

    asyncio.run(call())

    assert events == ["commit", "response sent"]
