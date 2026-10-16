"""Guard the held-out, synthetic Action dev set used by T-005 (T-071)."""

import json
from collections import Counter
from pathlib import Path

from app.ai.thai import normalize_th
from app.content.loader import load_case

ROOT = Path(__file__).resolve().parents[5]
DEVSET = ROOT / "eval" / "devset" / "actions_th.jsonl"
CASE = ROOT / "content" / "cases" / "DEV-001"
KINDS = {"direct", "colloquial", "short", "typo", "ambiguous", "irrelevant", "multi_intent"}


def rows() -> list[dict[str, object]]:
    return [json.loads(line) for line in DEVSET.read_text(encoding="utf-8").splitlines()]


def test_devset_has_enough_unique_held_out_utterances() -> None:
    samples = rows()
    assert len(samples) >= 50
    utterances = [normalize_th(str(row["text_th"])) for row in samples]
    assert all(utterances)
    assert len(utterances) == len(set(utterances))
    training_examples = {
        normalize_th(example)
        for action in load_case(CASE).actions
        for example in action.examples_th
    }
    assert not training_examples.intersection(utterances)


def test_devset_labels_follow_the_fixture_and_chat_contract() -> None:
    offered = {a.id for a in load_case(CASE).actions if a.category in {"HX", "COM"}}
    for row in rows():
        assert set(row) == {"case_id", "variant", "phase", "text_th", "action_ids", "kind"}
        assert row["case_id"] == "DEV-001"
        assert row["variant"] in {"A", "C"}
        assert row["phase"] in {"INTERVIEW", "PRESSURE"}
        assert isinstance(row["text_th"], str) and row["text_th"].strip()
        assert row["kind"] in KINDS
        assert isinstance(row["action_ids"], list)
        labels = row["action_ids"]
        assert len(labels) == len(set(labels)) <= 5
        assert set(labels) <= offered
        if row["phase"] == "PRESSURE":
            assert row["variant"] == "C"
        if set(labels) & {"C03", "C04"}:
            assert row["phase"] == "PRESSURE"
        if row["kind"] in {"ambiguous", "irrelevant"}:
            assert labels == []
        if row["kind"] == "multi_intent":
            assert len(labels) >= 2


def test_devset_covers_actions_and_challenging_language() -> None:
    samples = rows()
    offered = {a.id for a in load_case(CASE).actions if a.category in {"HX", "COM"}}
    counts = Counter(label for row in samples for label in row["action_ids"])
    kinds = Counter(str(row["kind"]) for row in samples)
    assert all(counts[action_id] >= 3 for action_id in offered)
    assert all(kinds[kind] >= 2 for kind in KINDS)
    assert sum(not row["action_ids"] for row in samples) >= 6
