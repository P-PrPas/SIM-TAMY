"""ADR-15 shared contracts: knowledge release gating and AI output schemas."""

import pytest
from pydantic import ValidationError

from app.ai.contracts import (
    CitedClaim,
    DebriefPoint,
    EvidenceItem,
    EvidencePack,
    IntentInterpretation,
)
from app.domain.knowledge import KnowledgeRelease, KnowledgeUnit


def unit(uid: str, *, status: str = "published", rights: str = "own_summary") -> KnowledgeUnit:
    return KnowledgeUnit.model_validate(
        {
            "id": uid,
            "version": "1.0.0",
            "title_th": "t",
            "care_stage": "postpartum",
            "domain": 6,
            "claims": [
                {
                    "id": "c1",
                    "type": "safety",
                    "text_th": "x",
                    "locators": [{"source_id": "S36", "locator": "KB p.11"}],
                }
            ],
            "evidence_status": "secondary",
            "rights_status": rights,
            "publish_status": status,
            "reviewed_on": "2026-10-28",
        }
    )


def test_release_keeps_only_published_usable_units_and_is_content_addressed() -> None:
    units = [
        unit("KB-PP-SAFE-001"),
        unit("KB-PP-SAFE-002", status="draft"),
        unit("KB-PP-SAFE-003", status="retired"),
        unit("KB-PP-SAFE-004", rights="metadata_only"),
    ]
    release = KnowledgeRelease.build(units)

    assert [u.id for u in release.units] == ["KB-PP-SAFE-001"]
    assert release.id == KnowledgeRelease.build(list(reversed(units))).id
    assert release.id != KnowledgeRelease.build([unit("KB-PP-SAFE-005")]).id


def test_unit_rejects_a_claim_without_a_source_locator() -> None:
    raw = unit("KB-PP-SAFE-001").model_dump()
    raw["claims"][0]["locators"] = []
    with pytest.raises(ValidationError):
        KnowledgeUnit.model_validate(raw)


def test_intent_ignores_extra_model_keys_and_defaults_to_uncertain() -> None:
    parsed = IntentInterpretation.model_validate({"intent_code": "ASK_TIMELINE", "score": 99})

    assert parsed.uncertainty_score == 1.0 and not hasattr(parsed, "score")


def test_evidence_pack_only_recognises_citations_it_contains() -> None:
    item = EvidenceItem(
        knowledge_id="KB-PP-SAFE-001",
        knowledge_version="1.0.0",
        claim_id="c1",
        source_id="S36",
        source_locator="KB p.11",
        allowed_text_th="x",
    )
    pack = EvidencePack(release_id="rel-1", items=[item])
    cited = CitedClaim(**item.model_dump(exclude={"allowed_text_th"}))

    assert pack.cites(cited)
    assert not pack.cites(cited.model_copy(update={"source_locator": "made up"}))


def test_debrief_point_must_point_at_an_event() -> None:
    with pytest.raises(ValidationError):
        DebriefPoint(text="x", event_ids=[])
