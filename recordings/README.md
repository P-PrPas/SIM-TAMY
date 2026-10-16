# Replay snapshots

`dev001-engineering.json` is generated from the synthetic DEV-001 engineering fixture by
`python -m scripts.build_dev_replay` (run inside `apps/api`). Its score and findings come
from the deterministic engine. It is **not** a clinical case and must never be used for a
real product demo. Replace it with a Content-approved synthetic case recording before a
public demonstration. Do not export real patient data or unreviewed learner free text.

The public replay API is disabled by default. Set `ENABLE_REPLAY=true` only when the
recordings directory contains reviewed, synthetic snapshots.
