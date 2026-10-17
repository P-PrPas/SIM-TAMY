"""A solo story resumes linked chapters without requiring or accepting another player."""

import uuid

from tests.integration.api.conftest import Api


def test_solo_parenthood_persists_recall_and_rejects_second_player(api: Api):
    response = api.client.post(
        "/v1/family/rooms", json={"story_id": "parenthood", "role": "father"}
    )
    assert response.status_code == 201
    saved = response.json()
    path = f"/v1/family/rooms/{saved['room_id']}"
    headers = {"Authorization": f"Bearer {saved['token']}"}
    assert (
        api.client.post(
            path + "/join", json={"invite": saved["invite"], "participant_token": str(uuid.uuid4())}
        ).status_code
        == 409
    )
    for i, choice in enumerate(["postpone-plan", "keep-private"]):
        response = api.client.post(
            path + "/decisions",
            headers=headers,
            json={
                "choice_id": choice,
                "state_version": i,
                "client_turn_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 200, response.text
    resumed = api.client.get(path, headers=headers).json()
    assert resumed == response.json()
    assert resumed["partner_joined"]
    assert resumed["scene"]["role"] == "father"
    assert resumed["scene"]["choices"]
    with api.db() as db:
        from app.db.family import FamilyRoom

        row = db.get(FamilyRoom, uuid.UUID(saved["room_id"]))
        assert resumed["scene"]["prompt_th"] == row.story["steps"][2]["prompt_if"]["no-plan"]
    assert resumed["report"] is None
