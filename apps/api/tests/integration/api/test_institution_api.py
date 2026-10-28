"""Institution workspace (S2-01..S2-05; CT-04, CT-08, CT-09, CT-12, CT-14) on a real database."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.content.family import load_stories
from app.core.config import get_settings
from app.db.family import FamilyEvent, FamilyRoom
from app.db.models import Assignment
from app.services.institution import Attempt
from tests.integration.api.conftest import Api

HOSPITAL, COMMUNITY = "org-demo-hospital", "org-demo-community"
EDU_H = {"X-Demo-Account": "staff-h-edu-1"}
EDU_C = {"X-Demo-Account": "staff-c-edu-1"}
SAFE = [("mother", "ask-rest"), ("father", "share-load"), ("mother", "trusted-backup")]
SAFE += [("father", "contact-professional")]
UNSAFE = [*SAFE[:3], ("father", "dismiss-concern")]
STORY = "first-night"


def post(api: Api, path: str, headers: dict[str, str], body: dict[str, Any] | None = None):
    return api.client.post(path, json=body or {}, headers=headers)


def new_cohort(api: Api, org: str, headers: dict[str, str], name: str = "Class") -> dict[str, Any]:
    r = post(api, f"/v1/orgs/{org}/cohorts", headers, {"name": name})
    assert r.status_code == 201, r.text
    return dict(r.json())


def assign(api: Api, cohort_id: str, headers: dict[str, str], story: str = STORY) -> dict[str, Any]:
    r = post(api, f"/v1/cohorts/{cohort_id}/assignments", headers, {"story_id": story})
    assert r.status_code == 201, r.text
    return dict(r.json())


def attempt(
    api: Api,
    assignment_id: str | None,
    path: list[tuple[str, str]],
    host: str | None = None,
    partner: str | None = None,
) -> uuid.UUID:
    """A room as the family API would have left it: pinned story plus its event log."""
    story = next(s for s in load_stories(get_settings().content_dir) if s.id == STORY)
    room_id = uuid.uuid4()
    with api.db() as db:
        db.add(
            FamilyRoom(
                id=room_id,
                story=story.model_dump(mode="json"),
                host_role="mother",
                host_hash=uuid.uuid4().hex,
                invite_hash=uuid.uuid4().hex,
                assignment_id=uuid.UUID(assignment_id) if assignment_id else None,
                host_account_id=host,
                partner_account_id=partner,
            )
        )
        db.flush()
        for idx, (role, choice) in enumerate(path, 1):
            db.add(
                FamilyEvent(
                    room_id=room_id,
                    idx=idx,
                    role=role,
                    kind="decision",
                    choice_id=choice,
                    client_turn_id=uuid.uuid4(),
                )
            )
    return room_id


def test_demo_accounts_lists_orgs_staff_and_free_learners(api: Api):
    items = api.client.get("/v1/demo/accounts").json()["items"]
    assert {set(i) == {"id", "org_id", "display_name_th", "role"} for i in items} == {True}
    for org in (HOSPITAL, COMMUNITY):
        roles = sorted(i["role"] for i in items if i["org_id"] == org and i["role"] != "learner")
        assert roles == ["educator", "educator", "org_admin", "reviewer"]
    assert any(i["org_id"] is None and i["role"] == "learner" for i in items)


def test_staff_routes_need_a_known_staff_account_of_that_org(api: Api):
    url = f"/v1/orgs/{HOSPITAL}/overview"
    assert api.client.get(url).status_code == 401
    assert api.client.get(url, headers={"X-Demo-Account": "nobody"}).status_code == 401
    assert api.client.get(url, headers={"X-Demo-Account": "parent-h-mom-1"}).status_code == 403
    assert api.client.get(url, headers={"X-Demo-Account": "staff-h-reviewer"}).status_code == 403
    assert api.client.get(url, headers=EDU_C).status_code == 403  # another org's educator
    assert api.client.get(url, headers={"X-Demo-Account": "staff-h-admin"}).status_code == 200
    body = api.client.get(url, headers=EDU_H).json()
    assert body["demo"] is True
    assert body["org"]["id"] == HOSPITAL
    assert body["cohort_count"] == body["assignment_count"] == body["finished_attempts"] == 0
    assert api.client.get("/v1/orgs/org-unknown/overview", headers=EDU_H).status_code == 403


def test_tenant_separation_across_cohorts_assignments_and_analytics(api: Api):
    mine = new_cohort(api, HOSPITAL, EDU_H, "Hospital class")
    theirs = new_cohort(api, COMMUNITY, EDU_C, "Community class")
    listed = api.client.get(f"/v1/orgs/{HOSPITAL}/cohorts", headers=EDU_H).json()["items"]
    assert [c["id"] for c in listed] == [mine["id"]]
    assert api.client.get(f"/v1/orgs/{HOSPITAL}/cohorts", headers=EDU_C).status_code == 403
    assert post(api, f"/v1/orgs/{HOSPITAL}/cohorts", EDU_C, {"name": "x"}).status_code == 403
    for url in (
        f"/v1/cohorts/{theirs['id']}/analytics",
        f"/v1/cohorts/{theirs['id']}/assignments",
    ):
        assert api.client.get(url, headers=EDU_H).status_code == 404
    other = f"/v1/cohorts/{theirs['id']}"
    assert post(api, other + "/assignments", EDU_H, {"story_id": STORY}).status_code == 404
    assert post(api, other + "/clone", EDU_H, {"name": "steal"}).status_code == 404
    assert api.client.get(f"/v1/cohorts/{mine['id']}/analytics").status_code == 401


def test_cohort_gets_a_fresh_code_and_overview_counts(api: Api):
    a, b = new_cohort(api, HOSPITAL, EDU_H, "A"), new_cohort(api, HOSPITAL, EDU_H, "B")
    assert len(a["code"]) == 6 and a["code"] != b["code"]
    assert a["assignment_count"] == 0
    assign(api, a["id"], EDU_H)
    listed = api.client.get(f"/v1/orgs/{HOSPITAL}/cohorts", headers=EDU_H).json()["items"]
    assert {c["name"]: c["assignment_count"] for c in listed} == {"A": 1, "B": 0}
    overview = api.client.get(f"/v1/orgs/{HOSPITAL}/overview", headers=EDU_H).json()
    assert (overview["cohort_count"], overview["assignment_count"]) == (2, 1)
    assert post(api, f"/v1/orgs/{HOSPITAL}/cohorts", EDU_H, {"name": " "}).status_code == 422


def test_assignment_shape_duplicates_and_unassignable_stories(api: Api):
    cohort = new_cohort(api, HOSPITAL, EDU_H)
    first = assign(api, cohort["id"], EDU_H)
    assert first["story_id"] == STORY and first["story_version"]
    assert first["title_th"] and first["join_url_path"] == f"/join/{cohort['code']}"
    assert assign(api, cohort["id"], EDU_H)["id"] == first["id"]  # same story version: one row
    assert (
        post(api, f"/v1/cohorts/{cohort['id']}/assignments", EDU_H, {"story_id": "nope"}).json()[
            "error"
        ]["code"]
        == "VALIDATION_ERROR"
    )
    listed = api.client.get(f"/v1/cohorts/{cohort['id']}/assignments", headers=EDU_H).json()
    assert [i["id"] for i in listed["items"]] == [first["id"]]


def test_draft_stories_are_not_assignable_when_drafts_are_off(
    api: Api, monkeypatch: pytest.MonkeyPatch
):
    cohort = new_cohort(api, HOSPITAL, EDU_H)
    monkeypatch.setenv("ALLOW_DRAFT_CASES", "false")
    get_settings.cache_clear()
    try:
        r = post(api, f"/v1/cohorts/{cohort['id']}/assignments", EDU_H, {"story_id": STORY})
        assert r.status_code == 422  # CT-04: not in the assignable catalog
    finally:
        get_settings.cache_clear()


def test_clone_copies_assignments_but_no_attempts_and_stays_independent(api: Api):
    source = new_cohort(api, HOSPITAL, EDU_H, "Source")
    original = assign(api, source["id"], EDU_H)
    attempt(api, original["id"], SAFE)
    copy = post(api, f"/v1/cohorts/{source['id']}/clone", EDU_H, {"name": "Next term"}).json()
    assert copy["id"] != source["id"] and copy["code"] != source["code"]
    assert copy["name"] == "Next term" and copy["assignment_count"] == 1
    cloned = api.client.get(f"/v1/cohorts/{copy['id']}/assignments", headers=EDU_H).json()["items"]
    assert [i["story_id"] for i in cloned] == [STORY] and cloned[0]["id"] != original["id"]
    stats = api.client.get(f"/v1/cohorts/{copy['id']}/analytics", headers=EDU_H).json()
    assert (stats["n_started"], stats["n_finished"]) == (0, 0)
    attempt(api, cloned[0]["id"], UNSAFE)  # an attempt in the copy never reaches the source
    source_stats = api.client.get(f"/v1/cohorts/{source['id']}/analytics", headers=EDU_H).json()
    assert source_stats["n_finished"] == 1 and source_stats["safety_not_met"] == {
        "numerator": 0,
        "n": 1,
    }
    with api.db() as db:  # removing the copy's assignment leaves the source untouched
        db.delete(db.get(Assignment, uuid.UUID(cloned[0]["id"])))
    assert (
        len(
            api.client.get(f"/v1/cohorts/{source['id']}/assignments", headers=EDU_H).json()["items"]
        )
        == 1
    )


def test_analytics_count_only_linked_finished_rooms_exactly_once(api: Api):
    cohort = new_cohort(api, HOSPITAL, EDU_H)
    other = new_cohort(api, HOSPITAL, EDU_H, "Other")
    mine, elsewhere = assign(api, cohort["id"], EDU_H), assign(api, other["id"], EDU_H)
    attempt(api, mine["id"], SAFE)
    attempt(api, mine["id"], UNSAFE)
    attempt(api, mine["id"], SAFE[:2])  # started, not finished
    attempt(api, elsewhere["id"], UNSAFE)  # another cohort
    attempt(api, None, UNSAFE)  # not linked to any assignment
    url = f"/v1/cohorts/{cohort['id']}/analytics"
    first = api.client.get(url, headers=EDU_H).json()
    assert first == api.client.get(url, headers=EDU_H).json()  # reading never changes a count
    assert first["demo"] is True and first["cohort_id"] == cohort["id"]
    assert (first["n_started"], first["n_finished"]) == (3, 2)
    assert first["safety_not_met"] == {"numerator": 1, "n": 2}
    version = next(s for s in load_stories(get_settings().content_dir) if s.id == STORY).version
    assert first["by_story"] == [{"story_id": STORY, "story_version": version, "n_finished": 2}]
    assert first["objectives"] == []  # stories carry no objective IDs yet
    attempt(api, mine["id"], SAFE)  # one more real completion increments by exactly one
    after = api.client.get(url, headers=EDU_H).json()
    assert (after["n_started"], after["n_finished"]) == (4, 3)
    text = str(after)
    assert "ask-rest" not in text and "text_th" not in text  # aggregates only


def test_objective_rates_are_suppressed_below_three_attempts(
    api: Api, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(Attempt, "objective_ids", property(lambda self: ["OBJ-3-01"]))
    cohort = new_cohort(api, HOSPITAL, EDU_H)
    mine = assign(api, cohort["id"], EDU_H)
    url = f"/v1/cohorts/{cohort['id']}/analytics"
    for done in range(1, 4):
        attempt(api, mine["id"], SAFE if done != 2 else UNSAFE)
        (rate,) = api.client.get(url, headers=EDU_H).json()["objectives"]
        assert rate["objective_id"] == "OBJ-3-01" and rate["n"] == done
        if done < 3:
            assert rate["suppressed"] is True and rate["numerator"] is None
        else:
            assert rate == {"objective_id": "OBJ-3-01", "numerator": 2, "n": 3, "suppressed": False}


def test_join_lists_assignments_and_rejects_unknown_or_expired_codes(api: Api):
    cohort = new_cohort(api, HOSPITAL, EDU_H, "Evening class")
    assert api.client.get(f"/v1/join/{cohort['code']}").json()["assignments"] == []
    mine = assign(api, cohort["id"], EDU_H)
    joined = api.client.get(f"/v1/join/{cohort['code'].lower()}")  # no auth, any case
    assert joined.status_code == 200
    assert joined.json()["cohort"] == {"id": cohort["id"], "name": "Evening class"}
    assert [(a["id"], a["story_id"]) for a in joined.json()["assignments"]] == [(mine["id"], STORY)]
    assert "token" not in str(joined.json())
    missing = api.client.get("/v1/join/ZZZZZZ")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "CLASS_NOT_FOUND")
    with api.db() as db:
        db.get(Assignment, uuid.UUID(mine["id"])).expires_at = datetime.now(UTC) - timedelta(days=1)
    expired = api.client.get(f"/v1/join/{cohort['code']}")
    assert (expired.status_code, expired.json()["error"]["code"]) == (410, "SESSION_EXPIRED")


def test_passport_lists_finished_attempts_of_host_and_partner_per_attempt(api: Api):
    cohort = new_cohort(api, HOSPITAL, EDU_H)
    mine = assign(api, cohort["id"], EDU_H)
    safe = attempt(api, mine["id"], SAFE, host="parent-h-mom-1", partner="parent-h-dad-1")
    unsafe = attempt(api, None, UNSAFE, host="parent-h-dad-1", partner="parent-h-mom-1")
    attempt(api, None, SAFE[:2], host="parent-h-mom-1")  # unfinished
    attempt(api, None, SAFE, host="parent-c-mom-1")  # someone else's
    mom = api.client.get("/v1/passport/parent-h-mom-1").json()
    assert mom["account"]["id"] == "parent-h-mom-1" and mom["account"]["display_name_th"]
    by_room = {a["room_id"]: a for a in mom["attempts"]}
    assert set(by_room) == {str(safe), str(unsafe)}
    assert by_room[str(safe)]["safety_status"] == "SAFETY_MET"
    assert by_room[str(unsafe)]["safety_status"] == "SAFETY_NOT_MET"  # never averaged away
    assert by_room[str(safe)]["story_id"] == STORY and by_room[str(safe)]["title_th"]
    assert by_room[str(safe)]["score_total"] is None and by_room[str(safe)]["objective_ids"] == []
    dad = api.client.get("/v1/passport/parent-h-dad-1").json()
    assert {a["room_id"] for a in dad["attempts"]} == {str(safe), str(unsafe)}
    assert api.client.get("/v1/passport/parent-free-mom-1").json()["attempts"] == []
    assert api.client.get("/v1/passport/nobody").status_code == 404


def test_overview_counts_finished_attempts_of_the_whole_org_only(api: Api):
    mine = assign(api, new_cohort(api, HOSPITAL, EDU_H)["id"], EDU_H)
    theirs = assign(api, new_cohort(api, COMMUNITY, EDU_C)["id"], EDU_C)
    attempt(api, mine["id"], SAFE)
    attempt(api, theirs["id"], SAFE)
    attempt(api, theirs["id"], UNSAFE)
    assert (
        api.client.get(f"/v1/orgs/{HOSPITAL}/overview", headers=EDU_H).json()["finished_attempts"]
        == 1
    )
    assert (
        api.client.get(f"/v1/orgs/{COMMUNITY}/overview", headers=EDU_C).json()["finished_attempts"]
        == 2
    )
