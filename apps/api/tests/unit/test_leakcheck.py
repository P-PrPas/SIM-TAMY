"""scripts/leakcheck.py: clean on the real spec, and it really fails when a field leaks in."""

import copy
import importlib.util
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("leakcheck", ROOT / "scripts" / "leakcheck.py")
assert _spec and _spec.loader
leakcheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(leakcheck)

SPEC: dict[str, Any] = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text(encoding="utf-8"))


def test_the_play_time_schemas_are_clean() -> None:
    assert leakcheck.check(SPEC) == []


def test_a_direct_leak_is_found() -> None:
    bad = copy.deepcopy(SPEC)
    bad["components"]["schemas"]["SessionView"]["properties"]["risk_state"] = {"type": "string"}

    assert leakcheck.check(bad) == ["SessionView: forbidden field 'risk_state'"]


def test_a_leak_behind_a_ref_is_found() -> None:
    bad = copy.deepcopy(SPEC)
    bad["components"]["schemas"]["Reply"]["properties"]["total_score"] = {"type": "number"}

    problems = leakcheck.check(bad)

    assert any("total_score" in p and "Reply" in p for p in problems)
    assert any(
        p.startswith("TurnResponse.replies -> Reply") for p in problems
    )  # reached through a $ref


def test_the_live_glass_box_is_the_only_allowed_exception() -> None:
    bad = copy.deepcopy(SPEC)
    bad["components"]["schemas"]["DecisionResponse"]["properties"]["glassbox"] = {
        "$ref": "#/components/schemas/LiveGlassBox"
    }

    assert leakcheck.check(bad)  # allowed on TurnResponse only
