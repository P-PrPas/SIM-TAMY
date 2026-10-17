from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import cases, health, instructor, pilot, replay, sessions
from app.core import errors
from app.core.config import get_settings
from app.core.hardening import HardeningMiddleware
from app.core.request_id import RequestIdMiddleware


def _openapi_without_default_422(app: FastAPI) -> dict[str, Any]:
    """FastAPI documents its own 422 body; ours is the `Error` envelope, which the spec declares."""
    if app.openapi_schema is None:
        schema = FastAPI.openapi(app)
        for item in schema["paths"].values():
            for op in item.values():
                op.get("responses", {}).pop("422", None)
        for name in ("HTTPValidationError", "ValidationError"):
            schema.get("components", {}).get("schemas", {}).pop(name, None)
        app.openapi_schema = schema
    return app.openapi_schema


def create_app() -> FastAPI:
    # one schema per model, like docs/openapi.yaml (no -Input/-Output twins)
    app = FastAPI(title="SIM-TAMY API", version=__version__, separate_input_output_schemas=False)
    settings = get_settings()
    app.add_middleware(
        HardeningMiddleware
    )  # innermost: its replies still get CORS and a request id
    if settings.cors_origin_list or settings.cors_origin_regex:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_origin_regex=settings.cors_origin_regex,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "Idempotent-Replay", "Retry-After"],
        )
    app.add_middleware(RequestIdMiddleware)
    errors.install(app)
    app.openapi = lambda: _openapi_without_default_422(app)  # type: ignore[method-assign]
    app.include_router(health.router)  # unversioned, per openapi.yaml
    app.include_router(cases.router)
    app.include_router(sessions.router)
    app.include_router(instructor.router)
    app.include_router(pilot.router)
    app.include_router(replay.router)
    return app


app = create_app()
