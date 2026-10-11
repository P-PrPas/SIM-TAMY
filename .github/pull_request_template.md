## Summary

<!-- What changed and why. Keep PRs <= ~400 lines, one concern each. -->

## Tickets / FR IDs

<!-- e.g. T-001, FR-OBS-01 -->

## What I ran

- [ ] `make lint`
- [ ] `make test`
- [ ] `make validate-content` (and `make eval` if `engine/`, `ai/`, `content/`, or prompts changed)

## Checklist

- [ ] Engine untouched by LLM / network / time; re-score is still deterministic
- [ ] No hidden facts, risk state, or scores leaked in play-time responses or the frontend
- [ ] No clinical text in code or prompts; Thai strings only in i18n / content / prompts
- [ ] New behavior has tests; docs / ADR updated if a contract changed
- [ ] No secrets, no real patient data
