"""Shared family simulation: pinned content, role isolation, serialized decisions."""

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.family_schemas import (
    FamilyCardSource,
    FamilyCompetency,
    FamilyDecision,
    FamilyDialogueTurn,
    FamilyDimension,
    FamilyEvidence,
    FamilyExchange,
    FamilyFactView,
    FamilyKnowledgeCard,
    FamilyLensView,
    FamilyOption,
    FamilyReport,
    FamilyScene,
    FamilyShare,
    FamilyView,
    FamilyVote,
    FamilyVoteChoice,
)
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_token
from app.db.family import FamilyEvent, FamilyMessage, FamilyRoom
from app.domain.family import FamilyRole, FamilyStory
from app.engine.family import (
    FamilyEventRecord,
    Progress,
    assess,
    choose,
    prompt,
    replay,
    revealing,
    rubric_score,
    selections,
)

ONLINE_WINDOW = timedelta(seconds=10)  # roughly three missed 3s polls


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


def progress(story: FamilyStory, saved: list[FamilyEvent]) -> Progress:
    records = [
        FamilyEventRecord(e.kind, cast(FamilyRole, e.role), e.choice_id, e.reply_th) for e in saved
    ]
    try:
        return replay(story, records)
    except ValueError as exc:  # corrupt log: never guess a state
        raise ApiError("INTERNAL_ERROR", "room history is inconsistent") from exc


def touch(row: FamilyRoom, role: FamilyRole) -> None:
    """Record that this role is polling; the partner only ever sees an online boolean."""
    now = datetime.now(UTC)
    if role == row.host_role:
        row.host_seen_at = now
    else:
        row.partner_seen_at = now


def partner_online(row: FamilyRoom, role: FamilyRole) -> bool:
    seen = row.partner_seen_at if role == row.host_role else row.host_seen_at
    return bool(seen and datetime.now(UTC) - seen <= ONLINE_WINDOW)


def view(db: Session, row: FamilyRoom, role: FamilyRole) -> FamilyView:
    story = FamilyStory.model_validate(row.story)
    state = progress(story, events(db, row))
    choices = state.choices
    chosen = selections(story, choices)
    transcript = [
        FamilyExchange(
            idx=i + 1,
            role=role if story.mode == "solo" else step.role,
            speaker_th=step.speaker_th,
            prompt_th=prompt(story, choices[:i], state.step_facts[i]),
            text_th=choice.text_th,
            reply_th=state.replies[i] or choice.reply_th,
        )
        for i, (step, choice) in enumerate(zip(story.steps, chosen, strict=False))
    ]
    report = None
    scene = None
    if len(chosen) == len(story.steps):
        assessment = assess(story, choices, state.facts)
        rubric = rubric_score(story, state)
        report = FamilyReport(
            safety_status="SAFETY_MET" if assessment.safety_met else "SAFETY_NOT_MET",
            score_total=rubric.total if rubric else None,
            dimensions=[
                FamilyDimension(
                    id=d.id, weight=d.weight, earned=d.earned, possible=d.possible, score=d.score
                )
                for d in (rubric.dimensions if rubric else ())
            ],
            competencies=[
                FamilyCompetency(skill=skill, observed=counts[0], opportunities=counts[1])
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
        vote = None
        if step.joint:
            texts = {c.id: c.text_th for c in step.choices}
            own = state.votes.get(role)
            vote = FamilyVote(
                my_choice_id=own,
                waiting_for_partner=own is not None,
                disagreement=[
                    FamilyVoteChoice(role=cast(FamilyRole, r), choice_id=c, text_th=texts[c])
                    for r, c in sorted(state.split.items())
                ]
                if state.split
                else None,
            )
        mine = story.mode == "solo" or step.joint or step.role == role
        discover = step.kind == "discover"
        by_id = {src.id: src for src in story.sources}
        scene = FamilyScene(
            id=step.id,
            chapter_th=step.chapter_th,
            role=role if story.mode == "solo" or step.joint else step.role,
            speaker_th=step.speaker_th,
            prompt_th=prompt(story, choices, state.facts),
            choices=[FamilyOption(id=c.id, text_th=c.text_th) for c in step.choices]
            if mine
            and not (vote and vote.my_choice_id)
            and (not discover or revealing(step, state.asked(len(chosen))) >= step.min_reveals)
            else [],
            joint=step.joint,
            vote=vote,
            kind=step.kind,
            character_th=step.character_th,
            accepts_text=bool(mine and not (vote and vote.my_choice_id)),
            can_continue=not discover
            or revealing(step, state.asked(len(chosen))) >= step.min_reveals,
            card=FamilyKnowledgeCard(
                lens=FamilyLensView(**step.card.lens.model_dump()) if step.card.lens else None,
                tradition_th=step.card.tradition_th,
                learning_point_th=step.card.learning_point_th,
                evidence_status=step.card.evidence_status,
                precautions_th=step.card.precautions_th,
                when_to_consult_th=step.card.when_to_consult_th,
                sources=[
                    FamilyCardSource(id=i, title_th=by_id[i].title_th, url=by_id[i].url)
                    for i in step.card.source_ids
                ],
            )
            if step.card
            else None,
        )
    shared = [fact for _, fact in state.shared]
    return FamilyView(
        room_id=row.id,
        story_id=story.id,
        title_th=story.title_th,
        role=role,
        private_brief_th=story.roles[role],
        partner_joined=story.mode == "solo" or bool(row.partner_hash),
        state_version=state.version,
        completed_steps=len(chosen),
        total_steps=len(story.steps),
        partner_online=story.mode == "coop" and partner_online(row, role),
        my_facts=[
            FamilyFactView(id=f.id, role=f.role, text_th=f.text_th, shared=f.id in shared)
            for f in story.facts
            if f.role == role and (f.id not in story.discoverable or f.id in state.revealed)
        ],
        shared_facts=[
            FamilyFactView(id=f.id, role=f.role, text_th=f.text_th, shared=True)
            for fact_id in shared
            for f in story.facts
            if f.id == fact_id
        ],
        scene=scene,
        transcript=transcript,
        report=report,
        dialogue=dialogue(db, row, story, state, role),
        assignment_id=row.assignment_id,
    )


def dialogue(
    db: Session, row: FamilyRoom, story: FamilyStory, state: Progress, role: FamilyRole
) -> list[FamilyDialogueTurn]:
    """The caller's own typed questions with the replies that were shown (never the partner's)."""
    if not state.asks:
        return []
    texts = {
        m.client_turn_id: m
        for m in db.scalars(
            select(FamilyMessage).where(FamilyMessage.room_id == row.id, FamilyMessage.role == role)
        )
    }
    turns = []
    for e in events(db, row):
        message = texts.get(e.client_turn_id)
        if e.kind == "ask" and e.role == role and message and e.reply_th:
            step = next((st for st in story.steps if st.id == message.step_id), None)
            if step:
                turns.append(
                    FamilyDialogueTurn(
                        step_id=step.id,
                        speaker_th=step.character_th or step.speaker_th,
                        text_th=message.text,
                        reply_th=e.reply_th,
                    )
                )
    return turns


def _prior(saved: list[FamilyEvent], turn_id: uuid.UUID) -> FamilyEvent | None:
    return next((event for event in saved if event.client_turn_id == turn_id), None)


def decide(db: Session, row: FamilyRoom, role: FamilyRole, body: FamilyDecision) -> FamilyView:
    """One endpoint for both turn decisions and joint votes; the current step decides which."""
    saved = events(db, row)
    prior = _prior(saved, body.client_turn_id)
    if prior:
        # A pending vote does not move state_version, so only decisions pin the event position.
        same = (prior.role, prior.choice_id) == (role, body.choice_id) and (
            prior.kind == "vote" or prior.idx == body.state_version + 1
        )
        if prior.kind == "share" or not same:
            raise ApiError("IDEMPOTENCY_CONFLICT", "decision ID reused")
        return view(db, row, role)
    story = FamilyStory.model_validate(row.story)
    if story.mode == "coop" and not row.partner_hash:
        raise ApiError("INVALID_PHASE", "waiting for partner")
    state = progress(story, saved)
    if body.state_version != state.version:
        raise ApiError("TURN_IN_PROGRESS", "room changed; refresh before deciding")
    if len(state.choices) >= len(story.steps):
        raise ApiError("DECISION_OPTION_INVALID", "not this role's turn")
    step = story.steps[len(state.choices)]
    if step.joint:
        if role in state.votes:
            raise ApiError("INVALID_PHASE", "vote already submitted; waiting for partner")
        if not any(c.id == body.choice_id for c in step.choices):
            raise ApiError("DECISION_OPTION_INVALID", "unknown decision")
        kind, reply = "vote", None
    else:
        try:
            choose(story, state.choices, role, body.choice_id)
            if step.kind == "discover" and revealing(step, state.asked(len(state.choices))) < (
                step.min_reveals
            ):
                raise ValueError("ask more questions before continuing")
        except ValueError as exc:
            raise ApiError("DECISION_OPTION_INVALID", str(exc)) from exc
        kind = "decision"
        reply = next(c for c in step.choices if c.id == body.choice_id).reply_th
    db.add(
        FamilyEvent(
            room_id=row.id,
            idx=len(saved) + 1,
            role=role,
            kind=kind,
            choice_id=body.choice_id,
            reply_th=reply,
            client_turn_id=body.client_turn_id,
        )
    )
    db.flush()
    return view(db, row, role)


def share(db: Session, row: FamilyRoom, role: FamilyRole, body: FamilyShare) -> FamilyView:
    """Move one fact from the caller's own private brief into the shared timeline."""
    saved = events(db, row)
    prior = _prior(saved, body.client_turn_id)
    if prior:
        if (prior.role, prior.kind, prior.choice_id) != (role, "share", body.fact_id):
            raise ApiError("IDEMPOTENCY_CONFLICT", "share ID reused")
        return view(db, row, role)
    story = FamilyStory.model_validate(row.story)
    if story.mode == "coop" and not row.partner_hash:
        raise ApiError("INVALID_PHASE", "waiting for partner")
    state = progress(story, saved)
    if len(state.choices) >= len(story.steps):
        raise ApiError("INVALID_PHASE", "story is complete")
    fact = next((f for f in story.facts if f.id == body.fact_id and f.role == role), None)
    # unknown, the other role's, or not yet discovered: deliberately indistinguishable
    if fact is None or (fact.id in story.discoverable and fact.id not in state.revealed):
        raise ApiError("DECISION_OPTION_INVALID", "fact cannot be shared")
    # A repeat share is recorded too (replay dedupes it) so its client_turn_id stays bound.
    db.add(
        FamilyEvent(
            room_id=row.id,
            idx=len(saved) + 1,
            role=role,
            kind="share",
            choice_id=fact.id,
            client_turn_id=body.client_turn_id,
        )
    )
    db.flush()
    return view(db, row, role)
