# Evidence

`prototype-status-matrix.csv` lists each module and capability with a status:
WORKING (tests pass, no LLM needed), MOCK (passes only with the mock LLM, real-model quality unmeasured),
PARTIAL, MISSING, NOT_TESTED. Each row names the test file or make target behind it.

To verify or regenerate a row (needs Postgres: `docker compose up -d db`, or any server in `DATABASE_URL`):

```
make test                # api (pytest + engine coverage gate) and web (vitest)
make validate-content
make leakcheck
make eval                # also: make eval-pp001, make eval-parents (mock LLM unless PROVIDER=env)
make test-e2e-live       # browser journeys; not part of the matrix run
```

Update a row's status only from a run you saw. Without Postgres the integration tests skip, and a
skipped test is not evidence. The safety scenarios are mapped in `docs/security/safety-test-matrix.md`.
