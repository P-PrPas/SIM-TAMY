"""T-058: createOverride keeps the engine's result and changes only `effective` (FR-INS-04)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.api.deps import get_store
from app.core.config import get_settings
from app.db.models import Report, ScoreOverride
from app.rescore import rescore
from tests.integration.api.conftest import Api
from tests.integration.api.test_closing_api import complete, play, report

SECRET = "instructor-test-secret"
REASON = "ให้คะแนนตามดุลยพินิจของอาจารย์"  # more than 10 characters


@pytest.fixture(autouse=True)
def _instructor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSTRUCTOR_SECRET", SECRET)
    get_settings.cache_clear()


def override(
    api: Api, created: dict[str, Any], body: dict[str, Any], secret: str | None = SECRET
) -> Any:
    headers = {"X-Instructor-Secret": secret} if secret else {}
    return api.client.post(
        f"/v1/instructor/sessions/{created['session_id']}/overrides", json=body, headers=headers
    )


def finished(api: Api) -> dict[str, Any]:
    created = play(api, "refer")
    assert complete(api, created).status_code == 200
    return created


def a_failed_plain_item(body: dict[str, Any]) -> dict[str, Any]:
    return next(i for i in body["items"] if i["result"] == "fail" and not i["critical"])


def test_an_override_changes_effective_but_not_the_original_or_the_rescore(api: Api) -> None:
    created = finished(api)
    before = report(api, created).json()
    item = a_failed_plain_item(before)

    r = override(
        api, created, {"rubric_item_id": item["id"], "new_result": "pass", "reason": REASON}
    )

    assert r.status_code == 201
    saved = r.json()
    assert (saved["rubric_item_id"], saved["original_result"], saved["new_result"]) == (
        item["id"],
        "fail",
        "pass",
    )
    after = report(api, created).json()
    assert [o["id"] for o in after["overrides"]] == [saved["id"]]
    assert after["effective"]["total_score"] > before["total_score"]
    assert after["effective"]["safety_status"] == before["safety_status"]
    for key in ("total_score", "safety_status", "items", "competencies", "findings"):
        assert after[key] == before[key]  # the engine's own result is untouched
    with api.db() as db:
        stored = db.get(Report, uuid.UUID(created["session_id"]))
        assert stored is not None
        assert (
            rescore(db, get_store(), stored.session_id).diffs == []
        )  # rescore equals the original


def test_the_latest_override_of_an_item_wins_and_all_stay_listed(api: Api) -> None:
    created = finished(api)
    item = a_failed_plain_item(report(api, created).json())
    base = {"rubric_item_id": item["id"], "reason": REASON}
    override(api, created, {**base, "new_result": "pass"})
    override(api, created, {**base, "new_result": "fail"})

    body = report(api, created).json()

    assert len(body["overrides"]) == 2
    assert body["effective"]["total_score"] == body["total_score"]  # last one put it back


@pytest.mark.parametrize(
    "reason", ["short", "         ", "x" * 9, "\x00\x00\x00 short \x01", "x" * 501]
)
def test_a_reason_under_ten_characters_is_refused(api: Api, reason: str) -> None:
    created = finished(api)
    item = a_failed_plain_item(report(api, created).json())

    r = override(
        api, created, {"rubric_item_id": item["id"], "new_result": "pass", "reason": reason}
    )

    assert r.status_code == 422 and r.json()["error"]["code"] in (
        "VALIDATION_ERROR",
        "TEXT_TOO_LONG",
    )
    assert report(api, created).json()["overrides"] == []


@pytest.mark.parametrize(
    "body",
    [
        {
            "rubric_item_id": "R-RISK-01",
            "new_result": "pass",
        },  # critical: the gate stays the engine's
        {"rubric_item_id": "NOPE", "new_result": "pass"},
        {"rubric_item_id": "R-COMM-02", "new_result": "pass"},  # does not apply to Variant A
        {"rubric_item_id": "R-HX-01", "new_result": "partial"},  # partial needs new_earned
        {"rubric_item_id": "R-HX-01", "new_result": "partial", "new_earned": 10},
    ],
)
def test_items_that_cannot_be_overridden_are_refused(api: Api, body: dict[str, Any]) -> None:
    created = finished(api)

    r = override(api, created, {**body, "reason": REASON})

    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    with api.db() as db:
        assert db.scalars(select(ScoreOverride)).first() is None


def test_only_the_instructor_secret_may_override(api: Api) -> None:
    created = finished(api)
    body = {"rubric_item_id": "R-HX-01", "new_result": "pass", "reason": REASON}

    assert override(api, created, body, secret=None).status_code == 401
    assert override(api, created, body, secret="wrong").status_code == 403
    learner = api.client.post(
        f"/v1/instructor/sessions/{created['session_id']}/overrides",
        json=body,
        headers=api.headers(created),
    )
    assert learner.status_code == 401  # a learner token is not an instructor secret


def test_unknown_session_404_and_an_unfinished_session_409(api: Api) -> None:
    open_session = play(api, "refer")  # decided, not completed: no report yet
    body = {"rubric_item_id": "R-HX-01", "new_result": "pass", "reason": REASON}

    assert override(api, open_session, body).status_code == 409
    assert override(api, open_session, body).json()["error"]["code"] == "REPORT_NOT_READY"
    ghost = {"session_id": str(uuid.uuid4())}
    assert override(api, ghost, body).status_code == 404
