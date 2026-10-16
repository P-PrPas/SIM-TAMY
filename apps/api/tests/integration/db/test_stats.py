"""T-044: `make stats` / `make cost-report` read measured rows only (FR-OBS-01)."""

from argparse import ArgumentTypeError

import pytest
from sqlalchemy.orm import Session

from app.db.models import LlmCall
from app.db.repo import EventRepo, SessionRepo
from app.stats import cost_report, parse_price, stats_report


def call(ms: int, *, ok: bool = True, tokens: tuple[int, int] | None = (10, 5)) -> LlmCall:
    p, c = tokens if tokens else (None, None)
    return LlmCall(
        purpose="interpreter",
        provider="openai_like",
        model="m",
        latency_ms=ms,
        ok=ok,
        prompt_tokens=p,
        completion_tokens=c,
    )


def test_an_empty_database_reports_no_data(db: Session) -> None:
    assert stats_report(db).startswith("no data")
    assert cost_report(db, {}).startswith("no data")


def test_stats_show_percentiles_error_rate_and_fallbacks(db: Session) -> None:
    db.add_all([call(ms) for ms in (100, 200, 300, 400, 1000)] + [call(500, ok=False)])
    row = SessionRepo(db).create(
        case_id="DEV-001",
        case_version="0.1",
        case_hash="h",
        variant="A",
        learner_name="n",
        token_hash="t",
        state={},
    )
    events = EventRepo(db)
    for i in (1, 2):
        events.append(session_id=row.id, turn_idx=i, type="LEARNER_MESSAGE", payload={})
    for component in ("interpreter", "generator"):  # two fallbacks in one turn
        events.append(
            session_id=row.id,
            turn_idx=2,
            type="LLM_FALLBACK_USED",
            payload={"component": component},
        )
    db.flush()

    lines = stats_report(db).splitlines()

    fields = lines[1].split()
    assert fields[1:] == ["openai_like/m", "6", "16.7", "350", "875"]  # p50 of 100..1000, p95
    assert lines[-1] == (
        "turns with a fallback: 1 of 2 (50.0%); "
        "fallback events by component: {'generator': 1, 'interpreter': 1}"
    )  # two events in one turn count as one turn, never 100%+


def test_cost_uses_only_a_price_it_was_given_and_flags_missing_token_counts(db: Session) -> None:
    db.add_all([call(100, tokens=(1_000_000, 500_000)), call(100, tokens=None)])
    db.flush()

    unpriced = cost_report(db, {})
    priced = cost_report(db, dict([parse_price("openai_like:m=2,8")]))

    assert "price not set" in unpriced and "total" not in unpriced
    assert "6.000000" in priced  # 1M tokens * 2 + 0.5M tokens * 8, per million
    assert "tokens known for 1/2 calls" in priced


def test_no_token_counts_is_not_a_zero_cost(db: Session) -> None:
    db.add_all([call(100, tokens=None), call(120, tokens=None)])
    db.flush()

    text = cost_report(db, dict([parse_price("openai_like:m=2,8")]))

    assert "N/A (no token counts)" in text
    assert "0.000000" not in text and "total" not in text


def test_a_partial_total_is_labelled_and_a_half_known_call_is_not_priced(db: Session) -> None:
    half = LlmCall(
        purpose="debrief", provider="openai_like", model="m", latency_ms=1, ok=True,
        prompt_tokens=1_000_000, completion_tokens=None,
    )  # fmt: skip
    db.add_all([call(100, tokens=(1_000_000, 0)), call(100, tokens=None), half])
    db.flush()

    text = cost_report(db, dict([parse_price("openai_like:m=2,8")]))

    assert "partial total: 2.000000 USD" in text  # only the one call with both counts
    assert not any(line.startswith("total:") for line in text.splitlines())


@pytest.mark.parametrize(
    "bad", ["m=1,2", "p:m=1", "p:m=a,b", "p:m=-1,2", "p:m=nan,1", "p:m=1,inf", "p:m=-inf,1"]
)
def test_a_malformed_price_is_refused(bad: str) -> None:
    with pytest.raises(ArgumentTypeError):
        parse_price(bad)
