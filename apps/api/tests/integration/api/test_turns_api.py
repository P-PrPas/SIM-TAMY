"""T-040b: sendTurn: pipeline, Event Log contract, idempotency, locking, limits, fallbacks."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.ai.llm_client import LLMTimeout
from app.db.models import Event, LearnerSession, LlmCall, Turn
from app.domain.case import Case
from app.domain.events import LoggedEvent
from app.engine.scoring import View, score
from app.services.patient_voice import CannedGenerator, FloorValidator, Voice, VoiceRequest, canned
from tests.integration.api.conftest import Api, ask

ASK_A03 = "สัญญาณทดสอบกเป็นยังไงบ้างคะ"
ASK_A04 = "สัญญาณทดสอบขเป็นยังไงบ้างคะ"
H1_TEXT = "ผู้รับบริการมีสัญญาณทดสอบก"
H1_FALLBACK = "ค่ะ มีสัญญาณทดสอบกค่ะ"
LEAK_H2 = "ผู้รับบริการมีสัญญาณทดสอบข"
FORBIDDEN_FIELDS = {"turn_idx", "replies", "phase", "clarification", "turns_remaining", "degraded"}


def turn(api: Api, created: dict[str, Any], text: str, **extra: Any) -> Any:
    return api.client.post(
        f"/v1/sessions/{created['session_id']}/turns",
        json={"text": text, **extra},
        headers=api.headers(created),
    )


def events_of(api: Api, created: dict[str, Any]) -> list[Event]:
    with api.db() as db:
        sid = uuid.UUID(created["session_id"])
        return list(db.scalars(select(Event).where(Event.session_id == sid).order_by(Event.id)))


def types_of(api: Api, created: dict[str, Any]) -> list[str]:
    return [e.type for e in events_of(api, created)]


def state_of(api: Api, created: dict[str, Any]) -> dict[str, Any]:
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None
        return {**row.state, "_version": row.state_version}


def setup_a03(api: Api) -> dict[str, Any]:
    api.llm.by_text[ASK_A03] = ask("A03", "สัญญาณทดสอบก")
    api.llm.by_text[ASK_A04] = ask("A04", "สัญญาณทดสอบข")
    return api.create()


def test_a_turn_unlocks_a_fact_and_answers_from_it(api: Api) -> None:
    created = setup_a03(api)

    r = turn(api, created, ASK_A03)

    assert r.status_code == 200
    body = r.json()
    assert set(body) >= FORBIDDEN_FIELDS and body["glassbox"] is None
    assert body["replies"] == [{"speaker": "patient", "text": H1_TEXT}]
    assert (body["turn_idx"], body["phase"], body["turns_remaining"]) == (1, "INTERVIEW", 39)
    assert (body["clarification"], body["degraded"]) == (False, False)
    api.assert_no_leak(body, revealed=("H1",))
    state = state_of(api, created)
    assert state["revealed_fact_ids"] == ["H1"] and state["fired_action_ids"] == ["A03"]
    assert (state["risk_state"], state["turn_idx"], state["phase"]) == (
        "recognized",
        1,
        "INTERVIEW",
    )
    assert state["_version"] == 1


def test_events_follow_the_scoring_contract_in_order(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    events = events_of(api, created)

    assert [e.type for e in events] == [
        "SESSION_STARTED",
        "LEARNER_MESSAGE",
        "ACTIONS_DETECTED",  # accepted actions come before the engine's events of the turn
        "PHASE_CHANGED",
        "FACT_REVEALED",
        "RISK_STATE_CHANGED",
    ]
    detected = events[2].payload
    assert detected["source"] == "llm"
    assert [(a["id"], a["confidence"]) for a in detected["actions"]] == [("A03", 0.9)]
    assert events[1].payload == {"chars": len(ASK_A03)}
    assert {e.turn_idx for e in events[1:]} == {1}


def test_the_logged_events_are_scorable_without_changes(api: Api) -> None:
    """The log the API writes is exactly what engine.scoring reads (PRD 7.5)."""
    created = setup_a03(api)
    turn(api, created, ASK_A03)
    turn(api, created, ASK_A04)
    log = [
        LoggedEvent(id=e.id, type=e.type, turn_idx=e.turn_idx, payload=e.payload)  # type: ignore[arg-type]
        for e in events_of(api, created)
    ]

    view = View.build(log, api.loaded.actions)
    result = score(log, api.loaded.rubric, api.loaded.actions, "A")

    assert [o.action_id for o in view.occurrences] == ["A03", "A04"]
    assert set(view.reveals) == {"H1", "H2"}
    assert result.safety_status in ("SAFETY_MET", "SAFETY_NOT_MET")


def test_turns_are_persisted_with_llm_calls(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    with api.db() as db:
        sid = uuid.UUID(created["session_id"])
        rows = db.scalars(select(Turn).where(Turn.session_id == sid).order_by(Turn.id)).all()
        assert [(t.idx, t.speaker, t.text) for t in rows] == [
            (1, "learner", ASK_A03),
            (1, "patient", H1_TEXT),
        ]
        assert rows[0].client_turn_id == "client-turn-0001"
        (call,) = db.scalars(select(LlmCall).where(LlmCall.session_id == sid)).all()
        assert (call.purpose, call.ok, call.turn_idx) == ("interpreter", True, 1)
    history = api.client.get(f"/v1/sessions/{created['session_id']}", headers=api.headers(created))
    assert [m["speaker"] for m in history.json()["history"]] == ["learner", "patient"]


def test_learner_free_text_never_enters_general_app_logs(
    api: Api, caplog: pytest.LogCaptureFixture
) -> None:
    marker = "synthetic-private-marker-9482"
    created = api.create()
    caplog.clear()

    response = turn(api, created, marker)

    assert response.status_code == 200
    assert marker not in caplog.text
    assert marker not in " ".join(record.getMessage() for record in caplog.records)
    with api.db() as db:
        saved = db.scalars(
            select(Turn).where(Turn.session_id == uuid.UUID(created["session_id"]))
        ).all()
        assert any(row.speaker == "learner" and row.text == marker for row in saved)


def test_a_repeated_action_is_logged_and_does_not_unlock_again(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    api.llm.by_text[ASK_A03 + " อีกที"] = ask("A03", "สัญญาณทดสอบก")
    again = turn(api, created, ASK_A03 + " อีกที")

    assert again.status_code == 200
    kinds = types_of(api, created)
    assert kinds.count("ACTION_REPEATED") == 1 and kinds.count("FACT_REVEALED") == 1
    assert state_of(api, created)["revealed_fact_ids"] == ["H1"]


@pytest.mark.parametrize(
    ("confidence", "clarifies"), [(0.74, True), (0.5, True), (0.49, False), (0.75, False)]
)
def test_confidence_policy_bands(api: Api, confidence: float, clarifies: bool) -> None:
    api.llm.by_text["ที่ว่านั้นค่ะ"] = ask("A03", "ที่ว่านั้น", confidence)
    created = api.create()

    body = turn(api, created, "ที่ว่านั้นค่ะ").json()

    assert body["clarification"] is clarifies
    state = state_of(api, created)
    unlocked = confidence >= 0.75
    assert state["revealed_fact_ids"] == (["H1"] if unlocked else [])
    assert state["flags"]["clarifications"] == (1 if clarifies else 0)
    if clarifies:
        assert body["replies"][0]["text"] == canned("clarify")
        assert "CLARIFICATION_ASKED" in types_of(api, created)
    # a message below the accept bar never counts as an action
    detected = [e for e in events_of(api, created) if e.type == "ACTIONS_DETECTED"][0]
    assert bool(detected.payload["actions"]) is unlocked


def test_configured_confidence_band_asks_without_unlocking_or_scoring(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ACTION_ACCEPT_THRESHOLD", "0.9")
    monkeypatch.setenv("ACTION_CLARIFY_THRESHOLD", "0.65")
    get_settings.cache_clear()
    api.llm.by_text[ASK_A03] = ask("A03", ASK_A03, 0.8)
    created = api.create()

    body = turn(api, created, ASK_A03).json()

    assert body["clarification"] is True
    assert body["replies"][0]["text"] == canned("clarify")
    assert state_of(api, created)["revealed_fact_ids"] == []
    events = events_of(api, created)
    assert next(e for e in events if e.type == "ACTIONS_DETECTED").payload["actions"] == []
    assert next(e for e in events if e.type == "CLARIFICATION_ASKED").payload == {
        "candidates": ["A03"]
    }


def test_small_talk_gets_a_neutral_line_and_changes_nothing(api: Api) -> None:
    created = api.create()

    body = turn(api, created, "สวัสดีค่ะ").json()

    assert body["replies"][0]["text"] == canned("smalltalk")
    state = state_of(api, created)
    assert state["revealed_fact_ids"] == [] and state["fired_action_ids"] == []
    assert (state["turn_idx"], state["phase"]) == (1, "INTERVIEW")  # still consumes a turn


def test_llm_outage_degrades_to_the_fallback_and_keeps_playing(api: Api) -> None:
    api.llm.by_text["ข้อความตอนระบบล่ม"] = "down"
    created = api.create()

    r = turn(api, created, "ข้อความตอนระบบล่ม")

    assert r.status_code == 200 and r.json()["degraded"] is True
    kinds = types_of(api, created)
    assert "LLM_FALLBACK_USED" in kinds
    detected = [e for e in events_of(api, created) if e.type == "ACTIONS_DETECTED"][0]
    assert detected.payload == {"actions": [], "source": "lexical"}
    with api.db() as db:
        calls = db.scalars(select(LlmCall)).all()
        assert len(calls) == 2 and not any(c.ok for c in calls)  # 2 attempts, both recorded
    assert turn(api, created, "สวัสดีค่ะ").json()["degraded"] is False


@pytest.mark.parametrize("failure", ["down", "invalid structured output"])
def test_llm_failure_uses_content_keyword_to_unlock_a_fact(api: Api, failure: str) -> None:
    api.llm.by_text[ASK_A03] = failure
    created = api.create()

    response = turn(api, created, ASK_A03)

    assert response.status_code == 200
    assert response.json()["degraded"] is True
    assert state_of(api, created)["revealed_fact_ids"] == ["H1"]
    events = events_of(api, created)
    detected = next(event for event in events if event.type == "ACTIONS_DETECTED")
    assert detected.payload["source"] == "lexical"
    assert [item["id"] for item in detected.payload["actions"]] == ["A03"]
    assert any(event.type == "LLM_FALLBACK_USED" for event in events)


class LeakyThenClean:
    """Says the hidden fact H2 (not unlocked) for the first `bad` attempts, then a clean line."""

    def __init__(self, bad: int) -> None:
        self.bad, self.calls = bad, 0

    def generate(self, request: VoiceRequest, attempt: int) -> str:
        self.calls += 1
        return LEAK_H2 if attempt < self.bad else H1_TEXT


def test_a_leaking_line_is_regenerated_and_never_shown(api: Api) -> None:
    gen = LeakyThenClean(bad=2)
    api.use_voice(Voice(gen, FloorValidator()))
    created = setup_a03(api)

    body = turn(api, created, ASK_A03).json()

    assert body["replies"][0]["text"] == H1_TEXT and body["degraded"] is False
    assert gen.calls == 3
    rejected = [e for e in events_of(api, created) if e.type == "VALIDATOR_REJECTED"]
    assert [e.payload for e in rejected] == [
        {"attempt": 1, "rules": ["leak_term:H2"]},
        {"attempt": 2, "rules": ["leak_term:H2"]},
    ]
    assert "LLM_FALLBACK_USED" not in types_of(api, created)


def test_after_two_regenerations_the_canned_utterance_is_used(api: Api) -> None:
    gen = LeakyThenClean(bad=99)
    api.use_voice(Voice(gen, FloorValidator()))
    created = setup_a03(api)

    body = turn(api, created, ASK_A03).json()

    assert body["replies"] == [{"speaker": "patient", "text": H1_FALLBACK}]
    assert body["degraded"] is True and gen.calls == 3
    assert types_of(api, created).count("VALIDATOR_REJECTED") == 3
    fallback = [e for e in events_of(api, created) if e.type == "LLM_FALLBACK_USED"]
    assert [e.payload for e in fallback] == [{"component": "validator"}]
    with api.db() as db:  # the rejected text exists nowhere: not in turns, not in events
        everything = str([t.text for t in db.scalars(select(Turn))]) + str(
            [e.payload for e in db.scalars(select(Event))]
        )
        assert LEAK_H2 not in everything


def test_when_no_canned_line_is_safe_the_patient_says_nothing(api: Api) -> None:
    class RejectAll:
        def check(self, text: str, case: Case, revealed: Sequence[str]) -> list[str]:
            return ["forbidden_term"]

    api.use_voice(Voice(LeakyThenClean(bad=99), RejectAll()))
    created = setup_a03(api)

    r = turn(api, created, ASK_A03)

    assert r.status_code == 200
    assert r.json()["replies"] == [] and r.json()["degraded"] is True
    with api.db() as db:  # the learner's turn is kept; no patient text exists anywhere
        assert [t.speaker for t in db.scalars(select(Turn))] == ["learner"]
        assert LEAK_H2 not in str([e.payload for e in db.scalars(select(Event))])
    again = turn(api, created, ASK_A03, client_turn_id="client-turn-0002")
    assert again.json()["replies"] == []


def test_a_failing_generator_falls_back_to_the_canned_line(api: Api) -> None:
    class Down:
        def generate(self, request: VoiceRequest, attempt: int) -> str:
            raise LLMTimeout("timeout")

    api.use_voice(Voice(Down(), FloorValidator()))
    created = setup_a03(api)

    body = turn(api, created, ASK_A03).json()

    assert body["replies"][0]["text"] == H1_FALLBACK and body["degraded"] is True
    fallback = [e for e in events_of(api, created) if e.type == "LLM_FALLBACK_USED"]
    assert [e.payload for e in fallback] == [{"component": "generator"}]


def test_the_generator_only_receives_allowed_facts(api: Api) -> None:
    seen: list[VoiceRequest] = []

    class Spy(CannedGenerator):
        def generate(self, request: VoiceRequest, attempt: int) -> str:
            seen.append(request)
            return super().generate(request, attempt)

    api.use_voice(Voice(Spy(), FloorValidator()))
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    (request,) = seen
    ids = {f.id for f in request.allowed.facts}
    assert ids == {"K1", "H1"} and request.allowed.must_convey_fact_ids == ("H1",)
    assert "H2" not in str(request) and LEAK_H2 not in str(request)


def test_same_client_turn_id_replays_the_stored_answer(api: Api) -> None:
    created = setup_a03(api)
    first = turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    second = turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    assert second.status_code == 200 and second.headers["Idempotent-Replay"] == "true"
    assert "Idempotent-Replay" not in first.headers
    assert second.json() == first.json()
    assert api.llm.calls == 1  # nothing was recomputed
    assert state_of(api, created)["turn_idx"] == 1
    assert types_of(api, created).count("LEARNER_MESSAGE") == 1


def test_replay_keeps_the_clarification_and_degraded_flags(api: Api) -> None:
    api.llm.by_text["ที่ว่านั้นค่ะ"] = ask("A03", "ที่ว่านั้น", 0.6)
    created = api.create()
    first = turn(api, created, "ที่ว่านั้นค่ะ", client_turn_id="client-turn-0001").json()

    again = turn(api, created, "ที่ว่านั้นค่ะ", client_turn_id="client-turn-0001")

    assert first["clarification"] is True and again.json() == first


def test_same_client_turn_id_with_other_text_conflicts(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    r = turn(api, created, ASK_A04, client_turn_id="client-turn-0001")

    assert (r.status_code, r.json()["error"]["code"]) == (409, "IDEMPOTENCY_CONFLICT")
    assert state_of(api, created)["turn_idx"] == 1


def test_a_second_turn_in_flight_is_refused(api: Api) -> None:
    created = setup_a03(api)
    with api.db() as db:  # another request is mid-turn: it holds the session row lock
        db.execute(
            select(LearnerSession)
            .where(LearnerSession.id == uuid.UUID(created["session_id"]))
            .with_for_update()
        )
        r = turn(api, created, ASK_A03)

    assert (r.status_code, r.json()["error"]["code"]) == (409, "TURN_IN_PROGRESS")
    assert state_of(api, created)["turn_idx"] == 0 and types_of(api, created) == ["SESSION_STARTED"]
    assert turn(api, created, ASK_A03).status_code == 200  # fine once the lock is gone


def _set_row(api: Api, created: dict[str, Any], **changes: Any) -> None:
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None
        state = changes.pop("state", None)
        if state:
            row.state = {**row.state, **state}
        for key, value in changes.items():
            setattr(row, key, value)


@pytest.mark.parametrize(
    ("change", "status", "code", "details"),
    [
        ({"state": {"phase": "CLOSING"}}, 409, "INVALID_PHASE", {"phase": "CLOSING"}),
        ({"status": "completed"}, 409, "SESSION_COMPLETED", {}),
        ({"state": {"turn_idx": 40}}, 422, "TURN_LIMIT", {"max_turns": 40}),
        ({"state": {"turn_idx": 39}}, 200, None, None),
        (
            {"last_activity_at": datetime.now(UTC) - timedelta(seconds=1900)},
            410,
            "SESSION_EXPIRED",
            {"idle_timeout_s": 1800},
        ),
    ],
)
def test_turn_gates(
    api: Api, change: dict[str, Any], status: int, code: str | None, details: dict[str, Any] | None
) -> None:
    created = api.create()
    _set_row(api, created, **change)

    r = turn(api, created, "สวัสดีค่ะ")

    assert r.status_code == status
    if code:
        assert r.json()["error"]["code"] == code
        assert r.json()["error"]["details"] == details
    else:
        assert r.json()["turns_remaining"] == 0  # turn 40 is the last one allowed


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"text": ""}, "VALIDATION_ERROR"),
        ({"text": "   "}, "VALIDATION_ERROR"),
        ({"text": "ก" * 501}, "TEXT_TOO_LONG"),
        ({"text": "ok", "client_turn_id": "short"}, "VALIDATION_ERROR"),
        ({"client_turn_id": "client-turn-0001"}, "VALIDATION_ERROR"),
    ],
)
def test_turn_request_validation(api: Api, body: dict[str, Any], code: str) -> None:
    created = api.create()

    r = api.client.post(
        f"/v1/sessions/{created['session_id']}/turns", json=body, headers=api.headers(created)
    )

    assert (r.status_code, r.json()["error"]["code"]) == (422, code)
    if code == "TEXT_TOO_LONG":
        assert r.json()["error"]["details"] == {"max": 500, "actual": 501}
    assert api.llm.calls == 0


def test_exactly_500_characters_is_accepted(api: Api) -> None:
    created = api.create()

    assert turn(api, created, "ก" * 500).status_code == 200


def test_turn_auth(api: Api) -> None:
    mine, other = api.create(), api.create()
    url = f"/v1/sessions/{mine['session_id']}/turns"

    assert api.client.post(url, json={"text": "hi"}).status_code == 401
    assert api.client.post(url, json={"text": "hi"}, headers=api.headers(other)).status_code == 404
    assert types_of(api, mine) == ["SESSION_STARTED"]


def test_stream_flag_is_accepted_and_returns_json_until_sse_exists(api: Api) -> None:
    created = api.create()

    r = api.client.post(
        f"/v1/sessions/{created['session_id']}/turns?stream=true",
        json={"text": "สวัสดีค่ะ"},
        headers=api.headers(created),
    )

    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")


def test_a_failure_mid_turn_leaves_no_trace(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    created = setup_a03(api)

    def boom(*_: Any, **__: Any) -> None:
        raise RuntimeError("db went away")

    monkeypatch.setattr("app.services.turns.SessionRepo.save_state", boom)

    r = turn(api, created, ASK_A03)

    assert r.status_code == 500
    assert types_of(api, created) == ["SESSION_STARTED"]  # one transaction: nothing half-written
    with api.db() as db:
        assert db.scalars(select(Turn)).all() == [] and db.scalars(select(LlmCall)).all() == []
