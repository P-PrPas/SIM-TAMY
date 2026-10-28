"""Family room endpoints. Invite secrets travel in request bodies, never URLs."""

import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.ai.contracts import DebriefOutput
from app.ai.evidence import current_release_id
from app.api.deps import Db, Llm
from app.api.v1.family_schemas import (
    FamilyCreate,
    FamilyCreated,
    FamilyDecision,
    FamilyJoin,
    FamilyMessage,
    FamilyMessageResult,
    FamilyShare,
    FamilyStoryCard,
    FamilyView,
)
from app.content.family import load_stories
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token, new_token
from app.db.family import FamilyRoom
from app.db.models import Assignment
from app.services import family, family_chat, family_debrief

router = APIRouter(prefix="/v1/family", tags=["Family"])
Auth = Annotated[str | None, Header(alias="Authorization")]
Account = Annotated[str | None, Header(alias="X-Demo-Account", max_length=64)]


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
def create(body: FamilyCreate, db: Db, account: Account = None) -> FamilyCreated:
    story = next(
        (s for s in load_stories(get_settings().content_dir) if s.id == body.story_id), None
    )
    if story is None or (story.status != "Approved" and not get_settings().allow_draft_cases):
        raise ApiError("CASE_NOT_AVAILABLE", "family story not available")
    if body.assignment_id and db.get(Assignment, body.assignment_id) is None:
        raise ApiError("NOT_FOUND", "assignment not found")
    token, invite = new_token(), new_token()
    row = FamilyRoom(
        assignment_id=body.assignment_id,
        host_account_id=account,
        release_id=current_release_id(),
        story=story.model_dump(mode="json"),
        host_role=body.role,
        host_hash=hash_token(token),
        invite_hash=hash_token(invite),
    )
    db.add(row)
    db.flush()
    return FamilyCreated(room_id=row.id, token=token, invite=invite)


@router.post("/rooms/{room_id}/join", operation_id="joinFamilyRoom", response_model=FamilyView)
def join(room_id: uuid.UUID, body: FamilyJoin, db: Db, account: Account = None) -> FamilyView:
    row = family.room(db, room_id, lock=True)
    if row.story.get("mode", "coop") == "solo":
        raise ApiError("INVALID_PHASE", "individual story does not accept a partner")
    digest = hash_token(body.participant_token)
    if not hmac.compare_digest(row.invite_hash, hash_token(body.invite)) or digest == row.host_hash:
        raise ApiError("UNAUTHORIZED", "invalid invitation")
    if row.partner_hash and not hmac.compare_digest(row.partner_hash, digest):
        raise ApiError("INVALID_PHASE", "room is full")
    row.partner_hash = digest
    row.partner_account_id = account
    db.flush()
    return family.view(db, row, "father" if row.host_role == "mother" else "mother")


@router.get("/rooms/{room_id}", operation_id="getFamilyRoom", response_model=FamilyView)
def get(room_id: uuid.UUID, db: Db, authorization: Auth = None) -> FamilyView:
    row = family.room(db, room_id)
    role = family.role_of(row, authorization)
    family.touch(row, role)
    return family.view(db, row, role)


@router.post(
    "/rooms/{room_id}/decisions", operation_id="decideFamilyRoom", response_model=FamilyView
)
def decide(
    room_id: uuid.UUID, body: FamilyDecision, db: Db, authorization: Auth = None
) -> FamilyView:
    row = family.room(db, room_id, lock=True)
    role = family.role_of(row, authorization)
    family.touch(row, role)
    return family.decide(db, row, role, body)


@router.post("/rooms/{room_id}/shares", operation_id="shareFamilyFact", response_model=FamilyView)
def share(room_id: uuid.UUID, body: FamilyShare, db: Db, authorization: Auth = None) -> FamilyView:
    row = family.room(db, room_id, lock=True)
    role = family.role_of(row, authorization)
    family.touch(row, role)
    return family.share(db, row, role, body)


@router.post(
    "/rooms/{room_id}/messages",
    operation_id="sendFamilyMessage",
    response_model=FamilyMessageResult,
)
def send_message(
    room_id: uuid.UUID, body: FamilyMessage, db: Db, llm: Llm, authorization: Auth = None
) -> FamilyMessageResult:
    row = family.room(db, room_id, lock=True)
    role = family.role_of(row, authorization)
    family.touch(row, role)
    return family_chat.message(db, row, role, body, llm)


@router.post(
    "/rooms/{room_id}/debrief", operation_id="getFamilyDebrief", response_model=DebriefOutput
)
def debrief(room_id: uuid.UUID, db: Db, llm: Llm, authorization: Auth = None) -> DebriefOutput:
    row = family.room(db, room_id, lock=True)
    family.role_of(row, authorization)
    return family_debrief.get_or_create(db, row, llm)[0]
