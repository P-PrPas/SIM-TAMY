"""T-062: scoring must not depend on time, randomness or hash order (plus the diff helper)."""

import os
import subprocess
import sys
from pathlib import Path

from app.rescore import diff

API_DIR = Path(__file__).resolve().parents[3]

# Scores a fixed play of DEV-001 and prints the JSON; run under different PYTHONHASHSEED values.
SCRIPT = """
from app.content.loader import load_case
from app.engine.scoring import score
from tests.unit.engine.play import DEV_001, Play

loaded = load_case(DEV_001)
p = Play(loaded, "C").turn("A01", "A02").turn("A03", "A04").turn("C01", "C02")
p.decide("refer").turn("C04").note(30).complete()
s = score(p.events, loaded.rubric, loaded.actions, "C")
print(s.model_dump_json())
"""


def run_with_hash_seed(seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run(  # noqa: S603
        [sys.executable, "-c", SCRIPT],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_rescore_scoring_is_byte_identical_under_any_hash_seed() -> None:
    """Fails if anything iterates a set/dict in hash order or reads time/randomness."""
    outputs = {run_with_hash_seed(seed) for seed in ("0", "1", "2", "12345")}
    assert len(outputs) == 1
    assert '"safety_status":"SAFETY_NOT_MET"' in outputs.pop()


def test_rescore_diff_lists_every_changed_path() -> None:
    stored = {"total": 90.0, "items": [{"id": "a", "r": "pass"}, {"id": "b", "r": "pass"}], "x": 1}
    same = {"total": 90.0, "items": [{"id": "a", "r": "pass"}, {"id": "b", "r": "pass"}], "x": 1}
    assert diff(stored, same) == []

    changed = {"total": 80.0, "items": [{"id": "a", "r": "pass"}, {"id": "b", "r": "fail"}], "y": 2}
    paths = sorted(d.split(":")[0] for d in diff(stored, changed))
    assert paths == ["items[1].r", "total", "x", "y"]


def test_rescore_diff_catches_list_length_and_type_changes() -> None:
    assert diff({"a": [1, 2]}, {"a": [1]})
    assert diff({"a": 1}, {"a": "1"})
    assert diff(None, {"a": 1}) == ["$: stored None != recomputed {'a': 1}"]


def test_rescore_diff_separates_a_missing_key_from_an_explicit_null() -> None:
    assert diff({"x": None}, {}) == ["x: stored None != recomputed <missing>"]
    assert diff({}, {"x": None}) == ["x: stored <missing> != recomputed None"]
    assert diff({"x": None}, {"x": None}) == []
    nested = diff({"items": [{"evidence": None}]}, {"items": [{}]})
    assert nested == ["items[0].evidence: stored None != recomputed <missing>"]
