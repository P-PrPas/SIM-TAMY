"""Institution workspace routes (S2-*): staff act in their own mock org; join is public."""

import uuid

from fastapi import APIRouter

from app.api.deps import Db, Demo
from app.api.v1.institution_schemas import (
    Cohort,
    CohortAnalytics,
    CohortAssignment,
    CohortAssignmentList,
    CohortList,
    CohortNameRequest,
    CreateAssignmentRequest,
    DemoAccount,
    DemoAccountList,
    JoinInfo,
    OrgOverview,
    Passport,
)
from app.content.institution import find_account
from app.core.errors import ApiError
from app.services import institution as service

router = APIRouter(prefix="/v1", tags=["Institution"])


@router.get("/demo/accounts", response_model=DemoAccountList, operation_id="listDemoAccounts")
def demo_accounts() -> DemoAccountList:
    return DemoAccountList(
        items=[
            DemoAccount(id=a.id, org_id=a.org_id, display_name_th=a.display_name_th, role=a.role)
            for a in service.accounts()
        ]
    )


@router.get("/orgs/{org_id}/overview", response_model=OrgOverview, operation_id="getOrgOverview")
def org_overview(org_id: str, db: Db, account: Demo) -> OrgOverview:
    service.staff_in_org(account, org_id)
    return service.overview(db, org_id)


@router.get("/orgs/{org_id}/cohorts", response_model=CohortList, operation_id="listCohorts")
def list_cohorts(org_id: str, db: Db, account: Demo) -> CohortList:
    service.staff_in_org(account, org_id)
    return service.list_cohorts(db, org_id)


@router.post(
    "/orgs/{org_id}/cohorts", status_code=201, response_model=Cohort, operation_id="createCohort"
)
def create_cohort(org_id: str, body: CohortNameRequest, db: Db, account: Demo) -> Cohort:
    service.staff_in_org(account, org_id)
    return service.create_cohort(db, org_id, body.name)


@router.post(
    "/cohorts/{cohort_id}/clone", status_code=201, response_model=Cohort, operation_id="cloneCohort"
)
def clone_cohort(cohort_id: uuid.UUID, body: CohortNameRequest, db: Db, account: Demo) -> Cohort:
    return service.clone_cohort(db, service.cohort_of(db, account, cohort_id), body.name)


@router.get(
    "/cohorts/{cohort_id}/assignments",
    response_model=CohortAssignmentList,
    operation_id="listCohortAssignments",
)
def list_assignments(cohort_id: uuid.UUID, db: Db, account: Demo) -> CohortAssignmentList:
    return service.list_assignments(db, service.cohort_of(db, account, cohort_id))


@router.post(
    "/cohorts/{cohort_id}/assignments",
    status_code=201,
    response_model=CohortAssignment,
    operation_id="createCohortAssignment",
)
def create_assignment(
    cohort_id: uuid.UUID, body: CreateAssignmentRequest, db: Db, account: Demo
) -> CohortAssignment:
    cohort = service.cohort_of(db, account, cohort_id)
    return service.add_assignment(db, cohort, body.story_id, body.expires_at)


@router.get(
    "/cohorts/{cohort_id}/analytics",
    response_model=CohortAnalytics,
    operation_id="getCohortAnalytics",
)
def cohort_analytics(cohort_id: uuid.UUID, db: Db, account: Demo) -> CohortAnalytics:
    return service.analytics(db, service.cohort_of(db, account, cohort_id))


@router.get("/join/{code}", response_model=JoinInfo, operation_id="getJoinInfo")
def join_info(code: str, db: Db) -> JoinInfo:
    return service.join_info(db, code)


@router.get("/passport/{account_id}", response_model=Passport, operation_id="getPassport")
def passport(account_id: str, db: Db) -> Passport:
    account = find_account(account_id)
    if account is None:
        raise ApiError("NOT_FOUND", "account not found")
    return service.passport(db, account)
