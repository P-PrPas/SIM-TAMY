"""One learner turn (API_DESIGN 7.2): Interpreter, policy, Engine, Generator/Validator, persist.

One transaction per turn. The session row is locked with NOWAIT, so a second turn in flight gets
TURN_IN_PROGRESS; `state_version` is the second guard. Events are logged in the order scoring
relies on (PRD 7.5): the accepted actions come before the engine's events of the same turn.
"""

import uuid
from typing import Any, NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.interpreter import HistoryTurn, Interpretation, interpret
from app.ai.lexical import match_actions
from app.ai.llm_client import LLMCallRecord, LLMError
from app.ai.policy import apply_policy
from app.api.deps import LLMFactory
from app.api.v1.schemas import Reply, TurnRequest, TurnResponse
from app.content.loader import ContentStore
from app.core import limits
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import Event, LearnerSession
from app.db.repo import EventRepo, LlmCallRepo, SessionRepo, TurnRepo
from app.domain.case import VariantId
from app.domain.events import EventType
from app.engine.scenario import apply
from app.services.patient_voice import Directive, Spoken, Voice, VoiceRequest, speak
from app.services.sessions import ensure_alive, lock_session, pinned_case, public_phase, state_of

OPEN_PHASES = {"INTRO", "INTERVIEW", "PRESSURE"}


class Outcome(NamedTuple):
    response: TurnResponse
    replayed: bool


def _remaining(idx: int) -> int:
    return max(0, limits.MAX_TURNS - idx)


def _replay(db: Session, row: LearnerSession, learner_turn_idx: int) -> TurnResponse:
    """Rebuild the stored answer of an earlier turn from turns + events (no new work)."""
    turns = [t for t in TurnRepo(db).list_for_session(row.id) if t.idx == learner_turn_idx]
    events = list(
        db.scalars(
            select(Event)
            .where(Event.session_id == row.id, Event.turn_idx <= learner_turn_idx)
            .order_by(Event.id)
        )
    )
    here = [e for e in events if e.turn_idx == learner_turn_idx]
    # the relative's opening line is stored at the decision's index: it answers the decision
    opened_at = {e.turn_idx for e in events if e.type == "PRESSURE_STARTED"}
    replies = [
        Reply(speaker=t.speaker, text=t.text)
        for t in turns
        if t.speaker != "learner" and not (t.speaker == "relative" and t.idx in opened_at)
    ]
    # a decision logged at this turn's index came after its answer; one before it (the pressure
    # scene) is the phase this turn was played in. The completion never precedes a turn.
    phases = [
        e.payload["to"]
        for e in events
        if e.type == "PHASE_CHANGED"
        and e.payload.get("trigger") != "complete"
        and not (e.payload.get("trigger") == "decision" and e.turn_idx == learner_turn_idx)
    ]
    return TurnResponse(
        turn_idx=learner_turn_idx,
        replies=replies,
        phase=public_phase(phases[-1] if phases else "INTERVIEW"),
        clarification=any(e.type == "CLARIFICATION_ASKED" for e in here),
        turns_remaining=_remaining(learner_turn_idx),
        degraded=any(e.type == "LLM_FALLBACK_USED" for e in here),
    )


def _stored(db: Session, row: LearnerSession, req: TurnRequest) -> TurnResponse | None:
    if req.client_turn_id is None:
        return None
    earlier = TurnRepo(db).find_by_client_id(row.id, req.client_turn_id)
    if earlier is None:
        return None
    if earlier.text != req.text:
        raise ApiError("IDEMPOTENCY_CONFLICT", "client_turn_id was used for a different message")
    return _replay(db, row, earlier.idx)


def _history(db: Session, session_id: uuid.UUID) -> tuple[HistoryTurn, ...]:
    return tuple(HistoryTurn(t.speaker, t.text) for t in TurnRepo(db).list_for_session(session_id))


def send_turn(
    db: Session,
    store: ContentStore,
    llm: LLMFactory,
    voice: Voice,
    authed: LearnerSession,
    req: TurnRequest,
) -> Outcome:
    if (stored := _stored(db, authed, req)) is not None:
        return Outcome(stored, True)
    row = lock_session(db, authed.id)
    if (stored := _stored(db, row, req)) is not None:  # finished while we waited for the lock
        return Outcome(stored, True)

    if row.status == "completed":
        raise ApiError("SESSION_COMPLETED", "the session is completed")
    ensure_alive(db, row)
    state = state_of(row)
    if state.phase not in OPEN_PHASES:
        raise ApiError("INVALID_PHASE", "messages are not accepted now", {"phase": state.phase})
    if state.turn_idx >= limits.MAX_TURNS:
        raise ApiError("TURN_LIMIT", "turn limit reached", {"max_turns": limits.MAX_TURNS})

    loaded = pinned_case(store, row)
    history = _history(db, row.id)
    calls: list[LLMCallRecord] = []

    # 1. Interpreter, with the lexical fallback when the LLM path fails
    degraded = False
    try:
        interp = interpret(
            llm("interpreter", calls.append),
            loaded.actions,
            req.text,
            history,
            public_phase(state.phase).value,
        )
        source = "llm"
    except LLMError:
        interp = Interpretation(actions=match_actions(req.text, loaded.actions))
        source, degraded = "lexical", True
    settings = get_settings()
    decision = apply_policy(
        interp,
        accept_threshold=settings.action_accept_threshold,
        clarify_threshold=settings.action_clarify_threshold,
    )

    # 2. Engine (pure)
    variant: VariantId = row.variant  # type: ignore[assignment]
    result = apply(state, [a.id for a in decision.accepted], loaded.case, variant)
    new_state = result.state
    if decision.clarify:
        flags = new_state.flags.model_copy(
            update={"clarifications": new_state.flags.clarifications + 1}
        )
        new_state = new_state.model_copy(update={"flags": flags})
    idx = new_state.turn_idx

    # 3. Reply: the pressure scene is scripted in the case (ADR-11), otherwise the patient speaks
    speaker = "patient"
    if state.phase == "PRESSURE":
        line = result.pressure_line
        speaker = line.speaker if line else speaker
        spoken = Spoken(line.text_th if line else "", (), False, False)
    else:
        directive: Directive = (
            "clarify"
            if decision.clarify
            else "answer"
            if decision.accepted
            else "deflect_smalltalk"
        )
        request = VoiceRequest(
            persona_style_th=loaded.case.variants[variant].persona.style_th,
            allowed=result.allowed,
            directive=directive,
            learner_text=req.text,
            history=history,
        )
        spoken = speak(request, loaded.case, new_state.revealed_fact_ids, voice)

    # 4. Persist: events in contract order, turns, llm_calls, state (CAS), all in this transaction
    log = EventRepo(db)

    def add(type_: EventType, payload: dict[str, Any], at: int = idx) -> None:
        log.append(session_id=row.id, turn_idx=at, type=type_, payload=payload)

    add("LEARNER_MESSAGE", {"chars": len(req.text)})
    accepted = [
        {"id": a.id, "confidence": a.confidence, "span": a.evidence_span} for a in decision.accepted
    ]
    add("ACTIONS_DETECTED", {"actions": accepted, "source": source})
    if decision.clarify:
        add("CLARIFICATION_ASKED", {"candidates": list(decision.candidates)})
    for e in result.events:
        add(e.type, e.payload, e.turn_idx)
    if degraded:
        add("LLM_FALLBACK_USED", {"component": "interpreter"})
    for attempt, rules in enumerate(spoken.rejected, start=1):
        add("VALIDATOR_REJECTED", {"attempt": attempt, "rules": list(rules)})
    if spoken.fallback:
        add(
            "LLM_FALLBACK_USED",
            {"component": "generator" if spoken.generator_failed else "validator"},
        )

    turns = TurnRepo(db)
    turns.add(
        session_id=row.id,
        idx=idx,
        speaker="learner",
        text=req.text,
        client_turn_id=req.client_turn_id,
    )
    if spoken.text:
        turns.add(session_id=row.id, idx=idx, speaker=speaker, text=spoken.text)
    for call in calls:
        LlmCallRepo(db).record(
            purpose=call.purpose,
            session_id=row.id,
            turn_idx=idx,
            provider=call.provider,
            model=call.model,
            prompt_tokens=call.prompt_tokens,
            completion_tokens=call.completion_tokens,
            latency_ms=call.latency_ms,
            ok=call.ok,
            error=call.error,
        )
    SessionRepo(db).save_state(
        row.id, new_state.model_dump(mode="json"), expected_version=row.state_version
    )

    return Outcome(
        TurnResponse(
            turn_idx=idx,
            replies=[Reply(speaker=speaker, text=spoken.text)] if spoken.text else [],
            phase=public_phase(new_state.phase),
            clarification=decision.clarify,
            turns_remaining=_remaining(idx),
            degraded=degraded or spoken.fallback,
        ),
        False,
    )
