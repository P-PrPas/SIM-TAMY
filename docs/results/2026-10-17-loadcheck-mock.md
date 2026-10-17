# Latency and concurrency check (T-074)

- Measured: 2026-10-17T06:07:16+00:00
- Concurrent learners: 20, turns each: 6, requests: 200, wall clock: 17.7 s
- Server: provider `mock`, version `0.1.0`, commit `unknown`
- Errors (non-2xx or no answer): 0 of 200 (0.0%); status codes: 200: 180, 201: 20
- Turn p95 3029 ms against the PRD 1.3 target of 8 s: met
- Latency is client wall clock, including network. Per-LLM-call numbers: `make stats`.

| Step | Requests | Errors | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| create session | 20 | 0 | 2729 | 2779 | 2788 |
| turn | 120 | 0 | 1717 | 3029 | 3335 |
| decision | 20 | 0 | 960 | 1404 | 1487 |
| complete | 20 | 0 | 1319 | 1506 | 1578 |
| report | 20 | 0 | 918 | 1194 | 1200 |

## Context of this run

- Local machine, one `uvicorn` process (default settings) on Postgres 16 in Docker, `LLM_PROVIDER=mock`, case `DEV-001`. The numbers measure the application, database and locking, not a real model. **The real-provider run (the second half of T-074) has not been done**: it spends the provider key and may hit the provider's own rate limit, so it waits for an explicit go-ahead.
- A first run with the same arguments, made a minute earlier and not saved, gave a turn p95 of 1383 ms and 9.0 s wall clock against 3029 ms and 17.7 s here, so a single run is not a stable figure. Re-run before quoting a number.
- The slowest step under 20 simultaneous learners is `create session`, not the turn.

## `make stats` after two runs of 20 x 6 on this database (240 turns, so both runs)

```
purpose      provider/model                calls  err%   p50ms   p95ms
debrief      mock/mock-model                  40 100.0       0       0
generator    mock/mock-model                 240   0.0      38     119
interpreter  mock/mock-model                 240   0.0       0       0
turns with a fallback: 0 of 240 (0.0%); fallback events by component: none
```

The debrief row is the template path: the mock provider has no rule for the structured debrief request (`mock_no_rule`), so each debrief call is logged as an error and the report uses the template. It is not a production error rate.
