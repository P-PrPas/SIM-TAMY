# ADR-13: JSON object mode with application schema validation

Status: Accepted (owner approval, 2026-10-14).

## Context

PRD section 9.1 originally required provider-enforced JSON Schema. The first
`openai_like` provider uses JSON object mode and cannot enforce that schema.

## Decision

Prefer provider-enforced JSON Schema when available. For this provider, permit
JSON object mode with the schema in the system prompt and mandatory Pydantic
validation in `LLMClient.complete_structured` before returning a result.
Malformed envelopes or schema-invalid results raise `LLMInvalidResponse`; each
attempt is recorded. Retry once, then the interpreter caller uses its specified
fallback. Text calls also reject missing, blank or non-string content.

## Consequences

JSON object mode does not guarantee schema compliance. No accuracy, latency or
valid-output-rate claim follows from this exception; measure them with the bench
and eval harnesses when implemented. This changes only the output enforcement
mechanism, not interpreter post-processing, allowed facts, scoring, state
transitions, or the three permitted LLM duties.
