"""Post-deploy smoke test (T-094): one learner journey against a running API.

    python scripts/smoke.py https://<service>.onrender.com [--case-id DEV-001] [--wait 120]

health -> case list -> create session -> one turn -> decision -> complete -> report. Exit 0 only if
every step held; the first failure prints which step and exits 1. It creates a real (synthetic)
session named "smoke", so the retention purge removes it like any other. Stdlib only. It prints
no token, learner text or key.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

Call = Callable[[str, str, dict[str, Any] | None, str | None], tuple[int, Any]]
# what a play-time response must never carry (AGENTS rule 5)
FORBIDDEN = {"revealed_fact_ids", "risk_state", "actions", "hidden_facts", "score", "total_score"}


class SmokeFailure(Exception):
    pass


def check(ok: object, step: str, detail: str = "") -> None:
    if not ok:
        raise SmokeFailure(f"FAIL {step}: {detail}".rstrip(": "))
    print(f"ok   {step}")


def keys_of(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_of(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_of(v)}
    return set()


def run(call: Call, case_id: str | None = None, wait_s: float = 0) -> None:
    deadline = time.monotonic() + wait_s
    while True:  # a sleeping free instance needs a while to answer
        try:
            status, health = call("GET", "/health", None, None)
        except OSError as exc:
            status, health = 0, {"error": type(exc).__name__}
        if status == 200 or time.monotonic() >= deadline:
            break
        time.sleep(5)
    check(status == 200 and health.get("status") == "ok", "health", f"{status} {health}")
    check(health.get("db") == "ok" and health.get("cases_loaded", 0) >= 1, "health db and content")

    status, cases = call("GET", "/v1/cases", None, None)
    items = [c for c in cases.get("items", []) if "A" in c["variants_available"]]
    chosen = next((c for c in items if case_id in (None, c["case_id"])), None)
    if status != 200 or chosen is None:
        raise SmokeFailure(f"FAIL case list: no playable case {case_id or ''}".rstrip())
    print("ok   case list")
    case = chosen["case_id"]
    status, brief = call("GET", f"/v1/cases/{case}", None, None)
    options = brief.get("decision_options", [])
    check(status == 200 and options, "case brief", "no decision options")

    body = {"case_id": case, "variant": "A", "learner_name": "smoke"}
    status, created = call("POST", "/v1/sessions", body, None)
    check(status == 201 and created.get("token"), "create session", str(status))
    base, token = f"/v1/sessions/{created['session_id']}", created["token"]
    check(
        created["case"].get("status_label_th") and created.get("notices"), "status badge, notices"
    )

    status, turn = call("POST", f"{base}/turns", {"text": "สวัสดีค่ะ"}, token)
    check(status == 200 and turn.get("turn_idx") == 1, "send turn", str(status))
    check(not keys_of(turn) & FORBIDDEN, "turn leaks nothing", str(keys_of(turn) & FORBIDDEN))

    status, _ = call("POST", f"{base}/decision", {"option_id": options[0]["id"]}, token)
    check(status == 200, "commit decision", str(status))
    status, _ = call("POST", f"{base}/complete", {}, token)
    check(status == 200, "complete", str(status))
    status, report = call("GET", f"{base}/report", None, token)
    check(status == 200 and report.get("items"), "report", str(status))
    check(report.get("safety_status") and report.get("disclaimers"), "report gate and disclaimer")


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
            try:
                return exc.code, json.load(exc)
            except ValueError:
                return exc.code, {}

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("base_url")
    parser.add_argument("--case-id")
    parser.add_argument("--wait", type=float, default=0, help="seconds to wait for /health")
    args = parser.parse_args(argv)
    try:
        run(http_call(args.base_url), args.case_id, args.wait)
    except SmokeFailure as exc:
        print(exc, file=sys.stderr)
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
