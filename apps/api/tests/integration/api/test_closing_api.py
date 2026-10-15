"""T-041: commitDecision, completeSession, getReport, and the whole session scored from its log."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.content.loader import ContentStore
from app.db.models import Event, LearnerSession, Report
from app.engine.scoring import InvalidRubric, score
from app.rescore import rescore
from app.services.closing import logged_events
from tests.integration.api.conftest import CONTENT_DIR, Api, ask
from tests.integration.api.test_turns_api import (
    ASK_A03,
    ASK_A04,
    events_of,
    setup_a03,
    state_of,
    turn,
    types_of,
)

DECISION_KEYS = {"phase", "decision", "replies", "pressure_turns_allowed"}


def decide(api: Api, created: dict[str, Any], option: str = "refer", **extra: Any) -> Any:
    return api.client.post(
        f"/v1/sessions/{created['session_id']}/decision",
        json={"option_id": option, **extra},
        headers=api.headers(created),
    )


def complete(api: Api, created: dict[str, Any], body: dict[str, Any] | None = None) -> Any:
    return api.client.post(
        f"/v1/sessions/{created['session_id']}/complete",
        json=body,
        headers=api.headers(created),
    )


def report(api: Api, created: dict[str, Any]) -> Any:
    return api.client.get(
        f"/v1/sessions/{created['session_id']}/report", headers=api.headers(created)
    )


def play(api: Api, option: str = "refer") -> dict[str, Any]:
    created = setup_a03(api)
    turn(api, created, ASK_A03)
    turn(api, created, ASK_A04)
    assert decide(api, created, option).status_code == 200
    return created


# ---- decision ----


def test_commit_decision_moves_to_closing_and_discloses_nothing(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    r = decide(api, created, "proceed_service", rationale_th="เหตุผลทดสอบ")

    assert r.status_code == 200
    body = r.json()
    assert set(body) == DECISION_KEYS
    assert body == {
        "phase": "CLOSING",
        "decision": {"option_id": "proceed_service", "committed_at_idx": 1},
        "replies": [],
        "pressure_turns_allowed": None,
    }
    api.assert_no_leak(body, revealed=("H1",))  # the unsafe-action effect is not disclosed
    assert "UNSAFE_ACTION" in types_of(api, created)  # but it is in the log, for the report
    assert state_of(api, created)["decision"] == "proceed_service"
    committed = [e for e in events_of(api, created) if e.type == "DECISION_COMMITTED"][0]
    assert committed.payload["option_id"] == "proceed_service"
    assert committed.payload["actions"] == ["B03"] and committed.payload["rationale_th"]


def test_the_same_decision_again_is_idempotent(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)
    first = decide(api, created)
    before = types_of(api, created)

    again = decide(api, created)

    assert again.status_code == 200 and again.json() == first.json()
    assert types_of(api, created) == before


@pytest.mark.parametrize(
    ("option", "status", "code"),
    [
        ("refer", 409, "INVALID_PHASE"),  # no turn yet: the interview has not started
        ("nope", 422, "DECISION_OPTION_INVALID"),
    ],
)
def test_decision_errors(api: Api, option: str, status: int, code: str) -> None:
    created = api.create()
    if code == "DECISION_OPTION_INVALID":
        turn(api, created, "สวัสดีค่ะ")

    r = decide(api, created, option)

    assert (r.status_code, r.json()["error"]["code"]) == (status, code)
    assert types_of(api, created)[-1] != "DECISION_COMMITTED"


def test_a_different_decision_after_committing_conflicts(api: Api) -> None:
    created = play(api, "refer")

    r = decide(api, created, "proceed_service")

    assert (r.status_code, r.json()["error"]["code"]) == (409, "DECISION_ALREADY_COMMITTED")
    assert state_of(api, created)["decision"] == "refer"


def test_no_messages_after_the_decision(api: Api) -> None:
    created = play(api)

    r = turn(api, created, ASK_A03)

    assert (r.status_code, r.json()["error"]["code"]) == (409, "INVALID_PHASE")
    assert r.json()["error"]["details"] == {"phase": "CLOSING"}


def test_replaying_a_turn_after_the_decision_keeps_its_original_phase(api: Api) -> None:
    created = setup_a03(api)
    first = turn(api, created, ASK_A03, client_turn_id="client-turn-0001").json()
    decide(api, created)  # commits at the same turn index and moves the phase to CLOSING

    again = turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    assert again.json() == first and again.json()["phase"] == "INTERVIEW"


def test_replaying_a_turn_after_complete_keeps_its_original_result(api: Api) -> None:
    created = setup_a03(api)
    first = turn(api, created, ASK_A03, client_turn_id="client-turn-0001").json()
    decide(api, created)
    assert complete(api, created).status_code == 200

    again = turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    assert again.status_code == 200 and again.json() == first
    assert again.json()["phase"] == "INTERVIEW"


def test_an_idle_session_does_not_answer_a_repeated_decision(api: Api) -> None:
    created = play(api)
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None
        row.last_activity_at = datetime.now(UTC) - timedelta(seconds=1900)

    r = decide(api, created)

    assert (r.status_code, r.json()["error"]["code"]) == (410, "SESSION_EXPIRED")


def test_rationale_is_limited_to_300_characters(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    r = decide(api, created, rationale_th="ก" * 301)

    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


# ---- complete ----


def test_complete_needs_a_decision_first(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    r = complete(api, created)

    assert (r.status_code, r.json()["error"]["code"]) == (409, "INVALID_PHASE")
    assert r.json()["error"]["details"] == {"phase": "INTERVIEW"}


def test_complete_locks_the_session_and_is_idempotent(api: Api) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)
    first_decision = decide(api, created, "refer")
    assert first_decision.status_code == 200

    first = complete(api, created, {"note_th": "สรุปเคสทดสอบ"})

    assert first.status_code == 200
    assert first.json() == {
        "status": "completed",
        "report_ready": True,
        "report_url": f"/v1/sessions/{created['session_id']}/report",
    }
    after = types_of(api, created)
    assert after[-3:] == ["NOTE_SUBMITTED", "PHASE_CHANGED", "SESSION_COMPLETED"]
    note = [e for e in events_of(api, created) if e.type == "NOTE_SUBMITTED"][0]
    assert note.payload["chars"] == len("สรุปเคสทดสอบ")
    assert complete(api, created).json() == first.json()
    assert types_of(api, created) == after  # nothing recomputed
    with api.db() as db:
        assert len(db.scalars(select(Report)).all()) == 1
    view = api.client.get(f"/v1/sessions/{created['session_id']}", headers=api.headers(created))
    assert (view.json()["status"], view.json()["phase"]) == ("completed", "COMPLETED")
    locked = turn(api, created, ASK_A03)
    assert (locked.status_code, locked.json()["error"]["code"]) == (409, "SESSION_COMPLETED")
    again = decide(api, created, "refer")  # the same choice still gets its first answer
    assert (again.status_code, again.json()) == (200, first_decision.json())
    assert again.json()["phase"] == "CLOSING"
    other = decide(api, created, "proceed_service")
    assert (other.status_code, other.json()["error"]["code"]) == (409, "DECISION_ALREADY_COMMITTED")


def test_complete_without_a_note_logs_no_note(api: Api) -> None:
    created = play(api)

    assert complete(api, created).status_code == 200

    assert "NOTE_SUBMITTED" not in types_of(api, created)


def test_a_session_that_cannot_be_scored_stays_open(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = play(api)

    def broken(*_: Any, **__: Any) -> None:
        raise InvalidRubric("rubric is invalid")

    monkeypatch.setattr("app.services.closing.score", broken)
    before = types_of(api, created)

    r = complete(api, created)

    assert (r.status_code, r.json()["error"]["code"]) == (500, "INTERNAL_ERROR")
    assert "rubric is invalid" not in r.text
    assert types_of(api, created) == before  # rolled back: no SESSION_COMPLETED, no report
    with api.db() as db:
        assert db.scalars(select(Report)).all() == []
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None and row.status == "active"


def test_complete_while_a_turn_is_in_flight_is_refused(api: Api) -> None:
    created = play(api)
    with api.db() as db:
        db.execute(
            select(LearnerSession)
            .where(LearnerSession.id == uuid.UUID(created["session_id"]))
            .with_for_update()
        )
        r = complete(api, created)

    assert (r.status_code, r.json()["error"]["code"]) == (409, "TURN_IN_PROGRESS")


# ---- report ----


def test_report_is_not_ready_before_completion_and_private(api: Api) -> None:
    created, other = play(api), api.create()

    early = report(api, created)
    assert (early.status_code, early.json()["error"]["code"]) == (409, "REPORT_NOT_READY")
    complete(api, created)
    assert report(api, created).status_code == 200
    stolen = api.client.get(
        f"/v1/sessions/{created['session_id']}/report", headers=api.headers(other)
    )
    assert stolen.status_code == 404
    anonymous = api.client.get(f"/v1/sessions/{created['session_id']}/report")
    assert anonymous.status_code == 401


def test_report_contents_for_a_safe_path(api: Api) -> None:
    created = play(api, "refer")
    complete(api, created)

    r = report(api, created)

    assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
    body = r.json()
    assert body["safety_status"] == "SAFETY_MET" and body["variant"] == "A"
    assert body["case"]["hash"] == api.loaded.case_hash and body["case"]["status"] == "Draft"
    assert body["rubric_version"] == "0.1" and body["overrides"] == [] and body["disclaimers"]
    assert 0 <= body["total_score"] <= 100
    assert body["effective"] == {
        "safety_status": body["safety_status"],
        "total_score": body["total_score"],
    }
    assert len(body["items"]) == len(api.loaded.rubric.items)
    scored = [i for i in body["items"] if i["result"] in ("pass", "fail")]
    assert scored and all(i["evidence"] for i in scored)  # every verdict carries evidence
    assert sum(c["weight"] for c in body["competencies"]) == pytest.approx(100)
    assert {f["rubric_item_id"] for f in body["findings"]} <= {i["id"] for i in body["items"]}
    assert all(f["reference_ids"] for f in body["findings"] if f["polarity"] == "improve")
    assert body["debrief"]["source"] == "template"
    assert [p["finding_ids"] for p in body["debrief"]["paragraphs"]] == [
        [f["id"]] for f in body["findings"]
    ]
    assert report(api, created).json() == body  # a report is stable


def test_report_for_an_unsafe_path_is_not_met_and_replays_the_consequence(api: Api) -> None:
    created = play(api, "proceed_service")  # found the critical sign, then carried on
    complete(api, created)

    body = report(api, created).json()

    assert body["safety_status"] == "SAFETY_NOT_MET"
    critical = [i for i in body["items"] if i["critical"]]
    assert any(i["result"] == "fail" for i in critical)
    assert body["replay"]["terminal_state"] == "UnsafeProceed"
    assert body["replay"]["timeline_th"] and body["replay"]["disclaimer_th"]
    assert {r["id"] for r in body["references"]} == {"REF1"}
    improve = [f for f in body["findings"] if f["polarity"] == "improve"]
    assert improve and all(f["evidence_refs"] for f in improve)
    types = [t["type"] for t in body["timeline"]]
    assert "UNSAFE_ACTION" in types and "DECISION_COMMITTED" in types


def test_report_glass_box_and_timeline_come_from_the_log(api: Api) -> None:
    created = play(api, "refer")
    complete(api, created)

    body = report(api, created).json()

    facts = {f["id"]: f for f in body["glassbox"]["facts"]}
    assert (facts["H1"]["revealed"], facts["H1"]["revealed_at_idx"]) == (True, 1)
    assert (facts["H2"]["revealed"], facts["H2"]["revealed_at_idx"]) == (True, 2)
    assert (facts["H3"]["revealed"], facts["H3"]["revealed_at_idx"]) == (False, None)
    assert facts["K1"]["kind"] == "known" and facts["K1"]["revealed"] is True
    assert [p["risk_state"] for p in body["glassbox"]["risk_state_timeline"]] == [
        "unrecognized",
        "recognized",
    ]
    assert [(a["turn_idx"], a["action_id"]) for a in body["glassbox"]["learner_actions"]] == [
        (1, "A03"),
        (2, "A04"),
    ]
    ids = [t["event_id"] for t in body["timeline"]]
    assert ids == sorted(ids) and body["timeline"][-1]["type"] == "SESSION_COMPLETED"


def test_the_stored_report_is_what_a_fresh_scoring_of_the_log_gives(api: Api) -> None:
    """FR-SCR-04: the API's own log is deterministic input to `score()` and to `make rescore`."""
    created = play(api, "refer")
    complete(api, created, {"note_th": "สรุปเคสทดสอบ"})
    sid = uuid.UUID(created["session_id"])

    with api.db() as db:
        log = logged_events(db, sid)
        fresh = score(log, api.loaded.rubric, api.loaded.actions, "A")
        stored = db.get(Report, sid)
        assert stored is not None and stored.scoring == fresh.model_dump(mode="json")
        result = rescore(db, ContentStore(CONTENT_DIR), sid)
    assert result.diffs == [] and result.stored is not None
    body = report(api, created).json()
    assert body["total_score"] == fresh.total_score
    assert body["safety_status"] == fresh.safety_status


def test_a_clarified_or_degraded_turn_does_not_break_scoring(api: Api) -> None:
    api.llm.by_text["ที่ว่านั้นค่ะ"] = ask("A03", "ที่ว่านั้น", 0.6)
    api.llm.by_text["ระบบล่ม"] = "down"
    created = api.create()
    turn(api, created, "ที่ว่านั้นค่ะ")
    turn(api, created, "ระบบล่ม")
    turn(api, created, "สวัสดีค่ะ")
    assert decide(api, created, "refer").status_code == 200

    assert complete(api, created).status_code == 200
    assert report(api, created).json()["safety_status"] in ("SAFETY_MET", "SAFETY_NOT_MET")


def test_events_stay_append_only_through_the_whole_session(api: Api) -> None:
    created = play(api)
    complete(api, created)

    with api.db() as db:
        ids = [e.id for e in db.scalars(select(Event).order_by(Event.id))]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
