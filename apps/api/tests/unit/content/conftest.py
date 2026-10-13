"""A tiny synthetic case (not clinical content) that passes every rule, plus helpers to break it."""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.content.loader import ContentError, Issue, load_case
from app.content.validate import check

Docs = dict[str, Any]


def finding(i: str) -> dict[str, Any]:
    return {"id": i, "template_th": "t", "references": ["REF1"]}


def valid_docs() -> Docs:
    case = {
        "case_id": "TEST-001",
        "version": "0.1",
        "status": "Draft",
        "title_th": "t",
        "learning_objectives": ["risk_recognition"],
        "patient_profile": {"display_th": "d", "known_facts": ["K1"]},
        "facts": [
            {"id": "K1", "kind": "known", "text_th": "k"},
            {
                "id": "H1",
                "kind": "hidden",
                "text_th": "h",
                "unlock_on": ["A03"],
                "leak_terms_th": ["x"],
                "fallback_utterances_th": ["y"],
                "risk_relevance": "critical",
                "source": "s",
            },
        ],
        "variants": {
            "A": {"persona": {"minimization": "low", "style_th": "s"}, "fact_set": "default"},
            "C": {
                "persona": {"minimization": "high", "family_pressure": True, "style_th": "s"},
                "fact_set": "default",
                "pressure_script": [{"speaker": "relative", "text_th": "p"}],
            },
        },
        "decision_options": [
            {"id": "refer", "label_th": "r", "maps_to_actions": ["B01"]},
            {"id": "proceed", "label_th": "p", "maps_to_actions": ["B03"]},
        ],
        "branch_rules": [
            {"from": "INTERVIEW", "on_action_any": ["A03"], "set_risk_state": "recognized"},
            {"from": "INTERVIEW", "on_decision": "refer", "to": "PRESSURE", "if_variant": ["C"]},
            {"from": "INTERVIEW", "on_decision": "refer", "to": "CLOSING", "if_variant": ["A"]},
            {"from": "INTERVIEW", "on_decision": "proceed", "to": "CLOSING"},
            {"from": "PRESSURE", "on_action_any": ["C03"], "to": "CLOSING"},
        ],
        "critical_facts_for_replay": ["H1"],
        "outcome_scripts": {"Referral": {"timeline_th": ["t"], "disclaimer_th": "d"}},
        "references": [{"id": "REF1", "title_th": "t", "locator": "l"}],
    }
    actions = [
        {
            "id": "A03",
            "category": "HX",
            "type": "critical_info",
            "label_th": "l",
            "examples_th": ["1", "2", "3", "4", "5"],
            "source": "s",
        },
        {"id": "B01", "category": "DEC", "type": "decision", "label_th": "l", "examples_th": []},
        {"id": "B03", "category": "DEC", "type": "decision", "label_th": "l", "examples_th": []},
        {
            "id": "C03",
            "category": "COM",
            "type": "communication",
            "label_th": "l",
            "examples_th": [],
        },
    ]
    rubric = {
        "rubric_version": "0.1",
        "competencies": [
            {"id": "RISK", "name_th": "n", "weight": 60},
            {"id": "DEC", "name_th": "n", "weight": 40},
        ],
        "items": [
            {
                "id": "R-RISK-01",
                "competency": "RISK",
                "points": 10,
                "critical": True,
                "check": {"type": "action_present_any", "actions": ["A03"]},
                "pass_finding": finding("F-P"),
                "fail_finding": finding("F-F"),
                "source": "s",
            },
            {
                "id": "R-DEC-01",
                "competency": "DEC",
                "points": 10,
                "applies_to_variants": ["A", "C"],
                "check": {"type": "decision_equals", "option": "refer"},
                "pass_finding": finding("F-P2"),
                "fail_finding": finding("F-F2"),
                "source": "s",
            },
        ],
    }
    return {"case.yaml": case, "actions.yaml": actions, "rubric.yaml": rubric}


def write_case(root: Path, docs: Docs) -> Path:
    case_dir = root / "cases" / "TEST-001"
    case_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in docs.items():
        (case_dir / name).write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return case_dir


Mutate = Callable[[Docs], None]


@pytest.fixture
def build(tmp_path: Path) -> Callable[[Mutate | None], Path]:
    def _build(mutate: Mutate | None = None) -> Path:
        docs = copy.deepcopy(valid_docs())
        if mutate:
            mutate(docs)
        return write_case(tmp_path, docs)

    return _build


@pytest.fixture
def run(build: Callable[[Mutate | None], Path]) -> Callable[..., list[Issue]]:
    """run(mutate, strict=False) -> issues for the (mutated) valid case."""

    def _run(mutate: Mutate | None = None, *, strict: bool = False) -> list[Issue]:
        try:
            return check(load_case(build(mutate)), strict=strict)
        except ContentError as exc:
            return exc.issues

    return _run
