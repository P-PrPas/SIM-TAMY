"""T-063: findings come only from the rubric's own templates, deterministically (FR-DEB-01/03)."""

import random
from collections.abc import Callable
from typing import Any

from app.content.loader import LoadedCase
from app.domain.case import VariantId
from app.domain.scoring import ItemResult
from app.engine.findings import build_findings
from app.engine.scoring import score
from tests.unit.engine.play import Play

NewPlay = Callable[[VariantId], Play]


def scored(p: Play) -> Any:
    return score(p.events, p.loaded.rubric, p.loaded.actions, p.variant)


def findings_for(p: Play) -> Any:
    return build_findings(scored(p).items, p.loaded.rubric)


def test_findings_perfect_path_is_all_strengths_with_evidence(play: NewPlay) -> None:
    p = play("A").turn("A01", "A02").turn("A03", "A04").turn("C01", "C02")
    p.decide("refer").note(30).complete()
    found = findings_for(p)

    assert found and {f.polarity for f in found} == {"strength"}
    assert all(f.evidence_refs for f in found)  # every strength points at events
    by_item = {f.rubric_item_id: f for f in found}
    assert by_item["R-RISK-01"].id == "R-RISK-01-P"
    rubric_text = {i.id: i.pass_finding.template_th for i in p.loaded.rubric.items}
    assert all(f.text_th == rubric_text[f.rubric_item_id] for f in found)  # template, verbatim


def test_findings_failures_are_improve_with_their_references(play: NewPlay) -> None:
    p = play("A").turn("A01", "A02").turn("A03", "A04").decide("proceed_service").complete()
    found = findings_for(p)
    improve = [f for f in found if f.polarity == "improve"]

    assert {f.rubric_item_id for f in improve} >= {"R-DEC-01", "R-ESC-01", "R-DEC-03"}
    assert all(f.reference_ids == ("REF1",) for f in improve)  # every improvement has a reference
    assert all(f.evidence_refs for f in improve)
    unsafe = next(f for f in improve if f.rubric_item_id == "R-ESC-01")
    unsafe_event = next(e for e in p.events if e.type == "UNSAFE_ACTION")
    assert unsafe.evidence_refs == (unsafe_event.id,)


def test_findings_partial_credit_is_an_improvement(play: NewPlay) -> None:
    p = play("A").turn("A01", "A02").turn("A03").decide("refer")  # asked A03 but not A04
    partial = {r.id: r for r in scored(p).items}["R-RISK-02"]
    assert partial.result == "partial"

    f = next(f for f in findings_for(p) if f.rubric_item_id == "R-RISK-02")
    assert f.polarity == "improve" and f.id == "R-RISK-02-F"


def test_findings_skip_items_that_do_not_apply(play: NewPlay) -> None:
    p = play("A").turn("A01")
    ids = {f.rubric_item_id for f in findings_for(p)}
    assert "R-COMM-02" not in ids and "R-COMM-03" not in ids  # variant-C-only items


def test_findings_follow_rubric_order_and_ignore_unknown_or_missing_results(
    play: NewPlay, dev001: LoadedCase
) -> None:
    p = play("A").turn("A01", "A02").turn("A03")
    results = scored(p).items
    rubric_ids = [i.id for i in dev001.rubric.items]

    found = build_findings(results, dev001.rubric)
    assert [f.rubric_item_id for f in found] == [
        i for i in rubric_ids if i in {f.rubric_item_id for f in found}
    ]

    stray = ItemResult(
        id="R-NOPE", competency="HX", result="fail", points=1, earned=0.0, critical=False
    )
    assert build_findings([*results, stray], dev001.rubric) == found  # not in the rubric: ignored
    assert build_findings(results[:3], dev001.rubric) == build_findings(results, dev001.rubric)[:3]


def test_findings_are_identical_on_every_run_and_for_any_log_order(play: NewPlay) -> None:
    p = play("A").turn("A01", "A02").turn("A03", "A04").decide("proceed_service").complete()
    first = findings_for(p)
    shuffled = list(p.events)
    random.Random(3).shuffle(shuffled)
    again = build_findings(
        score(shuffled, p.loaded.rubric, p.loaded.actions, "A").items, p.loaded.rubric
    )

    assert all(findings_for(p) == first for _ in range(100)) and again == first
    assert [f.model_dump_json() for f in again] == [f.model_dump_json() for f in first]


def test_findings_never_invent_references(play: NewPlay, dev001: LoadedCase) -> None:
    stripped = dev001.rubric.model_copy(
        update={
            "items": tuple(
                i.model_copy(
                    update={"fail_finding": i.fail_finding.model_copy(update={"references": []})}
                )
                for i in dev001.rubric.items
            )
        }
    )
    p = play("A").turn("A01").decide("proceed_service")
    results = scored(p).items

    improve = [f for f in build_findings(results, stripped) if f.polarity == "improve"]
    assert improve and all(f.reference_ids == () for f in improve)  # content gap stays visible
