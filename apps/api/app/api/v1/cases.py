"""Public, spoiler-free case and class-code reads (T-045)."""

import re

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import Db, Store, safe_case_id
from app.api.v1.schemas import CaseBrief, CaseSummary
from app.content.loader import ContentError, LoadedCase
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import ClassRoom
from app.services.briefs import case_brief

router = APIRouter(prefix="/v1", tags=["Cases"])
_CLASS_CODE = re.compile(r"[A-Z0-9]{6}")
_CASE_LIST_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {"type": "array", "items": {"$ref": "#/components/schemas/CaseSummary"}}
    },
}
_CLASS_NAME_SCHEMA = {
    "type": "object",
    "required": ["code", "name"],
    "properties": {"code": {"type": "string"}, "name": {"type": "string"}},
}


def _available(loaded: LoadedCase) -> bool:
    return loaded.case.status != "Draft" or get_settings().allow_draft_cases


@router.get(
    "/cases",
    operation_id="listCases",
    response_model=None,
    responses={200: {"content": {"application/json": {"schema": _CASE_LIST_SCHEMA}}}},
)
def list_cases(store: Store) -> dict[str, list[CaseSummary]]:
    items: list[CaseSummary] = []
    for folder in sorted(store.cases_dir.iterdir()):
        if not folder.is_dir():
            continue
        try:
            loaded = store.load(safe_case_id(folder.name))
        except (ContentError, ApiError):
            continue  # an invalid case cannot become a public item
        if _available(loaded):
            items.append(CaseSummary.model_validate(case_brief(loaded).model_dump()))
    return {"items": items}


@router.get("/cases/{case_id}", operation_id="getCase", response_model=CaseBrief)
def get_case(case_id: str, store: Store) -> CaseBrief:
    try:
        loaded = store.load(safe_case_id(case_id))
    except ContentError as exc:
        raise ApiError("CASE_NOT_AVAILABLE", "case not available") from exc
    if not _available(loaded):
        raise ApiError("CASE_NOT_AVAILABLE", "case not available")
    return case_brief(loaded)


@router.get(
    "/classes/{code}",
    operation_id="checkClassCode",
    response_model=None,
    responses={200: {"content": {"application/json": {"schema": _CLASS_NAME_SCHEMA}}}},
)
def check_class_code(code: str, db: Db) -> dict[str, str]:
    if not _CLASS_CODE.fullmatch(code):
        raise ApiError("CLASS_NOT_FOUND", "class code not found")
    row = db.scalar(select(ClassRoom).where(ClassRoom.code == code))
    if row is None:
        raise ApiError("CLASS_NOT_FOUND", "class code not found")
    return {"code": row.code, "name": row.name or ""}
