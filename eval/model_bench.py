"""Measured Interpreter benchmark for the synthetic Action dev set (T-005).

This never scores a learner or decides a case outcome. It compares Action IDs
accepted by the existing deterministic confidence policy against author labels.
"""

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.ai.interpreter import OFFERED_CATEGORIES, interpret
from app.ai.llm_client import (
    LLMCallRecord,
    LLMClient,
    LLMError,
    LLMProvider,
    build_provider,
)
from app.ai.policy import apply_policy
from app.content.loader import load_case
from app.core.config import Settings
from app.domain.action import Action


@dataclass(frozen=True)
class Sample:
    case_id: str
    variant: str
    phase: str
    text_th: str
    action_ids: frozenset[str]


@dataclass(frozen=True)
class Candidate:
    name: str
    provider: LLMProvider
    model: str
    input_price_usd_per_million: Decimal | None = None
    output_price_usd_per_million: Decimal | None = None


@dataclass(frozen=True)
class ActionMetrics:
    tp: int
    fp: int
    fn: int
    precision: float | None
    recall: float | None


@dataclass(frozen=True)
class BenchResult:
    candidate: str
    sample_count: int
    exact_match_rate: float
    structured_valid_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    estimated_cost_usd_per_turn: Decimal | None
    per_action: dict[str, ActionMetrics]
    call_count: int
    input_price_usd_per_million: Decimal | None
    output_price_usd_per_million: Decimal | None


def load_samples(
    path: Path, *, case_id: str, actions: Sequence[Action], min_count: int = 50
) -> list[Sample]:
    """Reject unlabelled/misaligned rows without echoing learner text in errors."""
    offered = {action.id for action in actions if action.category in OFFERED_CATEGORIES}
    samples: list[Sample] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise TypeError(f"line {number}: expected object")
        for key in ("case_id", "variant", "phase", "text_th", "action_ids", "kind"):
            if key not in row:
                raise ValueError(f"line {number}: missing {key}")
        if row["case_id"] != case_id:
            raise ValueError(f"line {number}: case_id mismatch")
        if row["variant"] not in ("A", "B", "C"):
            raise ValueError(f"line {number}: invalid variant")
        if row["phase"] not in ("INTRO", "INTERVIEW", "PRESSURE", "CLOSING"):
            raise ValueError(f"line {number}: invalid phase")
        if not isinstance(row["text_th"], str) or not row["text_th"].strip():
            raise ValueError(f"line {number}: invalid text_th")
        labels = row["action_ids"]
        if (
            not isinstance(labels, list)
            or any(
                not isinstance(label, str) or label not in offered for label in labels
            )
            or len(labels) != len(set(labels))
        ):
            raise ValueError(f"line {number}: invalid action_ids")
        if not isinstance(row["kind"], str) or not row["kind"].strip():
            raise ValueError(f"line {number}: invalid kind")
        samples.append(
            Sample(
                case_id, row["variant"], row["phase"], row["text_th"], frozenset(labels)
            )
        )
    if len(samples) < min_count:
        raise ValueError(f"dev set has {len(samples)} rows; minimum is {min_count}")
    return samples


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _p95(values: list[float]) -> float:
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def evaluate(
    candidate: Candidate, samples: Sequence[Sample], actions: Sequence[Action]
) -> BenchResult:
    if not samples:
        raise ValueError("cannot benchmark an empty dev set")
    calls: list[LLMCallRecord] = []
    client = LLMClient(
        candidate.provider, model=candidate.model, timeout_s=15, on_call=calls.append
    )
    labels_by_action = {
        a.id: [0, 0, 0] for a in actions if a.category in OFFERED_CATEGORIES
    }
    latencies: list[float] = []
    exact = valid = 0
    for sample in samples:
        start = time.perf_counter()
        try:
            result = interpret(client, actions, sample.text_th, phase=sample.phase)
        except LLMError:
            predicted: set[str] = set()
            parsed = False
        else:
            predicted = {a.id for a in apply_policy(result).accepted}
            parsed = True
            valid += 1
        latencies.append((time.perf_counter() - start) * 1000)
        exact += int(parsed and predicted == sample.action_ids)
        for action_id, counts in labels_by_action.items():
            expected = action_id in sample.action_ids
            found = action_id in predicted
            counts[0] += int(expected and found)
            counts[1] += int(not expected and found)
            counts[2] += int(expected and not found)
    per_action = {
        action_id: ActionMetrics(tp, fp, fn, _rate(tp, tp + fp), _rate(tp, tp + fn))
        for action_id, (tp, fp, fn) in sorted(labels_by_action.items())
    }
    price_in, price_out = (
        candidate.input_price_usd_per_million,
        candidate.output_price_usd_per_million,
    )
    if (
        price_in is None
        or price_out is None
        or any(c.prompt_tokens is None or c.completion_tokens is None for c in calls)
    ):
        cost = None
    else:
        total = sum(
            (
                Decimal(c.prompt_tokens) * price_in
                + Decimal(c.completion_tokens) * price_out
            )
            for c in calls
            if c.prompt_tokens is not None and c.completion_tokens is not None
        )
        cost = total / Decimal(1_000_000 * len(samples))
    return BenchResult(
        candidate.name,
        len(samples),
        exact / len(samples),
        valid / len(samples),
        statistics.median(latencies),
        _p95(latencies),
        cost,
        per_action,
        len(calls),
        price_in,
        price_out,
    )


def parse_prices(specs: Sequence[str]) -> dict[str, tuple[Decimal, Decimal]]:
    prices: dict[str, tuple[Decimal, Decimal]] = {}
    for spec in specs:
        try:
            name, raw = spec.split("=", 1)
            input_raw, output_raw = raw.split(",", 1)
            pair = (Decimal(input_raw), Decimal(output_raw))
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(
                "invalid price format; use provider:model=input,output"
            ) from exc
        if not name or any(not value.is_finite() or value < 0 for value in pair):
            raise ValueError(
                "invalid price: use nonnegative finite USD per million tokens"
            )
        if name in prices:
            raise ValueError("duplicate price candidate")
        prices[name] = pair
    return prices


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def render_report(
    results: Sequence[BenchResult],
    *,
    case_id: str,
    data_hash: str,
    when: datetime,
    case_hash: str | None = None,
) -> str:
    lines = [
        "# Interpreter model bench (T-005)",
        "",
        f"- Measured: {when.astimezone(UTC).isoformat()}",
        f"- Dataset: `{case_id}` synthetic engineering fixture; SHA-256 `{data_hash}`",
        "- Metric: exact set match after deterministic confidence policy; no clinical validation claim.",
        "- Latency includes Interpreter calls, retries, and local post-processing.",
        "- Cost is estimated from provider-reported tokens and supplied USD/M-token prices; N/A otherwise.",
        "",
    ]
    if len(results) == 1 and results[0].candidate.startswith("mock:"):
        lines += [
            "**Limitation:** single mock candidate; no provider/model selection or OD-1 decision yet.",
            "",
        ]
    if case_hash is not None:
        lines += [f"- Case catalogue SHA-256: `{case_hash}`", ""]
    lines += [
        "| Candidate | Rows | Exact match | Structured valid | p50 ms | p95 ms | USD/turn est. | Calls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        cost = (
            "N/A"
            if result.estimated_cost_usd_per_turn is None
            else str(result.estimated_cost_usd_per_turn)
        )
        lines.append(
            f"| `{result.candidate}` | {result.sample_count} | {_percent(result.exact_match_rate)} "
            f"| {_percent(result.structured_valid_rate)} | {result.latency_p50_ms:.2f} "
            f"| {result.latency_p95_ms:.2f} | {cost} | {result.call_count} |"
        )
    lines.append("")
    for result in results:
        if (
            result.input_price_usd_per_million is not None
            and result.output_price_usd_per_million is not None
        ):
            lines.append(
                f"Price assumption for `{result.candidate}`: USD "
                f"{result.input_price_usd_per_million} input / "
                f"{result.output_price_usd_per_million} output per million tokens."
            )
    for result in results:
        lines += [
            "",
            f"## {result.candidate}: per-Action",
            "",
            "| Action | TP | FP | FN | Precision | Recall |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for action_id, metric in result.per_action.items():
            lines.append(
                f"| `{action_id}` | {metric.tp} | {metric.fp} | {metric.fn} "
                f"| {_percent(metric.precision)} | {_percent(metric.recall)} |"
            )
    return "\n".join(lines) + "\n"


def _candidate(
    spec: str, prices: dict[str, tuple[Decimal, Decimal]], settings: Settings
) -> Candidate:
    try:
        provider_name, model = spec.split(":", 1)
    except ValueError as exc:
        raise ValueError("candidate must be provider:model") from exc
    if provider_name not in {"mock", "openai_like"} or not re.fullmatch(
        r"[A-Za-z0-9._:/-]+", model
    ):
        raise ValueError("unsupported candidate provider or model name")
    provider = build_provider(
        settings.model_copy(update={"llm_provider": provider_name})
    )
    price = prices.get(spec, (None, None))
    return Candidate(spec, provider, model, *price)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure Interpreter Action matching on synthetic data"
    )
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="provider:model; repeat to compare",
    )
    parser.add_argument(
        "--price",
        action="append",
        default=[],
        help="provider:model=input,output USD/M-token",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval" / "results")
    args = parser.parse_args(argv)
    specs = args.candidate or ["mock:mock-model"]
    if len(specs) != len(set(specs)):
        parser.error("duplicate candidate")
    try:
        prices = parse_prices(args.price)
        if set(prices) - set(specs):
            raise ValueError("price references an unselected candidate")
        settings = Settings()
        candidates = [_candidate(spec, prices, settings) for spec in specs]
        loaded = load_case(ROOT / "content" / "cases" / "DEV-001")
        devset = ROOT / "eval" / "devset" / "actions_th.jsonl"
        samples = load_samples(
            devset, case_id=loaded.case.case_id, actions=loaded.actions
        )
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    results = [evaluate(candidate, samples, loaded.actions) for candidate in candidates]
    when = datetime.now(UTC)
    report = render_report(
        results,
        case_id=loaded.case.case_id,
        data_hash=hashlib.sha256(devset.read_bytes()).hexdigest(),
        when=when,
        case_hash=loaded.case_hash,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    names = "-".join(re.sub(r"[^A-Za-z0-9._-]", "-", name) for name in specs)
    path = args.output_dir / f"{when.strftime('%Y-%m-%dT%H%M%S%fZ')}-{names}.md"
    with path.open("x", encoding="utf-8") as output:
        output.write(report)
    print(report)
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
