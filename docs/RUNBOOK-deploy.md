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

`render.yaml` already carries the GLM-5.3 settings (`LLM_BASE_URL`, `LLM_MODEL_*`, `LLM_REASONING_EFFORT`,
`LLM_TIMEOUT_S`) with `LLM_PROVIDER=mock`. To go live, in the Render dashboard type the `LLM_API_KEY` value
and change `LLM_PROVIDER` to `openai_like`; the key is never put in `render.yaml`. Set `LLM_PROVIDER` back to
`mock` to fall back to the deterministic provider.

Use a key from the standard Z.ai API, not a GLM Coding Plan key: the Coding Plan is limited to Z.ai's
supported coding tools and its keys are not interchangeable (docs.z.ai/devpack/quick-start), so the base
URL is `https://api.z.ai/api/paas/v4`, not `/api/coding/paas/v4`. Locally: `cp .env.glm.example .env`, then
fill `LLM_API_KEY`.

## Not covered here

CD from `main`/tags (T-092), image hardening (T-091), rate limiting and security headers (T-048),
production smoke test and rollback (T-094).
