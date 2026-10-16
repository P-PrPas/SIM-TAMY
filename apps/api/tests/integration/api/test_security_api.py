"""T-048: rate limit, security headers, request size, control characters, CORS."""

import pytest
from fastapi.testclient import TestClient

from app.core import limits, ratelimit
from app.core.config import get_settings
from app.main import create_app
from tests.integration.api.conftest import Api
from tests.integration.api.test_turns_api import state_of, turn

HELLO = "สวัสดีค่ะ"


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """A fake clock (one list cell) and a limit of 10, the production default."""
    t = [1000.0]
    monkeypatch.setattr(ratelimit, "now", lambda: t[0])
    ratelimit._hits.clear()
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "10")
    get_settings.cache_clear()
    return t


def test_the_eleventh_turn_in_a_minute_is_refused_with_the_standard_envelope(
    api: Api, clock: list[float]
) -> None:
    created = api.create()
    first = [turn(api, created, HELLO) for _ in range(10)]

    r = turn(api, created, HELLO)

    assert [x.status_code for x in first] == [200] * 10
    assert first[0].headers["X-RateLimit-Limit"] == "10"
    assert [x.headers["X-RateLimit-Remaining"] for x in (first[0], first[9])] == ["9", "0"]
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED" and r.json()["error"]["request_id"]
    assert r.json()["error"]["details"]["retry_after_s"] == int(r.headers["Retry-After"]) == 61
    assert (r.headers["X-RateLimit-Limit"], r.headers["X-RateLimit-Remaining"]) == ("10", "0")
    assert state_of(api, created)["turn_idx"] == 10  # the refused request did nothing


def test_the_window_slides_and_other_sessions_are_not_affected(
    api: Api, clock: list[float]
) -> None:
    created, other = api.create(), api.create()
    for _ in range(10):
        turn(api, created, HELLO)
    assert turn(api, created, HELLO).status_code == 429

    assert turn(api, other, HELLO).status_code == 200
    clock[0] += 61
    assert turn(api, created, HELLO).status_code == 200


def test_security_headers_ride_on_success_and_error_responses(api: Api) -> None:
    created = api.create()
    ok = turn(api, created, HELLO)
    missing = api.client.get("/v1/sessions/00000000-0000-0000-0000-000000000000")

    for r in (ok, missing):
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "no-referrer"
        assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert "Content-Security-Policy" not in api.client.get("/docs").headers  # Swagger needs scripts


def test_an_oversized_body_is_refused_before_it_is_read(api: Api) -> None:
    created = api.create()

    r = api.client.post(
        f"/v1/sessions/{created['session_id']}/turns",
        content=b"{" + b" " * limits.MAX_BODY_BYTES + b"}",
        headers={**api.headers(created), "Content-Type": "application/json"},
    )

    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["request_id"] and r.headers["X-Content-Type-Options"] == "nosniff"


def test_control_characters_are_dropped_before_the_database_sees_them(api: Api) -> None:
    created = api.create()

    r = turn(api, created, "สวัสดี\x00\x07ค่ะ\n")
    only_controls = turn(api, created, "\x00\x01\x1f")

    assert r.status_code == 200
    assert only_controls.status_code == 422
    assert only_controls.json()["error"]["code"] == "VALIDATION_ERROR"
    with api.db() as db:
        from sqlalchemy import select

        from app.db.models import Turn

        texts = [t.text for t in db.scalars(select(Turn).where(Turn.speaker == "learner"))]
    assert texts == ["สวัสดีค่ะ"]


def test_a_request_from_a_non_allowed_origin_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://sim-tamy.vercel.app")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        evil = {"Origin": "https://evil.example"}

        preflight = client.options(
            "/health", headers={**evil, "Access-Control-Request-Method": "GET"}
        )
        simple = client.get("/health", headers=evil)

        assert preflight.status_code == 400
        assert "access-control-allow-origin" not in preflight.headers
        assert "access-control-allow-origin" not in simple.headers
    finally:
        get_settings.cache_clear()


def test_security_headers_also_ride_on_an_unhandled_500(api: Api) -> None:
    def boom() -> None:
        raise RuntimeError("secret learner text must not leak")

    api.client.app.add_api_route("/boom", boom)  # type: ignore[attr-defined]

    r = api.client.get("/boom")

    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret" not in r.text
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Request-ID"]
