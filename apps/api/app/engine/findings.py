"""Findings builder (FR-DEB-01/03). PURE: item results + the rubric's own finding templates.

pass -> strength (pass_finding); fail and partial -> improve (fail_finding); na -> nothing.
Text and references come from the case; nothing is invented here, and the LLM never writes findings.
"""

from collections.abc import Sequence

from app.domain.rubric import Rubric, rubric_problems
from app.domain.scoring import Finding, ItemResult
from app.engine.scoring import InvalidRubric


class DuplicateResult(ValueError):
    """Two results for one rubric item: one would silently hide the other."""


def build_findings(results: Sequence[ItemResult], rubric: Rubric) -> tuple[Finding, ...]:
    problems = rubric_problems(rubric)
    if problems:  # duplicate item ids would let a later result overwrite an earlier one
        raise InvalidRubric("; ".join(f"{path}: {msg}" for path, msg in problems))
    ids = [r.id for r in results]
    if duplicated := sorted({i for i in ids if ids.count(i) > 1}):
        raise DuplicateResult(f"more than one result for rubric item(s): {', '.join(duplicated)}")
    by_id = {r.id: r for r in results}
    findings: list[Finding] = []
    for item in rubric.items:
        result = by_id.get(item.id)
        if result is None or result.result == "na":
            continue
        strength = result.result == "pass"
        template = item.pass_finding if strength else item.fail_finding
        findings.append(
            Finding(
                id=template.id,
                polarity="strength" if strength else "improve",
                rubric_item_id=item.id,
                text_th=template.template_th,
                evidence_refs=tuple(e.event_id for e in result.evidence),
                reference_ids=tuple(template.references),
            )
        )
    return tuple(findings)
