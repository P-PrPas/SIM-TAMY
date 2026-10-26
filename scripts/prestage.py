"""Pre-stage health check (C04): read-only, stdlib only, prints PASS/FAIL per check.

    python scripts/prestage.py <api-url> <web-url> [--wait 120]

Checks the API health (and times the first answer, which is the Render cold start), the web app,
the case list, the family stories, the offline Replay gallery and the browser CORS preflight from
the web origin. It only sends GET and one OPTIONS request: no session or room is created, so it
leaves no data behind. It prints no token, key or response body; only names, counts and timings.
Exit 0 only if every check passed.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

Fetch = Callable[[str, str, dict[str, str]], tuple[int, dict[str, str], Any]]


def http_fetch(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], Any]:
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read(2_000_000)
            status, got = resp.status, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, None
    except OSError:  # URLError, refused, timed out: status 0 means "no answer"
        return 0, {}, None
    try:
        return status, got, json.loads(raw) if raw[:1] in (b"{", b"[") else raw
    except ValueError:
        return status, got, raw


def run(api: str, web: str, fetch: Fetch, wait_s: float = 0) -> list[tuple[str, bool, str]]:
    api, web = api.rstrip("/"), web.rstrip("/")
    results: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    deadline = time.monotonic() + wait_s
    started = time.monotonic()
    while True:  # a sleeping free instance needs a while to answer
        status, _, health = fetch("GET", f"{api}/health", {})
        if status == 200 or time.monotonic() >= deadline:
            break
        time.sleep(5)
    took = time.monotonic() - started
    health = health if isinstance(health, dict) else {}
    record(
        "api health",
        status == 200 and health.get("status") == "ok" and health.get("db") == "ok",
        f"HTTP {status}, first answer after {took:.1f}s, db={health.get('db')}, "
        f"llm_provider={health.get('llm_provider')}, "
        f"commit={str(health.get('commit') or '-')[:12]}",
    )

    status, _, _ = fetch("GET", web, {})
    record("web reachable", status == 200, f"HTTP {status}")

    status, _, cases = fetch("GET", f"{api}/v1/cases", {})
    items = cases.get("items", []) if isinstance(cases, dict) else []
    record(
        "case list loads", status == 200 and len(items) >= 1, f"HTTP {status}, {len(items)} cases"
    )

    status, _, stories = fetch("GET", f"{api}/v1/family/stories", {})
    count = len(stories) if isinstance(stories, list) else 0
    record("family stories load", status == 200 and count >= 1, f"HTTP {status}, {count} stories")

    status, _, rec = fetch("GET", f"{api}/v1/replay/recordings", {})
    n = len(rec.get("items", [])) if isinstance(rec, dict) else 0
    record(
        "replay gallery (offline fallback)",
        status == 200 and n >= 1,
        f"HTTP {status}, {n} recordings",
    )

    status, got, _ = fetch(
        "OPTIONS",
        f"{api}/health",
        {"Origin": web, "Access-Control-Request-Method": "GET"},
    )
    allowed = got.get("access-control-allow-origin")
    record("cors from web origin", allowed in (web, "*"), f"HTTP {status}, allowed={allowed}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("api_url")
    parser.add_argument("web_url")
    parser.add_argument("--wait", type=float, default=0, help="seconds to wait for /health")
    args = parser.parse_args(argv)
    results = run(args.api_url, args.web_url, http_fetch, args.wait)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    failed = [name for name, ok, _ in results if not ok]
    print("PRESTAGE PASS" if not failed else f"PRESTAGE FAIL ({', '.join(failed)})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
