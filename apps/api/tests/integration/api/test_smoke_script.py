"""T-094: scripts/smoke.py passes on a healthy API and names the broken step when one fails."""

import importlib.util
import re
from pathlib import Path
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
