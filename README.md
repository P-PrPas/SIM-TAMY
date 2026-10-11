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
Requires GNU make and a POSIX shell (Git Bash / WSL on Windows), Python 3.11+, Node 22+.

## Layout

| Path | What |
|---|---|
| `apps/api` | FastAPI backend (`engine/` and `domain/` are pure + mypy strict) |
| `apps/web` | Next.js (App Router) + TypeScript + Tailwind; Thai strings in `lib/i18n/th.json` |
| `content/` | Case YAML (Content team owns `content/cases/**`) |
| `eval/`, `recordings/` | Golden tests / model bench, Replay Mode sessions |
| `docs/` | PRD, API design, OpenAPI, ADRs |

`make eval`, `bench`, `rescore`, `stats`, `cost-report`, `purge-old`, `demo` exit non-zero ("not implemented") until their tickets land; `validate-content` is a stub until T-010.
