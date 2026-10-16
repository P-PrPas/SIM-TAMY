"""Decision, completion and report (API_DESIGN 5, FR-ENG-03, FR-SES-04, FR-SCR-01).

The score is a pure function of the Event Log (`engine.scoring`); nothing here decides a result.
`complete` writes the report once; calling it again returns the same answer.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.ai.debrief import generate_debrief
from app.ai.llm_client import LLMCallRecord
from app.api.deps import LLMFactory
from app.api.v1.schemas import (
    CaseStatus,
    CompleteRequest,
    CompleteResponse,
    Debrief,
    DebriefParagraph,
    DecisionRecord,
    DecisionRequest,
    DecisionResponse,
    EffectiveScore,
    Reply,
    ReportCase,
    ReportResponse,
    SafetyStatus,
    Variant,
)
from app.content.loader import ContentStore, LoadedCase
from app.core import limits
from app.core.errors import ApiError
from app.db.models import Event, LearnerSession, Report, Turn
from app.db.repo import EventRepo, LlmCallRepo, SessionRepo, TurnRepo
from app.domain.case import VariantId
from app.domain.events import LoggedEvent
from app.domain.scoring import Finding, Scoring
from app.engine.findings import DuplicateResult, build_findings
from app.engine.glassbox import build_glassbox, build_timeline
from app.engine.replay import build_replay
from app.engine.scenario import commit_decision
from app.engine.scoring import InvalidRubric, MalformedEvent, score
from app.services.briefs import disclaimer_th, status_label, timeline_labels
from app.services.sessions import ensure_alive, lock_session, pinned_case, public_phase, state_of

log = logging.getLogger("app.closing")


def logged_events(db: Session, session_id: Any) -> list[LoggedEvent]:
    rows = db.scalars(select(Event).where(Event.session_id == session_id).order_by(Event.id))
    return [
        LoggedEvent.model_validate(
            {"id": e.id, "type": e.type, "turn_idx": e.turn_idx, "payload": e.payload}
        )
        for e in rows
    ]


# ---------- decision ----------


def _decision_response(db: Session, row: LearnerSession, option_id: str) -> DecisionResponse:
    """The answer the first commit gave, rebuilt from its events (later phases do not leak in)."""
    events = db.scalars(
        select(Event)
        .where(Event.session_id == row.id, Event.type.in_(("DECISION_COMMITTED", "PHASE_CHANGED")))
        .order_by(Event.id)
    ).all()
    at = next(e.turn_idx for e in events if e.type == "DECISION_COMMITTED")
    moved = [
        e.payload["to"]
        for e in events
        if e.type == "PHASE_CHANGED" and e.payload.get("trigger") == "decision"
    ]
    opening = db.scalars(
        select(Turn).where(Turn.session_id == row.id, Turn.idx == at, Turn.speaker == "relative")
    ).first()  # the scripted line a Variant C referral started the pressure with
    return DecisionResponse(
        phase=public_phase(moved[0] if moved else "INTERVIEW"),  # a decision starts in INTERVIEW
        decision=DecisionRecord(option_id=option_id, committed_at_idx=at),
        replies=[Reply(speaker="relative", text=opening.text)] if opening else [],
        pressure_turns_allowed=limits.PRESSURE_MAX_TURNS if opening else None,
    )


def commit(
    db: Session, store: ContentStore, authed: LearnerSession, req: DecisionRequest
) -> DecisionResponse:
    row = lock_session(db, authed.id)
    ensure_alive(db, row)  # a repeat is answered only while the session is alive or completed
    state = state_of(row)
    if state.decision == req.option_id:  # the same choice again: the original result
        return _decision_response(db, row, req.option_id)
    loaded = pinned_case(store, row)
    variant: VariantId = row.variant  # type: ignore[assignment]
    result = commit_decision(state, req.option_id, loaded.case, variant)  # EngineError -> envelope
    events = EventRepo(db)
    for e in result.events:
        payload = dict(e.payload)
        if e.type == "DECISION_COMMITTED" and req.rationale_th:
            payload["rationale_th"] = req.rationale_th  # scoring ignores extra keys
        events.append(session_id=row.id, turn_idx=e.turn_idx, type=e.type, payload=payload)
    SessionRepo(db).save_state(
        row.id, result.state.model_dump(mode="json"), expected_version=row.state_version
    )
    line = result.pressure_line
    if line:
        TurnRepo(db).add(
            session_id=row.id, idx=result.state.turn_idx, speaker=line.speaker, text=line.text_th
        )
    return DecisionResponse(
        phase=public_phase(result.state.phase),
        decision=DecisionRecord(option_id=req.option_id, committed_at_idx=result.state.turn_idx),
        replies=[Reply(speaker="relative", text=line.text_th)] if line else [],
        pressure_turns_allowed=limits.PRESSURE_MAX_TURNS if line else None,
    )


# ---------- complete ----------


def _done(session_id: Any) -> CompleteResponse:
    return CompleteResponse(
        status="completed", report_ready=True, report_url=f"/v1/sessions/{session_id}/report"
    )


def _template_debrief(findings: tuple[Finding, ...]) -> Debrief:
    """FR-DEB-02: the rubric's own wording, one paragraph per finding (T-035 adds the LLM path)."""
    paragraphs = [DebriefParagraph(finding_ids=[f.id], text_th=f.text_th) for f in findings]
    return Debrief(source="template", paragraphs=paragraphs)


def complete(
    db: Session, store: ContentStore, llm: LLMFactory, authed: LearnerSession, req: CompleteRequest
) -> CompleteResponse:
    row = lock_session(db, authed.id)
    if row.status == "completed":
        return _done(row.id)
    ensure_alive(db, row)
    state = state_of(row)
    if state.phase != "CLOSING":
        raise ApiError("INVALID_PHASE", "the case is not ready to complete", {"phase": state.phase})
    loaded = pinned_case(store, row)
    idx = state.turn_idx

    events = EventRepo(db)
    note = (req.note_th or "").strip()
    if note:
        payload: dict[str, Any] = {"chars": len(note), "note_th": note}
        events.append(session_id=row.id, turn_idx=idx, type="NOTE_SUBMITTED", payload=payload)
    phase = {"from": "CLOSING", "to": "COMPLETED", "trigger": "complete"}
    events.append(session_id=row.id, turn_idx=idx, type="PHASE_CHANGED", payload=phase)
    events.append(session_id=row.id, turn_idx=idx, type="SESSION_COMPLETED", payload={})

    log_ = logged_events(db, row.id)
    variant: VariantId = row.variant  # type: ignore[assignment]
    try:
        scoring = score(log_, loaded.rubric, loaded.actions, variant)
        findings = build_findings(scoring.items, loaded.rubric)
    except (MalformedEvent, InvalidRubric, DuplicateResult) as exc:
        log.error("session %s cannot be scored: %s", row.id, exc)
        raise ApiError("INTERNAL_ERROR", "the session could not be scored") from exc

    calls: list[LLMCallRecord] = []
    debrief = generate_debrief(llm("debrief", calls.append), findings)
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

    db.add(
        Report(
            session_id=row.id,
            rubric_version=loaded.rubric.rubric_version,
            scoring=scoring.model_dump(mode="json"),  # the shape `make rescore` diffs
            debrief=debrief.model_dump(mode="json"),
            glassbox=build_glassbox(log_, loaded.case, loaded.actions).model_dump(mode="json"),
            replay=build_replay(log_, loaded.case, disclaimer_th()).model_dump(mode="json"),
        )
    )
    SessionRepo(db).save_state(
        row.id,
        state.model_copy(update={"phase": "COMPLETED"}).model_dump(mode="json"),
        expected_version=row.state_version,
    )
    row.status = "completed"
    row.ended_at = datetime.now(UTC)
    return _done(row.id)


# ---------- report ----------


def report(db: Session, store: ContentStore, row: LearnerSession) -> ReportResponse:
    saved = db.get(Report, row.id)  # written once, when the session completes
    if saved is None:
        raise ApiError("REPORT_NOT_READY", "the report is available after the case is completed")
    loaded = pinned_case(store, row)
    scoring = Scoring.model_validate(saved.scoring)
    findings = build_findings(scoring.items, loaded.rubric)
    log_ = logged_events(db, row.id)
    return _assemble(row, loaded, saved, scoring, findings, log_)


def _assemble(
    row: LearnerSession,
    loaded: LoadedCase,
    saved: Report,
    scoring: Scoring,
    findings: tuple[Finding, ...],
    log_: list[LoggedEvent],
) -> ReportResponse:
    finding_of = {f.rubric_item_id: f.id for f in findings}
    cited = {i for f in findings for i in f.reference_ids}
    case = loaded.case
    return ReportResponse.model_validate(
        {
            "session_id": row.id,
            "generated_at": saved.created_at,
            "engine_version": __version__,
            "rubric_version": saved.rubric_version,
            "case": ReportCase(
                case_id=case.case_id,
                version=case.version,
                hash=loaded.case_hash,
                status=CaseStatus(case.status),
                status_label_th=status_label(case.status),
                title_th=case.title_th,
            ),
            "variant": Variant(row.variant),
            "safety_status": scoring.safety_status,
            "total_score": scoring.total_score,
            "competencies": [c.model_dump() for c in scoring.competencies],
            "items": [
                {**i.model_dump(), "finding_id": finding_of.get(i.id)} for i in scoring.items
            ],
            "findings": [f.model_dump() for f in findings],
            "debrief": saved.debrief,
            "timeline": [
                t.model_dump()
                for t in build_timeline(log_, case, loaded.actions, timeline_labels())
            ],
            "glassbox": saved.glassbox,
            "replay": saved.replay,
            "references": [r.model_dump() for r in case.references if r.id in cited],
            "overrides": [],
            "effective": EffectiveScore(
                safety_status=SafetyStatus(scoring.safety_status), total_score=scoring.total_score
            ),
            "disclaimers": [disclaimer_th()],
        }
    )
