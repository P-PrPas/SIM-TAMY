"""T-094: scripts/smoke.py passes on a healthy API and names the broken step when one fails."""

import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.integration.api.conftest import Api

_spec = importlib.util.spec_from_file_location(
    "smoke", Path(__file__).resolve().parents[5] / "scripts" / "smoke.py"
)
assert _spec and _spec.loader
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


def call_for(api: Api, tamper: Any = None) -> Any:
    def call(
        method: str, path: str, body: dict[str, Any] | None, token: str | None
    ) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = api.client.request(method, path, json=body, headers=headers)
        data = r.json()
        return r.status_code, tamper(method, path, data) if tamper else data

    return call


def test_the_whole_journey_passes_on_a_healthy_api(
    api: Api, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke.run(call_for(api))

    out = capsys.readouterr().out
    assert out.count("ok   ") >= 10 and "FAIL" not in out
    assert not re.search(r"st_[A-Za-z0-9_-]{20,}", out)  # the session token is never printed


def test_a_play_time_leak_fails_the_turn_step(api: Api) -> None:
    def leak(method: str, path: str, data: Any) -> Any:
        return {**data, "risk_state": "red"} if path.endswith("/turns") else data

    with pytest.raises(smoke.SmokeFailure, match="turn leaks nothing"):
        smoke.run(call_for(api, leak))


def test_an_unknown_case_fails_the_case_step(api: Api) -> None:
    with pytest.raises(smoke.SmokeFailure, match="case list"):
        smoke.run(call_for(api), case_id="NOPE-1")


def test_an_unhealthy_api_fails_the_health_step() -> None:
    def down(method: str, path: str, body: Any, token: Any) -> tuple[int, Any]:
        return 503, {"status": "down"}

    with pytest.raises(smoke.SmokeFailure, match="health"):
        smoke.run(down)


def test_expect_sha_waits_for_the_new_commit_and_fails_on_the_old_one(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    live: list[str | None] = ["old" * 13]  # what /health says now
    sleeps: list[float] = []
    clock = [0.0]

    def tamper(method: str, path: str, data: Any) -> Any:
        return {**data, "commit": live[0]} if path == "/health" else data

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds
        if len(sleeps) == 1:
            live[0] = "a" * 40  # the new deploy goes live while we wait

    # only smoke.py's clock: the stand-in is not the global `time` module
    monkeypatch.setattr(
        smoke, "time", SimpleNamespace(sleep=fake_sleep, monotonic=lambda: clock[0])
    )
    smoke.run(call_for(api, tamper), wait_s=60, expect_sha="A" * 40)  # case-insensitive
    assert sleeps == [5]

    live[0] = "old" * 13  # a failed deploy: the old instance keeps answering 200
    with pytest.raises(smoke.SmokeFailure, match="deployed commit: live oldoldoldold"):
        smoke.run(call_for(api, tamper), wait_s=20, expect_sha="a" * 40)
    assert clock[0] <= 5 + 5 * 5  # it gave up at the deadline, not forever

    live[0] = None  # an instance that does not report a commit
    with pytest.raises(smoke.SmokeFailure, match="live unknown"):
        smoke.run(call_for(api, tamper), expect_sha="a" * 40)
