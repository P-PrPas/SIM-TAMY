"""Security response headers, shared by the middleware and the 500 handler (T-048)."""

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
# a JSON API renders nothing; the Swagger pages need their own scripts, so they are left out
CSP = "default-src 'none'; frame-ancestors 'none'"
DOC_PATHS = ("/docs", "/redoc")


def security_headers(path: str) -> dict[str, str]:
    headers = dict(SECURITY_HEADERS)
    if not path.startswith(DOC_PATHS):
        headers["Content-Security-Policy"] = CSP
    return headers
