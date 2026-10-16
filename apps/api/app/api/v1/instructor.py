import uuid

from fastapi import APIRouter

from app.api.deps import Db, Instructor, Store
from app.api.v1.schemas import Override, OverrideRequest
from app.services import overrides

router = APIRouter(prefix="/v1", tags=["Instructor"])


@router.post(
    "/instructor/sessions/{session_id}/overrides",
    status_code=201,
    response_model=Override,
    operation_id="createOverride",
)
def create_override(
    session_id: uuid.UUID, body: OverrideRequest, _: Instructor, db: Db, store: Store
) -> Override:
    return overrides.create(db, store, session_id, body)
