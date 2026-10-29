<div align="center">
  <img src="apps/web/public/brand/logo.png" width="88" alt="SIM-TAMY emblem" />
  <h1>SIM-TAMY</h1>
  <p><strong>A practice space for the decisions families make together.</strong></p>
  <p>Thai midwifery learning · Interactive family simulations · Evidence-linked reflection</p>

  <p>
    <a href="https://github.com/P-PrPas/SIM-TAMY/actions/workflows/ci.yml"><img src="https://github.com/P-PrPas/SIM-TAMY/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status" /></a>
    <img src="https://img.shields.io/badge/Next.js-16-29221B?style=flat-square&amp;logo=nextdotjs" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/FastAPI-Python_3.12-56705B?style=flat-square&amp;logo=fastapi&amp;logoColor=white" alt="FastAPI on Python 3.12" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-B8892D?style=flat-square&amp;logo=postgresql&amp;logoColor=white" alt="PostgreSQL 16" />
  </p>

  <p><a href="https://sim-tamy.vercel.app"><strong>Open the app ↗</strong></a> · <a href="#quick-start">Run locally</a> · <a href="#architecture">Architecture</a> · <a href="docs/README.md">Documentation</a></p>
</div>

<img src="docs/assets/learning-journey.svg" width="100%" alt="Four learning stages: before and during pregnancy, preparing for birth, postpartum and recovery, newborn and family care." />

## Why SIM-TAMY?

SIM-TAMY is a Thai-language learning platform for families and the institutions that teach them. It brings Thai midwifery knowledge, conversation practice, and shared decision-making into one learning journey. Learners read a lesson, enter an illustrated scenario, ask questions, make decisions, and reflect on the evidence behind the result.

AI interprets language and phrases dialogue; a deterministic simulation engine controls transitions, scoring, and Critical Safety. All characters and accounts are fictional.

**Educational scope:** this is a hackathon prototype. It does not diagnose, prescribe treatment, or certify clinical competence.

## The learning experience

| Stage | Focus | Default availability |
| :--- | :--- | :--- |
| **01 · Before & during pregnancy** | Explore a lesson and practice a family conversation. | One lesson + one scenario |
| **02 · Preparing for birth** | Practice communication and planning together. | One lesson + one scenario |
| **03 · Postpartum & recovery** | Explore decisions and evidence-linked reflection. | One lesson + one scenario |
| **04 · Newborn & family care** | Practice sharing information and responsibilities. | One lesson + one scenario |

The learner experience opens this curated path. Additional content is greyed out; development and test environments can enable it with `NEXT_PUBLIC_SHOW_ALL_CONTENT=true`. Availability is defined in [learning-path.ts](apps/web/lib/learning-path.ts); curriculum definitions live in [content/curriculum/](content/curriculum/).

![SIM-TAMY home page with four-stage learning cards and existing pixel artwork](docs/assets/home.png)

### For learners

- **Learn, then practice.** Sourced knowledge units connect to interactive scenarios across four stages.
- **Talk with AI characters.** Ask questions in Thai, explore the information available to your role, and commit decisions.
- **Practice together.** Supported family scenarios let two participants share private facts and agree on joint decisions.
- **Understand the result.** Debriefs link findings to attempt events and source references. Critical Safety is shown separately from the score.
- **Follow your progress.** The profile dashboard holds completed lessons, finished attempts, stage progress, and the Learning Passport history.

### For institutions

- Dedicated accounts open an institution-only workspace and navigation.
- Dashboards show cohort, assignment, and learning activity data, with demo data identified in the interface.
- Educators can create and remove cohorts and assignments. Removal archives settings while retaining existing learning evidence.
- APIs scope institutional data by organization; aggregate reporting suppresses small samples where specified by the contract.

## Quick start

Install [Docker with Compose](https://docs.docker.com/get-started/get-docker/), then run:

```bash
git clone https://github.com/P-PrPas/SIM-TAMY.git
cd SIM-TAMY
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

In PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

| Service | Local address |
| :--- | :--- |
| Web application | <http://localhost:3000> |
| API health | <http://localhost:8000/health> |
| Interactive API reference | <http://localhost:8000/docs> |

The API applies migrations before serving. The default `LLM_PROVIDER=mock` runs without a model key. PostgreSQL persists in the Compose volume; `docker compose down` stops the stack without deleting its data. Change `DB_PORT` in `.env` if port 5432 is occupied.

### Sign in to the demo

Open `/login`, expand the demo-account selector, and choose a learner or institution account. The selector fills the credentials; submit the form to sign in.

The username is the synthetic account ID and the shared demo password is **`SimTamy2026!`**. Fixtures live in [content/demo/](content/demo/). Learners open their dashboard from the top-right profile menu; institution accounts land on `/institution`.

This fixed login uses the existing `X-Demo-Account` contract and is not production authentication. See the [account contract](docs/v2/demo-login.md) for session ownership and routing behavior.

<details>
<summary><strong>Local development without application containers</strong></summary>

Requires Python 3.11+, Node.js 22+, PostgreSQL 16, and GNU Make with a POSIX shell. Use Git Bash or WSL for Make commands on Windows.

```bash
cp .env.example .env
make install
docker compose up -d db
```

Export the database URL in your shell, adjusting the port if you changed `DB_PORT`. Then:

```bash
export DATABASE_URL=postgresql+psycopg://sim:sim@localhost:5432/simtamy
cd apps/api
.venv/bin/python -m alembic upgrade head
CONTENT_DIR=../../content .venv/bin/python -m uvicorn app.main:app --reload
```

In another terminal:

```bash
cd apps/web
npm run dev
```

On Windows, use `apps/api/.venv/Scripts/python.exe`. Copying `.env` does not export shell variables for CLI tools; export the values needed by the process when starting from `apps/api`.

</details>

## Configuration

[.env.example](.env.example) documents the local settings. The main switches are:

| Variable | Purpose |
| :--- | :--- |
| `LLM_PROVIDER` | `mock` for offline development; `openai_like` for the live-provider adapter. |
| `LLM_API_KEY`, `LLM_BASE_URL` | Server-side model credentials and endpoint. |
| `LLM_MODEL_INTERPRETER`, `LLM_MODEL_GENERATOR`, `LLM_MODEL_DEBRIEF` | Models for the three permitted AI jobs. |
| `DATABASE_URL` | PostgreSQL connection for the API and database tools. |
| `NEXT_PUBLIC_API_URL` | Public API origin, baked into the web build. |
| `NEXT_PUBLIC_SHOW_ALL_CONTENT` | Opens the full catalogue for development/tests; defaults to `false`. |
| `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | Allowed web origins and optional preview-origin pattern. |
| `ALLOW_DRAFT_CASES` | Controls access to draft case fixtures. |
| `GLASS_BOX_LIVE` | Debug-only disclosure switch; keep `false` for learner use. |
| `INSTRUCTOR_SECRET` | Server-side credential for legacy instructor tools. |

Keep keys and instructor credentials on the API server. Only `NEXT_PUBLIC_*` values belong in the web build. Check `llm_provider` in `/health` to confirm which provider a deployment uses.

## Architecture

```mermaid
flowchart LR
    W["Next.js · Thai learner and institution UI"] --> A["FastAPI · session and organization APIs"]
    A --> E["Deterministic engine · state and assessment"]
    A --> AI["AI pipeline · interpret, phrase, debrief"]
    C["Versioned YAML · scenarios and sourced knowledge"] --> E
    C --> AI
    A --> DB[("PostgreSQL · attempts, events, progress")]
    E --> R["Evidence-linked results"]
    R --> W
```

**The engine owns the outcome.** State transitions, rubric checks, scoring, and Critical Safety are pure Python. An append-only Event Log supports deterministic reconstruction of the assessment.

**AI has three bounded jobs.** The Interpreter maps language to allowed actions or intents. The Generator phrases replies from released facts and bounded evidence packs. The Debrief phrases feedback from engine-produced findings. The hard Validator rejects unacceptable replies before they are shown; fallback utterances are authored content.

**Safety is a gate.** A failed critical rubric item yields `SAFETY_NOT_MET` regardless of total score. Active-session responses omit hidden facts, risk state, detected actions, and scores unless explicit debugging is enabled.

### Repository map

```text
apps/
  api/            FastAPI, domain models, engine, AI pipeline, migrations
  web/            Next.js App Router, Thai UI, dashboards, browser tests
content/          Scenarios, curriculum, knowledge claims, sources, demo fixtures
design-system/    Brand tokens and page design decisions
docs/             Current contracts, deployment guide, knowledge base, source research
eval/             Golden cases, labeled evaluation sets, model benchmarks
recordings/       Synthetic snapshots and compiler fixtures for engineering tools
scripts/          Smoke, pre-stage, load, and schema leak checks
```

Clinical and Thai-wisdom content belongs in `content/`, with source IDs and locators. Research reports and the textbook catalogue are in [docs/knowledge base/](<docs/knowledge base/>); catalogue metadata is not permission to ingest full books.

## Quality checks

Run from the root after `make install`, with PostgreSQL available through `DATABASE_URL`:

| Command | Checks |
| :--- | :--- |
| `make lint` | Ruff, Python formatting, mypy, ESLint, TypeScript. |
| `make test` | API unit/integration tests, engine coverage gate (85%), web unit tests. |
| `make validate-content` | Content schemas, references, and authored scenario constraints. |
| `make leakcheck` | Play-time API schemas do not expose hidden assessment fields. |
| `make test-e2e` | Browser acceptance against the OpenAPI Prism mock. |
| `make test-e2e-live` | Real API/PostgreSQL browser journeys with mock LLM. |
| `make test-e2e-demo` | Solo, family co-op, golden-scenario, and curriculum journeys. |
| `make eval` / `make eval-v2` | Golden scenario checks / labeled AI-01 evaluation; mock by default. |
| `make gen-api` | Regenerate web API types from `docs/openapi.yaml`. |
| `make check-content-schemas` | Check generated JSON Schemas against Pydantic models. |

Browser tests require Chrome locally or Playwright Chromium in CI. Live/demo suites need a migrated, disposable PostgreSQL database. Do not point test suites at a deployed database. DB integration tests can skip locally when PostgreSQL is unavailable and fail in CI instead. Mock results describe the mock, not live-model accuracy.

[CI](.github/workflows/ci.yml) runs API, web, live browser journeys, Docker builds, and smoke checks. The [Makefile](Makefile) also provides latency, cost, retention, and rescore commands. No performance or accuracy claims are inferred from passing tests.

## Deployment

The repository supports **Vercel for the web application** and **Render for the API and PostgreSQL**. The API image runs migrations at startup; the web image uses Next.js standalone output.

Follow the [deployment runbook](docs/RUNBOOK-deploy.md) for configuration, CORS, health checks, smoke tests, and rollback. The [release workflow](.github/workflows/release.yml) validates `v*` tags and uses a configured production deploy hook. Merge status and rollout status are separate.

## Contributing and documentation

Start with the [documentation index](docs/README.md) and [AGENTS.md](AGENTS.md). Use focused PRs and Conventional Commits, include the relevant checks, keep Thai UI copy in i18n dictionaries, and use synthetic data only.

The current Blueprint, ADRs, API schema, and domain contracts are retained alongside the knowledge base. Superseded working notes and review artifacts are no longer tracked; committed versions remain in Git history.

## License and source materials

This repository currently has no project-wide `LICENSE` file. Third-party dependencies and referenced source materials retain their own licenses and attribution requirements. The content registry records provenance and rights metadata; catalogue inclusion does not grant rights to reproduce a book.

---

<div align="center">
  <sub>SIM-TAMY · Learn with context. Practice together. Reflect with evidence.</sub>
</div>
