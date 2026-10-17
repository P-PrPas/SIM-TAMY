"""Grandmother responses are validated, persisted atomically and replayed without new LLM calls."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.family import FamilyEvent, FamilyRoom
from app.db.models import LlmCall
from app.purge_old import purge_family
from tests.integration.api.conftest import Api


def test_bridge_uses_only_selected_reply_and_idempotently_persists_it(api: Api):
    saved = api.client.post(
        "/v1/family/rooms", json={"story_id": "bridge-herbs", "role": "mother"}
    ).json()
    room_id = uuid.UUID(saved["room_id"])
    path = f"/v1/family/rooms/{room_id}"
    headers = {"Authorization": f"Bearer {saved['token']}"}
    with api.db() as db:
        story = db.get(FamilyRoom, room_id).story
    choice = story["steps"][0]["choices"][0]
    accepted = choice["reply_alternatives_th"][0]
    api.llm.generator_reply = accepted
    body = {"choice_id": choice["id"], "state_version": 0, "client_turn_id": str(uuid.uuid4())}
    response = api.client.post(path + "/decisions", json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["transcript"][0]["reply_th"] == accepted
    calls = api.llm.calls
    assert (
        api.client.post(path + "/decisions", json=body, headers=headers).json() == response.json()
    )
    assert api.client.get(path, headers=headers).json() == response.json()
    assert api.llm.calls == calls == 1
    with api.db() as db:
        assert db.get(FamilyEvent, (room_id, 0)).reply_th == accepted
        assert len(list(db.scalars(select(LlmCall).where(LlmCall.session_id == room_id)))) == 1


def test_unapproved_reply_falls_back_and_retention_removes_calls_and_events(api: Api):
    saved = api.client.post(
        "/v1/family/rooms", json={"story_id": "bridge-fire", "role": "father"}
    ).json()
    room_id = uuid.UUID(saved["room_id"])
    api.llm.generator_reply = "unapproved medical claim"
    with api.db() as db:
        choice = db.get(FamilyRoom, room_id).story["steps"][0]["choices"][0]
    response = api.client.post(
        f"/v1/family/rooms/{room_id}/decisions",
        headers={"Authorization": f"Bearer {saved['token']}"},
        json={"choice_id": choice["id"], "state_version": 0, "client_turn_id": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    assert response.json()["transcript"][0]["reply_th"] == choice["reply_th"]
    assert "unapproved medical claim" not in response.text
    assert api.llm.calls == 3
    with api.db() as db:
        db.get(FamilyRoom, room_id).created_at = datetime.now(UTC) - timedelta(days=31)
        db.flush()
        assert purge_family(db, cutoff=datetime.now(UTC) - timedelta(days=30)) == 1
        assert db.get(FamilyEvent, (room_id, 0)) is None
        assert not list(db.scalars(select(LlmCall).where(LlmCall.session_id == room_id)))
