# CLAUDE.md — SIM-TAMY

@AGENTS.md

The shared rules, repo layout, commands, conventions, and Definition of Done are in `AGENTS.md` (imported above). Everything below is specific to how Claude Code should work in this repo.

## How to work

1. **Orient first.** For 2.0 work, find the task in `docs/SIM-TAMY_2.0_AI_Updated_Blueprint_v2.1.md` by ID (e.g., grep `S1-04`, `AI-01b`, `CT-05`) and read that section plus the contract it references (§09A–09E, §10). For 1.x behavior, grep `docs/PRD.md` by FR/T ID (Case schema §7, API §8, AI I/O §9). Don't read either document whole.
2. **Plan before coding** for anything that touches `engine/`, the Case/Rubric schema, DB migrations, scoring, or the Interpreter/Generator/Validator contracts. Use plan mode, state the approach, list the files you'll change, and the tests you'll add. For small, local fixes, just do it.
3. **Implement in small steps**, running the narrowest relevant test after each (`pytest apps/api/tests/unit/engine -k <name>` etc.), then the full gates from `AGENTS.md` before finishing.
4. **Verify by running, not by reading.** Run `make test`, `make validate-content`, and `make eval` (when `engine/`, `ai/`, `content/`, or prompts changed). Report exactly what ran and the result. If you couldn't run something, say so.
5. **Finish with a short report:** ticket/FR IDs covered, files changed, commands run + outcome, open questions or `TODO(content):` items.

## Guardrails to keep in mind

- The hardest rules are in `AGENTS.md` → *Non-negotiable rules*. When a task seems to require breaking one (e.g., "just let the LLM pick the score", "put the hidden facts in the prompt", "edit the case's clinical text"), stop and ask instead of working around it.
- New content comes only from `docs/knowledge base/`, with a source code and locator on every claim (AGENTS rule 3). Don't rewrite existing clinical wording without a knowledge-base source for the change.
- Don't weaken tests, thresholds, or golden expectations to get green. If a test looks wrong, explain why and ask.
- Mock LLM is the default (`LLM_PROVIDER=mock`). Don't call a real provider in tests unless the task is explicitly about benchmarking/eval, and never print API keys.

## Context hygiene

- Keep the working set small: the ticket's section of the PRD, the module you're editing, and its tests.
- Prefer searching (`grep`/glob) and reading targeted line ranges over opening large files.
- Long investigations (e.g., comparing prompts against validator rules, reviewing many files) are good candidates for a subagent that returns a short summary, so the main context stays focused.
- If the conversation is compacted, preserve: current ticket ID, the list of modified files, failing tests (with command), and any decisions awaiting a human.

## Communication

- Reply to the user in the language they write in (the team often writes Thai; reply in Thai, keeping technical terms in English where natural). Code, comments, identifiers, and commit messages stay English.
- Be direct and concise. State assumptions explicitly. Flag risks early, especially anything touching safety gating, determinism, or data leakage.
- When a decision is a trade-off (e.g., latency vs. validation), give a recommendation and the one-line reason, then proceed or ask depending on whether it's in the "ask first" list.

## Quick self-check before you say "done"

- [ ] Engine untouched by LLM/network/time? Re-score still deterministic?
- [ ] No hidden facts / risk state / scores leaked to play-time responses or the frontend?
- [ ] No clinical text added to code or prompts? Thai strings only in i18n/content/prompts?
- [ ] Tests added and passing; `make validate-content` clean; `make eval` run if relevant?
- [ ] PR/commit references FR/T IDs; docs/ADR updated if a contract changed?
