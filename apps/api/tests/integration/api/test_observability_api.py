"""T-044: every turn leaves events and an llm_calls row (FR-OBS-01)."""

import uuid

from sqlalchemy import select

from app.db.models import LlmCall
from tests.integration.api.conftest import Api
from tests.integration.api.test_turns_api import ASK_A03, ASK_A04, events_of, setup_a03, turn


def test_every_turn_leaves_events_and_an_interpreter_call(api: Api) -> None:
    created = setup_a03(api)

    for text in (ASK_A03, ASK_A04):
        assert turn(api, created, text).status_code == 200

    with api.db() as db:
        calls = list(
            db.scalars(
                select(LlmCall).where(LlmCall.session_id == uuid.UUID(created["session_id"]))
            )
        )
    assert sorted(c.turn_idx for c in calls if c.purpose == "interpreter") == [1, 2]
    assert all(c.provider and c.model and c.latency_ms is not None and c.ok for c in calls)
    learner_turns = [e.turn_idx for e in events_of(api, created) if e.type == "LEARNER_MESSAGE"]
    assert learner_turns == [1, 2]
