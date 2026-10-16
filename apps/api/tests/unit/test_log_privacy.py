"""T-049: unexpected errors must not leak possible learner input to app logs."""

import pytest
from starlette.requests import Request

from app.core.errors import _unexpected


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
