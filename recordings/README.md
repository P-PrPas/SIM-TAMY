# Synthetic engineering snapshots

The learner-facing recorded-example gallery has been retired. `/replay` redirects to `/lab`.
These snapshots and their API/build tools remain available for deterministic engineering
checks. They are separate from report consequence timelines and engine event-log replay.

`dev001-engineering.json` is generated from the synthetic DEV-001 engineering fixture by
`python -m scripts.build_dev_replay` (run inside `apps/api`). Its score and findings come
from the deterministic engine. It is **not** a clinical case and must never be used for a
real product demo. It is retained for engineering tests and excluded from recording listings.
Do not export real patient data or unreviewed learner free text.

The public replay API is disabled in application defaults. Compose, `.env.example`,
and the Render Blueprint explicitly enable it with `ENABLE_REPLAY=true`.
An existing deployment with an explicit false override must set `ENABLE_REPLAY=true`.

The six `*-example.json` files use authored dialogue from
`content/examples/dialogues_th.yaml` (58 learner/patient exchanges). Run
`make build-course-replays` to rebuild them without a database or LLM. Playback also
only reads static JSON; it never invokes a model.

The compiler checks each question against the existing golden action sequence,
case version, allowed fact references, newly revealed facts and hard patient Validator.
It fails on invalid dialogue rather than replacing it with generic canned replies.
Measurements are displayed as system observations using the exact newly allowed fact,
not phrased as something the patient says. Reports still come from the deterministic
engine; all six reports and their metadata are unchanged by this dialogue revision.

No live learner text or real patient data is used. Case status remains Draft in their
data; authored wording does not assert expert approval. DEV-001 remains excluded from
recording listings and its engineering snapshot is unchanged.
