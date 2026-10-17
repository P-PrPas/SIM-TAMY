# Latency and concurrency check (T-074)

- Measured: 2026-10-17T09:58:30+00:00
- Concurrent learners: 20, turns each: 6, requests: 200, wall clock: 45.6 s
- Server: provider `openai_like`, version `0.1.0`, commit `unknown`
- Errors (non-2xx or no answer): 0 of 200 (0.0%); status codes: 200: 180, 201: 20
- Turn p95 7888 ms against the PRD 1.3 target of 8 s: met
- Latency is client wall clock, including network. Per-LLM-call numbers: `make stats`.

| Step | Requests | Errors | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| create session | 20 | 0 | 1886 | 1959 | 1965 |
| turn | 120 | 0 | 6235 | 7888 | 12278 |
| decision | 20 | 0 | 618 | 1651 | 1828 |
| complete | 20 | 0 | 3920 | 5270 | 5548 |
| report | 20 | 0 | 35 | 742 | 802 |
