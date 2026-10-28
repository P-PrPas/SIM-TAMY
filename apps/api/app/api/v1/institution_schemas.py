"""Institution workspace contracts (S2-*). Aggregates only: never raw chats or learner names."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.content.institution import DemoRole
from app.domain.case import Model


class DemoAccount(Model):
    id: str
    org_id: str | None
    display_name_th: str
    role: DemoRole


class DemoAccountList(Model):
    items: list[DemoAccount]


class OrgRef(Model):
    id: str
    name_th: str


class OrgOverview(Model):
    org: OrgRef
    demo: bool
    cohort_count: int
    assignment_count: int
    finished_attempts: int


class Cohort(Model):
    id: uuid.UUID
    code: str
    name: str
    created_at: datetime
    assignment_count: int


class CohortList(Model):
    items: list[Cohort]


class CohortNameRequest(Model):
    name: str = Field(min_length=1, max_length=80)


class CreateAssignmentRequest(Model):
    story_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)
    expires_at: datetime | None = None


class CohortAssignment(Model):
    id: uuid.UUID
    story_id: str
    story_version: str
    title_th: str
    join_url_path: str


class CohortAssignmentList(Model):
    items: list[CohortAssignment]


class Ratio(Model):
    numerator: int
    n: int


class ObjectiveRate(Model):
    """Per-objective rate; `numerator` is null while `suppressed` (small n, CT-12)."""

    objective_id: str
    numerator: int | None
    n: int
    suppressed: bool


class StoryCount(Model):
    story_id: str
    story_version: str
    n_finished: int


class CohortAnalytics(Model):
    cohort_id: uuid.UUID
    demo: bool
    n_started: int
    n_finished: int
    safety_not_met: Ratio
    objectives: list[ObjectiveRate]
    by_story: list[StoryCount]


class JoinCohort(Model):
    id: uuid.UUID
    name: str


class JoinAssignment(Model):
    id: uuid.UUID
    story_id: str
    title_th: str


class JoinInfo(Model):
    cohort: JoinCohort
    assignments: list[JoinAssignment]


class PassportAccount(Model):
    id: str
    display_name_th: str


class PassportAttempt(Model):
    room_id: uuid.UUID
    story_id: str
    title_th: str
    finished_at: datetime
    safety_status: Literal["SAFETY_MET", "SAFETY_NOT_MET"]
    score_total: float | None
    objective_ids: list[str]


class Passport(Model):
    account: PassportAccount
    attempts: list[PassportAttempt]
