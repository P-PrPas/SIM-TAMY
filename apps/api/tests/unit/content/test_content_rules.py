"""One row per validation rule: break the valid case one way, expect that file + field path."""

from collections.abc import Callable
from typing import Any

import pytest

Docs = dict[str, Any]

# (id, mutation, expected file, expected path fragment)
BROKEN: list[tuple[str, Callable[[Docs], object], str, str]] = [
    ("wrong_type", lambda d: d["case.yaml"].update(version=1.5), "case.yaml", "version"),
    ("missing_field", lambda d: d["case.yaml"].pop("title_th"), "case.yaml", "title_th"),
    ("typo_key", lambda d: d["case.yaml"].update(titel_th="x"), "case.yaml", "titel_th"),
    (
        "hidden_without_leak_terms",
        lambda d: d["case.yaml"]["facts"][1].pop("leak_terms_th"),
        "case.yaml",
        "facts.1.hidden.leak_terms_th",
    ),
    (
        "hidden_empty_fallback",
        lambda d: d["case.yaml"]["facts"][1].update(fallback_utterances_th=[]),
        "case.yaml",
        "fallback_utterances_th",
    ),
    (
        "unlock_unknown_action",
        lambda d: d["case.yaml"]["facts"][1].update(unlock_on=["A99"]),
        "case.yaml",
        "facts.1.unlock_on",
    ),
    (
        "decision_unknown_action",
        lambda d: d["case.yaml"]["decision_options"][0].update(maps_to_actions=["B99"]),
        "case.yaml",
        "decision_options.0.maps_to_actions",
    ),
    (
        "rule_unknown_action",
        lambda d: d["case.yaml"]["branch_rules"][0].update(on_action_any=["A99"]),
        "case.yaml",
        "branch_rules.0.on_action_any",
    ),
    (
        "rubric_unknown_action",
        lambda d: d["rubric.yaml"]["items"][0]["check"].update(actions=["A99"]),
        "rubric.yaml",
        "items.0.check",
    ),
    *[
        (
            f"blank_{field}",
            lambda d, field=field, v=v: d["case.yaml"]["facts"][1].update({field: v}),
            "case.yaml",
            field,
        )
        for field in ("leak_terms_th", "fallback_utterances_th")
        for v in ([""], ["  "], ["ok", " 	"])
    ],
    (
        "decision_not_unknown_fact",
        lambda d: d["rubric.yaml"]["items"].append(
            {
                **d["rubric.yaml"]["items"][1],
                "id": "R-DEC-02",
                "check": {"type": "decision_not", "option": "proceed", "when_fact_revealed": "H9"},
            }
        ),
        "rubric.yaml",
        "items.2.check",
    ),
    (
        "invalid_risk_state",
        lambda d: d["case.yaml"]["branch_rules"][0].update(set_risk_state="panicking"),
        "case.yaml",
        "branch_rules.0.set_risk_state",
    ),
    (
        "known_fact_is_hidden",
        lambda d: d["case.yaml"]["patient_profile"].update(known_facts=["H1"]),
        "case.yaml",
        "patient_profile.known_facts",
    ),
    (
        "option_not_in_any_rule",
        lambda d: d["case.yaml"]["decision_options"].append(
            {"id": "orphan", "label_th": "o", "maps_to_actions": ["B01"]}
        ),
        "case.yaml",
        "decision_options",
    ),
    (
        "rule_unknown_option",
        lambda d: d["case.yaml"]["branch_rules"][3].update(on_decision="nope"),
        "case.yaml",
        "branch_rules.3.on_decision",
    ),
    (
        "branch_dead_end",  # variant C: PRESSURE no longer leads anywhere
        lambda d: d["case.yaml"]["branch_rules"].pop(4),
        "case.yaml",
        "variant C: phase PRESSURE cannot reach COMPLETED",
    ),
    (
        "branch_never_reaches_completed",  # variant A can only loop inside INTERVIEW
        lambda d: [d["case.yaml"]["branch_rules"][i].update(to="INTERVIEW") for i in (2, 3)],
        "case.yaml",
        "variant A: phase INTERVIEW cannot reach COMPLETED",
    ),
    (
        "critical_info_needs_5_examples",
        lambda d: d["actions.yaml"][0].update(examples_th=["only one"]),
        "actions.yaml",
        "0",
    ),
    (
        "weights_not_100",
        lambda d: d["rubric.yaml"]["competencies"][0].update(weight=10),
        "rubric.yaml",
        "",
    ),
    (
        "unknown_competency",
        lambda d: d["rubric.yaml"]["items"][0].update(competency="NOPE"),
        "rubric.yaml",
        "items.0.competency",
    ),
    (
        "unknown_reference",
        lambda d: d["rubric.yaml"]["items"][0]["fail_finding"].update(references=["REF9"]),
        "rubric.yaml",
        "items.0.F-F.references",
    ),
    (
        "case_id_not_folder_name",
        lambda d: d["case.yaml"].update(case_id="OTHER"),
        "case.yaml",
        "case_id",
    ),
]


def test_valid_case_has_no_issues(run: Callable[..., list]) -> None:
    assert run() == []


@pytest.mark.parametrize(
    ("mutate", "file", "path"), [b[1:] for b in BROKEN], ids=[b[0] for b in BROKEN]
)
def test_each_rule_fails_with_file_and_path(
    run: Callable[..., list], mutate: Callable[[Docs], object], file: str, path: str
) -> None:
    issues = run(mutate)
    assert any(i.file == file and path in f"{i.path} {i.message}" for i in issues), issues


STRICT_ONLY: list[tuple[str, Callable[[Docs], object], str, str]] = [
    (
        "hidden_fact",
        lambda d: d["case.yaml"]["facts"][1].pop("source"),
        "case.yaml",
        "facts.1.source",
    ),
    ("critical_action", lambda d: d["actions.yaml"][0].pop("source"), "actions.yaml", "0.source"),
    (
        "rubric_item",
        lambda d: d["rubric.yaml"]["items"][1].pop("source"),
        "rubric.yaml",
        "items.1.source",
    ),
]


@pytest.mark.parametrize(
    ("mutate", "file", "path"), [b[1:] for b in STRICT_ONLY], ids=[b[0] for b in STRICT_ONLY]
)
def test_missing_source_only_fails_in_strict_mode(
    run: Callable[..., list], mutate: Callable[[Docs], object], file: str, path: str
) -> None:
    assert run(mutate) == []
    assert any(i.file == file and i.path == path for i in run(mutate, strict=True))
