"""Shared family simulation: pinned content, role isolation, serialized decisions."""

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.family_schemas import (
    FamilyCompetency,
    FamilyDecision,
    FamilyEvidence,
    FamilyExchange,
    FamilyOption,
    FamilyReport,
    FamilyScene,
    FamilyView,
)
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token
from app.db.family import FamilyEvent, FamilyRoom
from app.domain.family import FamilyRole, FamilyStory
from app.engine.family import assess, choose, prompt, selections


def room(db: Session, room_id: uuid.UUID, *, lock: bool = False) -> FamilyRoom:
    query = select(FamilyRoom).where(FamilyRoom.id == room_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise ApiError("NOT_FOUND", "room not found")
    if row.created_at < datetime.now(UTC) - timedelta(days=get_settings().log_retention_days):
        raise ApiError("SESSION_EXPIRED", "room expired")
    return row


def role_of(row: FamilyRoom, authorization: str | None) -> FamilyRole:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError("UNAUTHORIZED", "missing room token")
    digest = hash_token(token)
    if hmac.compare_digest(digest, row.host_hash):
        return cast(FamilyRole, row.host_role)
    if row.partner_hash and hmac.compare_digest(digest, row.partner_hash):
        return "father" if row.host_role == "mother" else "mother"
    raise ApiError("UNAUTHORIZED", "invalid room token")


def events(db: Session, row: FamilyRoom) -> list[FamilyEvent]:
    return list(
        db.scalars(
            select(FamilyEvent).where(FamilyEvent.room_id == row.id).order_by(FamilyEvent.idx)
        )
    )


def view(db: Session, row: FamilyRoom, role: FamilyRole) -> FamilyView:
    story = FamilyStory.model_validate(row.story)
    choices = [event.choice_id for event in events(db, row)]
    chosen = selections(story, choices)
    transcript = [
        FamilyExchange(
            idx=i + 1,
            role=step.role,
            speaker_th=step.speaker_th,
            prompt_th=prompt(story, choices[:i]),
            text_th=choice.text_th,
            reply_th=choice.reply_th,
        )
        for i, (step, choice) in enumerate(zip(story.steps, chosen, strict=False))
    ]
    report = None
    scene = None
    if len(chosen) == len(story.steps):
        assessment = assess(story, choices)
        report = FamilyReport(
            safety_status="SAFETY_MET" if assessment.safety_met else "SAFETY_NOT_MET",
            competencies=[
                FamilyCompetency(
                    skill=skill,
                    observed=counts[0],
                    opportunities=counts[1],
                )
                for skill, counts in assessment.competencies.items()
            ],
            evidence=[
                FamilyEvidence(
                    idx=i + 1,
                    text_th=choice.text_th,
                    feedback_th=choice.feedback_th,
                    source_ids=step.source_ids,
                    safe=choice.safe,
                )
                for i, (step, choice) in enumerate(zip(story.steps, chosen, strict=True))
            ],
            sources=story.sources,
        )
    else:
        step = story.steps[len(chosen)]
        scene = FamilyScene(
            id=step.id,
            chapter_th=step.chapter_th,
            role=step.role,
            speaker_th=step.speaker_th,
            prompt_th=prompt(story, choices),
            choices=[FamilyOption(id=c.id, text_th=c.text_th) for c in step.choices]
            if step.role == role
            else [],
        )
    return FamilyView(
        room_id=row.id,
        story_id=story.id,
        title_th=story.title_th,
        role=role,
        private_brief_th=story.roles[role],
        partner_joined=bool(row.partner_hash),
        state_version=len(chosen),
        total_steps=len(story.steps),
        scene=scene,
        transcript=transcript,
        report=report,
    )


def decide(db: Session, row: FamilyRoom, role: FamilyRole, body: FamilyDecision) -> FamilyView:
    saved = events(db, row)
    prior = next((event for event in saved if event.client_turn_id == body.client_turn_id), None)
    if prior:
        if (prior.role, prior.choice_id, prior.idx) != (
            role,
            body.choice_id,
            body.state_version + 1,
        ):
            raise ApiError("IDEMPOTENCY_CONFLICT", "decision ID reused")
        return view(db, row, role)
    if not row.partner_hash:
        raise ApiError("INVALID_PHASE", "waiting for partner")
    if body.state_version != len(saved):
        raise ApiError("TURN_IN_PROGRESS", "room changed; refresh before deciding")
    story = FamilyStory.model_validate(row.story)
    try:
        choose(story, [event.choice_id for event in saved], role, body.choice_id)
    except ValueError as exc:
        raise ApiError("DECISION_OPTION_INVALID", str(exc)) from exc
    db.add(
        FamilyEvent(
            room_id=row.id,
            idx=len(saved) + 1,
            role=role,
            choice_id=body.choice_id,
            client_turn_id=body.client_turn_id,
        )
    )
    db.flush()
    return view(db, row, role)
