"""Cross-file content rules (PRD 7.1 "กฎการ validate", FR-CASE-04). Pure, no I/O."""

from collections.abc import Iterable
from typing import get_args

from app.content.loader import Issue, LoadedCase
from app.domain.case import Case, HiddenFact
from app.domain.rubric import ActionPresentAll, CountAtLeast
from app.domain.state import RiskState

# Phase moves the engine owns; branch_rules never spell them out (PRD 7.1 example has neither).
_IMPLICIT_EDGES = [("INTRO", "INTERVIEW"), ("CLOSING", "COMPLETED")]


def check(loaded: LoadedCase, *, strict: bool = False) -> list[Issue]:
    case, actions, rubric = loaded.case, loaded.actions, loaded.rubric
    issues: list[Issue] = []

    def need(file: str, path: str, ids: Iterable[str], valid: set[str], what: str) -> None:
        issues.extend(Issue(file, path, f"unknown {what} {i!r}") for i in ids if i not in valid)

    def in_case(path: str, ids: Iterable[str], valid: set[str], what: str) -> None:
        need("case.yaml", path, ids, valid, what)

    def in_rubric(path: str, ids: Iterable[str], valid: set[str], what: str) -> None:
        need("rubric.yaml", path, ids, valid, what)

    action_ids = {a.id for a in actions}
    fact_ids = {f.id for f in case.facts}
    hidden_ids = {f.id for f in case.facts if f.kind == "hidden"}
    option_ids = {o.id for o in case.decision_options}
    variant_ids: set[str] = set(case.variants)
    ref_ids = {r.id for r in case.references}
    competency_ids = {c.id for c in rubric.competencies}

    for file, ids in (
        ("actions.yaml", [a.id for a in actions]),
        ("case.yaml", [f.id for f in case.facts]),
    ):
        issues += [
            Issue(file, "", f"duplicate id {i!r}")
            for i in sorted({i for i in ids if ids.count(i) > 1})
        ]

    for n, fact in enumerate(case.facts):
        if isinstance(fact, HiddenFact):
            in_case(f"facts.{n}.unlock_on", fact.unlock_on, action_ids, "action id")
    for n, opt in enumerate(case.decision_options):
        in_case(
            f"decision_options.{n}.maps_to_actions", opt.maps_to_actions, action_ids, "action id"
        )
    for n, rule in enumerate(case.branch_rules):
        in_case(
            f"branch_rules.{n}.on_action_any", rule.on_action_any or [], action_ids, "action id"
        )
        in_case(f"branch_rules.{n}.if_variant", rule.if_variant or [], variant_ids, "variant")
        if rule.set_risk_state:
            in_case(
                f"branch_rules.{n}.set_risk_state",
                [rule.set_risk_state],
                set(get_args(RiskState)),
                "risk state",
            )
        if rule.on_decision:
            in_case(
                f"branch_rules.{n}.on_decision", [rule.on_decision], option_ids, "decision option"
            )
    for unused in sorted(option_ids - {r.on_decision for r in case.branch_rules}):
        issues.append(
            Issue(
                "case.yaml", "decision_options", f"option {unused!r} is not used by any branch rule"
            )
        )

    known = case.patient_profile.known_facts
    in_case("patient_profile.known_facts", known, fact_ids, "fact id")
    issues += [
        Issue("case.yaml", "patient_profile.known_facts", f"{i!r} is a hidden fact, not known")
        for i in known
        if i in hidden_ids
    ]
    in_case(
        "critical_facts_for_replay", case.critical_facts_for_replay, hidden_ids, "hidden fact id"
    )

    for n, item in enumerate(rubric.items):
        p, c = f"items.{n}", item.check
        in_rubric(f"{p}.competency", [item.competency], competency_ids, "competency")
        in_rubric(
            f"{p}.applies_to_variants", item.applies_to_variants or [], variant_ids, "variant"
        )
        # getattr: each check type carries a different subset of these reference fields
        in_rubric(f"{p}.check", getattr(c, "actions", []), action_ids, "action id")
        in_rubric(
            f"{p}.check",
            [getattr(c, a) for a in ("first", "then") if hasattr(c, a)],
            action_ids,
            "action id",
        )
        in_rubric(
            f"{p}.check",
            [getattr(c, a) for a in ("option", "decision") if hasattr(c, a)],
            option_ids,
            "decision option",
        )
        revealed = [getattr(c, "when_fact_revealed", None)]
        in_rubric(
            f"{p}.check",
            [*getattr(c, "fact_ids", []), *filter(None, revealed)],
            fact_ids,
            "fact id",
        )
        if item.critical and isinstance(c, ActionPresentAll | CountAtLeast):
            issues.append(
                Issue(
                    "rubric.yaml",
                    f"{p}.check",
                    "a critical item cannot use a partial-credit check "
                    f"({c.type}): the Critical Safety gate only trips on fail",
                )
            )
        for finding in (item.pass_finding, item.fail_finding):
            in_rubric(f"{p}.{finding.id}.references", finding.references, ref_ids, "reference id")

    issues += _unreachable(case)

    if strict:
        issues += [
            Issue("case.yaml", f"facts.{n}.source", "missing source (--strict)")
            for n, fact in enumerate(case.facts)
            if fact.kind == "hidden" and not fact.source
        ]
        issues += [
            Issue("actions.yaml", f"{n}.source", "missing source (--strict)")
            for n, a in enumerate(actions)
            if a.type == "critical_info" and not a.source
        ]
        issues += [
            Issue(
                "rubric.yaml",
                f"items.{n}.fail_finding.references",
                "an improve finding needs at least one reference (--strict, FR-DEB-03)",
            )
            for n, item in enumerate(rubric.items)
            if not item.fail_finding.references
        ]
        issues += [
            Issue("rubric.yaml", f"items.{n}.source", "missing source (--strict)")
            for n, item in enumerate(rubric.items)
            if not item.source
        ]
    return issues


def _reach(adj: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    todo = [start]
    while todo:
        node = todo.pop()
        if node not in seen:
            seen.add(node)
            todo += adj.get(node, ())
    return seen


def _unreachable(case: Case) -> list[Issue]:
    """Per variant: every phase reachable from INTRO must be able to reach COMPLETED."""
    issues: list[Issue] = []
    for variant in case.variants:
        adj: dict[str, set[str]] = {}
        # a rule with no if_variant applies to every variant
        rules = [r for r in case.branch_rules if r.to and variant in (r.if_variant or [variant])]
        for a, b in [*((r.from_, r.to) for r in rules), *_IMPLICIT_EDGES]:
            adj.setdefault(a, set()).add(str(b))
        dead = sorted(p for p in _reach(adj, "INTRO") if "COMPLETED" not in _reach(adj, p))
        issues += [
            Issue(
                "case.yaml", "branch_rules", f"variant {variant}: phase {p} cannot reach COMPLETED"
            )
            for p in dead
        ]
    return issues
