"""SIM-TAMY 2.0 knowledge (Blueprint §09, ADR-15): source registry -> knowledge units -> release.

Content lives in `content/knowledge/`; these models are the contract every stream codes against.
A release is the set of published, usable units; AI-02 may only cite claims from a pinned release.
"""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

SourceKind = Literal["catalog", "kb_source"]  # catalog = M/S/T/P/I/G codes; kb_source = S01-S40
RightsStatus = Literal["unknown", "metadata_only", "public_web", "own_summary"]
CareStage = Literal["preconception", "antenatal", "intrapartum", "postpartum", "newborn"]
UnitAudience = Literal["parent", "educator"]
ClaimType = Literal["tradition", "safety", "scope", "guidance", "service"]
EvidenceStatus = Literal["verified_primary", "secondary", "synthesis", "proposed"]
PublishStatus = Literal["draft", "published", "retired"]
ReviewBasis = Literal["knowledge_base_2026"]  # AGENTS rule 9: provenance, never expert review

# Units whose claims may be retrieved: the claim text is our own summary of a public source.
USABLE_RIGHTS: frozenset[str] = frozenset({"public_web", "own_summary"})

SOURCE_ID = r"^(S\d{2}|[MSTPIG]\d{2})$"
UNIT_ID = r"^KB-[A-Z]+-[A-Z]+-\d{3}$"


class SourceRecord(Model):
    id: str = Field(pattern=SOURCE_ID)
    kind: SourceKind
    title: NonBlank
    publisher: str | None = None
    year: str | None = None
    url: str | None = Field(default=None, pattern=r"^https?://")
    rights_status: RightsStatus = "unknown"
    note: str | None = None


class SourceLocator(Model):
    source_id: str = Field(pattern=SOURCE_ID)
    locator: NonBlank  # section / page / table in the source, or the KB report page


class KnowledgeClaim(Model):
    id: str = Field(pattern=r"^c\d+$")
    type: ClaimType
    text_th: NonBlank
    locators: list[SourceLocator] = Field(min_length=1)


class ThaiWisdomLens(Model):
    """The three views a Thai-wisdom card must show (Blueprint §01 item 2)."""

    wisdom_th: NonBlank  # tradition and where it comes from
    safety_th: NonBlank  # safety and limits
    rights_th: NonBlank  # who may provide it, where to consult


class KnowledgeUnit(Model):
    id: str = Field(pattern=UNIT_ID)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    title_th: NonBlank
    audience: UnitAudience = "parent"
    care_stage: CareStage
    domain: int = Field(ge=1, le=12)  # KB report section 2, knowledge domains 01-12
    claims: list[KnowledgeClaim] = Field(min_length=1)
    lens: ThaiWisdomLens | None = None
    evidence_status: EvidenceStatus
    rights_status: RightsStatus
    professional_scope: Literal["education_only"] = "education_only"
    contraindications_th: list[NonBlank] = []
    escalation_th: NonBlank | None = None
    tags: list[str] = []  # retrieval keywords (deterministic ranking), never shown
    publish_status: PublishStatus = "draft"
    review_basis: ReviewBasis = "knowledge_base_2026"
    reviewed_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def unique_claims(self) -> "KnowledgeUnit":
        if len({c.id for c in self.claims}) != len(self.claims):
            raise ValueError("duplicate claim ID")
        return self


class KnowledgeRelease(Model):
    """Immutable snapshot: the published, usable units. Its ID is a content hash."""

    id: str
    units: tuple[KnowledgeUnit, ...]

    @classmethod
    def build(cls, units: list[KnowledgeUnit]) -> "KnowledgeRelease":
        usable = sorted(
            (
                u
                for u in units
                if u.publish_status == "published" and u.rights_status in USABLE_RIGHTS
            ),
            key=lambda u: u.id,
        )
        payload = json.dumps([u.model_dump(mode="json") for u in usable], sort_keys=True)
        return cls(
            id="rel-" + hashlib.sha256(payload.encode()).hexdigest()[:12], units=tuple(usable)
        )

    def unit(self, unit_id: str) -> KnowledgeUnit | None:
        return next((u for u in self.units if u.id == unit_id), None)
