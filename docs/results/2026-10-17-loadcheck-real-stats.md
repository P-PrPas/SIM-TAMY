# Real-provider load check: LLM-side numbers (T-074)

Two runs of `scripts/loadcheck.py` (20 concurrent learners, 6 turns each, DEV-001) against a local API with
`LLM_PROVIDER=openai_like`, model `glm-5.3`, `LLM_REASONING_EFFORT=low`, `LLM_TIMEOUT_S=30`:
[run 1](2026-10-17-loadcheck-real.md), [run 2](2026-10-17-loadcheck-real-run2.md).

| Run | Errors | Turn p50 | Turn p95 | PRD 1.3 target (8 s) |
|---|---|---:|---:|---|
| 1 | 1 of 200 (a `409` on `report`; cause not investigated) | 6038 ms | 9387 ms | not met |
| 2 | 0 of 200 | 6235 ms | 7888 ms | met by 112 ms |

Two runs, one machine, one provider account: the p95 sits on the target and is not a stable pass.

`make stats` (`python -m app.stats stats`), `openai_like/glm-5.3` rows only. The database also holds mock rows from
earlier work, which are left out. These rows cover both runs plus two 1-session smoke runs.

| Purpose | Calls | Errors | p50 ms | p95 ms |
|---|---:|---:|---:|---:|
| interpreter | 124 | 0.0% | 2302 | 4017 |
| generator | 124 | 0.0% | 2209 | 3209 |
| debrief | 22 | 0.0% | 3420 | 3865 |

Tokens for those rows (`make cost-report`): prompt 414,225, completion 25,687. No price table is configured, so no
cost is claimed.

Not measured here: the share of turns that fell back to a canned line on the real provider. The fallback counter
(`turns with a fallback`) mixes mock and real turns in this database, so it is not quoted.

Setup note: with Python 3.14 on Windows, `httpx2` + `truststore` raised `RecursionError` on every real call. Setting
`SSL_CERT_FILE` to the `certifi` bundle avoided it. CI runs Python 3.12 and is not affected.
