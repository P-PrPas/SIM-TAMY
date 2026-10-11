<!--
Code PR template. Content-only PR (content/**)? Use ?template=content.md in the PR URL.
Rules: one concern per PR, <= ~400 changed lines (lockfiles excluded), Conventional Commit title,
e.g. `feat(engine): unlock hidden facts (FR-ENG-02, T-021)`. Never push directly to main.
-->

## Summary

<!-- 1-3 sentences: what changed and why. -->

## Tickets / FR IDs

<!-- e.g. T-021, FR-ENG-02. Link ADRs or PRD sections if relevant. -->

## Areas touched

- [ ] `engine/` / `domain/` (pure: no network, LLM, randomness, clock)
- [ ] `ai/` or prompts (Interpreter / Generator / Validator / Debrief)
- [ ] `api/` / `db/` / migrations
- [ ] `apps/web`
- [ ] CI / Docker / tooling
- [ ] Docs / ADR

## What I ran

<!-- Paste the real commands and outcome. If something was not run, say so and why. -->

| Command | Result |
|---|---|
| `make lint` | |
| `make test` | |
| `make validate-content` | |
| `make eval` (if `engine/`, `ai/`, `content/`, or prompts changed) | |

## Definition of Done

- [ ] Lint, type-check, and relevant tests pass; new behavior has new tests
- [ ] No Thai string literals outside `lib/i18n/th.json`, `content/`, `ai/prompts/`
- [ ] Works from a clean `docker compose up`
- [ ] Docs / PRD / ADR updated if config, endpoint, schema, or a contract changed

## Safety rules (AGENTS.md, non-negotiable)

Tick what applies; write `N/A` for what does not.

- [ ] Engine stays deterministic; re-scoring from the Event Log gives identical results
- [ ] LLM is used only to interpret, phrase a reply, or phrase a debrief. It never scores, transitions state, or decides safety status
- [ ] Generator receives allowed facts only (no whole case, hidden facts, or rubric in prompts)
- [ ] No leak during play: no `revealed_fact_ids`, `risk_state`, detected `actions`, hidden facts, or scores in play-time responses or the frontend
- [ ] Rejected replies are never shown or streamed; fallback utterance after 2 regenerations
- [ ] Critical Safety stays a gate: any failed `critical` item means `SAFETY_NOT_MET`, and the UI never shows "pass" wording then
- [ ] `events` is append-only (no UPDATE / DELETE)
- [ ] Case status badge and "education only" banner present on every user-facing content surface
- [ ] No clinical content in code or prompts; no real patient data; no secrets or learner free text in logs
- [ ] No hard-coded metrics; tests, thresholds, and `eval/golden/*` were not weakened to get green

## Needs a human decision? (ask first)

- [ ] Changes an ADR, or the Case / Rubric schema
- [ ] Edits or squashes a migration that may hold data
- [ ] Changes scoring semantics or Critical Safety rules
- [ ] Adds a new LLM duty or a new dependency (reason: )
- [ ] Touches `content/cases/**` (outside content tooling or the `DEV-001` fixture)

## Screenshots / recordings (UI changes)

<!-- Mobile (>= 360px) and desktop. Never include hidden state or scores from an active session. -->

## Risks, rollout, and follow-ups

<!-- What could break? How to roll back? Leave `TODO(content):` notes for the Content team here. -->
