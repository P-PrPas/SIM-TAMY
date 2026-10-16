"""T-065: the live Glass Box is off by default and opens only for the flag or an instructor."""

from typing import Any

import pytest

from app.core.config import get_settings
from tests.integration.api.conftest import Api, ask
from tests.integration.api.test_turns_api import ASK_A03, ASK_A04, setup_a03, turn

SECRET = "instructor-test-secret"


def live(api: Api, created: dict[str, Any], **headers: str) -> Any:
    return api.client.get(
        f"/v1/sessions/{created['session_id']}/glassbox",
        headers=headers or api.headers(created),
    )


@pytest.fixture
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GLASS_BOX_LIVE", "true")
    get_settings.cache_clear()


@pytest.fixture
def instructor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSTRUCTOR_SECRET", SECRET)
    get_settings.cache_clear()


def test_a_learner_is_refused_by_default_and_turns_carry_no_glassbox(api: Api) -> None:
    created = setup_a03(api)

    sent = turn(api, created, ASK_A03)

    assert sent.json()["glassbox"] is None
    r = live(api, created)
    assert r.status_code == 403 and r.json()["error"]["code"] == "GLASSBOX_DISABLED"


def test_with_the_flag_the_learner_sees_hidden_state_and_turns_carry_it(
    api: Api, flag_on: None
) -> None:
    created = setup_a03(api)
    first = live(api, created).json()
    assert first["risk_state"] == "unrecognized" and first["fired_action_ids"] == []
    assert {f["id"]: f["revealed"] for f in first["facts"] if f["kind"] == "hidden"} == {
        "H1": False,
        "H2": False,
        "H3": False,
    }

    sent = turn(api, created, ASK_A03).json()

    assert sent["glassbox"] == live(api, created).json()
    assert sent["glassbox"]["risk_state"] == "recognized"
    assert sent["glassbox"]["fired_action_ids"] == ["A03"]
    h1 = next(f for f in sent["glassbox"]["facts"] if f["id"] == "H1")
    assert (h1["revealed"], h1["revealed_at_idx"]) == (True, 1)


def test_an_instructor_sees_it_without_the_flag(api: Api, instructor: None) -> None:
    created = setup_a03(api)
    turn(api, created, ASK_A03)

    r = live(api, created, **{"X-Instructor-Secret": SECRET})

    assert r.status_code == 200 and r.json()["fired_action_ids"] == ["A03"]


@pytest.mark.parametrize("secret", ["wrong", SECRET + "x", SECRET[:-1]])
def test_a_wrong_instructor_secret_is_forbidden(api: Api, instructor: None, secret: str) -> None:
    created = setup_a03(api)

    r = live(api, created, **{"X-Instructor-Secret": secret})

    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_no_instructor_secret_configured_means_no_instructor(api: Api) -> None:
    created = setup_a03(api)

    assert live(api, created, **{"X-Instructor-Secret": "anything"}).status_code == 401


def test_without_a_token_or_with_another_sessions_token_it_is_refused(
    api: Api, flag_on: None
) -> None:
    api.llm.by_text[ASK_A03] = ask("A03", "สัญญาณทดสอบก")
    mine, other = api.create(), api.create()

    no_token = api.client.get(f"/v1/sessions/{mine['session_id']}/glassbox")
    crossed = api.client.get(
        f"/v1/sessions/{mine['session_id']}/glassbox", headers=api.headers(other)
    )

    assert no_token.status_code == 401 and crossed.status_code == 404


def test_a_retried_turn_returns_the_glassbox_it_first_got(api: Api, flag_on: None) -> None:
    created = setup_a03(api)
    first = turn(api, created, ASK_A03, client_turn_id="client-turn-0001").json()
    last = turn(api, created, ASK_A04, client_turn_id="client-turn-0002").json()
    assert first["glassbox"]["fired_action_ids"] == ["A03"]
    assert last["glassbox"]["fired_action_ids"] == ["A03", "A04"]
    decided = api.client.post(
        f"/v1/sessions/{created['session_id']}/decision",
        json={"option_id": "proceed_service"},
        headers=api.headers(created),
    )
    assert decided.status_code == 200

    for body, cid in ((first, "client-turn-0001"), (last, "client-turn-0002")):
        text = ASK_A03 if cid.endswith("1") else ASK_A04
        retry = turn(api, created, text, client_turn_id=cid)
        assert retry.headers["Idempotent-Replay"] == "true"
        assert retry.json()["glassbox"] == body["glassbox"]


def test_a_retried_turn_stays_hidden_when_the_flag_is_off(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = setup_a03(api)
    monkeypatch.setenv("GLASS_BOX_LIVE", "true")
    get_settings.cache_clear()
    assert turn(api, created, ASK_A03, client_turn_id="client-turn-0001").json()["glassbox"]
    monkeypatch.setenv("GLASS_BOX_LIVE", "false")
    get_settings.cache_clear()

    retry = turn(api, created, ASK_A03, client_turn_id="client-turn-0001")

    assert retry.json()["glassbox"] is None
