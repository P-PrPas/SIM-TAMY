# SIM-TAMY

The AI Flight Simulator for Thai Midwifery

เอกสารออกแบบ: [หลักสูตร 4 ระยะและแนวคิดโซลูชัน](docs/SIM-TAMY-curriculum-and-solution.md)

AI virtual patient simulator (Thai) for training Thai traditional medicine / midwifery learners to recognize red flags and decide when to stop and refer. **Education tool, not a medical device.**

Rules, layout, and conventions: [AGENTS.md](AGENTS.md). Requirements: [docs/PRD.md](docs/PRD.md).

## Quick start

```bash
cp .env.example .env     # defaults to LLM_PROVIDER=mock (offline, deterministic)
make up                  # db + api (:8000) + web (:3000)
curl localhost:8000/health
```

Local (no Docker) dev: `make install`, then `make lint test validate-content`.
DB integration tests need Postgres: `docker compose up -d db` (they skip locally if it is down, and fail in CI).
Requires GNU make and a POSIX shell (Git Bash / WSL on Windows), Python 3.11+, Node 22+.

Until the sessions API is implemented, run the S1–S3 web flow against the OpenAPI Prism mock in separate terminals:

```bash
make mock-api
NEXT_PUBLIC_API_URL=http://localhost:4010 npm --prefix apps/web run dev
```

The web app stores the anonymous session token in the current tab's `sessionStorage`. The decision button is present but disabled until the S4 decision-panel ticket is implemented.

Run the S1–S3 browser acceptance checks with `make test-e2e` (or `npm --prefix apps/web run test:e2e` on Windows without Make). The test starts Prism and Next.js, uses Chrome locally, and checks the 360px layout and chat retry flow. CI needs Playwright Chromium installed.

Docker Compose pins the API and Postgres images to the Debian Bookworm variants so the development stack does not change base OS when upstream floating tags move.

## Layout

| Path | What |
|---|---|
| `apps/api` | FastAPI backend (`engine/` and `domain/` are pure + mypy strict) |
| `apps/web` | Next.js (App Router) + TypeScript + Tailwind; Thai strings in `lib/i18n/th.json` |
| `content/` | Case YAML (Content team owns `content/cases/**`) |
| `eval/`, `recordings/` | Golden tests / model bench, Replay Mode sessions |
| `docs/` | PRD, API design, OpenAPI, ADRs |

`make eval`, `bench`, `rescore`, `stats`, `cost-report`, `purge-old`, `demo` exit non-zero ("not implemented") until their tickets land; `validate-content` is a stub until T-010.
