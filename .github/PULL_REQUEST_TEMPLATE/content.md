<!--
Content PR template (Content team). Only touch `content/**` in this PR.
CI runs `validate-content` automatically.
Open with: <repo>/compare/main...<branch>?template=content.md
-->

## What changed

<!-- Case ID(s) and files, e.g. PP-001: case.yaml, actions.yaml. -->

## Why

<!-- New case, correction, new source, review feedback, etc. -->

## Case status

- Current status: <!-- Draft / In Review / Approved -->
- Status after this PR: <!-- Draft / In Review / Approved -->
- Clinical reviewer (name / role): 
- Review date: 

## Content checklist

- [ ] Every clinical item has a `source` (`make validate-content STRICT=1`)
- [ ] Status field is correct and matches the review above
- [ ] Every hidden fact has `leak_terms_th` and `fallback_utterances_th`
- [ ] Every decision option is referenced by a branch rule, and every branch path reaches `COMPLETED`
- [ ] Action IDs referenced in `case.yaml` / `rubric.yaml` exist in `actions.yaml`
- [ ] Synthetic data only: no real patient information
- [ ] Only `content/**` is changed (no code, prompts, or tests)

## What I ran

| Command | Result |
|---|---|
| `make validate-content` | |
| `make validate-content STRICT=1` | |
| `make eval` (if rubric or actions changed) | |

## Open questions for engineering

<!-- Anything the schema or tooling could not express. -->
