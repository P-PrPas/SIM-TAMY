# Deploy runbook: Vercel (web) + Render (API, Postgres)

Decision and limits: [ADR-14](adr/ADR-14-hosting-vercel-render.md). Tickets: T-090, T-093.
You do the account steps; the repo already holds the Blueprint (`render.yaml`) and image.

## 1. API and database on Render

1. Render dashboard -> New -> **Blueprint** -> connect `P-PrPas/SIM-TAMY`, branch `main`.
   It reads `render.yaml` and creates `sim-tamy-db` (free Postgres) and `sim-tamy-api` (free web service).
2. When asked for the `sync: false` values, enter:
   - `INSTRUCTOR_SECRET`: a long random string you generate (keep it in your password manager, never in git or chat).
   - `CORS_ORIGINS`: leave a placeholder for now; set it in step 3.
   - `CORS_ORIGIN_REGEX`: placeholder for now (optional).
3. Wait for the first deploy. Expected: the service shows **Live**, and
   `curl https://<service>.onrender.com/health` returns `"status":"ok"`, `"db":"ok"`, `"cases_loaded"` of at least 1.
   The first call after a sleep can take tens of seconds.
4. Note the date the database was created: **free Postgres expires after 30 days** and has **no backups**.

## 2. Web on Vercel

1. Vercel -> Add New Project -> import the repo. Set **Root Directory** to `apps/web`.
2. Environment variable `NEXT_PUBLIC_API_URL` = `https://<service>.onrender.com` (public, build time; no secrets).
3. Deploy. Vercel serves HTTPS on `https://<project>.vercel.app`.

## 3. Connect them (T-093)

1. Render -> `sim-tamy-api` -> Environment:
   - `CORS_ORIGINS` = `https://<project>.vercel.app`
   - `CORS_ORIGIN_REGEX` (only if you want preview deployments to work) = `https://<project>-.*-<vercel-team>\.vercel\.app`
2. Save; Render redeploys. If `NEXT_PUBLIC_API_URL` ever changes, redeploy the web project too (it is baked in at build time).
3. Browser check (acceptance for T-093; needs the Join/Briefing/Chat flow of PR #17 on `main`,
   until then the web has only the landing page): open the Vercel URL over HTTPS, join with a case, send a message,
   commit the decision, complete the session and open the report. DevTools -> Network: no CORS errors.
   Preflight check from a terminal:
   `curl -si -X OPTIONS https://<service>.onrender.com/health -H "Origin: https://<project>.vercel.app" -H "Access-Control-Request-Method: GET"`
   must contain `access-control-allow-origin: https://<project>.vercel.app`.

## 4. Keep the API awake (the link may be opened at any time)

Render's free web service sleeps after about 15 minutes without traffic. Use any external monitor
(UptimeRobot, cron-job.org, a GitHub Actions cron) to call `https://<service>.onrender.com/health`
**every 10 minutes**. This is best effort: if the monitor stops, or Render restarts the service,
the next visitor can still wait through a cold start. Before sending the link:

- open `/health` yourself and confirm `ok`;
- check the monitor shows recent successful pings;
- check the database creation date is less than 30 days ago.

## 5. Storage and cookie policy (T-093)

The learner token is in `sessionStorage` and sent as `Authorization: Bearer ...`. There are no cookies,
so there is no `SameSite`/CSRF surface and the API does not enable CORS credentials. Both platforms
redirect HTTP to HTTPS. Secrets are only in the Render dashboard.

## 6. Switching to a real LLM later

Add `LLM_API_KEY` (and `LLM_PROVIDER`, `LLM_MODEL_*`, `LLM_BASE_URL`) in the Render dashboard; never in
`render.yaml`. Set `LLM_PROVIDER` back to `mock` to fall back to the deterministic provider.

## 7. The API image (T-091)

One image (`apps/api/Dockerfile`, built from the repo root) runs everywhere: `docker compose`, Render
staging and production. Its contract:

- `CMD` runs `alembic upgrade head`, then `uvicorn` on `$PORT` (8000 locally). Migrations are idempotent,
  so a restart is safe, and a failed migration stops the container before it serves traffic.
- It runs as the non-root user `app` (uid 10001); `HEALTHCHECK` calls `/health`.
- `content/` and `recordings/` are baked in; there are no secrets in the image (all come from env).
- Checked from an empty database: `docker compose up --wait db api`, then `/health` is `ok` and
  `POST /v1/sessions` returns 201.

## 8. Smoke test (T-094)

`python scripts/smoke.py https://<service>.onrender.com [--wait 120]` plays one learner journey (health,
case list, create session, one turn, decision, complete, report) and exits non-zero at the first broken
step, naming it. Use `--wait` for a sleeping free instance. CI runs it against `docker compose` from an
empty database on every PR. It creates one synthetic session named `smoke`; with a real LLM provider the
turn makes a few real LLM calls. Run it after every production deploy and before sharing the link.

## 9. Rollback (T-094)

1. **Code:** Render dashboard -> `sim-tamy-api` -> Deploys -> **Rollback** on the last good deploy -> "Rollback
   to this deploy". It reuses that deploy's build artifact, so it is fast. Limits from Render's docs:
   it works only while that build artifact is still retained, and a dashboard rollback **turns autodeploy
   off** for the service; turn it back on in Settings once the fix is on `main`. The docs do not say
   whether free instances can roll back: if the button is missing, redeploy the previous tag instead
   (re-run the release workflow's deploy for the old tag, or "Manual Deploy" -> a specific commit).
2. **Check:** run the smoke test against the service.
3. **Database:** a rollback does **not** undo migrations, and the free Postgres has no backups. So every
   migration must be additive while a release is live (add nullable columns/tables; drop or rename only
   in a later release), so the previous image still works on the newer schema. If a release shipped a
   destructive migration, there is no automatic way back: restore from your own dump, or recreate the
   database and re-run `alembic upgrade head` (sessions are lost; content is in the image).
4. **After:** write down what broke and which tag is live. `/health` returns `version`.

## Not covered here

CD from `main`/tags (T-092), rate limiting and security headers (T-048).
