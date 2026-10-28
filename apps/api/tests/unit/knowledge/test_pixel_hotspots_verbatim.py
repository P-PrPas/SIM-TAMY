"""Pixel lesson hotspots for safety units are contiguous quotes of their own claim (LP-01).

Danger-sign wording must never be rephrased in a tap-to-learn sheet: each hotspot `text_th`
(whitespace-normalised) has to be a substring of the claim it hangs on. Units without hotspots
pass vacuously, so later PRs that add hotspots to them are bound by this test.
"""

from pathlib import Path

import pytest

from app.content.knowledge import load_knowledge

CONTENT = Path(__file__).resolve().parents[5] / "content"
SAFETY_UNITS = ("KB-PP-WARN-001", "KB-TM-SAFE-001", "KB-NB-WARN-001")
# KB-PP-WARN-001 is authored in this PR; the other two bind later PRs.
AUTHORED = {"KB-PP-WARN-001": [4, 3, 3, 4]}


def squash(text: str) -> str:
    return "".join(text.split())


@pytest.fixture(scope="module")
def kb():
    return load_knowledge(CONTENT)


@pytest.mark.parametrize("unit_id", SAFETY_UNITS)
def test_hotspot_text_is_a_contiguous_quote_of_its_claim(kb, unit_id: str) -> None:
    unit = kb.release.unit(unit_id)
    assert unit is not None
    for claim in unit.claims:
        for spot in claim.hotspots:
            assert squash(spot.text_th) in squash(claim.text_th), f"{unit_id} {claim.id} {spot.id}"
            assert 1 <= len(spot.label_th.split()) <= 3, f"{unit_id} {claim.id} {spot.id} label"


@pytest.mark.parametrize(("unit_id", "counts"), AUTHORED.items())
def test_authored_units_cover_every_claim(kb, unit_id: str, counts: list[int]) -> None:
    unit = kb.release.unit(unit_id)
    assert unit is not None
    assert [len(c.hotspots) for c in unit.claims] == counts
