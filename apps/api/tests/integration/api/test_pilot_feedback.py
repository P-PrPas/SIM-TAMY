"""Pilot feedback persists once, stays class-scoped, and cascades with retention."""

import uuid

from sqlalchemy import delete

from app.core.config import get_settings
from app.db.models import LearnerSession, PilotFeedback
from tests.integration.api.conftest import Api

BODY = dict(role="learner", usefulness=4, realism=3, comment="Synthetic feedback", consent=True)


def completed(api: Api, **kwargs):
    created = api.create(**kwargs)
    with api.db() as db:
        row = db.get(LearnerSession, uuid.UUID(created["session_id"]))
        row.status = "completed"
    return created


def test_feedback_requires_own_completed_session_and_explicit_consent(api: Api):
    session = api.create()
    path = f"/v1/sessions/{session['session_id']}/feedback"
    assert api.client.post(path, json=BODY).status_code == 401
    assert api.client.post(path, json=BODY, headers=api.headers(api.create())).status_code == 404
    assert api.client.post(path, json=BODY, headers=api.headers(session)).status_code == 409
    assert (
        api.client.post(
            path, json={**BODY, "consent": False}, headers=api.headers(session)
        ).status_code
        == 422
    )


def test_feedback_retries_are_idempotent_and_retention_removes_it(api: Api):
    session = completed(api)
    path = f"/v1/sessions/{session['session_id']}/feedback"
    first = api.client.post(path, json=BODY, headers=api.headers(session))
    assert first.status_code == 201
    assert first.headers["Cache-Control"] == "no-store"
    retry = api.client.post(path, json=BODY, headers=api.headers(session))
    assert retry.json() == first.json()
    assert (
        api.client.post(path, json={**BODY, "realism": 5}, headers=api.headers(session)).status_code
        == 409
    )
    with api.db() as db:
        db.execute(
            delete(LearnerSession).where(LearnerSession.id == uuid.UUID(session["session_id"]))
        )
        assert db.get(PilotFeedback, uuid.UUID(session["session_id"])) is None


def test_instructor_feedback_is_class_scoped_and_empty_means_no_measurement(api: Api, monkeypatch):
    monkeypatch.setenv("INSTRUCTOR_SECRET", "synthetic-pilot-secret")
    get_settings.cache_clear()
    headers = {"X-Instructor-Secret": "synthetic-pilot-secret"}
    room = api.client.post("/v1/classes", json={"name": "Synthetic pilot"}, headers=headers).json()
    path = f"/v1/instructor/feedback?class_code={room['code']}"
    assert api.client.get(path).status_code == 401
    assert api.client.get(path, headers=headers).json() == dict(
        total=0, usefulness_avg=None, realism_avg=None, items=[]
    )
    for kwargs in ({"class_code": room["code"]}, {}):
        session = completed(api, **kwargs)
        assert (
            api.client.post(
                f"/v1/sessions/{session['session_id']}/feedback",
                json=BODY,
                headers=api.headers(session),
            ).status_code
            == 201
        )
    data = api.client.get(path, headers=headers).json()
    assert data["total"] == len(data["items"]) == 1
    assert data["usefulness_avg"] == 4 and data["realism_avg"] == 3
    get_settings.cache_clear()
