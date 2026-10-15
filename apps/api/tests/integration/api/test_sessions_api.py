"""T-040a: createSession / getSession, the error envelope, auth and the no-leak rule."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.db.models import ClassRoom, Event, LearnerSession
from app.db.repo import EventRepo, TurnRepo
from tests.integration.api.conftest import Api


def test_create_session(api: Api) -> None:
    r = api.client.post(
        "/v1/sessions", json={"case_id": "DEV-001", "variant": "A", "learner_name": " มะลิ "}
    )

    assert r.status_code == 201
    body = r.json()
    assert r.headers["Location"] == f"/v1/sessions/{body['session_id']}"
    assert r.headers["X-Request-ID"] and r.headers["Cache-Control"] == "no-store"
    assert body["token"].startswith("st_") and body["token_type"] == "Bearer"
    assert (body["phase"], body["variant"]) == ("INTERVIEW", "A")
    assert body["case"]["status"] == "Draft" and body["case"]["status_label_th"]
    assert body["case"]["variants_available"] == ["A"]  # C waits for the pressure scene (T-023)
    assert [o["id"] for o in body["case"]["decision_options"]] == ["refer", "proceed_service"]
    assert {n["code"] for n in body["notices"]} == {
        "EDUCATION_ONLY",
        "CASE_STATUS",
        "PRIVACY_LLM",
        "NO_REAL_PII",
    }
    assert body["limits"]["max_turns"] == 40
    api.assert_no_leak(body)
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(body["session_id"]))
        assert row is not None
        assert row.learner_name == "มะลิ" and row.token_hash != body["token"]
        assert body["token"] not in str(row.__dict__)
        assert (row.case_hash, row.state["phase"], row.status) == (
            api.loaded.case_hash,
            "INTRO",
            "active",
        )
        started = db.scalars(select(Event).where(Event.session_id == row.id)).all()
        assert [(e.type, e.turn_idx) for e in started] == [("SESSION_STARTED", 0)]


@pytest.mark.parametrize(
    ("body", "code", "status"),
    [
        ({"case_id": "NOPE"}, "CASE_NOT_AVAILABLE", 404),
        ({"case_id": "../cases/DEV-001"}, "CASE_NOT_AVAILABLE", 404),
        ({"case_id": "a/b"}, "CASE_NOT_AVAILABLE", 404),
        ({"variant": "C"}, "VARIANT_NOT_AVAILABLE", 422),
        ({"variant": "B"}, "VARIANT_NOT_AVAILABLE", 422),  # DEV-001 defines no B
        ({"class_code": "ZZ99ZZ"}, "CLASS_NOT_FOUND", 404),
        ({"class_code": "ab12cd"}, "VALIDATION_ERROR", 422),
        ({"learner_name": "   "}, "VALIDATION_ERROR", 422),
        ({"learner_name": "x" * 31}, "VALIDATION_ERROR", 422),
        ({"variant": "Z"}, "VALIDATION_ERROR", 422),
    ],
)
def test_create_session_errors(api: Api, body: dict[str, Any], code: str, status: int) -> None:
    payload = {"case_id": "DEV-001", "variant": "A", "learner_name": "tester", **body}

    r = api.client.post("/v1/sessions", json=payload)

    assert r.status_code == status
    err = r.json()["error"]
    assert err["code"] == code
    assert err["request_id"] == r.headers["X-Request-ID"] and isinstance(err["details"], dict)


def test_validation_errors_never_echo_the_input(api: Api) -> None:
    r = api.client.post(
        "/v1/sessions", json={"case_id": "DEV-001", "learner_name": "SECRET-" + "x" * 40}
    )

    assert r.status_code == 422 and "SECRET-" not in r.text


def test_draft_cases_can_be_switched_off(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ALLOW_DRAFT_CASES", "false")
    get_settings.cache_clear()

    r = api.client.post("/v1/sessions", json={"case_id": "DEV-001", "learner_name": "t"})

    assert (r.status_code, r.json()["error"]["code"]) == (404, "CASE_NOT_AVAILABLE")


def test_create_session_with_a_class_code(api: Api) -> None:
    with api.db() as db:
        room = ClassRoom(code="AB12CD", name="room")
        db.add(room)
        db.flush()
        room_id = room.id

    created = api.create(class_code="AB12CD")

    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None and row.class_id == room_id


def test_get_session_resumes_with_history(api: Api) -> None:
    created = api.create()
    sid = uuid.UUID(created["session_id"])
    with api.db() as db:
        TurnRepo(db).add(session_id=sid, idx=1, speaker="learner", text="สวัสดี", client_turn_id="c1")
        TurnRepo(db).add(session_id=sid, idx=1, speaker="patient", text="ค่ะ")

    r = api.client.get(f"/v1/sessions/{sid}", headers=api.headers(created))

    assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
    body = r.json()
    assert [(m["idx"], m["speaker"], m["text"]) for m in body["history"]] == [
        (1, "learner", "สวัสดี"),
        (1, "patient", "ค่ะ"),
    ]
    assert (body["phase"], body["status"], body["turn_idx"], body["turns_remaining"]) == (
        "INTERVIEW",
        "active",
        0,
        40,
    )
    assert body["decision"] == {"committed": False, "option_id": None, "committed_at_idx": None}
    api.assert_no_leak(body)


def test_get_session_reports_the_decision_and_completion(api: Api) -> None:
    created = api.create()
    sid = uuid.UUID(created["session_id"])
    with api.db() as db:
        row = db.get(LearnerSession, sid)
        assert row is not None
        row.state = {**row.state, "phase": "CLOSING", "turn_idx": 7, "decision": "refer"}
        EventRepo(db).append(session_id=sid, turn_idx=6, type="DECISION_COMMITTED", payload={})

    body = api.client.get(f"/v1/sessions/{sid}", headers=api.headers(created)).json()
    assert (body["phase"], body["turns_remaining"]) == ("CLOSING", 33)
    assert body["decision"] == {"committed": True, "option_id": "refer", "committed_at_idx": 6}

    with api.db() as db:
        row = db.get(LearnerSession, sid)
        assert row is not None
        row.status = "completed"
    body = api.client.get(f"/v1/sessions/{sid}", headers=api.headers(created)).json()
    assert (body["phase"], body["status"]) == ("COMPLETED", "completed")


def test_idle_sessions_expire_and_stay_expired(api: Api) -> None:
    created = api.create()
    sid = uuid.UUID(created["session_id"])
    with api.db() as db:
        row = db.get(LearnerSession, sid)
        assert row is not None
        row.last_activity_at = datetime.now(UTC) - timedelta(seconds=1801)

    for _ in range(2):
        r = api.client.get(f"/v1/sessions/{sid}", headers=api.headers(created))
        assert (r.status_code, r.json()["error"]["code"]) == (410, "SESSION_EXPIRED")

    with api.db() as db:
        row = db.get(LearnerSession, sid)
        assert row is not None and row.status == "expired" and row.ended_at is not None


def test_a_recently_active_session_does_not_expire(api: Api) -> None:
    created = api.create()
    sid = uuid.UUID(created["session_id"])
    with api.db() as db:
        row = db.get(LearnerSession, sid)
        assert row is not None
        row.last_activity_at = datetime.now(UTC) - timedelta(seconds=1700)

    assert api.client.get(f"/v1/sessions/{sid}", headers=api.headers(created)).status_code == 200


def test_session_auth(api: Api) -> None:
    mine, other = api.create(), api.create()
    url = f"/v1/sessions/{mine['session_id']}"

    assert api.client.get(url).json()["error"]["code"] == "UNAUTHORIZED"
    assert api.client.get(url, headers={"Authorization": "Basic abc"}).status_code == 401
    assert api.client.get(url, headers={"Authorization": "Bearer "}).status_code == 401
    assert api.client.get(url, headers={"Authorization": "Bearer st_junk"}).status_code == 401
    # a valid token for someone else's session must not reveal that the session exists
    r = api.client.get(url, headers=api.headers(other))
    assert (r.status_code, r.json()["error"]["code"]) == (404, "NOT_FOUND")
    r = api.client.get(f"/v1/sessions/{uuid.uuid4()}", headers=api.headers(mine))
    assert r.status_code == 404
    r = api.client.get(f"/v1/sessions/{uuid.uuid4()}", headers={"Authorization": "Bearer st_junk"})
    assert r.status_code == 401
    lower = {"Authorization": f"bearer {mine['token']}"}
    assert api.client.get(url, headers=lower).status_code == 200


def test_malformed_session_id_is_a_validation_error(api: Api) -> None:
    r = api.client.get("/v1/sessions/not-a-uuid", headers={"Authorization": "Bearer x"})

    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


def test_unknown_route_uses_the_envelope(api: Api) -> None:
    r = api.client.get("/v1/nope")

    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    assert r.headers["X-Request-ID"] == r.json()["error"]["request_id"]


def test_unexpected_errors_are_500_envelopes_without_details(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("secret internals")

    monkeypatch.setattr("app.api.v1.sessions.sessions.create_session", boom)

    r = api.client.post("/v1/sessions", json={"case_id": "DEV-001", "learner_name": "t"})

    assert r.status_code == 500 and "secret internals" not in r.text
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert r.headers["X-Request-ID"] == r.json()["error"]["request_id"]


def test_a_failed_request_rolls_back(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("after the session row was written")

    monkeypatch.setattr("app.services.sessions.EventRepo.append", boom)

    r = api.client.post("/v1/sessions", json={"case_id": "DEV-001", "learner_name": "t"})

    assert r.status_code == 500
    with api.db() as db:
        assert db.scalars(select(LearnerSession)).all() == []
