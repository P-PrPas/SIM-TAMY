"""Typed chat in a family room (AI-01 -> controller -> AI-02). The engine stays the only authority.

The model maps text to an allowed intent; this controller decides what that means: a discover
`ask` reveals facts to the asking role, a non-critical choice step may commit from text, and
critical or joint steps only ever offer their buttons. Every outcome is a deterministic function
of the accepted intent and the replayed state.
"""

from functools import lru_cache

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.evidence import evidence_pack
from app.ai.grounded import AllowedFact, GroundedRequest, GroundedResult, generate
from app.ai.intent import (
    V2,
    HistoryItem,
    IntentResult,
    guard,
    interpret_intent,
    options_for,
    prompt_version,
)
from app.ai.trace import Trace
from app.api.deps import LLMFactory
from app.api.v1.family_schemas import (
    FamilyCitation,
    FamilyClarification,
    FamilyMessageResult,
    FamilyOption,
    FamilyReply,
)
from app.api.v1.family_schemas import FamilyMessage as MessageBody
from app.core.errors import ApiError
from app.db.family import FamilyEvent, FamilyMessage, FamilyRoom
from app.domain.family import FamilyIntent, FamilyRole, FamilyStep, FamilyStory
from app.engine.family import Progress
from app.services import family

AI01 = "ai.intent.v1"
AI02 = "ai.grounded_reply.v1"
HISTORY = 6


@lru_cache
def canned() -> dict[str, str]:
    loaded: dict[str, str] = yaml.safe_load((V2 / "canned_th.yaml").read_text(encoding="utf-8"))
    return loaded


def _reply(speaker: str, text: str, citations: list[FamilyCitation] | None = None) -> FamilyReply:
    return FamilyReply(speaker_th=speaker, text_th=text, citations=citations or [])


def _clarification(step: FamilyStep) -> FamilyClarification:
    return FamilyClarification(
        options=[FamilyOption(id=o.id, text_th=o.label_th) for o in options_for(step)]
    )


def _citations(story: FamilyStory, result: GroundedResult) -> list[FamilyCitation]:
    titles = {s.id: s.title_th for s in story.sources}
    return [
        FamilyCitation(
            knowledge_id=c.knowledge_id,
            claim_id=c.claim_id,
            source_id=c.source_id,
            title=titles.get(c.source_id, c.source_id),
            locator=c.source_locator,
        )
        for c in result.citations
    ]


def _history(db: Session, row: FamilyRoom, role: FamilyRole) -> list[HistoryItem]:
    rows = db.scalars(
        select(FamilyMessage)
        .where(FamilyMessage.room_id == row.id, FamilyMessage.role == role)
        .order_by(FamilyMessage.id.desc())
        .limit(HISTORY)
    )
    return [HistoryItem(m.text, m.intent_code) for m in reversed(list(rows))]


def _answer(
    row: FamilyRoom,
    story: FamilyStory,
    step: FamilyStep,
    intent: FamilyIntent,
    state: Progress,
    text: str,
    llm: LLMFactory,
    trace: Trace,
) -> tuple[str, list[FamilyCitation]]:
    """The reply shown for an accepted ask: stored on repeat, template, abstain or AI-02."""
    stored = state.reply_for(len(state.choices), intent.id)
    if stored:  # a repeat is logged but never re-reveals or re-generates
        return stored, []
    if intent.high_risk:  # authored template only (contracts section 5, step 4)
        return intent.reply_th, []
    revealed = set(intent.reveals)
    facts = tuple(AllowedFact(f.id, f.text_th) for f in story.facts if f.id in revealed)
    pack = evidence_pack(
        story,
        step,
        step.role,
        [f.id for f in facts],
        unit_ids=intent.unit_ids,
        release_id=row.release_id,
    )
    if not facts and not pack.items:
        return step.abstain_th or canned()["abstain"], []
    blocked = tuple(
        (f.id, tuple(f.leak_terms_th))
        for f in story.facts
        if f.leak_terms_th and f.id not in revealed
    )
    result = generate(
        llm("generator", trace.on_call),
        GroundedRequest(
            character_th=step.character_th or step.speaker_th,
            learner_text=text,
            facts=facts,
            pack=pack,
            must_use=tuple(intent.reveals),
            need_citation=not facts,
            blocked_terms=blocked,
        ),
        intent.reply_th,
    )
    trace.close(
        "ai02",
        prompt_version=prompt_version("grounded_reply.md"),
        schema_version=AI02,
        status=result.status,
        fallback_reason=result.fallback_reason,
    )
    return result.text_th, _citations(story, result)


def message(
    db: Session, row: FamilyRoom, role: FamilyRole, body: MessageBody, llm: LLMFactory
) -> FamilyMessageResult:
    story = FamilyStory.model_validate(row.story)
    saved = family.events(db, row)
    prior = db.scalar(
        select(FamilyMessage).where(
            FamilyMessage.room_id == row.id, FamilyMessage.client_turn_id == body.client_turn_id
        )
    )
    if prior:
        if (prior.role, prior.text) != (role, body.text):
            raise ApiError("IDEMPOTENCY_CONFLICT", "message ID reused")
        event = next((e for e in saved if e.client_turn_id == body.client_turn_id), None)
        step = next((s for s in story.steps if s.id == prior.step_id), story.steps[0])
        shown = (
            _reply(step.character_th or step.speaker_th, event.reply_th)
            if event and event.reply_th
            else None
        )
        return FamilyMessageResult(view=family.view(db, row, role), reply=shown, clarification=None)
    if story.mode == "coop" and not row.partner_hash:
        raise ApiError("INVALID_PHASE", "waiting for partner")
    state = family.progress(story, saved)
    if body.state_version != state.version:
        raise ApiError("TURN_IN_PROGRESS", "room changed; refresh before typing")
    if len(state.choices) >= len(story.steps):
        raise ApiError("INVALID_PHASE", "story is complete")
    step = story.steps[len(state.choices)]
    speaker = step.character_th or step.speaker_th

    def done(
        reply: FamilyReply | None = None, clarification: FamilyClarification | None = None
    ) -> FamilyMessageResult:
        db.flush()
        return FamilyMessageResult(
            view=family.view(db, row, role), reply=reply, clarification=clarification
        )

    boundary = _reply(canned()["speaker_system"], story.boundary_th or canned()["boundary"])
    if not (story.mode == "solo" or step.joint or step.role == role):
        return done(_reply(canned()["speaker_system"], canned()["not_your_turn"]))
    record = FamilyMessage(
        room_id=row.id,
        role=role,
        step_id=step.id,
        text=body.text,
        client_turn_id=body.client_turn_id,
    )
    db.add(record)
    blocked = guard(body.text)
    if blocked == "boundary":
        record.intent_code = "REAL_WORLD_HEALTH_QUERY"
        return done(boundary)
    if blocked == "injection":
        record.intent_code = "OUT_OF_SCOPE"
        return done(_reply(speaker, canned()["out_of_scope"]))

    trace = Trace(db, row.id, row.release_id)
    result: IntentResult = interpret_intent(
        llm("interpreter", trace.on_call),
        options_for(step),
        body.text,
        _history(db, row, role),
        [i for _, i, _ in state.asks],
    )
    trace.close(
        "ai01",
        prompt_version=prompt_version("intent.md"),
        schema_version=AI01,
        status=result.status,
        fallback_reason=result.fallback_reason,
    )
    record.intent_code = result.code
    if result.kind == "boundary":
        return done(boundary)
    if result.kind == "generic":
        if result.code == "REQUEST_CLARIFICATION":
            return done(clarification=_clarification(step))
        key = "discuss_with_partner" if result.code == "DISCUSS_WITH_PARTNER" else "out_of_scope"
        return done(_reply(speaker, canned()[key]))
    if result.kind == "clarify":
        return done(clarification=_clarification(step))
    if result.kind == "ignore" or result.code is None:
        return done(_reply(speaker, canned()["rephrase"]))

    if step.kind == "discover":
        intent = next(i for i in step.intents if i.id == result.code)
        text, citations = _answer(row, story, step, intent, state, body.text, llm, trace)
        _log(row, db, len(saved), role, "ask", intent.id, text, body)
        return done(_reply(speaker, text, citations))
    # choice step: only a non-critical, non-joint step may commit from text
    if step.critical or step.joint:
        return done(clarification=_clarification(step))
    choice = next(c for c in step.choices if c.id == result.code)
    _log(row, db, len(saved), role, "decision", choice.id, choice.reply_th, body)
    return done(_reply(speaker, choice.reply_th))


def _log(
    row: FamilyRoom,
    db: Session,
    count: int,
    role: FamilyRole,
    kind: str,
    choice_id: str,
    reply: str,
    body: MessageBody,
) -> None:
    db.add(
        FamilyEvent(
            room_id=row.id,
            idx=count + 1,
            role=role,
            kind=kind,
            choice_id=choice_id,
            reply_th=reply,
            client_turn_id=body.client_turn_id,
        )
    )
