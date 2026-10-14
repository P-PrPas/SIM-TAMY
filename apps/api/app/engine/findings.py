"""Findings builder (FR-DEB-01/03). PURE: item results + the rubric's own finding templates.

pass -> strength (pass_finding); fail and partial -> improve (fail_finding); na -> nothing.
Text and references come from the case; nothing is invented here, and the LLM never writes findings.
"""

from collections.abc import Sequence

from app.domain.rubric import Rubric
from app.domain.scoring import Finding, ItemResult


def build_findings(results: Sequence[ItemResult], rubric: Rubric) -> tuple[Finding, ...]:
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
