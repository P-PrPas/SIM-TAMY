"""AI-02a: retrieve_claims is deterministic and never leaves the pinned release."""

from app.domain.knowledge import KnowledgeRelease, KnowledgeUnit
from app.services.knowledge import retrieve_claims


def unit(
    uid: str,
    *,
    stage: str = "postpartum",
    tags: list[str] | None = None,
    status: str = "published",
    rights: str = "own_summary",
    audience: str = "parent",
    claims: int = 2,
) -> KnowledgeUnit:
    return KnowledgeUnit.model_validate(
        {
            "id": uid,
            "version": "1.0.0",
            "title_th": "t",
            "audience": audience,
            "care_stage": stage,
            "domain": 6,
            "tags": tags or [],
            "claims": [
                {
                    "id": f"c{n}",
                    "type": "safety",
                    "text_th": f"{uid} ข้อ {n}",
                    "locators": [
                        {"source_id": "S36", "locator": f"KB p.{n}"},
                        {"source_id": "S05", "locator": "KB p.9"},
                    ],
                }
                for n in range(1, claims + 1)
            ],
            "evidence_status": "secondary",
            "rights_status": rights,
            "publish_status": status,
            "reviewed_on": "2026-10-28",
        }
    )


UNITS = [
    unit("KB-PP-AAA-001", tags=["bleeding"]),
    unit("KB-PP-BBB-001", tags=["bleeding", "urgent"]),
    unit("KB-PP-CCC-001"),
    unit("KB-PP-DRAFT-001", status="draft", tags=["bleeding", "urgent"]),
    unit("KB-PP-OLD-001", status="retired", tags=["bleeding", "urgent"]),
    unit("KB-PP-CAT-001", rights="metadata_only", tags=["bleeding", "urgent"]),
    unit("KB-PP-EDU-001", audience="educator", tags=["bleeding"]),
    unit("KB-NB-NEW-001", stage="newborn", tags=["bleeding"]),
]
RELEASE = KnowledgeRelease.build(UNITS)
ALL = [u.id for u in UNITS]


def ids(pack: object) -> list[tuple[str, str]]:
    return [(i.knowledge_id, i.claim_id) for i in pack.items]  # type: ignore[attr-defined]


def test_unreleased_units_are_never_retrieved_even_when_asked_for() -> None:
    pack = retrieve_claims(RELEASE, unit_ids=ALL, limit=100)

    returned = {k for k, _ in ids(pack)}
    assert returned.isdisjoint({"KB-PP-DRAFT-001", "KB-PP-OLD-001", "KB-PP-CAT-001"})
    assert pack.release_id == RELEASE.id


def test_only_requested_units_matching_audience_and_stage_are_used() -> None:
    pack = retrieve_claims(RELEASE, unit_ids=ALL, care_stage="postpartum", limit=100)

    assert {k for k, _ in ids(pack)} == {"KB-PP-AAA-001", "KB-PP-BBB-001", "KB-PP-CCC-001"}
    only = retrieve_claims(RELEASE, unit_ids=["KB-PP-CCC-001"], limit=100)
    assert {k for k, _ in ids(only)} == {"KB-PP-CCC-001"}
    educator = retrieve_claims(RELEASE, unit_ids=ALL, audience="educator", limit=100)
    assert {k for k, _ in ids(educator)} == {"KB-PP-EDU-001"}
    assert retrieve_claims(RELEASE, unit_ids=[]).items == []


def test_ranking_is_tag_overlap_then_unit_then_claim_order_and_is_limited() -> None:
    pack = retrieve_claims(
        RELEASE, unit_ids=ALL, care_stage="postpartum", tags=["bleeding", "urgent"], limit=3
    )

    assert ids(pack) == [("KB-PP-BBB-001", "c1"), ("KB-PP-BBB-001", "c2"), ("KB-PP-AAA-001", "c1")]
    default = retrieve_claims(RELEASE, unit_ids=ALL, care_stage="postpartum")
    assert len(default.items) == 5


def test_each_item_cites_the_first_locator_and_the_pack_accepts_it() -> None:
    from app.ai.contracts import CitedClaim

    item = retrieve_claims(RELEASE, unit_ids=["KB-PP-AAA-001"]).items[0]

    assert (item.source_id, item.source_locator) == ("S36", "KB p.1")
    assert item.knowledge_version == "1.0.0" and item.allowed_text_th == "KB-PP-AAA-001 ข้อ 1"
    pack = retrieve_claims(RELEASE, unit_ids=["KB-PP-AAA-001"])
    assert pack.cites(CitedClaim(**item.model_dump(exclude={"allowed_text_th"})))


def test_retrieval_is_deterministic_regardless_of_input_order() -> None:
    first = retrieve_claims(RELEASE, unit_ids=ALL, tags=["urgent"], limit=4)
    shuffled = KnowledgeRelease.build(list(reversed(UNITS)))
    second = retrieve_claims(shuffled, unit_ids=list(reversed(ALL)), tags=["urgent"], limit=4)

    assert first == second and first.release_id == shuffled.id


def test_retiring_a_unit_changes_the_release_and_removes_it_from_new_packs() -> None:
    retired = KnowledgeRelease.build([*UNITS[1:], unit("KB-PP-AAA-001", status="retired")])
    old_pack = retrieve_claims(RELEASE, unit_ids=["KB-PP-AAA-001"])
    new_pack = retrieve_claims(retired, unit_ids=["KB-PP-AAA-001"])

    assert old_pack.items and new_pack.items == []
    assert retired.id != RELEASE.id  # the earlier snapshot stays addressable by its own ID
