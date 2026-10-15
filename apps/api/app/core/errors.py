"""Error envelope (API_DESIGN 2.1): `{"error": {code, message, details, request_id}}`.

`message` is English for developers; the web maps `code` to Thai (API_DESIGN 2).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.limits import MAX_TEXT_CHARS
from app.engine.scenario import EngineError

log = logging.getLogger("app.errors")

# HTTP status per code, as declared in docs/openapi.yaml (TURN_LIMIT is 422 there and in the PRD).
STATUS: dict[str, int] = {
    "VALIDATION_ERROR": 422,
    "TEXT_TOO_LONG": 422,
    "TURN_LIMIT": 422,
    "TURN_IN_PROGRESS": 409,
    "SESSION_COMPLETED": 409,
    "SESSION_EXPIRED": 410,
    "INVALID_PHASE": 409,
    "DECISION_ALREADY_COMMITTED": 409,
    "DECISION_OPTION_INVALID": 422,
    "IDEMPOTENCY_CONFLICT": 409,
    "REPORT_NOT_READY": 409,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "GLASSBOX_DISABLED": 403,
    "NOT_FOUND": 404,
    "CASE_NOT_AVAILABLE": 404,
    "VARIANT_NOT_AVAILABLE": 422,
    "CLASS_NOT_FOUND": 404,
    "RATE_LIMITED": 429,
    "LLM_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.details = code, message, details or {}


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def envelope(
    request: Request, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id(request),
        }
    }
    # also set here: errors raised outside the request-id middleware (500) never pass through it
    return JSONResponse(
        body, status_code=STATUS[code], headers={"X-Request-ID": request_id(request)}
    )


def _api_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return envelope(request, exc.code, exc.message, exc.details)


def _engine_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, EngineError)
    return envelope(request, exc.code, str(exc) or exc.code)


def _validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = exc.errors()
    for e in errors:
        if e["loc"][-1:] == ("text",) and e["type"] == "string_too_long":
            actual = len(e.get("input") or "")
            return envelope(
                request,
                "TEXT_TOO_LONG",
                f"text is longer than {MAX_TEXT_CHARS} characters",
                {"max": MAX_TEXT_CHARS, "actual": actual},
            )
    # never echo `input`: it can hold learner free text (AGENTS.md rule 10)
    fields = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in errors]
    return envelope(request, "VALIDATION_ERROR", "request validation failed", {"fields": fields})


def _http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return envelope(request, "NOT_FOUND", "not found")
    if exc.status_code in (401, 403):
        return envelope(request, "UNAUTHORIZED", "unauthorized")
    return envelope(request, "VALIDATION_ERROR", str(exc.detail))


def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error request_id=%s", request_id(request))
    return envelope(request, "INTERNAL_ERROR", "unexpected server error")


def install(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(EngineError, _engine_error)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _unexpected)
