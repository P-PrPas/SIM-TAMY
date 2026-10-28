"""Knowledge base reads (contracts §4, Blueprint §09): release, sources, units, learning paths.

Only units of the current release are exposed: draft, retired and rights-blocked units are not.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.content.knowledge import KnowledgeBase, cached_knowledge
from app.core.config import get_settings
from app.core.errors import ApiError
from app.domain.knowledge import KnowledgeUnit

router = APIRouter(prefix="/v1", tags=["Knowledge"])


class KnowledgeReleaseInfo(BaseModel):
    id: str
    unit_count: int


class SourceItem(BaseModel):
    id: str
    kind: Literal["catalog", "kb_source"]
    title: str
    publisher: str | None = None
    year: str | None = None
    url: str | None = None
    rights_status: Literal["unknown", "metadata_only", "public_web", "own_summary"]


class SourceList(BaseModel):
    items: list[SourceItem]


class UnitListItem(BaseModel):
    id: str
    version: str
    title_th: str
    care_stage: str
    domain: int
    has_lens: bool


class UnitList(BaseModel):
    release_id: str
    items: list[UnitListItem]


class ClaimSource(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    locator: str


class ClaimView(BaseModel):
    id: str
    type: str
    text_th: str
    sources: list[ClaimSource]


class LensView(BaseModel):
    wisdom_th: str
    safety_th: str
    rights_th: str


class UnitDetail(BaseModel):
    id: str
    version: str
    title_th: str
    care_stage: str
    domain: int
    evidence_status: str
    review_basis: str
    reviewed_on: str
    claims: list[ClaimView]
    lens: LensView | None = None
    contraindications_th: list[str]
    escalation_th: str | None = None


class ObjectiveView(BaseModel):
    id: str
    title_th: str
    dimension: str
    unit_ids: list[str]
    story_ids: list[str]


class StageView(BaseModel):
    stage: int
    title_th: str
    summary_th: str
    objectives: list[ObjectiveView]


class LearningPathsView(BaseModel):
    release_id: str
    stages: list[StageView]


def _kb() -> KnowledgeBase:
    return cached_knowledge(get_settings().content_dir)


def _detail(kb: KnowledgeBase, unit: KnowledgeUnit) -> UnitDetail:
    claims = []
    for c in unit.claims:
        sources = []
        for loc in c.locators:
            src = kb.source(loc.source_id)
            sources.append(
                ClaimSource(
                    source_id=loc.source_id,
                    title=src.title if src else loc.source_id,
                    url=src.url if src else None,
                    locator=loc.locator,
                )
            )
        claims.append(ClaimView(id=c.id, type=c.type, text_th=c.text_th, sources=sources))
    return UnitDetail(
        id=unit.id,
        version=unit.version,
        title_th=unit.title_th,
        care_stage=unit.care_stage,
        domain=unit.domain,
        evidence_status=unit.evidence_status,
        review_basis=unit.review_basis,
        reviewed_on=unit.reviewed_on,
        claims=claims,
        lens=LensView(**unit.lens.model_dump()) if unit.lens else None,
        contraindications_th=list(unit.contraindications_th),
        escalation_th=unit.escalation_th,
    )


@router.get("/knowledge/release", operation_id="getKnowledgeRelease")
def get_release() -> KnowledgeReleaseInfo:
    release = _kb().release
    return KnowledgeReleaseInfo(id=release.id, unit_count=len(release.units))


@router.get("/knowledge/sources", operation_id="listKnowledgeSources")
def list_sources(kind: Literal["catalog", "kb_source"] | None = None) -> SourceList:
    return SourceList(
        items=[
            SourceItem(**s.model_dump(include=set(SourceItem.model_fields)))
            for s in _kb().sources
            if kind is None or s.kind == kind
        ]
    )


@router.get("/knowledge/units", operation_id="listKnowledgeUnits")
def list_units() -> UnitList:
    release = _kb().release
    return UnitList(
        release_id=release.id,
        items=[
            UnitListItem(
                id=u.id,
                version=u.version,
                title_th=u.title_th,
                care_stage=u.care_stage,
                domain=u.domain,
                has_lens=u.lens is not None,
            )
            for u in release.units
        ],
    )


@router.get("/knowledge/units/{unit_id}", operation_id="getKnowledgeUnit")
def get_unit(unit_id: str) -> UnitDetail:
    kb = _kb()
    unit = kb.release.unit(unit_id)
    if unit is None:
        raise ApiError("NOT_FOUND", "knowledge unit not found")
    return _detail(kb, unit)


@router.get("/learning-paths", operation_id="listLearningPaths")
def learning_paths() -> LearningPathsView:
    kb = _kb()
    return LearningPathsView(
        release_id=kb.release.id,
        stages=[
            StageView(
                stage=s.stage,
                title_th=s.title_th,
                summary_th=s.summary_th,
                objectives=[ObjectiveView(**o.model_dump()) for o in s.objectives],
            )
            for s in kb.paths.stages
        ],
    )
