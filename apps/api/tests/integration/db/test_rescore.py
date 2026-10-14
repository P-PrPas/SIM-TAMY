"""T-062 against a real Postgres: rescore rebuilds the score from stored events and diffs it."""

import copy
import json
import uuid

import pytest
from sqlalchemy.orm import Session

from app.content.loader import LoadedCase, load_case
from app.db.models import Report
from app.db.repo import EventRepo, SessionRepo
from app.domain.events import LoggedEvent
from app.engine.scoring import score
from app.rescore import RescoreError, rescore
from tests.unit.engine.play import DEV_001, Play

CONTENT = DEV_001.parents[1]


class FakeStore:
    """Stands in for ContentStore: serves DEV-001 (optionally pretending it changed on disk)."""

    def __init__(self, loaded: LoadedCase, hash_override: str | None = None) -> None:
        self.loaded = LoadedCase(
            loaded.case, loaded.actions, loaded.rubric, hash_override or loaded.case_hash
        )

    def load(self, case_id: str) -> LoadedCase:
        assert case_id == "DEV-001"
        return self.loaded


@pytest.fixture
def loaded() -> LoadedCase:
    return load_case(DEV_001)


def completed_session(db: Session, loaded: LoadedCase, *, with_report: bool = True) -> uuid.UUID:
    p = Play(loaded, "A").turn("A01", "A02").turn("A03", "A04").decide("proceed_service").complete()
    row = SessionRepo(db).create(
        case_id="DEV-001",
        case_version="0.1",
        case_hash=loaded.case_hash,
        variant="A",
        learner_name="nick",
        token_hash="h",
        state={},
    )
    events = EventRepo(db)
    for e in p.events:
        events.append(session_id=row.id, turn_idx=e.turn_idx, type=e.type, payload=e.payload)
    if with_report:
        # the report is computed from the stored rows, so evidence carries the real DB event ids
        stored = [
            LoggedEvent(id=e.id, type=e.type, turn_idx=e.turn_idx, payload=e.payload)
            for e in events.list_for_session(row.id)
        ]
        scoring = json.loads(score(stored, loaded.rubric, loaded.actions, "A").model_dump_json())
        db.add(
            Report(
                session_id=row.id,
                rubric_version=loaded.rubric.rubric_version,
                scoring=scoring,
                debrief={},
                glassbox={},
                replay={},
            )
        )
        db.flush()
    return row.id


def test_rescore_of_a_completed_session_equals_the_stored_result(
    db: Session, loaded: LoadedCase
) -> None:
    sid = completed_session(db, loaded)

    result = rescore(db, FakeStore(loaded), sid)  # type: ignore[arg-type]

    assert result.diffs == [] and result.stored == result.computed
    assert result.computed["safety_status"] == "SAFETY_NOT_MET"  # proceeded after the red flag


def test_rescore_reports_every_difference_when_the_stored_result_was_altered(
    db: Session, loaded: LoadedCase
) -> None:
    sid = completed_session(db, loaded)
    report = db.get(Report, sid)
    assert report is not None
    tampered = copy.deepcopy(report.scoring)
    tampered["total_score"] = 99.9
    tampered["items"][0]["result"] = "fail"
    report.scoring = tampered
    db.flush()

    result = rescore(db, FakeStore(loaded), sid)  # type: ignore[arg-type]

    assert any(d.startswith("total_score:") for d in result.diffs)
    assert any(d.startswith("items[0].result:") for d in result.diffs)


def test_rescore_flags_a_rubric_version_change(db: Session, loaded: LoadedCase) -> None:
    sid = completed_session(db, loaded)
    report = db.get(Report, sid)
    assert report is not None
    report.rubric_version = "0.0-old"
    db.flush()

    result = rescore(db, FakeStore(loaded), sid)  # type: ignore[arg-type]
    assert any(d.startswith("rubric_version:") for d in result.diffs)


def test_rescore_without_a_stored_report_only_computes(db: Session, loaded: LoadedCase) -> None:
    sid = completed_session(db, loaded, with_report=False)

    result = rescore(db, FakeStore(loaded), sid)  # type: ignore[arg-type]

    assert result.stored is None and result.diffs == [] and result.computed["items"]


def test_rescore_refuses_when_the_case_changed_since_the_session(
    db: Session, loaded: LoadedCase
) -> None:
    sid = completed_session(db, loaded)
    with pytest.raises(RescoreError, match="changed since this session started"):
        rescore(db, FakeStore(loaded, hash_override="0" * 64), sid)  # type: ignore[arg-type]


def test_rescore_unknown_session_is_an_error(db: Session, loaded: LoadedCase) -> None:
    with pytest.raises(RescoreError, match="not found"):
        rescore(db, FakeStore(loaded), uuid.uuid4())  # type: ignore[arg-type]
