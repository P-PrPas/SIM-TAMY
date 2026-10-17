"""T-074: scripts/loadcheck.py counts what it measured and plays the real API."""

import importlib.util
from pathlib import Path
from typing import Any

from tests.integration.api.conftest import Api

_spec = importlib.util.spec_from_file_location(
    "loadcheck", Path(__file__).resolve().parents[5] / "scripts" / "loadcheck.py"
)
assert _spec and _spec.loader
loadcheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loadcheck)


def test_percentile_is_an_observed_value_not_an_interpolation() -> None:
    values = [float(n) for n in range(1, 101)]
    assert loadcheck.percentile(values, 50) == 50.0
    assert loadcheck.percentile(values, 95) == 95.0
    assert loadcheck.percentile([7.0], 95) == 7.0


def fake_api(rate_limited: int = 0) -> Any:
    sent = {"turns": 0}

    def call(method: str, path: str, body: Any, token: Any) -> tuple[int, Any]:
        if path == "/v1/cases":
            return 200, {"items": [{"case_id": "X-1", "variants_available": ["A"]}]}
        if path == "/v1/cases/X-1":
            return 200, {"decision_options": [{"id": "refer"}]}
        if path == "/v1/sessions":
            return 201, {"session_id": "s", "token": "t"}
        if path.endswith("/turns"):
            sent["turns"] += 1
            return (429 if sent["turns"] <= rate_limited else 200), {}
        return 200, {}

    return call


def test_every_request_is_recorded_and_failures_are_counted() -> None:
    records, _ = loadcheck.run(fake_api(rate_limited=2), sessions=3, turns=2)

    assert len(records) == 3 * (1 + 2 + 3)  # create, turns, decision, complete, report
    assert sum(r.status == 429 for r in records) == 2
    report = loadcheck.render(records, 1.0, 3, 2, {"llm_provider": "fake"})
    assert "Errors (non-2xx or no answer): 2 of 18" in report
    assert "429: 2" in report and "provider `fake`" in report


def test_a_run_with_no_answered_turn_is_not_a_pass() -> None:
    records = [loadcheck.Record("create session", 500, 0.01)]
    assert loadcheck.turn_p95_s(records) > loadcheck.TURN_P95_TARGET_S
    assert "no turn answered" in loadcheck.render(records, 1.0, 1, 1, {})


def test_it_plays_the_real_api_without_errors(api: Api) -> None:
    def call(method: str, path: str, body: Any, token: Any) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = api.client.request(method, path, json=body, headers=headers)
        return r.status_code, r.json()

    records, _ = loadcheck.run(call, sessions=1, turns=2)

    assert [r.step for r in records] == [
        "create session", "turn", "turn", "decision", "complete", "report",
    ]  # fmt: skip
    assert all(r.status in (200, 201) for r in records), [(r.step, r.status) for r in records]
