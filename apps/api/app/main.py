from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import health, sessions
from app.core import errors
from app.core.config import get_settings
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
    origins = get_settings().cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "Idempotent-Replay", "Retry-After"],
        )
    app.add_middleware(RequestIdMiddleware)
    errors.install(app)
    app.openapi = lambda: _openapi_without_default_422(app)  # type: ignore[method-assign]
    app.include_router(health.router)  # unversioned, per openapi.yaml
    app.include_router(sessions.router)
    return app


app = create_app()
