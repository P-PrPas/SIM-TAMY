"""AI-03 debrief for a finished family room, stored once per debrief version (idempotent)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.contracts import DebriefOutput
from app.ai.evidence import evidence_pack
from app.ai.family_debrief import DebriefInput, StepFact, debrief
from app.ai.intent import prompt_version
from app.ai.trace import Trace
from app.api.deps import LLMFactory
from app.core.errors import ApiError
from app.db.family import FamilyDebrief, FamilyRoom
from app.domain.family import FamilyStory
from app.engine.family import assess, rubric_score, selections
from app.services import family

SCHEMA = "ai.debrief.v1"


def build_input(db: Session, row: FamilyRoom, story: FamilyStory) -> DebriefInput | None:
    saved = family.events(db, row)
    state = family.progress(story, saved)
    if len(state.choices) < len(story.steps):
        return None
    chosen = selections(story, state.choices)
    steps: list[StepFact] = []
    seen: set[str] = set()
    intents = {i.id: i for s in story.steps for i in s.intents}
    for event in saved:
        if event.kind == "ask" and event.choice_id not in seen:
            seen.add(event.choice_id)
            intent = intents[event.choice_id]
            steps.append(StepFact(f"{row.id}:{event.idx}", intent.label_th, intent.dimension, True))
    for i, (step, choice) in enumerate(zip(story.steps, chosen, strict=True)):
        if step.kind == "choice":
            steps.append(
                StepFact(
                    f"{row.id}:{state.locked_at[i]}",
                    choice.feedback_th,
                    choice.dimension,
                    choice.safe,
                )
            )
    steps.sort(key=lambda s: int(s.event_id.rsplit(":", 1)[1]))
    rubric = rubric_score(story, state)
    pack = evidence_pack(story, story.steps[0], "mother", [], release_id=row.release_id)
    return DebriefInput(
        attempt_id=str(row.id),
        score_total=rubric.total if rubric else None,
        safety_met=assess(story, state.choices, state.facts).safety_met,
        steps=tuple(steps),
        objective_ids=tuple(story.objective_ids),
        claim_ids=tuple(f"{i.knowledge_id}:{i.claim_id}" for i in pack.items),
        asset_ids=tuple(story.knowledge_unit_ids),
        dimensions=tuple(story.weights),
    )


def get_or_create(db: Session, row: FamilyRoom, llm: LLMFactory) -> tuple[DebriefOutput, str]:
    story = FamilyStory.model_validate(row.story)
    version = f"{SCHEMA}+{prompt_version('debrief.md')}"
    stored = db.scalar(
        select(FamilyDebrief).where(
            FamilyDebrief.room_id == row.id, FamilyDebrief.debrief_version == version
        )
    )
    if stored:
        return DebriefOutput.model_validate(stored.payload), version
    src = build_input(db, row, story)
    if src is None:
        raise ApiError("REPORT_NOT_READY", "debrief is available after the story is complete")
    trace = Trace(db, row.id, row.release_id)
    out, reason = debrief(llm("debrief", trace.on_call), src)
    trace.close(
        "ai03",
        prompt_version=prompt_version("debrief.md"),
        schema_version=SCHEMA,
        status="valid" if reason is None else "rejected",
        fallback_reason=reason,
    )
    db.add(
        FamilyDebrief(
            room_id=row.id,
            debrief_version=version,
            payload=out.model_dump(mode="json"),
            fallback_used=out.fallback_used,
        )
    )
    db.flush()
    return out, version
