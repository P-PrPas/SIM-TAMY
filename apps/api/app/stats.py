"""`make stats` / `make cost-report`: measured numbers from `llm_calls` and `events` (FR-OBS-01).

Nothing here is estimated or invented (AGENTS rule 11): no data prints "no data", a missing price
prints tokens only, and a call without token counts adds nothing to the cost (not a zero).
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Event, LlmCall
from app.db.session import get_sessionmaker


@dataclass(frozen=True)
class Row:
    purpose: str
    provider: str
    model: str
    calls: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    prompt_tokens: int
    completion_tokens: int
    counted: int  # calls that reported token counts


def llm_rows(db: Session) -> list[Row]:
    stmt = (
        select(
            LlmCall.purpose,
            func.coalesce(LlmCall.provider, "?"),
            func.coalesce(LlmCall.model, "?"),
            func.count(),
            func.count().filter(LlmCall.ok.is_(False)),
            func.percentile_cont(0.5).within_group(LlmCall.latency_ms),
            func.percentile_cont(0.95).within_group(LlmCall.latency_ms),
            func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
            func.coalesce(func.sum(LlmCall.completion_tokens), 0),
            func.count().filter(
                LlmCall.prompt_tokens.is_not(None), LlmCall.completion_tokens.is_not(None)
            ),
        )
        .group_by(LlmCall.purpose, LlmCall.provider, LlmCall.model)
        .order_by(LlmCall.purpose, LlmCall.provider, LlmCall.model)
    )
    return [
        Row(
            purpose=r[0],
            provider=r[1],
            model=r[2],
            calls=r[3],
            errors=r[4],
            p50_ms=r[5],
            p95_ms=r[6],
            prompt_tokens=int(r[7]),
            completion_tokens=int(r[8]),
            counted=r[9],
        )
        for r in db.execute(stmt)
    ]


def fallbacks(db: Session) -> tuple[int, dict[str, int]]:
    """(learner turns, fallback events by component)."""
    turns = db.scalar(select(func.count()).where(Event.type == "LEARNER_MESSAGE")) or 0
    component = Event.payload["component"].as_string()
    by = db.execute(
        select(component, func.count()).where(Event.type == "LLM_FALLBACK_USED").group_by(component)
    )
    return turns, {str(c): n for c, n in by}


def _ms(v: float | None) -> str:
    return "N/A" if v is None else f"{v:.0f}"


def stats_report(db: Session) -> str:
    rows = llm_rows(db)
    turns, by = fallbacks(db)
    if not rows and not turns:
        return "no data: no LLM calls or turns recorded yet"
    out = ["purpose      provider/model                calls  err%   p50ms   p95ms"]
    for r in rows:
        err = f"{100 * r.errors / r.calls:.1f}" if r.calls else "N/A"
        name = f"{r.provider}/{r.model}"
        out.append(
            f"{r.purpose:<12} {name:<28} {r.calls:>6} {err:>5} "
            f"{_ms(r.p50_ms):>7} {_ms(r.p95_ms):>7}"
        )
    total = sum(by.values())
    rate = f"{100 * total / turns:.1f}% of {turns} turns" if turns else "N/A (no turns)"
    out.append(f"fallbacks: {total} ({rate}); by component: {by or 'none'}")
    return "\n".join(out)


Prices = dict[tuple[str, str], tuple[float, float]]


def parse_price(spec: str) -> tuple[tuple[str, str], tuple[float, float]]:
    """`provider:model=input,output` in USD per million tokens (the format `make bench` takes)."""
    try:
        name, prices = spec.split("=", 1)
        provider, model = name.split(":", 1)
        inp, out = (float(p) for p in prices.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{spec!r}: expected provider:model=input,output") from exc
    if min(inp, out) < 0:
        raise argparse.ArgumentTypeError(f"{spec!r}: prices cannot be negative")
    return (provider, model), (inp, out)


def cost_report(db: Session, prices: Prices) -> str:
    rows = llm_rows(db)
    if not rows:
        return "no data: no LLM calls recorded yet"
    out = ["purpose      provider/model                prompt_tok  compl_tok   USD (priced calls)"]
    total, any_cost = 0.0, False
    for r in rows:
        price = prices.get((r.provider, r.model))
        cost = "price not set"
        if price:
            usd = (r.prompt_tokens * price[0] + r.completion_tokens * price[1]) / 1_000_000
            total, any_cost = total + usd, True
            cost = f"{usd:.6f}"
        note = "" if r.counted == r.calls else f"  (tokens known for {r.counted}/{r.calls} calls)"
        name = f"{r.provider}/{r.model}"
        out.append(
            f"{r.purpose:<12} {name:<28} {r.prompt_tokens:>10} {r.completion_tokens:>10}"
            f"   {cost}{note}"
        )
    if any_cost:
        out.append(f"total (priced rows only): {total:.6f} USD")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stats")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="LLM latency p50/p95, error rate and fallback rate")
    cost = sub.add_parser("cost-report", help="tokens and cost by component")
    cost.add_argument("--price", action="append", default=[], type=parse_price)
    args = parser.parse_args(argv)
    with get_sessionmaker()() as db:
        if args.command == "stats":
            print(stats_report(db))
        else:
            print(cost_report(db, dict(args.price)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
