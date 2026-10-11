from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="SIM-TAMY API", version=__version__)
    origins = get_settings().cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)  # unversioned, per openapi.yaml
    return app


app = create_app()
