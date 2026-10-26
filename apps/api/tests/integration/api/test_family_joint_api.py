"""Joint decisions, private-fact sharing ACL and presence through the real API and database."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from app.db.family import FamilyEvent, FamilyRoom
from tests.integration.api.conftest import Api

STORY = "golden-first-night"
TO_JOINT = ["say-what-you-see", "share-and-listen", "listen-then-ask"]


def create(api: Api, story: str = STORY):
    made = api.client.post("/v1/family/rooms", json={"story_id": story, "role": "mother"}).json()
    path = f"/v1/family/rooms/{made['room_id']}"
    token = str(uuid.uuid4())
    api.client.post(path + "/join", json={"invite": made["invite"], "participant_token": token})
    return (
        made["room_id"],
        path,
        {"Authorization": f"Bearer {made['token']}"},
        {"Authorization": f"Bearer {token}"},
    )


def get(api: Api, path: str, headers: dict) -> dict:
    return api.client.get(path, headers=headers).json()


def decide(api: Api, path: str, headers: dict, choice: str, version: int, turn=None):
    body = {
        "choice_id": choice,
        "state_version": version,
        "client_turn_id": turn or str(uuid.uuid4()),
    }
    return api.client.post(path + "/decisions", json=body, headers=headers), body


def share(api: Api, path: str, headers: dict, fact: str, turn=None):
    body = {"fact_id": fact, "client_turn_id": turn or str(uuid.uuid4())}
    return api.client.post(path + "/shares", json=body, headers=headers), body


def to_joint(api: Api, path: str, mother: dict, father: dict) -> int:
    roles = [mother, father, mother]
    for choice, headers in zip(TO_JOINT, roles, strict=True):
        version = get(api, path, headers)["state_version"]
        assert decide(api, path, headers, choice, version)[0].status_code == 200
    return get(api, path, mother)["state_version"]


def test_share_acl_private_facts_stay_private_until_shared(api: Api):
    _, path, mother, father = create(api)
    seen = [get(api, path, h) for h in (mother, father)]
    assert [f["id"] for f in seen[0]["my_facts"]] == ["m-feed", "m-sleepy"]
    assert [f["id"] for f in seen[1]["my_facts"]] == ["f-nappy", "f-yellow"]
    assert seen[0]["shared_facts"] == seen[1]["shared_facts"] == []
    for view, other in ((seen[0], "f-nappy"), (seen[1], "m-feed")):
        assert other not in str(view)
    assert share(api, path, father, "m-feed")[0].status_code == 422  # not father's fact
    assert share(api, path, mother, "nope")[0].status_code == 422
    assert share(api, path, {}, "m-feed")[0].status_code == 401
    assert share(api, path, {"Authorization": "Bearer bad"}, "m-feed")[0].status_code == 401
    response, body = share(api, path, mother, "m-feed")
    assert response.status_code == 200
    after = [get(api, path, h) for h in (mother, father)]
    assert [f["id"] for f in after[1]["shared_facts"]] == ["m-feed"]
    assert after[1]["shared_facts"][0]["role"] == "mother"
    assert "m-sleepy" not in str(after[1])  # unshared stays hidden
    assert "f-yellow" not in str(after[0])
    assert after[0]["my_facts"][0]["shared"] and not after[0]["my_facts"][1]["shared"]
    # retry with the same ID and re-sharing the same fact are both harmless no-ops
    assert api.client.post(path + "/shares", json=body, headers=mother).json() == after[0]
    assert share(api, path, mother, "m-feed")[0].status_code == 200
    with api.db() as db:
        kinds = db.scalars(
            select(FamilyEvent.kind).where(FamilyEvent.room_id == uuid.UUID(path[-36:]))
        ).all()
    assert list(kinds) == ["share"]
    assert share(api, path, mother, "m-sleepy", body["client_turn_id"])[0].status_code == 409


def test_joint_vote_hides_partner_choice_then_locks_on_match(api: Api):
    _, path, mother, father = create(api)
    version = to_joint(api, path, mother, father)
    before = get(api, path, father)
    assert before["scene"]["joint"] and len(before["scene"]["choices"]) == 3
    assert before["scene"]["vote"] == {
        "my_choice_id": None,
        "waiting_for_partner": False,
        "disagreement": None,
    }
    first, body = decide(api, path, mother, "contact-health-service", version)
    assert first.status_code == 200
    mine = first.json()["scene"]
    assert mine["vote"]["waiting_for_partner"] and mine["choices"] == []
    seen_by_father = get(api, path, father)
    assert seen_by_father["state_version"] == version  # a pending vote does not stale the partner
    assert seen_by_father["scene"]["vote"]["disagreement"] is None
    assert "contact-health-service" not in str(seen_by_father["scene"]["vote"])
    # idempotent resubmit returns the same view; a second vote from the same role is rejected
    assert api.client.post(path + "/decisions", json=body, headers=mother).json() == first.json()
    assert decide(api, path, mother, "wait-until-morning", version)[0].status_code == 409
    locked, _ = decide(api, path, father, "contact-health-service", version)
    assert locked.status_code == 200
    view = locked.json()
    assert view["completed_steps"] == 4 and view["scene"]["id"] == "consequence"
    assert view["state_version"] == version + 2
    assert view["transcript"][-1]["text_th"].startswith("ติดต่อบุคลากรสุขภาพ")


def test_mismatch_shows_both_choices_then_revote_agrees_and_critical_gate_holds(api: Api):
    _, path, mother, father = create(api)
    version = to_joint(api, path, mother, father)
    decide(api, path, mother, "contact-health-service", version)
    split, _ = decide(api, path, father, "wait-until-morning", version)
    scene = split.json()["scene"]
    assert scene["id"] == "joint-help-decision" and scene["joint"]
    assert {d["role"]: d["choice_id"] for d in scene["vote"]["disagreement"]} == {
        "mother": "contact-health-service",
        "father": "wait-until-morning",
    }
    assert get(api, path, mother)["scene"]["vote"]["disagreement"] == scene["vote"]["disagreement"]
    assert get(api, path, mother)["scene"]["vote"]["my_choice_id"] is None
    assert len(scene["choices"]) == 3  # both may vote again
    version += 2
    assert (
        decide(api, path, mother, "wait-until-morning", version - 2)[0].status_code == 409
    )  # stale
    decide(api, path, father, "wait-until-morning", version)
    agreed, _ = decide(api, path, mother, "wait-until-morning", version)
    assert agreed.json()["scene"]["id"] == "consequence"
    for headers, choice in ((father, "report-observations"), (mother, "agree-share-and-ask")):
        current = get(api, path, headers)
        assert decide(api, path, headers, choice, current["state_version"])[0].status_code == 200
    report = get(api, path, mother)["report"]
    assert report["safety_status"] == "SAFETY_NOT_MET"
    skills = {c["skill"]: c for c in report["competencies"]}
    assert skills["shared_decision"] == {
        "skill": "shared_decision",
        "observed": 1,
        "opportunities": 6,
    }
    with api.db() as db:
        rows = db.execute(
            select(FamilyEvent.idx, FamilyEvent.kind)
            .where(FamilyEvent.room_id == uuid.UUID(path[-36:]))
            .order_by(FamilyEvent.idx)
        ).all()
    assert [r.idx for r in rows] == list(range(1, len(rows) + 1))
    assert [r.kind for r in rows].count("vote") == 4


def test_stale_version_and_out_of_turn_are_rejected_for_joint_stories(api: Api):
    _, path, mother, father = create(api)
    assert decide(api, path, father, "say-what-you-see", 0)[0].status_code == 422  # wrong role
    assert decide(api, path, mother, "say-what-you-see", 3)[0].status_code == 409  # stale
    assert share(api, path, mother, "m-feed")[0].status_code == 200
    assert decide(api, path, mother, "say-what-you-see", 0)[0].status_code == 409  # share moved it
    assert decide(api, path, mother, "say-what-you-see", 1)[0].status_code == 200


def test_concurrent_joint_votes_serialize_without_losing_either_vote(api: Api):
    _, path, mother, father = create(api)
    version = to_joint(api, path, mother, father)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(
            pool.map(
                lambda h: decide(api, path, h, "contact-health-service", version)[0].status_code,
                (mother, father),
            )
        )
    assert codes == [200, 200]
    assert get(api, path, mother)["scene"]["id"] == "consequence"


def test_presence_reports_only_an_online_boolean(api: Api):
    saved, path, mother, father = create(api)
    first = get(api, path, mother)
    assert first["partner_online"] is False  # father has not polled yet
    assert get(api, path, father)["partner_online"] is True
    assert get(api, path, mother)["partner_online"] is True
    assert set(first) >= {"partner_online"} and "seen" not in str(first)
    with api.db() as db:
        row = db.get(FamilyRoom, uuid.UUID(saved))
        row.partner_seen_at = row.partner_seen_at.replace(year=2000)
        db.commit()
    assert get(api, path, mother)["partner_online"] is False  # stale poll -> offline


def test_existing_stories_and_cards_are_unchanged_by_the_new_fields(api: Api):
    _, path, mother, _ = create(api, "first-night")
    view = get(api, path, mother)
    assert view["my_facts"] == view["shared_facts"] == [] and view["scene"]["vote"] is None
    assert view["completed_steps"] == view["state_version"] == 0
    assert share(api, path, mother, "m-feed")[0].status_code == 422
    _, bridge, host, _ = create(api, "bridge-fire")
    card = get(api, bridge, host)["scene"]["card"]
    assert card["evidence_status"] == "traditional_practice" and card["sources"]
    assert set(card["sources"][0]) == {"id", "title_th", "url"}
    golden = create(api)
    assert get(api, golden[1], golden[2])["scene"]["card"] is None  # only the elder step has one
