"""scripts/prestage.py (C04): PASS only when every check holds, FAIL names the broken one."""

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("prestage", ROOT / "scripts" / "prestage.py")
assert _spec and _spec.loader
prestage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prestage)

API, WEB = "https://api.example", "https://web.example"
CORS = "cors preflight (POST + Authorization)"
PREFLIGHT = {
    "access-control-allow-origin": WEB,
    "access-control-allow-methods": "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT",
    "access-control-allow-headers": "authorization,content-type",
}


def healthy(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
    if method == "OPTIONS":
        return 200, PREFLIGHT, None
    body: dict[str, Any] = {
        API + "/health": {"status": "ok", "db": "ok", "llm_provider": "mock", "commit": "abc"},
        API + "/v1/cases": {"items": [{"case_id": "X"}]},
        API + "/v1/family/stories": [{"id": "s"}],
    }
    return (200, {}, body[url]) if url in body else (200, {}, b"<html>")


def test_everything_healthy_passes() -> None:
    results = prestage.run(API, WEB, healthy)

    assert len(results) == 5 and all(ok for _, ok, _ in results)


def test_a_broken_family_endpoint_is_named() -> None:
    def broken(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        if url.endswith("/family/stories"):
            return 500, {}, None
        return healthy(method, url, headers)

    failed = [name for name, ok, _ in prestage.run(API, WEB, broken) if not ok]

    assert failed == ["family stories load"]


def test_an_unreachable_api_fails_without_raising() -> None:
    def down(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        return (200, {}, b"<html>") if url == WEB else (0, {}, None)

    failed = [name for name, ok, _ in prestage.run(API, WEB, down) if not ok]

    assert "api health" in failed and "web reachable" not in failed


def test_a_cors_mismatch_fails() -> None:
    def other_origin(
        method: str, url: str, headers: dict[str, str]
    ) -> tuple[int, dict[str, str], Any]:
        if method == "OPTIONS":
            return 200, {**PREFLIGHT, "access-control-allow-origin": "https://else.example"}, None
        return healthy(method, url, headers)

    failed = [name for name, ok, _ in prestage.run(API, WEB, other_origin) if not ok]

    assert failed == [CORS]


def test_a_rejected_preflight_fails_even_with_a_matching_origin() -> None:
    def rejected(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        return (400, PREFLIGHT, None) if method == "OPTIONS" else healthy(method, url, headers)

    assert [n for n, ok, _ in prestage.run(API, WEB, rejected) if not ok] == [CORS]


def test_a_preflight_that_omits_the_real_request_headers_fails() -> None:
    def partial(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        if method == "OPTIONS":
            return 200, {**PREFLIGHT, "access-control-allow-headers": "content-type"}, None
        return healthy(method, url, headers)

    assert [n for n, ok, _ in prestage.run(API, WEB, partial) if not ok] == [CORS]


def test_a_wildcard_does_not_stand_in_for_authorization() -> None:
    def wildcard(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        if method == "OPTIONS":
            return 204, {**PREFLIGHT, "access-control-allow-headers": "*"}, None
        return healthy(method, url, headers)

    assert [n for n, ok, _ in prestage.run(API, WEB, wildcard) if not ok] == [CORS]


def test_a_wildcard_may_cover_content_type_beside_authorization() -> None:
    def named(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
        if method == "OPTIONS":
            return 200, {**PREFLIGHT, "access-control-allow-headers": "authorization, *"}, None
        return healthy(method, url, headers)

    assert all(ok for _, ok, _ in prestage.run(API, WEB, named))
