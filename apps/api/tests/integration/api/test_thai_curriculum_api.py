"""New cultural exercises work through real turn, decision, report and debrief endpoints."""

import uuid
from pathlib import Path

import pytest

from app.ai.providers.mock import MockProvider
from app.content.family import load_stories
from tests.integration.api.conftest import Api, keys_of
from tests.integration.api.test_family_v2_api import use

STORIES = {s.id: s for s in load_stories(Path(__file__).resolve().parents[5] / "content")}


@pytest.mark.parametrize("sid", [sid for sid in STORIES if sid.startswith("thai-")])
def test_new_story_questions_and_decisions_reach_a_report_and_debrief(api: Api, sid: str):
    use(api, MockProvider())
    story = STORIES[sid]
    created = api.client.post("/v1/family/rooms", json={"story_id": sid, "role": "mother"})
    assert created.status_code == 201
    data = created.json()
    path = f"/v1/family/rooms/{data['room_id']}"
    mother = {"Authorization": f"Bearer {data['token']}"}
    father = {"Authorization": f"Bearer {uuid.uuid4()}"}
    if story.mode == "coop":
        joined = api.client.post(
            path + "/join",
            headers=mother,
            json={"invite": data["invite"], "participant_token": father["Authorization"][7:]},
        )
        assert joined.status_code == 200
    for step in story.steps:
        who = mother if story.mode == "solo" or step.role == "mother" else father
        if step.kind == "discover":
            for intent in step.intents:
                view = api.client.get(path, headers=who).json()
                response = api.client.post(
                    path + "/messages",
                    headers=who,
                    json={
                        "text": intent.examples_th[0],
                        "state_version": view["state_version"],
                        "client_turn_id": str(uuid.uuid4()),
                    },
                )
                assert response.status_code == 200, response.text
                assert response.json()["reply"] is not None
                assert not {"score_total", "risk_state", "revealed_fact_ids"} & keys_of(
                    response.json()
                )
        for actor in (mother, father) if step.joint else (who,):
            view = api.client.get(path, headers=actor).json()
            response = api.client.post(
                path + "/decisions",
                headers=actor,
                json={
                    "choice_id": step.choices[0].id,
                    "state_version": view["state_version"],
                    "client_turn_id": str(uuid.uuid4()),
                },
            )
            assert response.status_code == 200, response.text
    report = api.client.get(path, headers=mother).json()["report"]
    assert report["score_total"] is not None
    debrief = api.client.post(path + "/debrief", headers=mother)
    assert debrief.status_code == 200
    assert debrief.json()["score_total_readonly"] == report["score_total"]
