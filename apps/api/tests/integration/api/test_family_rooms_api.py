"""Real database contracts for isolated roles, replay, retries and shared decisions."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from app.db.family import FamilyRoom
from tests.integration.api.conftest import Api


def create(api: Api):
    response = api.client.post(
        "/v1/family/rooms", json={"story_id": "first-night", "role": "mother"}
    )
    assert response.status_code == 201, response.text
    saved = response.json()
    path = f"/v1/family/rooms/{saved['room_id']}"
    host = {"Authorization": f"Bearer {saved['token']}"}
    partner_token = str(uuid.uuid4())
    joined = api.client.post(
        path + "/join", json={"invite": saved["invite"], "participant_token": partner_token}
    )
    assert joined.status_code == 200, joined.text
    return saved, path, host, {"Authorization": f"Bearer {partner_token}"}


def test_role_isolation_no_scores_or_future_outcomes_during_play(api: Api):
    saved, path, mother, father = create(api)
    a, b = [api.client.get(path, headers=headers).json() for headers in (mother, father)]
    assert a["private_brief_th"] != b["private_brief_th"]
    assert a["private_brief_th"] not in str(b)
    assert b["private_brief_th"] not in str(a)
    assert a["report"] is b["report"] is None
    assert not b["scene"]["choices"]
    assert set(a["scene"]["choices"][0]) == {"id", "text_th"}
    assert api.client.get(path).status_code == 401
    assert api.client.get(path, headers={"Authorization": "Bearer bad"}).status_code == 401
    with api.db() as db:
        row = db.get(FamilyRoom, uuid.UUID(saved["room_id"]))
        assert saved["token"] not in str(row.__dict__)
        assert saved["invite"] not in str(row.__dict__)


def test_shared_completion_is_replayable_and_idempotent(api: Api):
    _, path, mother, father = create(api)
    for i, choice in enumerate(["ask-rest", "share-load", "trusted-backup", "dismiss-concern"]):
        body = {"choice_id": choice, "state_version": i, "client_turn_id": str(uuid.uuid4())}
        headers = mother if i % 2 == 0 else father
        response = api.client.post(path + "/decisions", json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert (
            api.client.post(path + "/decisions", json=body, headers=headers).json()
            == response.json()
        )
        assert (
            api.client.post(
                path + "/decisions", json={**body, "choice_id": "bad"}, headers=headers
            ).status_code
            == 409
        )
    report = response.json()["report"]
    assert report["safety_status"] == "SAFETY_NOT_MET"
    assert len(report["evidence"]) == 4
    assert report == api.client.get(path, headers=father).json()["report"]


def test_join_retry_capacity_out_of_turn_and_stale_decisions(api: Api):
    saved, path, mother, father = create(api)
    token = father["Authorization"].split()[1]
    assert (
        api.client.post(
            path + "/join", json={"invite": saved["invite"], "participant_token": token}
        ).status_code
        == 200
    )
    assert (
        api.client.post(
            path + "/join", json={"invite": saved["invite"], "participant_token": str(uuid.uuid4())}
        ).status_code
        == 409
    )
    body = {"choice_id": "ask-rest", "state_version": 0, "client_turn_id": str(uuid.uuid4())}
    assert api.client.post(path + "/decisions", json=body, headers=father).status_code == 422
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: (
                    api.client.post(
                        path + "/decisions",
                        json={**body, "client_turn_id": str(uuid.uuid4())},
                        headers=mother,
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [200, 409]
