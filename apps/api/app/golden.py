"""Golden Test Suite runner: `make eval` (PRD 12.2, T-070).

Plays each `eval/golden/*.yaml` conversation through the real FastAPI app (in process) on a
throwaway migrated Postgres, then checks the outcome against the file. Nothing here scores or
decides: it only asks the system and compares. Results are reported as measured (AGENTS.md 11, 13):

- PASS / FAIL: every expectation held / one did not.
- SKIP: the file declares `blocked_by` and the system refuses it for that reason (Variant C).
- A `pending` block holds expectations that cannot pass yet: listed, never counted as passed.

Modes: `mock` answers the Interpreter with the deterministic lexical matcher over the case's own
phrases (offline; it exercises the plumbing, not language understanding). `--provider env` uses
whatever LLM_PROVIDER the environment configures. Exit code: 1 when any file FAILs, else 0.
"""

import argparse
import html
import json
import os
import sys
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.ai.lexical import match_actions
from app.ai.llm_client import LLMClient, LLMRequest, LLMResponse
from app.ai.thai import normalize_th
from app.api.deps import get_llm_factory, get_store
from app.content.loader import LoadedCase, load_case
from app.core.config import get_settings
from app.db.models import Event, LearnerSession
from app.db.session import get_engine, get_sessionmaker
from app.domain.case import Case, HiddenFact
from app.main import create_app
from app.rescore import rescore

API_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = API_DIR.parents[1]
FORBIDDEN_KEYS = {"revealed_fact_ids", "risk_state", "actions", "fired_action_ids", "items"}
FORBIDDEN_KEYS |= {"total_score", "safety_status", "findings", "unlock_on", "leak_terms_th"}


# ---------- the golden file ----------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(_Strict):
    say: str | None = None
    decision: str | None = None
    complete: bool = False
    note: str | None = None  # sent with `complete`
    expect_actions_any: list[str] = []  # at least one of these was detected this turn
    expect_actions: list[str] | None = None  # exactly these were detected this turn
    expect_events: list[str] = []  # event types logged this turn

    @model_validator(mode="after")
    def _one_kind(self) -> "Step":
        if sum([self.say is not None, self.decision is not None, self.complete]) != 1:
            raise ValueError("a step is exactly one of say / decision / complete")
        return self


class Expect(_Strict):
    safety_status: Literal["SAFETY_MET", "SAFETY_NOT_MET"] | None = None
    events_include: list[str] = []
    events_exclude: list[str] = []
    items: dict[str, Literal["pass", "fail", "partial", "na"]] = {}
    revealed: list[str] | None = None  # exactly these facts, read from the session state
    fact_reveals: dict[str, int] = {}  # FACT_REVEALED events logged per fact id, exactly
    replay_terminal_state: str | None = None
    replay_missed_opportunities_include: list[str] = []
    min_step_pass_rate: float | None = None  # share of `say` steps whose own expectation held


class Pending(_Strict):
    blocked_by: str
    expect: Expect


class Golden(_Strict):
    id: str
    case: str = "DEV-001"
    variant: Literal["A", "B", "C"] = "A"
    blocked_by: str | None = None
    steps: list[Step]
    expect: Expect
    pending: list[Pending] = []


def load_golden(path: Path) -> Golden:
    return Golden.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# ---------- the mock Interpreter ----------


class LexicalProvider:
    """Offline stand-in for the Interpreter LLM: the deterministic lexical matcher (FR-ACT-03)."""

    name = "golden-lexical"

    def __init__(self, loaded: LoadedCase) -> None:
        self.loaded = loaded

    def complete(self, request: LLMRequest) -> LLMResponse:
        text = request.prompt.split("<learner_text>" + chr(10))[-1].split(
            chr(10) + "</learner_text>"
        )[0]
        found = match_actions(html.unescape(text), self.loaded.actions)
        body = {"actions": [a.model_dump() for a in found], "needs_clarification": False}
        return LLMResponse(json.dumps(body), prompt_tokens=0, completion_tokens=0)


# ---------- running one file ----------


@dataclass
class Outcome:
    id: str
    status: Literal["PASS", "FAIL", "SKIP"]
    mode: str
    details: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)  # expectations still blocked
    warnings: list[str] = field(default_factory=list)


@dataclass
class Facts:
    safety_status: str | None
    event_types: set[str]
    items: dict[str, str]
    revealed: set[str]
    reveal_counts: dict[str, int]
    terminal_state: str | None
    missed: set[str]
    step_rate: float | None


def check(expect: Expect, facts: Facts) -> list[str]:
    """Every expectation that does not hold (empty list: all hold)."""
    failed: list[str] = []
    if expect.safety_status and facts.safety_status != expect.safety_status:
        failed.append(f"safety_status {facts.safety_status} != {expect.safety_status}")
    failed += [f"event {e} missing" for e in expect.events_include if e not in facts.event_types]
    failed += [f"event {e} present" for e in expect.events_exclude if e in facts.event_types]
    for item, want in expect.items.items():
        if facts.items.get(item) != want:
            failed.append(f"item {item} is {facts.items.get(item)}, expected {want}")
    if expect.revealed is not None and facts.revealed != set(expect.revealed):
        failed.append(f"revealed {sorted(facts.revealed)} != {sorted(expect.revealed)}")
    for fact_id, want_n in expect.fact_reveals.items():
        if (got := facts.reveal_counts.get(fact_id, 0)) != want_n:
            failed.append(f"fact {fact_id} revealed {got} time(s), expected {want_n}")
    if expect.replay_terminal_state and facts.terminal_state != expect.replay_terminal_state:
        failed.append(f"terminal_state {facts.terminal_state} != {expect.replay_terminal_state}")
    missing = set(expect.replay_missed_opportunities_include) - facts.missed
    failed += [f"missed opportunity {m} not in the replay" for m in sorted(missing)]
    if expect.min_step_pass_rate is not None:
        rate = facts.step_rate
        if rate is None or rate < expect.min_step_pass_rate:
            failed.append(f"step pass rate {rate} < {expect.min_step_pass_rate}")
    return failed


def _keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def leaks(text: str, case: Case, revealed: set[str]) -> list[str]:
    """Hidden-fact and forbidden terms in a reply; normalized like the Validator (no zero-width)."""
    text = normalize_th(text)
    found = [
        f"reply leaks {f.id} before it was revealed"
        for f in case.facts
        if isinstance(f, HiddenFact)
        and f.id not in revealed
        and any(normalize_th(t) in text for t in f.leak_terms_th)
    ]
    if any(normalize_th(t) in text for t in case.forbidden_terms_th):
        found.append("reply contains a forbidden term")
    return found


@dataclass
class Env:
    client: TestClient
    maker: "sessionmaker[Session]"
    mode: str


def run_golden(g: Golden, env: Env) -> Outcome:
    out = Outcome(g.id, "PASS", env.mode)
    loaded = load_case(_content_dir() / "cases" / g.case)
    r = env.client.post(
        "/v1/sessions",
        json={"case_id": g.case, "variant": g.variant, "learner_name": "golden"},
    )
    if r.status_code != 201:
        code = r.json().get("error", {}).get("code")
        if g.blocked_by and code == "VARIANT_NOT_AVAILABLE":
            return Outcome(g.id, "SKIP", env.mode, [f"blocked by {g.blocked_by}"])
        return Outcome(g.id, "FAIL", env.mode, [f"createSession {r.status_code} {code}"])
    created = r.json()
    sid = uuid.UUID(created["session_id"])
    headers = {"Authorization": f"Bearer {created['token']}"}
    base = f"/v1/sessions/{sid}"
    fail = out.details

    def state_revealed() -> set[str]:
        with env.maker() as db:
            row = db.get(LearnerSession, sid)
            return set(row.state["revealed_fact_ids"]) if row else set()

    def events() -> list[Event]:
        with env.maker() as db:
            return list(db.scalars(select(Event).where(Event.session_id == sid).order_by(Event.id)))

    def no_leaks(label: str, body: dict[str, Any]) -> None:
        if _keys(body) & FORBIDDEN_KEYS:
            fail.append(f"{label}: forbidden key in a play-time response")
        revealed = state_revealed()
        text = " ".join(x["text"] for x in body.get("replies", []))
        fail.extend(f"{label}: {m}" for m in leaks(text, loaded.case, revealed))

    said = held = 0
    for n, step in enumerate(g.steps, start=1):
        label = f"step {n}"
        if step.say is not None:
            resp = env.client.post(
                f"{base}/turns",
                json={"text": step.say, "client_turn_id": uuid.uuid4().hex},
                headers=headers,
            )
            if resp.status_code != 200:
                fail.append(f"{label}: sendTurn {resp.status_code} {resp.json()['error']['code']}")
                return _done(out, fail)
            body = resp.json()
            no_leaks(label, body)
            logged = [e for e in events() if e.turn_idx == body["turn_idx"]]
            detected = {
                a["id"]
                for e in logged
                if e.type == "ACTIONS_DETECTED"
                for a in e.payload["actions"]
            }
            types = {e.type for e in logged}
            mine: list[str] = []
            if step.expect_actions_any and not detected & set(step.expect_actions_any):
                mine.append(f"expected one of {step.expect_actions_any}, got {sorted(detected)}")
            if step.expect_actions is not None and detected != set(step.expect_actions):
                mine.append(f"expected actions {step.expect_actions}, got {sorted(detected)}")
            mine += [f"event {e} not logged" for e in step.expect_events if e not in types]
            said += 1
            held += not mine
            if mine and g.expect.min_step_pass_rate is None:
                fail += [f"{label}: {m}" for m in mine]
        elif step.decision is not None:
            resp = env.client.post(
                f"{base}/decision", json={"option_id": step.decision}, headers=headers
            )
            if resp.status_code != 200:
                fail.append(f"{label}: decision {resp.status_code} {resp.json()['error']['code']}")
                return _done(out, fail)
            no_leaks(label, resp.json())
        else:
            resp = env.client.post(f"{base}/complete", json={"note_th": step.note}, headers=headers)
            if resp.status_code != 200:
                fail.append(f"{label}: complete {resp.status_code} {resp.json()['error']['code']}")
                return _done(out, fail)

    report = env.client.get(f"{base}/report", headers=headers)
    body = report.json() if report.status_code == 200 else {}
    if body:
        with env.maker() as db:
            diffs = rescore(db, get_store(), sid).diffs
        fail += [f"rescore differs from the stored report: {d}" for d in diffs[:3]]
    logged_all = events()
    reveal_counts: dict[str, int] = {}
    for e in logged_all:
        if e.type == "FACT_REVEALED":
            reveal_counts[e.payload["id"]] = reveal_counts.get(e.payload["id"], 0) + 1
    facts = Facts(
        safety_status=body.get("safety_status"),
        event_types={e.type for e in logged_all},
        items={i["id"]: i["result"] for i in body.get("items", [])},
        revealed=state_revealed(),
        reveal_counts=reveal_counts,
        terminal_state=body.get("replay", {}).get("terminal_state"),
        missed={
            m.get("fact_id", "") for m in body.get("replay", {}).get("missed_opportunities", [])
        },
        step_rate=(held / said) if said else None,
    )
    fail += check(g.expect, facts)
    for p in g.pending:
        still = check(p.expect, facts)
        if still:
            out.pending += [f"{m} (blocked by {p.blocked_by})" for m in still]
        else:
            out.warnings.append(
                f"pending expectation blocked by {p.blocked_by} now passes: remove it"
            )
    if g.blocked_by:
        out.warnings.append(f"blocked_by {g.blocked_by} is stale: the file ran")
    return _done(out, fail)


def _done(out: Outcome, fail: list[str]) -> Outcome:
    out.status = "FAIL" if fail else "PASS"
    return out


def _content_dir() -> Path:
    return get_settings().content_dir


# ---------- database, app, CLI ----------


def alembic_config(url: str) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    # ConfigParser interpolates %: an unescaped one in a password fails and prints the credentials
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


@contextmanager
def temp_database(server_url: str) -> Iterator[str]:
    """An empty database migrated to head, dropped on exit."""
    url = make_url(server_url)
    name = f"simtamy_eval_{uuid.uuid4().hex[:12]}"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    new_url = url.set(database=name).render_as_string(hide_password=False)
    try:
        command.upgrade(alembic_config(new_url), "head")
        yield new_url
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.dispose()


def run_all(files: Sequence[Path], database_url: str, *, mock: bool = True) -> list[Outcome]:
    os.environ["DATABASE_URL"] = database_url
    os.environ["ALLOW_DRAFT_CASES"] = "true"
    os.environ["RATE_LIMIT_PER_MIN"] = "0"  # a golden file plays up to 40 turns back to back
    os.environ.setdefault("CONTENT_DIR", str(REPO_DIR / "content"))
    for cached in (get_settings, get_engine, get_sessionmaker, get_store):
        cached.cache_clear()
    app = create_app()
    mode = "mock" if mock else get_settings().llm_provider
    env = Env(TestClient(app, raise_server_exceptions=False), get_sessionmaker(), mode)
    outcomes: list[Outcome] = []
    for path in files:
        try:
            g = load_golden(path)
        except (ValidationError, yaml.YAMLError, OSError) as exc:
            outcomes.append(Outcome(path.stem, "FAIL", mode, [f"unreadable golden file: {exc}"]))
            continue
        if mock:
            provider = LexicalProvider(load_case(_content_dir() / "cases" / g.case))
            app.dependency_overrides[get_llm_factory] = lambda p=provider: (
                lambda purpose, on_call: LLMClient(p, model="golden", timeout_s=1, on_call=on_call)
            )
        outcomes.append(run_golden(g, env))
    for cached in (get_settings, get_engine, get_sessionmaker, get_store):
        cached.cache_clear()
    return outcomes


def render(outcomes: Sequence[Outcome]) -> str:
    lines = [f"{'ID':<6} {'mode':<8} {'result':<7} detail"]
    for o in outcomes:
        detail = "; ".join(o.details) or "ok"
        lines.append(f"{o.id:<6} {o.mode:<8} {o.status:<7} {detail}")
        lines += [f"{'':<23}pending: {p}" for p in o.pending]
        lines += [f"{'':<23}WARN: {w}" for w in o.warnings]
    n = {s: sum(o.status == s for o in outcomes) for s in ("PASS", "FAIL", "SKIP")}
    pending = sum(len(o.pending) for o in outcomes)
    lines.append(
        f"{n['PASS']} passed, {n['FAIL']} failed, {n['SKIP']} skipped, "
        f"{pending} pending expectations"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval")
    parser.add_argument("--golden-dir", type=Path, default=REPO_DIR / "eval" / "golden")
    parser.add_argument("--provider", choices=["mock", "env"], default="mock")
    parser.add_argument("only", nargs="*", help="golden ids to run (default: all)")
    args = parser.parse_args(argv)
    files = sorted(args.golden_dir.glob("T*.yaml"))
    if args.only:
        files = [f for f in files if f.stem in args.only]
    if not files:
        print("no golden files found", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    with temp_database(get_settings().database_url) as url:
        outcomes = run_all(files, url, mock=args.provider == "mock")
    print(render(outcomes))
    return 1 if any(o.status == "FAIL" for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
