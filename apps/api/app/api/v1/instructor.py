"""Instructor-only routes for classes, reports listing, cohort analytics and score overrides."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Db, Instructor, Store
from app.api.v1.schemas import (
    ClassAnalytics,
    ClassInfo,
    ClassList,
    CreateClassRequest,
    InstructorSessionList,
    Override,
    OverrideRequest,
    SafetyStatus,
    SessionStatus,
    Variant,
)
from app.services import instructor as service
from app.services import overrides

router = APIRouter(prefix="/v1", tags=["Instructor"])


@router.post("/classes", status_code=201, response_model=ClassInfo, operation_id="createClass")
def create_class(body: CreateClassRequest, db: Db, _: Instructor) -> ClassInfo:
    return service.create_class(db, body.name)


@router.get("/instructor/classes", response_model=ClassList, operation_id="listClasses")
def list_classes(db: Db, _: Instructor) -> ClassList:
    return ClassList(items=service.list_classes(db))


@router.get(
    "/instructor/sessions",
    response_model=InstructorSessionList,
    operation_id="listInstructorSessions",
)
def list_sessions(
    db: Db,
    store: Store,
    _: Instructor,
    class_code: Annotated[str | None, Query(pattern=r"^[A-Z0-9]{6}$")] = None,
    case_id: str | None = None,
    variant: Variant | None = None,
    status: SessionStatus | None = None,
    safety_status: SafetyStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> InstructorSessionList:
    return service.list_sessions(
        db,
        store,
        class_code=class_code,
        case_id=case_id,
        variant=variant,
        status=status,
        safety_status=safety_status,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/instructor/analytics", response_model=ClassAnalytics, operation_id="getClassAnalytics"
)
def get_analytics(
    db: Db,
    store: Store,
    _: Instructor,
    class_code: Annotated[str, Query(pattern=r"^[A-Z0-9]{6}$")],
) -> ClassAnalytics:
    return service.class_analytics(db, store, class_code)


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
