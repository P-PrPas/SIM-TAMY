"""Sensitive family responses must never be cached, including errors."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.request_id import RequestIdMiddleware


@pytest.mark.parametrize(
    "path",
    [
        "/v1/family/rooms",
        "/v1/family/rooms/test",
        "/v1/family/rooms/test/join",
        "/v1/family/rooms/test/decisions",
    ],
)
@pytest.mark.parametrize("status", [200, 201, 401, 422])
def test_family_responses_are_no_store(path: str, status: int) -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    def response(path: str) -> JSONResponse:
        return JSONResponse({"synthetic": True}, status_code=status)

    result = TestClient(app).post(path)
    assert result.status_code == status
    assert result.headers.get("Cache-Control") == "no-store"
    assert result.headers["X-Request-ID"]
