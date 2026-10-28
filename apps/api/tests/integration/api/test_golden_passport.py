"""Golden reports and institution consumers use the same deterministic rubric result."""

from app.ai.providers.mock import MockProvider
from tests.integration.api.conftest import Api
from tests.integration.api.test_family_v2_api import Room, finish, use


def test_passport_retains_the_completed_golden_report_score(api: Api) -> None:
    use(api, MockProvider())
    room = Room(api, **{"X-Demo-Account": "parent-h-mom-1"})
    finish(room)
    report = room.view(room.mother)["report"]
    response = api.client.get("/v1/passport/parent-h-mom-1")
    assert response.status_code == 200
    (attempt,) = response.json()["attempts"]
    assert attempt["score_total"] is not None
    assert attempt["score_total"] == report["score_total"]
    assert attempt["safety_status"] == report["safety_status"]
    assert attempt["objective_ids"] == ["OBJ-3-01", "OBJ-3-03"]
