"""T-023: the Variant C pressure scene through the API (FR-ENG-05, ADR-11)."""

from typing import Any

from tests.integration.api.conftest import Api, ask
from tests.integration.api.test_closing_api import complete, decide, report
from tests.integration.api.test_turns_api import (
    ASK_A03,
    ASK_A04,
    events_of,
    state_of,
    turn,
    types_of,
)

HOLD = "ขอยืนยันว่าต้องส่งต่อค่ะ"
FOLD = "ถ้าอย่างนั้นทำต่อให้ก็ได้ค่ะ"
CHAT = "สวัสดีค่ะ"
CHAT_2 = "ขอบคุณค่ะ"


def script(api: Api) -> list[str]:
    return [line.text_th for line in api.loaded.case.variants["C"].pressure_script]


def at_pressure(api: Api) -> dict[str, Any]:
    api.llm.by_text[ASK_A03] = ask("A03", "สัญญาณทดสอบก")
    api.llm.by_text[ASK_A04] = ask("A04", "สัญญาณทดสอบข")
    api.llm.by_text[HOLD] = ask("C03", "ส่งต่อ")
    api.llm.by_text[FOLD] = ask("C04", "ทำต่อให้ก็ได้")
    created = api.create(variant="C")
    turn(api, created, ASK_A03)
    turn(api, created, ASK_A04)
    return created


def item_results(api: Api, created: dict[str, Any]) -> dict[str, str]:
    return {i["id"]: i["result"] for i in report(api, created).json()["items"]}


def test_referring_starts_the_pressure_with_the_scripted_relative_line(api: Api) -> None:
    created = at_pressure(api)

    r = decide(api, created)

    assert r.status_code == 200
    assert r.json() == {
        "phase": "PRESSURE",
        "decision": {"option_id": "refer", "committed_at_idx": 2},
        "replies": [{"speaker": "relative", "text": script(api)[0]}],
        "pressure_turns_allowed": 2,
    }
    api.assert_no_leak(r.json(), revealed=("H1", "H2"))
    assert state_of(api, created)["pressure"] == {"started_at_idx": 2, "resolved": None}
    assert types_of(api, created).count("PRESSURE_STARTED") == 1
    assert decide(api, created).json() == r.json()  # a retry gets the same line, nothing new
    assert types_of(api, created).count("PRESSURE_STARTED") == 1


def test_holding_the_referral_resolves_the_pressure_and_passes_the_comm_items(api: Api) -> None:
    created = at_pressure(api)
    decide(api, created)

    r = turn(api, created, HOLD, client_turn_id="hold-0001")

    assert r.status_code == 200
    assert (r.json()["phase"], r.json()["replies"]) == ("CLOSING", [])
    assert [e.payload for e in events_of(api, created) if e.type == "PRESSURE_RESOLVED"] == [
        {"resolved": True, "by": ["C03"]}
    ]
    assert turn(api, created, HOLD, client_turn_id="hold-0001").json() == r.json()  # replay
    assert complete(api, created).status_code == 200
    results = item_results(api, created)
    assert (results["R-COMM-02"], results["R-COMM-03"]) == ("pass", "pass")


def test_giving_in_is_unsafe_and_fails_the_pressure_items(api: Api) -> None:
    created = at_pressure(api)
    decide(api, created)

    r = turn(api, created, FOLD)

    assert r.json()["phase"] == "CLOSING"
    assert "UNSAFE_ACTION" in types_of(api, created)
    assert complete(api, created).status_code == 200
    results = item_results(api, created)
    assert (results["R-COMM-02"], results["R-COMM-03"]) == ("fail", "fail")
    assert report(api, created).json()["replay"]["terminal_state"] == "UnsafeProceed"


def test_two_turns_without_an_answer_close_the_phase_unresolved(api: Api) -> None:
    created = at_pressure(api)
    decide(api, created)

    first = turn(api, created, CHAT)
    second = turn(api, created, CHAT_2)

    assert first.json()["replies"] == [{"speaker": "relative", "text": script(api)[1]}]
    assert (first.json()["phase"], second.json()["phase"]) == ("PRESSURE", "CLOSING")
    assert second.json()["replies"] == []
    events = events_of(api, created)
    assert [e.payload for e in events if e.type == "PRESSURE_RESOLVED"] == [
        {"resolved": False, "by": []}
    ]
    assert "UNSAFE_ACTION" not in [e.type for e in events]
    assert complete(api, created).status_code == 200
    results = item_results(api, created)
    assert (results["R-COMM-02"], results["R-COMM-03"]) == ("fail", "pass")


def test_a_turn_replay_does_not_pick_up_the_decision_line(api: Api) -> None:
    created = at_pressure(api)
    api.llm.by_text[ASK_A04] = ask("A04", "สัญญาณทดสอบข")
    decide(api, created)

    r = turn(api, created, CHAT, client_turn_id="chat-0001")
    again = turn(api, created, CHAT, client_turn_id="chat-0001")

    assert again.json() == r.json() and again.headers.get("Idempotent-Replay")
    assert [x["speaker"] for x in r.json()["replies"]] == ["relative"]


def test_variant_a_never_enters_the_pressure_scene(api: Api) -> None:
    api.llm.by_text[ASK_A03] = ask("A03", "สัญญาณทดสอบก")
    created = api.create()
    turn(api, created, ASK_A03)

    r = decide(api, created)

    assert (r.json()["phase"], r.json()["replies"], r.json()["pressure_turns_allowed"]) == (
        "CLOSING",
        [],
        None,
    )
    assert "PRESSURE_STARTED" not in types_of(api, created)
