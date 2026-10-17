"""Family room endpoints. Invite secrets travel in request bodies, never URLs."""

import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import Db, Llm
from app.api.v1.family_schemas import (
    FamilyCreate,
    FamilyCreated,
    FamilyDecision,
    FamilyJoin,
    FamilyStoryCard,
    FamilyView,
)
from app.content.family import load_stories
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token, new_token
from app.db.family import FamilyRoom
from app.services import family

router = APIRouter(prefix="/v1/family", tags=["Family"])
Auth = Annotated[str | None, Header(alias="Authorization")]


@router.get("/stories", operation_id="listFamilyStories", response_model=list[FamilyStoryCard])
def stories() -> list[FamilyStoryCard]:
    return [
        FamilyStoryCard(
            id=s.id,
            title_th=s.title_th,
            description_th=s.description_th,
            mode=s.mode,
            chapters_th=list(dict.fromkeys(step.chapter_th for step in s.steps)),
        )
        for s in load_stories(get_settings().content_dir)
        if s.status == "Approved" or get_settings().allow_draft_cases
    ]


@router.post(
    "/rooms", operation_id="createFamilyRoom", response_model=FamilyCreated, status_code=201
)
def create(body: FamilyCreate, db: Db) -> FamilyCreated:
    story = next(
        (s for s in load_stories(get_settings().content_dir) if s.id == body.story_id), None
    )
    if story is None or (story.status != "Approved" and not get_settings().allow_draft_cases):
        raise ApiError("CASE_NOT_AVAILABLE", "family story not available")
    token, invite = new_token(), new_token()
    row = FamilyRoom(
        story=story.model_dump(mode="json"),
        host_role=body.role,
        host_hash=hash_token(token),
        invite_hash=hash_token(invite),
    )
    db.add(row)
    db.flush()
    return FamilyCreated(room_id=row.id, token=token, invite=invite)


@router.post("/rooms/{room_id}/join", operation_id="joinFamilyRoom", response_model=FamilyView)
def join(room_id: uuid.UUID, body: FamilyJoin, db: Db) -> FamilyView:
    row = family.room(db, room_id, lock=True)
    if row.story.get("mode", "coop") == "solo":
        raise ApiError("INVALID_PHASE", "individual story does not accept a partner")
    digest = hash_token(body.participant_token)
    if not hmac.compare_digest(row.invite_hash, hash_token(body.invite)) or digest == row.host_hash:
        raise ApiError("UNAUTHORIZED", "invalid invitation")
    if row.partner_hash and not hmac.compare_digest(row.partner_hash, digest):
        raise ApiError("INVALID_PHASE", "room is full")
    row.partner_hash = digest
    db.flush()
    return family.view(db, row, "father" if row.host_role == "mother" else "mother")


@router.get("/rooms/{room_id}", operation_id="getFamilyRoom", response_model=FamilyView)
def get(room_id: uuid.UUID, db: Db, authorization: Auth = None) -> FamilyView:
    row = family.room(db, room_id)
    return family.view(db, row, family.role_of(row, authorization))


@router.post(
    "/rooms/{room_id}/decisions", operation_id="decideFamilyRoom", response_model=FamilyView
)
def decide(
    room_id: uuid.UUID, body: FamilyDecision, db: Db, llm: Llm, authorization: Auth = None
) -> FamilyView:
    row = family.room(db, room_id, lock=True)
    return family.decide(db, row, family.role_of(row, authorization), body, llm=llm)
