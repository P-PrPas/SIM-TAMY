"""T-070: the Golden Test Suite runs in CI exactly as `make eval` runs it (mock LLM)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.golden import render, run_all

GOLDEN_DIR = Path(__file__).resolve().parents[4] / "eval" / "golden"
CONTENT_DIR = Path(__file__).resolve().parents[4] / "content"


def test_the_golden_suite_has_no_failures(
    make_db: Callable[[], str],
    alembic_config: Callable[[str], Config],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = make_db()
    command.upgrade(alembic_config(url), "head")
    for name, value in {  # run_all sets these; monkeypatch puts the originals back afterwards
        "DATABASE_URL": url,
        "ALLOW_DRAFT_CASES": "true",
        "CONTENT_DIR": str(CONTENT_DIR),
    }.items():
        monkeypatch.setenv(name, value)

    outcomes = run_all(sorted(GOLDEN_DIR.glob("T*.yaml")), url)

    assert len(outcomes) == 10
    failed = [o for o in outcomes if o.status == "FAIL"]
    assert not failed, render(outcomes)
    assert any(o.status == "PASS" for o in outcomes)
