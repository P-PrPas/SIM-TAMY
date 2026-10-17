"""Authenticated learner submission and instructor-only class feedback."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Db, Instructor, Learner
from app.api.v1.schemas import ClassPilotFeedback, PilotFeedback, PilotFeedbackRequest
from app.services import pilot

router = APIRouter(prefix="/v1", tags=["Instructor"])


@router.post(
    "/sessions/{session_id}/feedback",
    response_model=PilotFeedback,
    status_code=201,
    operation_id="submitPilotFeedback",
)
def submit_feedback(body: PilotFeedbackRequest, row: Learner, db: Db) -> PilotFeedback:
    return pilot.submit(db, row, body)


@router.get(
    "/instructor/feedback", response_model=ClassPilotFeedback, operation_id="getClassPilotFeedback"
)
def class_feedback(
    db: Db, _: Instructor, class_code: Annotated[str, Query(pattern=r"^[A-Z0-9]{6}$")]
) -> ClassPilotFeedback:
    return pilot.for_class(db, class_code)
