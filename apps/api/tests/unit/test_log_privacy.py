"""T-049: unexpected errors must not leak possible learner input to app logs."""

import io
import logging
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from starlette.requests import Request

from app.core.errors import _unexpected
from app.main import create_app


def test_unexpected_error_log_omits_exception_message_and_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "synthetic-private-marker-9482"
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})

    try:
        raise RuntimeError(marker)
    except RuntimeError as exc:
        response = _unexpected(request, exc)

    assert response.status_code == 500
    assert marker not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_uvicorn_does_not_log_the_message_of_an_unhandled_exception() -> None:
    """Starlette re-raises after the 500 handler; Uvicorn then logs the traceback (real server)."""
    marker = "synthetic-private-marker-7311"
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(marker)

    logged = io.StringIO()
    handler = logging.StreamHandler(logged)
    server_log = logging.getLogger("uvicorn.error")
    server_log.addHandler(handler)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, port=port, log_config=None, log_level="error"))
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        while not server.started:
            time.sleep(0.05)
        assert httpx.get(f"http://127.0.0.1:{port}/boom").status_code == 500
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_log.removeHandler(handler)

    assert "Exception in ASGI application" in logged.getvalue()  # the record is still emitted
    assert "RuntimeError" in logged.getvalue()
    assert marker not in logged.getvalue()
