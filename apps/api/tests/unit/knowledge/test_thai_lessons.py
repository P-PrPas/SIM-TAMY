"""Thai heritage summaries retain the distinction between tradition and clinical evidence."""

from pathlib import Path

from app.content.knowledge import load_knowledge

CONTENT = Path(__file__).resolve().parents[5] / "content"
NEW_UNITS = {
    "KB-TM-ELEMENT-001",
    "KB-ANC-HERITAGE-001",
    "KB-IP-HERITAGE-001",
    "KB-TM-FOOD-001",
    "KB-BF-COLOSTRUM-001",
    "KB-NB-FAMILY-001",
}


def test_heritage_units_separate_tradition_from_other_claim_types_and_trace_every_claim():
    kb = load_knowledge(CONTENT)
    for uid in NEW_UNITS:
        unit = kb.release.unit(uid)
        assert unit is not None and unit.lens is not None
        kinds = {c.type for c in unit.claims}
        assert "tradition" in kinds and len(kinds) > 1
        assert any(loc.source_id == "S51" for c in unit.claims for loc in c.locators)
        assert all(kb.source(loc.source_id) for c in unit.claims for loc in c.locators)
    supplied = kb.source("S51")
    assert supplied is not None and supplied.url is None and supplied.rights_status == "unknown"
    assert all(kb.source(f"S{i}").rights_status == "public_web" for i in range(41, 51))
