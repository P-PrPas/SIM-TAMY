"""Institution workspace: org-scoped cohorts, assignments, aggregate analytics, join and passport.

Prototype boundary (ADR-15): accounts are mock, the caller's org is trusted. Every query is still
scoped by `classes.org_id`, so organization A never sees organization B (CT-08). Analytics are
replayed from the family event log (never stored scores) and each room counts once (CT-09).
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.v1 import institution_schemas as out
from app.content.family import load_stories
from app.content.institution import STAFF_ROLES, DemoAccount, DemoOrg, institutions
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.family import FamilyEvent, FamilyMessage, FamilyRoom
from app.db.models import Assignment, ClassRoom
from app.domain.family import FamilyRole, FamilyStory
from app.engine.family import FamilyEventRecord, assess, replay, rubric_score
from app.services import instructor

MIN_OBJECTIVE_N = 3  # per-objective rates stay hidden below this many finished attempts (CT-12)


# --- accounts -------------------------------------------------------------------------------


def accounts() -> list[DemoAccount]:
    return list(institutions(get_settings().content_dir).accounts)


def org_of(org_id: str) -> DemoOrg:
    org = next((o for o in institutions(get_settings().content_dir).orgs if o.id == org_id), None)
    if org is None:
        raise ApiError("NOT_FOUND", "organization not found")
    return org


def staff_in_org(account: DemoAccount, org_id: str) -> None:
    """Educator or org_admin of exactly this org; anything else is forbidden."""
    if account.role not in STAFF_ROLES or account.org_id != org_id:
        raise ApiError("FORBIDDEN", "not staff of this organization")


# --- catalog --------------------------------------------------------------------------------


def catalog() -> dict[str, FamilyStory]:
    """Stories a cohort may assign: the family catalog, Draft only while ALLOW_DRAFT_CASES."""
    settings = get_settings()
    return {
        s.id: s
        for s in load_stories(settings.content_dir)
        if s.status == "Approved" or settings.allow_draft_cases
    }


# --- cohorts --------------------------------------------------------------------------------


def _cohort_out(row: ClassRoom, assignment_count: int) -> out.Cohort:
    return out.Cohort(
        id=row.id,
        code=row.code,
        name=row.name or "",
        created_at=row.created_at,
        assignment_count=assignment_count,
    )


def _counts(db: Session, class_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(Assignment.class_id, func.count(Assignment.id))
        .where(Assignment.class_id.in_(class_ids))
        .group_by(Assignment.class_id)
    )
    return {class_id: count for class_id, count in rows}


def _org_cohorts(db: Session, org_id: str) -> list[ClassRoom]:
    return list(
        db.scalars(
            select(ClassRoom)
            .where(ClassRoom.org_id == org_id)
            .order_by(ClassRoom.created_at.desc(), ClassRoom.id.desc())
        )
    )


def cohort_of(db: Session, account: DemoAccount, cohort_id: uuid.UUID) -> ClassRoom:
    """A cohort of the caller's own org. Another org's cohort is indistinguishable from none."""
    if account.role not in STAFF_ROLES:
        raise ApiError("FORBIDDEN", "not staff")
    row = db.get(ClassRoom, cohort_id)
    if row is None or row.org_id is None or row.org_id != account.org_id:
        raise ApiError("NOT_FOUND", "cohort not found")
    return row


def list_cohorts(db: Session, org_id: str) -> out.CohortList:
    rows = _org_cohorts(db, org_id)
    counts = _counts(db, [r.id for r in rows])
    return out.CohortList(items=[_cohort_out(r, counts.get(r.id, 0)) for r in rows])


def create_cohort(db: Session, org_id: str, name: str) -> out.Cohort:
    info = instructor.create_class(db, name, org_id)
    row = db.get(ClassRoom, info.class_id)
    assert row is not None
    return _cohort_out(row, 0)


def _assignments(db: Session, cohort_id: uuid.UUID) -> list[Assignment]:
    return list(
        db.scalars(
            select(Assignment)
            .where(Assignment.class_id == cohort_id)
            .order_by(Assignment.created_at, Assignment.id)
        )
    )


def _assignment_out(row: Assignment, code: str, titles: dict[str, str]) -> out.CohortAssignment:
    return out.CohortAssignment(
        id=row.id,
        story_id=row.story_id,
        story_version=row.story_version,
        title_th=titles.get(row.story_id, row.story_id),
        join_url_path=f"/join/{code}",
    )


def _titles() -> dict[str, str]:
    return {s.id: s.title_th for s in catalog().values()}


def list_assignments(db: Session, cohort: ClassRoom) -> out.CohortAssignmentList:
    titles = _titles()
    return out.CohortAssignmentList(
        items=[_assignment_out(a, cohort.code, titles) for a in _assignments(db, cohort.id)]
    )


def add_assignment(
    db: Session, cohort: ClassRoom, story_id: str, expires_at: datetime | None
) -> out.CohortAssignment:
    """Only stories in the current catalog; a retired or hidden story cannot be assigned (CT-04)."""
    story = catalog().get(story_id)
    if story is None:
        raise ApiError("VALIDATION_ERROR", "story is not assignable", {"story_id": story_id})
    row = next(
        (
            a
            for a in _assignments(db, cohort.id)
            if a.story_id == story.id and a.story_version == story.version
        ),
        None,
    )
    if row is None:  # assigning the same story version twice is a no-op, not a duplicate row
        row = Assignment(
            class_id=cohort.id,
            story_id=story.id,
            story_version=story.version,
            expires_at=expires_at,
        )
        db.add(row)
        db.flush()
    return _assignment_out(row, cohort.code, {story.id: story.title_th})


def clone_cohort(db: Session, source: ClassRoom, name: str) -> out.Cohort:
    """New cohort of the same org with the source's still-assignable stories; no attempts move."""
    assert source.org_id is not None
    created = create_cohort(db, source.org_id, name)
    current = catalog()
    seen: set[str] = set()
    for old in _assignments(db, source.id):
        story = current.get(old.story_id)
        if story is None or story.id in seen:
            continue
        seen.add(story.id)
        db.add(
            Assignment(
                class_id=created.id,
                story_id=story.id,
                story_version=story.version,
                expires_at=old.expires_at,
            )
        )
    db.flush()
    return created.model_copy(update={"assignment_count": len(seen)})


# --- attempts (replayed from the event log) -------------------------------------------------


@dataclass(frozen=True)
class Attempt:
    room: FamilyRoom
    story: FamilyStory
    finished: bool
    safety_met: bool
    score_total: float | None
    last_activity: datetime

    @property
    def objective_ids(self) -> list[str]:
        return list(getattr(self.story, "objective_ids", []) or [])


def attempts(db: Session, rooms: Sequence[FamilyRoom]) -> list[Attempt]:
    """Replay every room once. A room whose log cannot be replayed counts as unfinished."""
    ids = [r.id for r in rooms]
    events: dict[uuid.UUID, list[FamilyEventRecord]] = defaultdict(list)
    for e in db.scalars(
        select(FamilyEvent).where(FamilyEvent.room_id.in_(ids)).order_by(FamilyEvent.idx)
    ):
        events[e.room_id].append(
            FamilyEventRecord(e.kind, cast(FamilyRole, e.role), e.choice_id, e.reply_th)
        )
    last_message = {
        room_id: when
        for room_id, when in db.execute(
            select(FamilyMessage.room_id, func.max(FamilyMessage.created_at))
            .where(FamilyMessage.room_id.in_(ids))
            .group_by(FamilyMessage.room_id)
        )
    }
    result: list[Attempt] = []
    for room in rooms:
        story = FamilyStory.model_validate(room.story)
        seen = [room.created_at, room.host_seen_at, room.partner_seen_at, last_message.get(room.id)]
        activity = max(t for t in seen if t is not None)
        finished, safety_met, score = False, True, None
        try:
            state = replay(story, events[room.id])
            if len(state.choices) == len(story.steps):
                assessment = assess(story, state.choices, state.facts)
                finished, safety_met = True, assessment.safety_met
                rubric = rubric_score(story, state)
                score = rubric.total if rubric else None
        except ValueError:
            pass
        result.append(Attempt(room, story, finished, safety_met, score, activity))
    return result


def _rooms_of(db: Session, class_ids: Sequence[uuid.UUID]) -> list[FamilyRoom]:
    return list(
        db.scalars(
            select(FamilyRoom)
            .join(Assignment, Assignment.id == FamilyRoom.assignment_id)
            .where(Assignment.class_id.in_(class_ids))
            .order_by(FamilyRoom.created_at, FamilyRoom.id)
        )
    )


def overview(db: Session, org_id: str) -> out.OrgOverview:
    org = org_of(org_id)
    ids = [c.id for c in _org_cohorts(db, org_id)]
    done = [a for a in attempts(db, _rooms_of(db, ids)) if a.finished] if ids else []
    return out.OrgOverview(
        org=out.OrgRef(id=org.id, name_th=org.name_th),
        demo=True,
        cohort_count=len(ids),
        assignment_count=sum(_counts(db, ids).values()) if ids else 0,
        finished_attempts=len(done),
    )


def analytics(db: Session, cohort: ClassRoom) -> out.CohortAnalytics:
    rooms = attempts(db, _rooms_of(db, [cohort.id]))
    done = [a for a in rooms if a.finished]
    objectives: dict[str, list[bool]] = defaultdict(list)
    per_story: dict[tuple[str, str], int] = defaultdict(int)
    for a in done:
        per_story[(a.story.id, a.story.version)] += 1
        for objective_id in a.objective_ids:
            objectives[objective_id].append(a.safety_met)
    return out.CohortAnalytics(
        cohort_id=cohort.id,
        demo=True,
        n_started=len(rooms),
        n_finished=len(done),
        safety_not_met=out.Ratio(numerator=sum(not a.safety_met for a in done), n=len(done)),
        objectives=[
            out.ObjectiveRate(
                objective_id=oid,
                # numerator: finished attempts that met the safety gate
                numerator=None if len(met) < MIN_OBJECTIVE_N else sum(met),
                n=len(met),
                suppressed=len(met) < MIN_OBJECTIVE_N,
            )
            for oid, met in sorted(objectives.items())
        ],
        by_story=[
            out.StoryCount(story_id=sid, story_version=ver, n_finished=n)
            for (sid, ver), n in sorted(per_story.items())
        ],
    )


# --- learner side: join + passport ----------------------------------------------------------


def join_info(db: Session, code: str) -> out.JoinInfo:
    cohort = db.scalar(select(ClassRoom).where(ClassRoom.code == code.upper()))
    if cohort is None:
        raise ApiError("CLASS_NOT_FOUND", "class code not found", {"code": code})
    all_rows = _assignments(db, cohort.id)
    now = datetime.now(UTC)
    live = [a for a in all_rows if a.expires_at is None or a.expires_at > now]
    if all_rows and not live:
        raise ApiError("SESSION_EXPIRED", "class code expired", {"reason": "expired"})
    titles = _titles()
    return out.JoinInfo(
        cohort=out.JoinCohort(id=cohort.id, name=cohort.name or ""),
        assignments=[
            out.JoinAssignment(id=a.id, story_id=a.story_id, title_th=titles[a.story_id])
            for a in live
            if a.story_id in titles
        ],
    )


def passport(db: Session, account: DemoAccount) -> out.Passport:
    """Finished attempts of the account as host or partner; safety per attempt, never averaged."""
    rooms = list(
        db.scalars(
            select(FamilyRoom).where(
                or_(
                    FamilyRoom.host_account_id == account.id,
                    FamilyRoom.partner_account_id == account.id,
                )
            )
        )
    )
    done = sorted(
        (a for a in attempts(db, rooms) if a.finished),
        key=lambda a: (a.last_activity, str(a.room.id)),
        reverse=True,
    )
    return out.Passport(
        account=out.PassportAccount(id=account.id, display_name_th=account.display_name_th),
        attempts=[
            out.PassportAttempt(
                room_id=a.room.id,
                story_id=a.story.id,
                title_th=a.story.title_th,
                finished_at=a.last_activity,
                safety_status="SAFETY_MET" if a.safety_met else "SAFETY_NOT_MET",
                score_total=a.score_total,
                objective_ids=a.objective_ids,
            )
            for a in done
        ],
    )
