"""AI-02a: deterministic retrieval of released claims into a bounded EvidencePack."""

from app.ai.contracts import EvidenceItem, EvidencePack
from app.domain.knowledge import KnowledgeRelease


def retrieve_claims(
    release: KnowledgeRelease,
    *,
    unit_ids: list[str],
    care_stage: str | None = None,
    audience: str = "parent",
    tags: list[str] | None = None,
    limit: int = 5,
) -> EvidencePack:
    """Claims from the pinned release only: filter, rank by tag overlap, then by unit/claim ID.

    No model is involved, so the same inputs always give the same pack (AI-T07/T08).
    """
    wanted, tagset = set(unit_ids), set(tags or [])
    matching = [
        u
        for u in release.units
        if u.id in wanted and u.audience == audience and care_stage in (None, u.care_stage)
    ]
    ranked = sorted(matching, key=lambda u: (-len(tagset & set(u.tags)), u.id))
    items = [
        EvidenceItem(
            knowledge_id=u.id,
            knowledge_version=u.version,
            claim_id=c.id,
            source_id=c.locators[0].source_id,
            source_locator=c.locators[0].locator,
            allowed_text_th=c.text_th,
        )
        for u in ranked
        for c in sorted(u.claims, key=lambda c: int(c.id[1:]))
    ]
    return EvidencePack(release_id=release.id, items=items[: max(limit, 0)])
