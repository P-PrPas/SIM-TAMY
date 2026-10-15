"""Session lifecycle: create, view, liveness (PRD 8, API_DESIGN 5)."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import safe_case_id
from app.api.v1.schemas import (
    CaseStatus,
    CreateSessionRequest,
    CreateSessionResponse,
    DecisionState,
    Message,
    Phase,
    SessionCase,
    SessionStatus,
    SessionView,
    Speaker,
    Variant,
)
from app.content.loader import ContentError, ContentStore, LoadedCase
from app.core import limits
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token, new_token
from app.db.models import ClassRoom, Event, LearnerSession
from app.db.repo import EventRepo, SessionRepo, TurnRepo
from app.domain.state import SessionState, initial_state
from app.services.briefs import LIMITS, case_brief, notices, playable_variants, status_label

log = logging.getLogger("app.sessions")


def public_phase(phase: str) -> Phase:
    """INTRO is internal: the API shows it as INTERVIEW (openapi `Phase`)."""
    return Phase.INTERVIEW if phase == "INTRO" else Phase(phase)


def state_of(row: LearnerSession) -> SessionState:
    return SessionState.model_validate(row.state)


def pinned_case(store: ContentStore, row: LearnerSession) -> LoadedCase:
    """The case version this session started with (FR-CASE-05)."""
    loaded = store.resolve(row.case_id, row.case_hash)
    if loaded is None:
        log.error("session %s: case %s version %s is gone", row.id, row.case_id, row.case_hash)
        raise ApiError("INTERNAL_ERROR", "the case changed while this session was open")
    return loaded


def ensure_alive(db: Session, row: LearnerSession) -> None:
    """Idle sessions expire (FR-SES-03); completed ones are only read."""
    if row.status == "active":
        idle = (datetime.now(UTC) - row.last_activity_at).total_seconds()
        if idle > limits.IDLE_TIMEOUT_S:
            row.status = "expired"
            row.ended_at = datetime.now(UTC)
            db.commit()  # the error below rolls the request back; keep the new status
    if row.status == "expired":
        raise ApiError(
            "SESSION_EXPIRED", "session expired", {"idle_timeout_s": limits.IDLE_TIMEOUT_S}
        )


def create_session(
    db: Session, store: ContentStore, req: CreateSessionRequest
) -> CreateSessionResponse:
    case_id = safe_case_id(req.case_id)
    try:
        loaded = store.load(case_id)
    except ContentError as exc:
        log.warning("case %s not loadable: %s", case_id, exc)
        raise ApiError("CASE_NOT_AVAILABLE", "case not available") from exc
    if loaded.case.status == "Draft" and not get_settings().allow_draft_cases:
        raise ApiError("CASE_NOT_AVAILABLE", "case not available")
    available = playable_variants(loaded)
    if req.variant not in available:
        raise ApiError(
            "VARIANT_NOT_AVAILABLE",
            "variant not available for this case",
            {"variants_available": [v.value for v in available]},
        )
    class_id = None
    if req.class_code is not None:
        class_id = db.scalar(select(ClassRoom.id).where(ClassRoom.code == req.class_code))
        if class_id is None:
            raise ApiError("CLASS_NOT_FOUND", "class code not found")

    token = new_token()
    row = SessionRepo(db).create(
        case_id=loaded.case.case_id,
        case_version=loaded.case.version,
        case_hash=loaded.case_hash,
        variant=req.variant.value,
        learner_name=req.learner_name,
        token_hash=hash_token(token),
        state=initial_state().model_dump(mode="json"),
        class_id=class_id,
    )
    EventRepo(db).append(
        session_id=row.id,
        turn_idx=0,
        type="SESSION_STARTED",
        payload={"case_id": row.case_id, "case_hash": row.case_hash, "variant": row.variant},
    )
    db.refresh(row)  # server-side defaults (started_at)
    return CreateSessionResponse(
        session_id=row.id,
        token=token,
        token_type="Bearer",
        created_at=row.started_at,
        case=case_brief(loaded),
        variant=req.variant,
        phase=Phase.INTERVIEW,
        limits=LIMITS,
        notices=notices(loaded),
    )


def view_session(db: Session, store: ContentStore, row: LearnerSession) -> SessionView:
    loaded = pinned_case(store, row)
    state = state_of(row)
    committed_at = None
    if state.decision is not None:
        committed_at = db.scalar(
            select(Event.turn_idx)
            .where(Event.session_id == row.id, Event.type == "DECISION_COMMITTED")
            .order_by(Event.id)
            .limit(1)
        )
    history = [
        Message(idx=t.idx, speaker=Speaker(t.speaker), text=t.text, created_at=t.created_at)
        for t in TurnRepo(db).list_for_session(row.id)
    ]
    return SessionView(
        session_id=row.id,
        case=SessionCase(
            case_id=row.case_id,
            version=row.case_version,
            status=CaseStatus(loaded.case.status),
            status_label_th=status_label(loaded.case.status),
        ),
        variant=Variant(row.variant),
        status=SessionStatus(row.status),
        phase=Phase.COMPLETED if row.status == "completed" else public_phase(state.phase),
        turn_idx=state.turn_idx,
        turns_remaining=max(0, limits.MAX_TURNS - state.turn_idx),
        decision=DecisionState(
            committed=state.decision is not None,
            option_id=state.decision,
            committed_at_idx=committed_at,
        ),
        history=history,
        limits=LIMITS,
        created_at=row.started_at,
        last_activity_at=row.last_activity_at,
    )
