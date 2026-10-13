"""Engine tests on the DEV-001 fixture. Rule 1 (pure engine) is enforced by the AST scan below."""

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.loader import load_case
from app.domain.case import BranchRule, Case, Phase, VariantId
from app.domain.state import SessionState, initial_state
from app.engine.scenario import apply, next_phase

ROOT = Path(__file__).resolve().parents[5]
CASE = load_case(ROOT / "content" / "cases" / "DEV-001").case
ENGINE_DIR = Path(__file__).resolve().parents[3] / "app" / "engine"


def at(phase: Phase, **kw: object) -> SessionState:
    return initial_state().model_copy(update={"phase": phase, **kw})


def rules(*specs: dict[str, object]) -> Case:
    return CASE.model_copy(update={"branch_rules": [BranchRule.model_validate(s) for s in specs]})


# (phase, variant, decision) -> expected phase, for every transition DEV-001 declares
DECISION_TRANSITIONS: list[tuple[Phase, VariantId, str | None, Phase | None]] = [
    ("INTERVIEW", "A", "refer", "CLOSING"),
    ("INTERVIEW", "C", "refer", "PRESSURE"),
    ("INTERVIEW", "A", "proceed_service", "CLOSING"),
    ("INTERVIEW", "C", "proceed_service", "CLOSING"),
    ("INTERVIEW", "A", None, None),
    ("INTERVIEW", "A", "unknown_option", None),
    ("CLOSING", "A", "refer", None),  # rule is for INTERVIEW only
    ("PRESSURE", "C", "refer", None),
]


@pytest.mark.parametrize(("phase", "variant", "decision", "expected"), DECISION_TRANSITIONS)
def test_next_phase_on_decision(
    phase: Phase, variant: VariantId, decision: str | None, expected: Phase | None
) -> None:
    assert next_phase(CASE, variant, phase, decision=decision) == expected


@pytest.mark.parametrize(
    ("actions", "expected"),
    [(["C03"], "CLOSING"), (["C04"], "CLOSING"), (["C01", "C03"], "CLOSING"), (["C01"], None)],
)
def test_next_phase_on_action_in_pressure(actions: list[str], expected: Phase | None) -> None:
    assert next_phase(CASE, "C", "PRESSURE", actions=actions) == expected


def test_first_turn_starts_the_interview() -> None:
    result = apply(initial_state(), ["A01"], CASE, "A")

    assert result.state.phase == "INTERVIEW" and result.state.turn_idx == 1
    assert [(e.type, e.payload["to"]) for e in result.events] == [("PHASE_CHANGED", "INTERVIEW")]


def test_action_without_a_target_phase_only_records_the_action() -> None:
    state = apply(initial_state(), [], CASE, "A").state
    result = apply(state, ["A03"], CASE, "A")  # DEV-001's A03 rule sets risk only (T-021)

    assert result.state.phase == "INTERVIEW" and result.state.fired_action_ids == ("A03",)
    assert result.events == ()


def test_pressure_action_moves_to_closing() -> None:
    result = apply(at("PRESSURE", turn_idx=5), ["C03"], CASE, "C")

    assert result.state.phase == "CLOSING" and result.state.turn_idx == 6
    (event,) = result.events
    assert event.payload == {"from": "PRESSURE", "to": "CLOSING", "trigger": "action"}


def test_repeated_action_is_logged_but_not_fired_twice() -> None:
    state = apply(initial_state(), ["A03"], CASE, "A").state
    result = apply(state, ["A03", "A04"], CASE, "A")

    assert result.state.fired_action_ids == ("A03", "A04")
    assert [(e.type, e.payload["id"]) for e in result.events] == [("ACTION_REPEATED", "A03")]


def test_duplicates_within_one_turn_count_once() -> None:
    result = apply(at("INTERVIEW"), ["A02", "A02"], CASE, "A")
    assert result.state.fired_action_ids == ("A02",) and result.events == ()


def test_fired_order_is_preserved() -> None:
    state = at("INTERVIEW")
    for ids in (["A04"], ["A02", "A03"], ["A01"]):
        state = apply(state, ids, CASE, "A").state
    assert state.fired_action_ids == ("A04", "A02", "A03", "A01")


def test_first_matching_rule_wins_and_variant_filter_applies() -> None:
    case = rules(
        {"from": "INTERVIEW", "on_action_any": ["A01"], "to": "CLOSING", "if_variant": ["C"]},
        {"from": "INTERVIEW", "on_action_any": ["A01"], "to": "PRESSURE"},
        {"from": "INTERVIEW", "on_action_any": ["A01"], "to": "COMPLETED"},
    )
    assert next_phase(case, "C", "INTERVIEW", actions=["A01"]) == "CLOSING"
    assert next_phase(case, "A", "INTERVIEW", actions=["A01"]) == "PRESSURE"


def test_apply_does_not_mutate_its_input_and_state_is_frozen() -> None:
    state = at("INTERVIEW", fired_action_ids=("A01",))
    before = state.model_dump()

    apply(state, ["A02"], CASE, "A")

    assert state.model_dump() == before
    with pytest.raises(ValidationError):
        state.phase = "CLOSING"  # type: ignore[misc]
    assert isinstance(state.fired_action_ids, tuple)


def test_same_input_gives_same_output_100_times() -> None:
    state = at("INTERVIEW", fired_action_ids=("A01",), turn_idx=2)
    outputs = {
        apply(state, ["A03", "A01", "C03"], CASE, "C").state.model_dump_json() for _ in range(100)
    }
    assert len(outputs) == 1


def test_state_round_trips_through_json() -> None:
    state = apply(initial_state(), ["A03", "A04"], CASE, "A").state
    assert SessionState.model_validate_json(state.model_dump_json()) == state
    assert state.model_dump(mode="json")["fired_action_ids"] == ["A03", "A04"]


# ---- AGENTS.md rule 1: the engine has no network, LLM, clock or randomness ----

FORBIDDEN = {
    "random", "secrets", "time", "datetime", "socket", "http", "urllib", "httpx", "httpx2",
    "requests", "asyncio", "os", "subprocess", "app.ai", "app.db", "app.api", "app.content",
}  # fmt: skip


def forbidden_imports(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return {n for n in names if any(n == f or n.startswith(f + ".") for f in FORBIDDEN)}


def test_engine_imports_nothing_impure() -> None:
    files = list(ENGINE_DIR.rglob("*.py"))
    assert files
    offenders = {p.name: bad for p in files if (bad := forbidden_imports(p.read_text("utf-8")))}
    assert offenders == {}


def test_import_scan_is_not_vacuous() -> None:
    assert forbidden_imports("import random\nfrom datetime import datetime")
    assert forbidden_imports("from app.ai.llm_client import LLMClient")
    assert not forbidden_imports("from app.domain.case import Case\nimport typing")
