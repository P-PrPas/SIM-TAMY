# AGENTS.md — SIM-TAMY

Instructions for any AI coding agent working in this repo (Claude Code, Codex, Cursor, etc.). Humans: this is also the quick-start for the engineering rules.

## What this project is

SIM-TAMY 2.0 is a Thai **midwifery decision-practice platform** for families and the institutions that teach them (parent schools, health services). It is organized as four pillars: (1) Thai Midwifery Learning Paths, (2) Interactive Family Simulation & Thai Wisdom Decision Lab, (3) Evidence & Learning Assessment (Learning Passport), (4) Institutional Learning Workspace. Learners talk with AI characters, share role-private facts with a partner, commit joint decisions, and get a scored, evidence-linked debrief. It is a **hackathon prototype** used to pitch the idea to customers.

It is an **education tool, not a medical device**. It never diagnoses, never recommends treatment, never certifies competence.

## Source of truth (read before non-trivial work)

| File | Use it for |
|---|---|
| `docs/SIM-TAMY_2.0_AI_Updated_Blueprint_v2.1.md` | **2.0 scope, pillars, AI-01/02/03 contracts, backlog (S0-* .. S3-*, AI-*), acceptance tests (CT-*, AI-T*). Authoritative for 2.0.** |
| `docs/v2/contracts.md` + `docs/adr/ADR-15-*` | **Binding 2.0 contracts:** stream ownership, merge order, content files, family-story extension, API routes, AI pipeline, web routes. Read before any 2.0 task. |
| `docs/knowledge base/` | Content team's research: `Thai_Midwifery_Knowledge_Base_2026.pdf` (sources S01–S40) and `Midwifery_Textbook_Catalog_2026.json` (84 catalog records). **The only source for new clinical/Thai-wisdom content.** |
| `docs/PRD.md` | 1.x requirements (FR-*), API, data model, AI specs, scoring, tests, backlog (T-*). Still authoritative where the Blueprint is silent. |
| `docs/CONCEPT.md` | Product concept and business context (background only) |
| `docs/adr/` | Architecture decisions. Add a new ADR when you change one |

PRD is long. Don't load all of it: search by ID (`FR-ENG-04`, `T-034`, `ADR-04`) and read only the relevant section.
Precedence: Blueprint v2.1 > ADRs > PRD. Where the Blueprint names a contract or route, adapt it to the existing stack (keep `/v1/...` routes, the current `apps/api` layout and `content/` tree) instead of copying its suggested skeleton. If a document is ambiguous, pick the more conservative option and note it in the PR.

Curriculum suggestions inside the knowledge base are background: the Blueprint's stages, scenarios and rubric weights win.

## Non-negotiable rules

These protect patient-safety credibility. Do not trade them for speed.

1. **Engine is deterministic.** `engine/` (state machine, rubric, scoring) is pure Python: no network, no LLM, no randomness, no clock. Same input → same output. Re-scoring a session from its Event Log must give identical results.
2. **LLMs do exactly three jobs** (Blueprint AI-01/02/03): (a) **AI-01 Interpreter**: map learner text, with multi-turn context, to an allowed intent / Action ID / requested fact IDs, or ask for clarification; (b) **AI-02 Generator**: phrase a character or explainer reply from allowed scenario facts and released knowledge claims only, with citations to the IDs it was given; (c) **AI-03 Debrief**: phrase feedback from the finished, engine-produced assessment and event IDs. **Never** use an LLM to score, to decide state transitions, to decide safety status, to pick citations outside the supplied pack, or to invent facts/outcomes.
3. **No clinical content in code or prompts.** Symptoms, red-flag criteria, contraindications, cultural practices, outcome scripts, knowledge claims and rubric items live in `content/`. For 2.0 there is no separate content review: agents author content directly from `docs/knowledge base/` and must give every claim its source code (`S01`–`S40` or catalog `M/S/T/P/I/G` code) plus a locator (section/page/URL). Do not add clinical statements that the knowledge base does not support, and never ingest full copyrighted books (the catalog is metadata only).
4. **Generator gets allowed facts only.** Never pass the whole case file, hidden facts, the partner role's private facts, the rubric, or other unlocked-later data into a prompt. Knowledge claims enter a prompt only as a bounded evidence pack from the pinned release.
5. **Don't leak during play.** API responses during an active session must not include `revealed_fact_ids`, `risk_state`, detected `actions`, hidden facts, or scores (unless `GLASS_BOX_LIVE=true`).
6. **Validator is hard.** Rejected patient replies are never shown or streamed. After 2 regenerations, use the canned `fallback_utterances_th`.
7. **Critical Safety is a gate, not a score.** If any `critical` rubric item fails, `safety_status = SAFETY_NOT_MET` regardless of total score, and the UI must never show "pass" language in that case.
8. **Event Log is append-only.** No UPDATE/DELETE on `events` in application code. It is the single source of truth for scoring.
9. **Show provenance, not fake approval.** Knowledge cards and the Thai Wisdom Lens show their sources (code, title, locator). Content derived from the knowledge base is published with `review_basis: knowledge_base_2026`; never label it as expert- or professionally-reviewed, and never present it as certification. Demo or mock data (seeded cohorts, sample analytics, mock accounts) must be labeled as demo data wherever it appears. The educational scope and the Critical Safety gate are unchanged.
10. **Synthetic data only.** No real patient data, ever. Characters, families and accounts are fictional. Don't log learner free text to general app logs; it goes to the DB under the retention policy, and class analytics never show raw chats.
11. **Honest claims.** Never hard-code or fabricate metrics (accuracy, pass rates, cost). Report only what `make eval` / `make bench` / `make cost-report` actually measured.
12. **Secrets stay server-side.** LLM API keys never reach the frontend, repo, logs, or test fixtures. No frontend call goes directly to a model provider.
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
apps/web/      Next.js (App Router) + TypeScript + Tailwind; i18n in lib/i18n/th.json (+ v2/<namespace>.json per 2.0 stream)
content/       cases/<id>/{case,actions,rubric}.yaml  ← Content team owns; schemas/ is generated
eval/          model_bench.py, run_eval.py, devset/, golden/T01..T10.yaml
recordings/    recorded sessions for Replay Mode
docs/          PRD, concept, ADRs
```

Content cases: `DEV-001` is a synthetic **engineering fixture** (never use in a real demo); `PP-001` is the real case supplied by the Content team.

2.0 content (Blueprint §09): `content/knowledge/` holds the source registry (catalog import) and knowledge units; Golden Scenarios GS-A (critical-safety route) and GS-B (positive Thai-service route) are the featured family simulations. Earlier family stories (`golden-first-night`, bridge stories) stay playable as extra modules.

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
| `make eval-v2 [PROVIDER=env]` | AI-01 labeled Thai sets (`eval/v2/`: paraphrase, multi-turn, ambiguous, adversarial; dev + held-out); prints n, accuracy and errors. Mock by default, so numbers describe the mock |
| `make bench` | Model comparison on the Action dev set |
| `make rescore SESSION=<id>` | Re-score from the Event Log |
| `make stats` / `make cost-report` | Latency / LLM cost summaries |
| `make loadcheck URL=<api>` | 20 concurrent learners; client-side p50/p95 and error rate (`docs/results/` holds saved runs) |
| `make demo` | Demo mode (Mock LLM / Replay as configured) |
| `make build-course-replays` | Rebuild synthetic course examples from content-owned golden conversations |

Local default is `LLM_PROVIDER=mock` so everything runs offline and deterministically. Key env vars: `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_{INTERPRETER,GENERATOR,DEBRIEF}`, `ALLOW_DRAFT_CASES`, `GLASS_BOX_LIVE`, `INSTRUCTOR_SECRET` (full list in PRD §6.5 and `.env.example`).

## Conventions

**General**
- Code, identifiers, comments, commit messages: **English**. User-facing strings: **Thai**, only in `apps/web/lib/i18n/th.json` (or its `v2/*.json` namespaces), `content/`, or `ai/prompts/`. No Thai string literals scattered in components or services.
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
- **Temporary files and worktrees — mandatory cleanup after every task:** Prefer the current checkout and read-only `git show` for reviews. Do not create temporary folders alongside this repo in `C:\Code\hackathon`. If temporary files are unavoidable, keep them under the repo's `.tmp/<task>/` where practical, record every path created (including test artifacts and paths outside the repo), and use `try/finally` or an equivalent cleanup step. Remove them before the final handoff, whether the task succeeds or fails. Do not leave temporary folders for the user to clean up.
- **Verify cleanup before handing back:** List the locations used and confirm that your temporary files, test directories, and review worktrees are gone. Check for uncommitted work first; remove worktrees with `git worktree remove`, and unlink junctions/symlinks without deleting their targets. Never remove another person's or agent's active workspace or discard uncommitted work without explicit authorization. If deletion is blocked, report the exact remaining paths and reason; do not silently leave them behind or claim cleanup succeeded.
- **Ask first** (stop and request a human decision) before: changing an ADR; editing or squashing migrations that may have data; changing scoring semantics or Critical Safety rules; adding a new LLM duty beyond AI-01/02/03. Contracts and schemas spelled out in the Blueprint (knowledge units, intent / grounded-reply / debrief schemas, institution entities) are pre-approved; extending the Case/Rubric schema for them is fine, with the ADR/PRD update in the same PR.
- **Prototype boundaries (product owner, 2026-10-28):** no real authentication or production security work. Institutions, staff and learners use mock accounts (pick-a-profile or a fixed demo login), clearly labeled as demo. Keep data separated per mock organization in queries so the demo story holds, but don't build auth, password storage, SSO, billing, or tenant-security hardening. Pilot studies and buyer interviews (Blueprint S3-03, S3-04) are out of scope.
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
| **content** | `content/` cases, family stories, knowledge units, source registry; loader, validator CLI, schemas | add claims without a knowledge-base source and locator; claim expert review |
| **reviewer** | read-only review against the rules above and PRD | approve PRs that violate a non-negotiable rule |

Hand-offs go through the contracts in `docs/v2/contracts.md` (2.0) and PRD §7 (Case schema), §8 (API), §9 (AI I/O). If a contract must change, update the PRD section and the schema in the same PR.

## Gotchas

- Streaming: **buffer-then-chunk** — only emit text after the Validator accepts it.
- `idx` is the *learner turn index* (starts at 1) and is the unit of "time" in rubric checks; don't substitute timestamps.
- Repeating an already-fired Action does not unlock again but is logged as `ACTION_REPEATED`.
- Decisions are committed via the Decision Panel endpoint, not inferred from chat text. Exception (2.0): a non-critical, non-joint family `choice` step may commit from typed text the Interpreter mapped confidently; `critical` and `joint` steps always need the explicit button (`docs/v2/contracts.md` §3).
- Pressure-phase lines (Variant C) are scripted in the case file, not LLM-generated.
- `ALLOW_DRAFT_CASES=true` is expected during the hackathon so Draft cases stay playable; learner screens show sources, not review badges (rule 9).
