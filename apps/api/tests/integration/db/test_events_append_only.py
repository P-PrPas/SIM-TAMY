"""AGENTS.md rule 8: `events` is append-only. No DB needed; runs everywhere."""

import ast
import re
from pathlib import Path

from app.db.repo import EventRepo

APP_DIR = Path(__file__).resolve().parents[3] / "app"
SQL_MUTATION = re.compile(r"\b(update|delete\s+from|truncate)\s+(table\s+)?events\b", re.I)


def find_event_mutations(source: str) -> list[str]:
    """Flag update(Event)/delete(Event), Event.__table__.update/delete, and raw SQL on events."""
    hits: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SQL_MUTATION.search(node.value)
        ):
            hits.append(f"line {node.lineno}: raw SQL mutates events")
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (
            isinstance(fn, ast.Name)
            and fn.id in {"update", "delete"}
            and any(isinstance(a, ast.Name) and a.id == "Event" for a in node.args)
        ):
            hits.append(f"line {node.lineno}: {fn.id}(Event)")
        if isinstance(fn, ast.Attribute) and fn.attr in {"update", "delete"}:
            val = fn.value
            if isinstance(val, ast.Attribute) and val.attr == "__table__":
                hits.append(f"line {node.lineno}: __table__.{fn.attr}")
    return hits


def test_event_repo_only_exposes_append_and_read() -> None:
    public = {n for n in dir(EventRepo) if not n.startswith("_")}
    assert public == {"append", "list_for_session"}


def test_no_update_or_delete_on_events_in_application_code() -> None:
    offenders = {
        str(path.relative_to(APP_DIR)): hits
        for path in APP_DIR.rglob("*.py")
        if (hits := find_event_mutations(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}


def test_detector_catches_mutations() -> None:
    """The scan above must not be vacuous."""
    assert find_event_mutations("from sqlalchemy import delete\ndelete(Event)")
    assert find_event_mutations("update(Event).values(type='x')")
    assert find_event_mutations("Event.__table__.delete()")
    assert find_event_mutations("conn.execute('DELETE FROM events WHERE id = 1')")
    assert not find_event_mutations("select(Event).where(Event.id == 1)")
