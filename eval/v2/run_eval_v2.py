"""AI-EVAL-01: score the AI-01 intent pipeline on the labeled Thai sets in eval/v2/.

Run from apps/api so `app` imports:  CONTENT_DIR=../../content python ../../eval/v2/run_eval_v2.py
The provider is the offline mock by default (a deterministic lexical stand-in, NOT a language
model): its numbers describe the mock and the guard rules, never a real model. Use
`--provider env` to run the configured LLM_PROVIDER and report what that measures (AGENTS rule 11).
Nothing here is a threshold: it prints n, accuracy and every error. Held-out rows are reported on
their own line and must never be used to tune prompts or rules.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from app.ai.intent import HistoryItem, guard, interpret_intent, options_for
from app.ai.llm_client import LLMClient, get_llm_client
from app.ai.providers.mock import MockProvider
from app.content.family import load_stories
from app.core.config import get_settings

HERE = Path(__file__).resolve().parent
STORY_KEYS = {"A": "gs-a-postpartum-warning", "B": "gs-b-thai-recovery"}
CATEGORIES = ("paraphrase", "multiturn", "ambiguous", "adversarial")


def run_row(client: LLMClient, story: Any, row: dict[str, Any]) -> tuple[str, str | None]:
    """The same boundary + AI-01 post-processing the room controller applies."""
    blocked = guard(row["text"])
    if blocked == "boundary":
        return "boundary", None
    if blocked == "injection":
        return "generic", "OUT_OF_SCOPE"
    step = next(s for s in story.steps if s.id == row["step"])
    history = [HistoryItem(h["text"], h.get("code")) for h in row.get("history", [])]
    result = interpret_intent(client, options_for(step), row["text"], history)
    return result.kind, result.code


def correct(expect: dict[str, Any], kind: str, code: str | None) -> bool:
    want = expect["kind"]
    if want == "accept":
        return kind == "accept" and code == expect["code"]
    if want == "not_accept":
        return kind != "accept"
    if want == "clarify_or_generic":
        return kind in {"clarify", "generic"}
    return kind == want


def evaluate(path: Path, client: LLMClient, stories: dict[str, Any]) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for category in CATEGORIES:
        for row in data.get(category, []):
            kind, code = run_row(client, stories[STORY_KEYS[row["story"]]], row)
            out.append(
                {"id": row["id"], "category": category, "ok": correct(row["expect"], kind, code)}
                | {"got": f"{kind}:{code}", "want": row["expect"], "text": row["text"]}
            )
    return out


def report(label: str, rows: list[dict[str, Any]]) -> int:
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by[r["category"]].append(r)
    print(f"\n[{label}]  category        n  correct  accuracy")
    for category in CATEGORIES:
        part = by[category]
        ok = sum(r["ok"] for r in part)
        pct = f"{100 * ok / len(part):.1f}%" if part else "n/a"
        print(f"  {category:<14} {len(part):>3}  {ok:>7}  {pct:>8}")
    total_ok = sum(r["ok"] for r in rows)
    print(f"  {'all':<14} {len(rows):>3}  {total_ok:>7}  {100 * total_ok / max(1, len(rows)):.1f}%")
    errors = [r for r in rows if not r["ok"]]
    for r in errors:
        print(f"  ERROR {r['id']} ({r['category']}): got {r['got']} want {r['want']} | {r['text']}")
    return len(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval-v2")
    parser.add_argument("--provider", choices=("mock", "env"), default="mock")
    parser.add_argument("--set", choices=("dev", "heldout", "both"), default="both")
    args = parser.parse_args(argv)
    stories = {s.id: s for s in load_stories(get_settings().content_dir)}
    client = (
        LLMClient(MockProvider(), model="mock-model", timeout_s=5)
        if args.provider == "mock"
        else get_llm_client("interpreter")
    )
    print(
        f"AI-01 eval, provider={args.provider} (mock = deterministic lexical stand-in, not an LLM)"
    )
    names = ("dev", "heldout") if args.set == "both" else (args.set,)
    for name in names:
        report(name, evaluate(HERE / f"{name}.yaml", client, stories))
    return 0


if __name__ == "__main__":
    sys.exit(main())
