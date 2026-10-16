"""Pure ASGI middleware: security headers, request-size limit, rate-limit headers (T-048)."""

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import errors, limits

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
# a JSON API renders nothing; the Swagger pages need their own scripts, so they are left out
CSP = "default-src 'none'; frame-ancestors 'none'"
DOC_PATHS = ("/docs", "/redoc")


class HardeningMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # ponytail: Content-Length only; a chunked body is bounded by the host proxy, not here
        length = Headers(scope=scope).get("content-length", "")
        if length.isdigit() and int(length) > limits.MAX_BODY_BYTES:
            reply = errors.envelope(
                Request(scope),
                "VALIDATION_ERROR",
                "request body is too large",
                {"max_bytes": limits.MAX_BODY_BYTES},
            )
            await reply(scope, receive, self._with_headers(scope, send))
            return
        await self.app(scope, receive, self._with_headers(scope, send))

    def _with_headers(self, scope: Scope, send: Send) -> Send:
        docs = scope["path"].startswith(DOC_PATHS)

        async def send_with(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
                if not docs:
                    headers["Content-Security-Policy"] = CSP
                rate = scope.get("state", {}).get("rate_limit")
                if rate:  # (limit, remaining) set by the sendTurn dependency
                    headers["X-RateLimit-Limit"], headers["X-RateLimit-Remaining"] = map(str, rate)
            await send(message)

        return send_with
