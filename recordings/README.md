# Replay snapshots

`dev001-engineering.json` is generated from the synthetic DEV-001 engineering fixture by
`python -m scripts.build_dev_replay` (run inside `apps/api`). Its score and findings come
from the deterministic engine. It is **not** a clinical case and must never be used for a
real product demo. It is retained for engineering tests and excluded from the learner
gallery. Do not export real patient data or unreviewed learner free text.

The public replay API is disabled in application defaults. Compose, `.env.example`,
and the Render Blueprint explicitly enable it with `ENABLE_REPLAY=true`.
An existing deployment with an explicit false override must set `ENABLE_REPLAY=true`.

The six `*-example.json` files are synthetic learning examples built by
`make build-course-replays` from the existing content-owned golden conversations.
Patient lines pass through the same Generator/Validator/fallback path using the canned
generator; reports are computed by the real deterministic engine. No live learner text,
real patient data, or live LLM calls are used. Case status remains Draft in their data;
these examples do not assert expert approval. The learner gallery excludes DEV-001.
