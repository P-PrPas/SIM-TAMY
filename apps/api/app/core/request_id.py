"""Pure ASGI middleware: a server-made request id on every response (D3), no-store for sessions."""

import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = uuid.uuid4().hex[:12]  # never taken from the client (log injection)
        scope.setdefault("state", {})["request_id"] = rid
        no_store = (
            scope["path"].startswith(("/v1/sessions", "/v1/instructor", "/v1/family"))
            or scope["path"] == "/v1/classes"
        )

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = rid
                if no_store:
                    headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_id)
