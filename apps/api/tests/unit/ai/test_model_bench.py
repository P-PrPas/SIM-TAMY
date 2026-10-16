"""T-005: measure the Interpreter, never fabricate a candidate's results."""

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from eval.model_bench import (  # noqa: E402
    Candidate,
    Sample,
    evaluate,
    load_samples,
    main,
    parse_prices,
    render_report,
)

from app.ai.llm_client import LLMInvalidResponse, LLMRequest, LLMResponse  # noqa: E402
from app.domain.action import Action  # noqa: E402


class ScriptedProvider:
    name = "scripted"

    def __init__(self, replies: list[dict[str, object] | Exception]) -> None:
        self.replies = replies
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResponse(json.dumps(reply), prompt_tokens=10, completion_tokens=5)


def actions() -> list[Action]:
    return [
        Action(id="A01", category="HX", type="info", label_th="alpha", examples_th=["alpha"]),
        Action(id="A02", category="HX", type="info", label_th="beta", examples_th=["beta"]),
    ]


def samples() -> list[Sample]:
    return [
        Sample("DEV-001", "A", "INTERVIEW", "ask alpha", frozenset({"A01"})),
        Sample("DEV-001", "A", "INTERVIEW", "ask beta", frozenset({"A02"})),
        Sample("DEV-001", "A", "INTERVIEW", "weather", frozenset()),
    ]


def test_load_samples_reads_the_67_labelled_devset() -> None:
    from app.content.loader import load_case

    catalogue = load_case(ROOT / "content" / "cases" / "DEV-001")
    loaded = load_samples(
        ROOT / "eval" / "devset" / "actions_th.jsonl",
        case_id="DEV-001",
        actions=catalogue.actions,
    )
    assert len(loaded) == 67
    assert any(sample.action_ids == frozenset() for sample in loaded)


@pytest.mark.parametrize(
    ("bad_row", "error_code"),
    [
        (
            {
                "case_id": "OTHER",
                "variant": "A",
                "phase": "INTERVIEW",
                "text_th": "x",
                "action_ids": [],
                "kind": "direct",
            },
            "case_id",
        ),
        (
            {
                "case_id": "DEV-001",
                "variant": "A",
                "phase": "INTERVIEW",
                "text_th": "x",
                "action_ids": ["B01"],
                "kind": "direct",
            },
            "action_ids",
        ),
        (
            {
                "case_id": "DEV-001",
                "variant": "A",
                "phase": "INTERVIEW",
                "text_th": "",
                "action_ids": [],
                "kind": "direct",
            },
            "text_th",
        ),
    ],
)
def test_load_samples_rejects_invalid_rows(
    tmp_path: Path, bad_row: dict[str, object], error_code: str
) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=error_code):
        load_samples(path, case_id="DEV-001", actions=actions(), min_count=1)


def test_evaluate_measures_exact_match_per_action_and_token_cost() -> None:
    provider = ScriptedProvider(
        [
            {"actions": [{"id": "A01", "confidence": 0.9, "evidence_span": "alpha"}]},
            {"actions": [{"id": "A01", "confidence": 0.9, "evidence_span": "beta"}]},
            {"actions": []},
        ]
    )
    candidate = Candidate("scripted:test", provider, "test", Decimal("1"), Decimal("1"))
    result = evaluate(candidate, samples(), actions())
    assert result.exact_match_rate == pytest.approx(2 / 3)
    assert result.structured_valid_rate == 1
    assert result.per_action["A01"].precision == 0.5
    assert result.per_action["A01"].recall == 1
    assert result.per_action["A02"].precision is None
    assert result.per_action["A02"].recall == 0
    assert result.estimated_cost_usd_per_turn == Decimal("0.000015")
    assert result.latency_p50_ms >= 0 and result.latency_p95_ms >= result.latency_p50_ms
    assert all(request.purpose == "interpreter" for request in provider.requests)


def test_invalid_structured_response_is_not_counted_as_a_correct_negative() -> None:
    provider = ScriptedProvider(
        [LLMInvalidResponse("invalid_response"), LLMInvalidResponse("invalid_response")]
    )
    candidate = Candidate("scripted:bad", provider, "bad", Decimal("1"), Decimal("1"))
    negative = Sample("DEV-001", "A", "INTERVIEW", "weather", frozenset())
    result = evaluate(candidate, [negative], actions())
    assert result.structured_valid_rate == 0
    assert result.exact_match_rate == 0
    assert result.estimated_cost_usd_per_turn is None
    assert len(provider.requests) == 2


def test_parse_prices_rejects_negative_and_duplicate_entries() -> None:
    assert parse_prices(["openai_like:model=0.2,0.4"]) == {
        "openai_like:model": (Decimal("0.2"), Decimal("0.4"))
    }
    with pytest.raises(ValueError, match="price"):
        parse_prices(["openai_like:model=-1,0.4"])
    with pytest.raises(ValueError, match="duplicate"):
        parse_prices(["mock:x=0,0", "mock:x=0,0"])


def test_report_contains_aggregate_metrics_but_no_learner_text() -> None:
    provider = ScriptedProvider([{"actions": []}])
    result = evaluate(
        Candidate("scripted:test", provider, "test"),
        [Sample("DEV-001", "A", "INTERVIEW", "private learner text", frozenset())],
        actions(),
    )
    report = render_report(
        [result],
        case_id="DEV-001",
        data_hash="abc123",
        when=datetime(2026, 10, 15, tzinfo=UTC),
    )
    assert "scripted:test" in report and "A01" in report
    assert "private learner text" not in report
    assert "N/A" in report


def test_report_records_price_assumptions_and_case_hash() -> None:
    provider = ScriptedProvider([{"actions": []}])
    result = evaluate(
        Candidate("scripted:priced", provider, "priced", Decimal("0.2"), Decimal("0.4")),
        [Sample("DEV-001", "A", "INTERVIEW", "private learner text", frozenset())],
        actions(),
    )
    report = render_report(
        [result],
        case_id="DEV-001",
        data_hash="dataset",
        case_hash="catalogue",
        when=datetime(2026, 10, 15, tzinfo=UTC),
    )
    assert "catalogue" in report and "0.2 input / 0.4 output" in report
    assert "private learner text" not in report


def test_cli_runs_offline_mock_and_writes_a_dated_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--candidate", "mock:mock-model", "--output-dir", str(tmp_path)]) == 0
    reports = list(tmp_path.glob("*-mock-mock-model*.md"))
    assert len(reports) == 1
    text = reports[0].read_text(encoding="utf-8")
    assert "67" in text and "mock:mock-model" in text
    assert "single mock candidate" in text
    assert "mock:mock-model" in capsys.readouterr().out
