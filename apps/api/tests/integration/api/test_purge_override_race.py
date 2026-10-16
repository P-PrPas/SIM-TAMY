"""T-049 x T-058: an override must not outlive the session that purge_old is deleting.

`score_overrides` has no foreign key, so the only guard is the session row lock both paths take.
"""

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_store
from app.core.config import get_settings
from app.db.models import LearnerSession, ScoreOverride
from app.purge_old import purge_expired
from tests.integration.api.conftest import Api
from tests.integration.api.test_closing_api import report
from tests.integration.api.test_override_api import REASON, SECRET, a_failed_plain_item, finished

DAYS = 30


@pytest.fixture(autouse=True)
def _instructor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSTRUCTOR_SECRET", SECRET)
    get_settings.cache_clear()
    get_store.cache_clear()


def test_an_override_arriving_while_purge_deletes_the_session_leaves_no_orphan(api: Api) -> None:
    created = finished(api)
    item = a_failed_plain_item(report(api, created).json())
    old = datetime.now(UTC) - timedelta(days=DAYS + 1)
    with api.db() as db:
        db.execute(update(LearnerSession).values(ended_at=old, status="completed"))

    answer: dict[str, Any] = {}

    def post_override() -> None:
        r = api.client.post(
            f"/v1/instructor/sessions/{created['session_id']}/overrides",
            json={"rubric_item_id": item["id"], "new_result": "pass", "reason": REASON},
            headers={"X-Instructor-Secret": SECRET},
        )
        answer["status"] = r.status_code

    with api.db() as purger:  # purge has deleted the session but not committed yet
        assert purge_expired(purger, retention_days=DAYS, now=datetime.now(UTC)) == 1
        poster = threading.Thread(target=post_override)
        poster.start()
        time.sleep(0.5)
    poster.join(timeout=10)

    assert answer == {"status": 404}
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(ScoreOverride)) == 0
