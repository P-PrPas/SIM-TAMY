"""Bounded evidence from the released knowledge base; abstain if the release is unavailable."""

from collections.abc import Callable
from typing import Any

from app.ai.contracts import EvidencePack
from app.content.knowledge import load_knowledge
from app.core.config import get_settings
from app.domain.family import FamilyStep, FamilyStory
from app.services.knowledge import retrieve_claims

NO_RELEASE = "none"
Resolver = Callable[[], tuple[Callable[..., EvidencePack], Any] | None]


def _resolve() -> tuple[Callable[..., EvidencePack], Any] | None:
    """(retrieve_claims, release) from the knowledge stream, or None while it is absent."""
    try:
        return retrieve_claims, load_knowledge(get_settings().content_dir).release
    except Exception:  # a broken release must degrade to abstain, never break a room
        return None


def current_release_id(resolve: Resolver | None = None) -> str:
    found = (resolve or _resolve)()
    return str(getattr(found[1], "id", NO_RELEASE)) if found else NO_RELEASE


def evidence_pack(
    story: FamilyStory,
    step: FamilyStep,
    role: str,
    allowed_fact_ids: list[str],
    *,
    unit_ids: list[str] | None = None,
    release_id: str | None = None,
    resolve: Resolver | None = None,
) -> EvidencePack:
    """Claims the controller allows in this reply. Scoped to the story's units (and an intent's)."""
    scope = [u for u in (unit_ids or story.knowledge_unit_ids) if u in story.knowledge_unit_ids]
    found = (resolve or _resolve)()
    if not found or not scope:
        return EvidencePack(release_id=NO_RELEASE, allowed_fact_ids=allowed_fact_ids)
    retrieve, release = found
    if release_id not in (None, NO_RELEASE) and getattr(release, "id", None) != release_id:
        return EvidencePack(release_id=NO_RELEASE, allowed_fact_ids=allowed_fact_ids)  # pinned
    try:
        pack = retrieve(
            release, unit_ids=scope, care_stage=None, audience="parent", tags=None, limit=5
        )
    except Exception:
        return EvidencePack(release_id=NO_RELEASE, allowed_fact_ids=allowed_fact_ids)
    return pack.model_copy(update={"allowed_fact_ids": allowed_fact_ids})
