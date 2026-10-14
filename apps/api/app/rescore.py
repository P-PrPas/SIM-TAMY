"""`make rescore SESSION=<id>`: rebuild the score from the Event Log, diff it with the stored one.

FR-SCR-04: same log + same rubric version => same result. Exit codes: 0 equal (or nothing stored to
compare), 1 the recomputed result differs from the stored one, 2 cannot rescore (no such session,
case files changed since the session, unreadable log).
"""

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.content.loader import ContentError, ContentStore
from app.core.config import get_settings
from app.db.models import Report
from app.db.repo import EventRepo, SessionRepo
from app.db.session import get_sessionmaker
from app.domain.events import LoggedEvent
from app.engine.scoring import InvalidRubric, MalformedEvent, score


class RescoreError(Exception):
    """The session cannot be rescored (exit code 2)."""


@dataclass(frozen=True)
class Rescored:
    computed: dict[str, Any]
    stored: dict[str, Any] | None
    diffs: list[str]


_MISSING = object()  # a key that is absent is not the same as a key that is null


def diff(stored: Any, computed: Any, path: str = "") -> list[str]:
    """Every path where the two JSON values differ."""
    if isinstance(stored, dict) and isinstance(computed, dict):
        keys = sorted(set(stored) | set(computed))
        return [
            d
            for k in keys
            for d in diff(
                stored.get(k, _MISSING), computed.get(k, _MISSING), f"{path}.{k}".lstrip(".")
            )
        ]
    if isinstance(stored, list) and isinstance(computed, list) and len(stored) == len(computed):
        return [
            d
            for i, (a, b) in enumerate(zip(stored, computed, strict=True))
            for d in diff(a, b, f"{path}[{i}]")
        ]
    if stored is _MISSING or computed is _MISSING or stored != computed:
        a = "<missing>" if stored is _MISSING else repr(stored)
        b = "<missing>" if computed is _MISSING else repr(computed)
        return [f"{path or '$'}: stored {a} != recomputed {b}"]
    return []


def rescore(db: Session, store: ContentStore, session_id: uuid.UUID) -> Rescored:
    row = SessionRepo(db).get(session_id)
    if row is None:
        raise RescoreError(f"session {session_id} not found")
    try:
        loaded = store.load(row.case_id)
    except (ContentError, OSError) as exc:
        raise RescoreError(f"case {row.case_id!r} cannot be loaded: {exc}") from exc
    if loaded.case_hash != row.case_hash:
        raise RescoreError(
            f"case {row.case_id!r} changed since this session started (pinned "
            f"{row.case_hash[:12]}, on disk {loaded.case_hash[:12]}); restore that version"
        )
    try:
        log = [
            LoggedEvent(id=e.id, type=e.type, turn_idx=e.turn_idx, payload=e.payload)
            for e in EventRepo(db).list_for_session(session_id)
        ]
    except ValidationError as exc:
        raise RescoreError(f"the Event Log has an unknown event: {exc.errors()[0]['msg']}") from exc

    try:
        scored = score(log, loaded.rubric, loaded.actions, row.variant)  # type: ignore[arg-type]
    except (MalformedEvent, InvalidRubric) as exc:
        raise RescoreError(f"cannot score this session: {exc}") from exc
    computed = json.loads(scored.model_dump_json())
    report = db.get(Report, session_id)
    if report is None:
        return Rescored(computed, None, [])
    diffs = diff(report.scoring, computed)
    if report.rubric_version != loaded.rubric.rubric_version:
        diffs.append(
            f"rubric_version: stored {report.rubric_version!r} != on disk "
            f"{loaded.rubric.rubric_version!r}"
        )
    return Rescored(computed, report.scoring, diffs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rescore")
    parser.add_argument("session_id", type=uuid.UUID)
    args = parser.parse_args(argv)

    store = ContentStore(get_settings().content_dir)
    with get_sessionmaker()() as db:
        try:
            result = rescore(db, store, args.session_id)
        except RescoreError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    if result.stored is None:
        print("no stored report to compare (session not completed yet?); computed result:")
        print(json.dumps(result.computed, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    for line in result.diffs:
        print(f"DIFF {line}", file=sys.stderr)
    if result.diffs:
        return 1
    print(
        f"OK {args.session_id}: rescore equals the stored report "
        f"(total {result.computed['total_score']}, {result.computed['safety_status']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
