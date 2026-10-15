# ADR-14: Hosting on Vercel (web) and Render (API + Postgres)

Status: Accepted (owner decision, 2026-10-15). Resolves PRD OD-2.

## Context

The demo link is sent to judges who may open it at any time, with no operator
present. We need HTTPS, deploy-from-git, a managed Postgres, and server-side
secrets (AGENTS.md rule 12), with about three days left and no ops capacity.

## Decision

- `apps/web` on **Vercel** (Root Directory `apps/web`; `NEXT_PUBLIC_API_URL` is a
  build-time variable).
- API as a **Render Docker web service** built from the repo root
  (`apps/api/Dockerfile`, `content/` baked into the image), plus **Render
  Postgres**, both declared in `render.yaml`. Migrations run in the start
  command (`alembic upgrade head`), which is idempotent.
- Secrets (`INSTRUCTOR_SECRET`, later `LLM_API_KEY`) are typed into the Render
  dashboard (`sync: false` in the Blueprint). Nothing secret is in the repo, CI
  logs, or the web bundle.
- Plan for now: **Render free for both the web service and Postgres**, with an
  external pinger hitting `/health` every 10 minutes (see the runbook).

## Alternatives considered

- One VM with Docker Compose: cheapest per month, but we would own TLS, patching
  and restarts.
- GCP (Cloud Run + Cloud SQL): no 30-60 s cold start and real backups, but more
  setup (billing, IAM) than the schedule allows. Revisit for production.

## Consequences

- **Cold starts.** The free web service sleeps after about 15 minutes without
  inbound traffic, and the first request then takes tens of seconds. The pinger
  keeps it awake but is best effort: if the pinger is down, or Render restarts
  the service, the next visitor still sees a cold start. A single always-on free
  service fits the monthly free instance-hours.
- **No backups, 30-day expiry.** Render's free Postgres has neither backups nor
  an indefinite lifetime. This does **not** meet T-090's "managed Postgres with
  backups" criterion. It is acceptable only for synthetic demo data. Before real
  use, move to a paid Postgres.
- **Preview origins.** Vercel preview URLs change per branch, so CORS accepts an
  exact allowlist (`CORS_ORIGINS`) plus an optional whole-origin regex
  (`CORS_ORIGIN_REGEX`).
- **Storage policy (T-093).** The learner token is kept in `sessionStorage` and
  sent in the `Authorization` header. There are no cookies, so no
  `SameSite`/CSRF surface, and CORS `allow_credentials` stays off.
- CD from `main` to staging and tagged releases to production remain T-092.
