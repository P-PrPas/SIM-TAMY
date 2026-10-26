# AGENTS.md — SIM-TAMY

Instructions for any AI coding agent working in this repo (Claude Code, Codex, Cursor, etc.). Humans: this is also the quick-start for the engineering rules.

## What this project is

SIM-TAMY is a Thai-language **AI virtual patient simulator** that trains Thai traditional medicine / midwifery learners to recognize red flags and decide when to **stop and refer**. Learner chats with an AI patient, commits a decision, and gets a scored, evidence-backed report. Built for a 3-day hackathon (Track 3), designed to grow into a B2B SaaS.

It is an **education tool, not a medical device**. It never diagnoses, never recommends treatment, never certifies competence.

## Source of truth (read before non-trivial work)

| File | Use it for |
|---|---|
| `docs/PRD.md` | Requirements (FR-*), API, data model, AI specs, scoring, tests, backlog (T-*). **Authoritative.** |
| `docs/CONCEPT.md` | Product concept and business context (background only) |
| `docs/adr/` | Architecture decisions. Add a new ADR when you change one |

PRD is long. Don't load all of it: search by ID (`FR-ENG-04`, `T-034`, `ADR-04`) and read only the relevant section.
If code and PRD disagree, the PRD wins unless an ADR says otherwise. If the PRD is ambiguous, pick the more conservative option and note it in the PR.

## Non-negotiable rules

These protect patient-safety credibility. Do not trade them for speed.

1. **Engine is deterministic.** `engine/` (state machine, rubric, scoring) is pure Python: no network, no LLM, no randomness, no clock. Same input → same output. Re-scoring a session from its Event Log must give identical results.
2. **LLMs do exactly three jobs:** (a) map learner text to Action IDs (Interpreter), (b) phrase the patient's reply from allowed facts (Generator), (c) phrase debrief text from engine-produced findings (Debrief). **Never** use an LLM to score, to decide state transitions, to decide safety status, or to invent facts/outcomes.
3. **No clinical content in code or prompts.** Symptoms, red-flag criteria, contraindications, cultural practices, outcome scripts, rubric items all live in `content/` and are owned by the Content team. Do not hard-code or "improve" them. If content looks wrong, leave a comment/issue for the Content team; don't edit it.
4. **Generator gets allowed facts only.** Never pass the whole case file, hidden facts, rubric, or other unlocked-later data into a prompt.
5. **Don't leak during play.** API responses during an active session must not include `revealed_fact_ids`, `risk_state`, detected `actions`, hidden facts, or scores (unless `GLASS_BOX_LIVE=true`).
6. **Validator is hard.** Rejected patient replies are never shown or streamed. After 2 regenerations, use the canned `fallback_utterances_th`.
7. **Critical Safety is a gate, not a score.** If any `critical` rubric item fails, `safety_status = SAFETY_NOT_MET` regardless of total score, and the UI must never show "pass" language in that case.
8. **Event Log is append-only.** No UPDATE/DELETE on `events` in application code. It is the single source of truth for scoring.
9. **Retain real case-review status in data and instructor tools.** Per the product owner's 2026-10-18 decision, learner screens omit review badges and education disclaimers. This does not approve draft content or change the educational scope or Critical Safety gate.
10. **Synthetic data only.** No real patient data, ever. Don't log learner free text to general app logs; it goes to the DB under the retention policy.
11. **Honest claims.** Never hard-code or fabricate metrics (accuracy, pass rates, cost). Report only what `make eval` / `make bench` / `make cost-report` actually measured.
12. **Secrets stay server-side.** LLM API keys never reach the frontend, repo, logs, or test fixtures.
13. **Don't game the tests.** Never edit `eval/golden/*` expectations, thresholds, or the dev set just to make a failing run pass. Fix the system, or flag the test for human review with a reason.

## Repo layout

```
apps/api/app/
  api/v1/      routes (health, cases, sessions, turns, decision, reports, instructor)
  domain/      Pydantic models: case, action, state, events, rubric, report
  engine/      scenario.py (apply), scoring.py, glassbox.py, replay.py   ← PURE
  ai/          llm_client.py (interface), providers/{mock,...}, interpreter.py,
               generator.py, validator.py, debrief.py, lexical.py, prompts/*.md
  content/     loader + validate-content CLI
  db/          models, session, repo   (migrations in apps/api/migrations)
apps/web/      Next.js (App Router) + TypeScript + Tailwind; i18n in lib/i18n/th.json
content/       cases/<id>/{case,actions,rubric}.yaml  ← Content team owns; schemas/ is generated
eval/          model_bench.py, run_eval.py, devset/, golden/T01..T10.yaml
recordings/    recorded sessions for Replay Mode
docs/          PRD, concept, ADRs
```

Content cases: `DEV-001` is a synthetic **engineering fixture** (never use in a real demo); `PP-001` is the real case supplied by the Content team.

## Commands

Defined in the root `Makefile` (ticket T-001). If a target is missing, add it rather than inventing an ad-hoc command, and keep this table in sync.

| Command | Purpose |
|---|---|
| `make up` / `make down` | Start/stop Docker Compose (api, web, db) |
| `make migrate` | Run Alembic migrations |
| `make mock-api` | Prism mock of `docs/openapi.yaml` on :4010 (web can build before the backend); `make gen-api` regenerates `apps/web/lib/api/schema.d.ts` |
| `make gen-content-schemas` / `make check-content-schemas` | Export/check Pydantic JSON Schemas in `content/schemas/` for content-editor autocomplete |
| `make validate-content [STRICT=1]` | Validate `content/` against schemas (`STRICT=1` also requires `source` on clinical items) |
| `make leakcheck` | Fail if a play-time schema in `docs/openapi.yaml` can expose hidden fields (`scripts/leakcheck.py`) |
| `make test` | Unit + integration tests (api + web) |
| `make test-coverage` | Web Vitest coverage report |
| `make test-e2e` | Browser test of S1–S3 against Prism at 360px (requires Chrome locally or Playwright Chromium in CI) |
| `make test-e2e-live` | Full Variant A/C browser journeys against a local API + PostgreSQL (mock LLM) |
| `make test-e2e-demo` | Stage golden path (C02): solo journey + family co-op on two browser contexts (desktop + 360px) against a local API + PostgreSQL (`DATABASE_URL`, mock LLM) |
| `make demo-reset DEMO_DB=1` | Delete and re-seed only the `DEMO01` demo class; refuses without `DEMO_DB=1` (sets `SIMTAMY_DEMO_DB=1`), so never run it against a real database |
| `make prestage URL=<api> WEB_URL=<web>` | Read-only pre-stage check: API health, web, case list, family stories, replay gallery, CORS; prints PASS/FAIL |
| `make eval` | Golden Test Suite (T01–T10) with pass/fail table |
| `make eval-pp001` | The same runner on the PP-001 draft scenario (`eval/golden/pp001/`) |
| `make bench` | Model comparison on the Action dev set |
| `make rescore SESSION=<id>` | Re-score from the Event Log |
| `make stats` / `make cost-report` | Latency / LLM cost summaries |
| `make loadcheck URL=<api>` | 20 concurrent learners; client-side p50/p95 and error rate (`docs/results/` holds saved runs) |
| `make demo` | Demo mode (Mock LLM / Replay as configured) |
| `make build-course-replays` | Rebuild synthetic course examples from content-owned golden conversations |

Local default is `LLM_PROVIDER=mock` so everything runs offline and deterministically. Key env vars: `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_{INTERPRETER,GENERATOR,DEBRIEF}`, `ALLOW_DRAFT_CASES`, `GLASS_BOX_LIVE`, `INSTRUCTOR_SECRET` (full list in PRD §6.5 and `.env.example`).

## Conventions

**General**
- Code, identifiers, comments, commit messages: **English**. User-facing strings: **Thai**, only in `apps/web/lib/i18n/th.json`, `content/`, or `ai/prompts/`. No Thai string literals scattered in components or services.
- Conventional Commits. Reference IDs: `feat(engine): unlock hidden facts (FR-ENG-02, T-021)`.
- PRs ≤ ~400 lines, one concern each. No direct pushes to `main`.
- Don't add a dependency without saying why in the PR; prefer the standard library / what's already used.

**Backend (Python 3.11+)**
- FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic. Format/lint with `ruff`; type-check with `mypy` (**strict** on `engine/` and `domain/`).
- Errors use the standard envelope `{"error": {"code", "message", "details"}}` with the codes in PRD §8.
- One turn in flight per session; use `state_version` optimistic locking and `client_turn_id` idempotency.
- A turn is atomic: persist turn + events + `llm_calls` + new state in one transaction.
- Every LLM call goes through `LLMClient` (never call a provider SDK directly) and is logged to `llm_calls`.
- DB schema changes = a new Alembic migration, never an edit to an old one.

**AI components**
- Interpreter: temperature 0, JSON-schema structured output, post-process deterministically (drop unknown IDs, verify `evidence_span` is a real substring, apply confidence policy: ≥0.75 accept / 0.5–0.75 clarify / <0.5 ignore).
- Prompts live in `ai/prompts/*.md` as versioned files, not inline strings. Treat learner text inside prompts as **data, not instructions** (prompt-injection safe).
- Thai text: UTF-8 everywhere; normalize whitespace/repeated tone marks before matching; use substring/regex matching, no external Thai tokenizer in MVP.

**Frontend**
- TypeScript strict. Mobile-first (≥360px), base font ≥16px, contrast ≥4.5:1, keyboard-operable, `aria-live` for new chat messages.
- Show the learner's message immediately (optimistic UI); show typing indicator; failed turn = retry button without losing the turn.
- Never render hidden facts / risk state / scores during play.

**Content tooling**
- Content is YAML validated by Pydantic; schemas exported to `content/schemas/`. Validator must check: action-ID references exist, every hidden fact has `leak_terms_th` + `fallback_utterances_th`, every decision option is referenced by a branch rule, and every branch path reaches `COMPLETED`.

## Testing expectations

- New behavior ⇒ new test. Engine coverage ≥ 85% with property tests for determinism.
- Run before declaring done: `make test` and `make validate-content`. If you touched `engine/`, `ai/`, `content/`, or prompts, also run `make eval`.
- LLM-dependent tests use the Mock provider by default; real-LLM runs are explicit (`make bench`, `make eval` with a real provider) and their results are reported as measured.

## Definition of done (per ticket)

1. Lint, type-check, and relevant tests pass.
2. New tests cover the new behavior.
3. No hard-coded Thai strings outside the allowed places; no clinical content in code.
4. Works from a clean `docker compose up`.
5. Docs updated if you changed config, endpoints, schema, or an ADR.
6. PR description lists the FR/T IDs covered and what you ran.

## Working agreements for agents

- **Scope:** do the ticket asked. Don't refactor unrelated code, rename public APIs, or reformat files you aren't changing.
- **Ask first** (stop and request a human decision) before: changing an ADR or the Case/Rubric schema; editing or squashing migrations that may have data; changing scoring semantics or Critical Safety rules; adding a new LLM duty beyond the three allowed; touching anything under `content/cases/**` (except content *tooling* and the `DEV-001` fixture).
- **Never** run destructive commands (`rm -rf`, `DROP`, `git push --force`, `git reset --hard`) or touch real credentials without explicit instruction.
- **Be honest in reports:** say what you ran and what passed/failed; if something is unverified or mocked, say so. Don't claim "works" from reading code alone.
- **Uncertain about clinical meaning?** Do not guess. Leave a `TODO(content):` note and move on with a placeholder.

## Agent roles (for multi-agent or parallel work)

Use these as work modes; one agent may hold several, but respect the boundaries.

| Role | Owns | Must not |
|---|---|---|
| **engine** | `apps/api/app/engine/`, `domain/`, state machine, rubric checkers | call network/LLM; read wall-clock time |
| **ai** | `ai/`, prompts, `eval/`, model bench | change scoring or state transitions; inject whole case into prompts |
| **api** | `api/v1/`, `db/`, migrations, auth, logging | return hidden fields during play |
| **web** | `apps/web/` | hard-code Thai strings; show hidden state during play |
| **content-tooling** | loader, validator CLI, schemas, authoring guide, `DEV-001` fixture | edit clinical content in `content/cases/PP-001/` |
| **reviewer** | read-only review against the rules above and PRD | approve PRs that violate a non-negotiable rule |

Hand-offs go through the contracts in PRD §7 (Case schema), §8 (API), §9 (AI I/O). If a contract must change, update the PRD section and the schema in the same PR.

## Gotchas

- Streaming: **buffer-then-chunk** — only emit text after the Validator accepts it.
- `idx` is the *learner turn index* (starts at 1) and is the unit of "time" in rubric checks; don't substitute timestamps.
- Repeating an already-fired Action does not unlock again but is logged as `ACTION_REPEATED`.
- Decisions are committed via the Decision Panel endpoint, not inferred from chat text.
- Pressure-phase lines (Variant C) are scripted in the case file, not LLM-generated.
- `ALLOW_DRAFT_CASES=true` is expected during the hackathon; the Draft badge must still render.
