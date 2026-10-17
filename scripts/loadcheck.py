"""Latency and concurrency check (T-074): N learners play one short journey at the same time.

    python scripts/loadcheck.py http://localhost:8000 [--sessions 20] [--turns 6]
                                [--case-id DEV-001] [--expect-provider openai_like]
                                [--output eval/results/<name>.md]

Every learner: create session -> N turns -> decision -> complete -> report, all learners released
together. Latency is wall clock as the client sees it, per request; error rate is every non-2xx
answer or transport failure (a 429 from the per-session rate limit counts). Nothing is estimated
(AGENTS rule 11): the markdown report holds only what was measured in this run. Server-side numbers
per LLM call come from `make stats` against the same database. Stdlib only. Prints no token or text.
"""

import argparse
import json
import math
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Call = Callable[[str, str, dict[str, Any] | None, str | None], tuple[int, Any]]
TURN_P95_TARGET_S = 8.0  # PRD §1.3, non-streaming turn
# Neutral, non-clinical learner utterances stay in content, not source code.
_PHRASES_FILE = Path(__file__).resolve().parents[1] / "content" / "loadcheck" / "utterances_th.json"
PHRASES = tuple(json.loads(_PHRASES_FILE.read_text(encoding="utf-8"))["utterances_th"])


@dataclass(frozen=True)
class Record:
    step: str
    status: int  # 0 = no HTTP answer
    seconds: float


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile; the value actually observed, never an interpolation."""
    ordered = sorted(values)
    return ordered[max(1, math.ceil(len(ordered) * p / 100)) - 1]


def turn_p95_s(records: list[Record]) -> float:
    turns = [r.seconds for r in records if r.step == "turn"]
    return percentile(turns, 95) if turns else math.inf  # no turn answered at all is a failure


def journey(call: Call, case: str, option_id: str, turns: int, log: list[Record]) -> None:
    def step(
        name: str, method: str, path: str, body: dict[str, Any] | None, token: str | None
    ) -> tuple[int, Any]:
        start = time.perf_counter()
        try:
            status, data = call(method, path, body, token)
        except OSError:
            status, data = 0, {}
        log.append(Record(name, status, time.perf_counter() - start))
        return status, data

    status, created = step(
        "create session",
        "POST",
        "/v1/sessions",
        {"case_id": case, "variant": "A", "learner_name": "loadcheck"},
        None,
    )
    if status != 201:
        return
    base, token = f"/v1/sessions/{created['session_id']}", created["token"]
    for i in range(turns):
        step("turn", "POST", f"{base}/turns", {"text": PHRASES[i % len(PHRASES)]}, token)
    step("decision", "POST", f"{base}/decision", {"option_id": option_id}, token)
    step("complete", "POST", f"{base}/complete", {}, token)
    step("report", "GET", f"{base}/report", None, token)


def run(
    call: Call, sessions: int, turns: int, case_id: str | None = None
) -> tuple[list[Record], float]:
    status, cases = call("GET", "/v1/cases", None, None)
    playable = [c for c in cases.get("items", []) if "A" in c["variants_available"]]
    chosen = next((c for c in playable if case_id in (None, c["case_id"])), None)
    if status != 200 or chosen is None:
        raise SystemExit(f"no playable case {case_id or ''}".rstrip())
    case = chosen["case_id"]
    _, brief = call("GET", f"/v1/cases/{case}", None, None)
    option_id = brief["decision_options"][0]["id"]

    logs: list[list[Record]] = [[] for _ in range(sessions)]
    start_together = threading.Barrier(sessions)

    def learner(log: list[Record]) -> None:
        start_together.wait()
        journey(call, case, option_id, turns, log)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=sessions) as pool:
        list(pool.map(learner, logs))
    return [r for log in logs for r in log], time.perf_counter() - started


def stats_row(name: str, records: list[Record]) -> str:
    ms = [r.seconds * 1000 for r in records]
    errors = sum(not 200 <= r.status < 300 for r in records)
    return (
        f"| {name} | {len(records)} | {errors} | {percentile(ms, 50):.0f} "
        f"| {percentile(ms, 95):.0f} | {max(ms):.0f} |"
    )


def render(
    records: list[Record], wall_s: float, sessions: int, turns: int, health: dict[str, Any]
) -> str:
    steps = list(dict.fromkeys(r.step for r in records))
    errors = sum(not 200 <= r.status < 300 for r in records)
    p95 = turn_p95_s(records)
    p95_text = "no turn answered" if math.isinf(p95) else f"{p95 * 1000:.0f} ms"
    verdict = "met" if p95 <= TURN_P95_TARGET_S else "NOT met"
    codes = ", ".join(f"{c}: {n}" for c, n in sorted(Counter(r.status for r in records).items()))
    commit = str(health.get("commit") or "unknown")[:12]
    lines = [
        "# Latency and concurrency check (T-074)",
        "",
        f"- Measured: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- Concurrent learners: {sessions}, turns each: {turns}, requests: {len(records)}, "
        f"wall clock: {wall_s:.1f} s",
        f"- Server: provider `{health.get('llm_provider', '?')}`, "
        f"version `{health.get('version', '?')}`, commit `{commit}`",
        f"- Errors (non-2xx or no answer): {errors} of {len(records)} "
        f"({100 * errors / len(records):.1f}%); status codes: {codes}",
        f"- Turn p95 {p95_text} against the PRD 1.3 target of {TURN_P95_TARGET_S:.0f} s: {verdict}",
        "- Latency is client wall clock, including network. Per-LLM-call numbers: `make stats`.",
        "",
        "| Step | Requests | Errors | p50 ms | p95 ms | max ms |",
        "|---|---:|---:|---:|---:|---:|",
        *(stats_row(s, [r for r in records if r.step == s]) for s in steps),
        "",
    ]
    return "\n".join(lines)


def http_call(base_url: str) -> Call:
    def call(
        method: str, path: str, body: dict[str, Any] | None, token: str | None
    ) -> tuple[int, Any]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base_url.rstrip("/") + path, data, headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            return exc.code, {}

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("base_url")
    parser.add_argument("--sessions", type=int, default=20)
    parser.add_argument(
        "--turns", type=int, default=6, help="keep below the per-session rate limit"
    )
    parser.add_argument("--case-id")
    parser.add_argument(
        "--expect-provider", help="fail before load if /health reports another provider"
    )
    parser.add_argument("--output", type=Path, help="also write the markdown report here")
    args = parser.parse_args(argv)
    if args.sessions < 1 or args.turns < 1:
        parser.error("--sessions and --turns must be positive")
    call = http_call(args.base_url)
    status, health = call("GET", "/health", None, None)
    if status != 200 or health.get("db") != "ok":
        print("loadcheck: API /health is not ready", file=sys.stderr)
        return 2
    if args.expect_provider and health.get("llm_provider") != args.expect_provider:
        print("loadcheck: provider does not match --expect-provider", file=sys.stderr)
        return 2
    records, wall = run(call, args.sessions, args.turns, args.case_id)
    report = render(records, wall, args.sessions, args.turns, health)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    failed = any(not 200 <= r.status < 300 for r in records)
    return 1 if failed or turn_p95_s(records) > TURN_P95_TARGET_S else 0


if __name__ == "__main__":
    sys.exit(main())
