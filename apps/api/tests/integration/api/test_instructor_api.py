"""T-055/T-057: instructor-only class, session and cohort APIs."""

import re
import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import LearnerSession, Report
from tests.integration.api.conftest import Api


@pytest.fixture
def instructor(api: Api, monkeypatch: pytest.MonkeyPatch) -> tuple[Api, dict[str, str]]:
    monkeypatch.setenv("INSTRUCTOR_SECRET", "synthetic-instructor-secret")
    get_settings.cache_clear()
    return api, {"X-Instructor-Secret": "synthetic-instructor-secret"}


def test_class_requires_secret_and_creates_six_character_code(
    instructor: tuple[Api, dict[str, str]],
) -> None:
    api, headers = instructor
    assert api.client.post("/v1/classes", json={"name": "Synthetic class"}).status_code == 401
    response = api.client.post("/v1/classes", json={"name": "Synthetic class"}, headers=headers)
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json()
    assert re.fullmatch(r"[A-Z0-9]{6}", body["code"])
    assert body["name"] == "Synthetic class"
    listed = api.client.get("/v1/instructor/classes", headers=headers)
    assert listed.status_code == 200
    assert listed.headers["Cache-Control"] == "no-store"
    assert listed.json()["items"][0]["class_id"] == body["class_id"]


def test_instructor_sessions_and_analytics_are_class_scoped(
    instructor: tuple[Api, dict[str, str]],
) -> None:
    api, headers = instructor
    room = api.client.post("/v1/classes", json={"name": "Synthetic class"}, headers=headers).json()
    other = api.create(learner_name="outside")
    created = api.create(class_code=room["code"], learner_name="inside")
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        assert row is not None
        row.status = "completed"
        db.add(
            Report(
                session_id=row.id,
                rubric_version="synthetic",
                debrief={},
                glassbox={},
                replay={},
                scoring={
                    "safety_status": "SAFETY_NOT_MET",
                    "total_score": 40,
                    "competencies": [
                        {
                            "id": "RISK",
                            "name_th": "Synthetic risk",
                            "weight": 100,
                            "score_pct": 40,
                            "earned": 40,
                            "possible": 100,
                        }
                    ],
                    "items": [
                        {
                            "id": "SYN-1",
                            "competency": "RISK",
                            "result": "fail",
                            "points": 1,
                            "earned": 0,
                            "critical": True,
                            "evidence": [],
                        }
                    ],
                },
            )
        )
    response = api.client.get(
        "/v1/instructor/sessions", params={"class_code": room["code"]}, headers=headers
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1 and items[0]["session_id"] == created["session_id"]
    assert items[0]["session_id"] != other["session_id"]
    assert items[0]["safety_status"] == "SAFETY_NOT_MET"
    assert items[0]["total_score"] == 40
    assert items[0]["case_status"] == "Draft"
    assert "token" not in items[0] and "state" not in items[0]
    analytics = api.client.get(
        "/v1/instructor/analytics", params={"class_code": room["code"]}, headers=headers
    )
    assert analytics.status_code == 200
    assert analytics.json()["sessions_completed"] == 1
    assert analytics.json()["safety_not_met_rate"] == 1
    assert analytics.json()["critical_item_fail_rates"][0]["n"] == 1


def test_instructor_filters_and_rejects_unknown_class(
    instructor: tuple[Api, dict[str, str]],
) -> None:
    api, headers = instructor
    room = api.client.post("/v1/classes", json={"name": "Synthetic class"}, headers=headers).json()
    first = api.create(class_code=room["code"])
    second = api.create(class_code=room["code"])
    page = api.client.get(
        "/v1/instructor/sessions",
        params={"class_code": room["code"], "limit": 1},
        headers=headers,
    ).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    next_page = api.client.get(
        "/v1/instructor/sessions",
        params={"class_code": room["code"], "limit": 1, "cursor": page["next_cursor"]},
        headers=headers,
    ).json()
    assert {page["items"][0]["session_id"], next_page["items"][0]["session_id"]} == {
        first["session_id"],
        second["session_id"],
    }
    assert (
        api.client.get(
            "/v1/instructor/analytics", params={"class_code": "ZZ99ZZ"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        api.client.get(
            "/v1/instructor/sessions", params={"cursor": "invalid"}, headers=headers
        ).status_code
        == 422
    )
    with api.db() as db:
        assert db.scalar(
            select(LearnerSession).where(LearnerSession.id == uuid.UUID(first["session_id"]))
        )
