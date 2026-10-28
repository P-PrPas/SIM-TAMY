"""AI-EVAL-01: the labeled sets meet the contract sizes and the runner scores them offline."""

import importlib.util
from pathlib import Path

import yaml

from app.ai.llm_client import LLMClient
from app.ai.providers.mock import MockProvider
from app.content.family import load_stories

ROOT = Path(__file__).resolve().parents[5]
SPEC = importlib.util.spec_from_file_location(
    "run_eval_v2", ROOT / "eval" / "v2" / "run_eval_v2.py"
)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def load(name: str) -> dict[str, list[dict]]:
    return yaml.safe_load((ROOT / "eval" / "v2" / f"{name}.yaml").read_text(encoding="utf-8"))


def test_dev_set_meets_the_contract_minimums_and_heldout_is_separate() -> None:
    dev = load("dev")
    minimums = {"paraphrase": 60, "multiturn": 20, "ambiguous": 20, "adversarial": 20}
    assert {k: len(dev[k]) >= v for k, v in minimums.items()} == dict.fromkeys(minimums, True)
    held = load("heldout")
    dev_texts = {r["text"] for rows in dev.values() for r in rows}
    held_texts = {r["text"] for rows in held.values() for r in rows}
    assert held_texts and not (dev_texts & held_texts)  # no leakage between the two files
    ids = [r["id"] for rows in (*dev.values(), *held.values()) for r in rows]
    assert len(ids) == len(set(ids))


def test_runner_scores_every_row_without_a_network() -> None:
    stories = {s.id: s for s in load_stories(ROOT / "content")}
    client = LLMClient(MockProvider(), model="mock", timeout_s=1)
    rows = runner.evaluate(ROOT / "eval" / "v2" / "dev.yaml", client, stories)
    assert len(rows) == sum(len(v) for v in load("dev").values())
    # adversarial rows (leakage, injection, boundary) are never accepted as an intent
    assert all(r["ok"] for r in rows if r["category"] == "adversarial")
