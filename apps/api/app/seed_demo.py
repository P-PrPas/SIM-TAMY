"""`make seed-demo`: a demo class with a few completed, clearly synthetic sessions (T-081).

The sessions are not hand-written rows: five golden conversations are played through the real API
(offline lexical Interpreter, no LLM), so every report is a genuine engine result that
`make rescore` reproduces. Re-running is a no-op once the class has sessions. The static recorded
session for Replay Mode is `recordings/dev001-engineering.json` (T-073); it needs no database.
"""

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.ai.llm_client import LLMClient
from app.api.deps import get_llm_factory, get_store
from app.content.loader import load_case
from app.core.config import get_settings
from app.db.migrate import migrate
from app.db.models import ClassRoom, LearnerSession
from app.db.session import get_engine, get_sessionmaker
from app.golden import REPO_DIR, Env, LexicalProvider, Outcome, load_golden, run_golden
from app.main import create_app

CLASS_CODE = "DEMO01"
CLASS_NAME = "ห้องเรียนตัวอย่าง (ข้อมูลสังเคราะห์ ไม่ใช่ผู้เรียนจริง)"
# a safe referral, two unsafe/late paths and both Variant C outcomes: a dashboard with variety
SCENARIOS = ("T01", "T02", "T03", "T05", "T06")


def _name(n: int) -> str:
    return f"ตัวอย่าง {n} (สังเคราะห์)"


def seed(golden_dir: Path | None = None) -> list[Outcome]:
    """Seed the database named by DATABASE_URL; [] when the class already has sessions."""
    golden_dir = golden_dir or REPO_DIR / "eval" / "golden"
    caches = (get_settings, get_engine, get_sessionmaker, get_store)
    env_patch = {"ALLOW_DRAFT_CASES": "true", "RATE_LIMIT_PER_MIN": "0"}
    with mock.patch.dict(os.environ, env_patch):
        os.environ.setdefault("CONTENT_DIR", str(REPO_DIR / "content"))
        for cached in caches:
            cached.cache_clear()
        try:
            migrate(
                Config("alembic.ini")
            )  # `make demo` may be the first thing run on a new database
            maker = get_sessionmaker()
            with maker.begin() as db:
                room = db.scalar(select(ClassRoom).where(ClassRoom.code == CLASS_CODE))
                if room is None:
                    room = ClassRoom(code=CLASS_CODE, name=CLASS_NAME)
                    db.add(room)
                    db.flush()
                taken = db.scalar(
                    select(func.count())
                    .select_from(LearnerSession)
                    .where(LearnerSession.class_id == room.id)
                )
            if taken:
                return []
            app = create_app()
            env = Env(TestClient(app, raise_server_exceptions=False), maker, "mock")
            outcomes: list[Outcome] = []
            for n, scenario in enumerate(SCENARIOS, start=1):
                g = load_golden(golden_dir / f"{scenario}.yaml")
                provider = LexicalProvider(load_case(get_settings().content_dir / "cases" / g.case))
                app.dependency_overrides[get_llm_factory] = lambda p=provider: (
                    lambda purpose, on_call: LLMClient(
                        p, model="seed", timeout_s=1, on_call=on_call
                    )
                )
                outcomes.append(
                    run_golden(g, env, {"learner_name": _name(n), "class_code": CLASS_CODE})
                )
            return outcomes
        finally:
            for cached in caches:
                cached.cache_clear()


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    outcomes = seed()
    if not outcomes:
        print(f"class {CLASS_CODE} already has sessions: nothing to seed")
        return 0
    for o in outcomes:
        print(f"{o.id}: {o.status}" + ("" if o.status == "PASS" else f" {'; '.join(o.details)}"))
    failed = [o for o in outcomes if o.status != "PASS"]
    print(f"seeded class {CLASS_CODE} with {len(outcomes) - len(failed)} synthetic sessions")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
