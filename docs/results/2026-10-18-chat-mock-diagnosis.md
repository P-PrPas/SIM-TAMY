# Repeated patient reply: diagnosis and validation

## Observed failure

On 2026-10-18, the deployed web bundle pointed to `https://sim-tamy-api.onrender.com`.
Its public `/health` reported provider `mock` and commit `5217d87`. Two synthetic
DAD-001 questions taken verbatim from the course's A01 and A03 examples returned
the identical `smalltalk` entry in `ai/prompts/canned_th.yaml`; `degraded` was false.
No production token or conversation is included here. Synthetic QA sessions remain
subject to the normal retention policy; no historical events were edited or deleted.

## Experiment ledger

1. Read the deployed public provider name, not local defaults: confirmed `mock`.
2. An initial PowerShell pipe corrupted Thai input to question marks; that probe
   was discarded as evidence of recognition failure. Repeated the probe using
   UTF-8 YAML-loaded question strings, which reproduced the same response.
3. Trace: unscripted mock Interpreter returned a valid empty Action list. Thus no
   exception triggered `match_actions`, no facts unlocked, and the turn directive
   was `deflect_smalltalk`. Mock Generator returned constant smalltalk regardless
   of the question. This explains the false non-degraded success.
4. Disproof check: an allowed-fact request through the actual Generator and hard
   Validator rejected the mock smalltalk, then returned the content fallback.
   Thus the Validator was not universally rejecting relevant answers; the
   unscripted provider's behavior caused both failures. Explicit scripted rules
   still work and must retain precedence.
5. Regression tests failed before the fix: unscripted Interpreter did not signal
   fallback, and mock Generator did not answer the supplied allowed fact.
6. Fix: absent structured mock rule raises the existing nonretryable provider
   error, invoking the existing lexical fallback and logging the fallback event.
   Default mock generation reads only the turn's allowed facts and directive.
   The hard Validator, regeneration budget, safety gate and engine are unchanged.
7. Targeted validation: 227 AI/turn tests passed, including real HTTP routes on
   PostgreSQL with the unscripted Mock provider, production Generator/Validator,
   and two distinct content questions for each of six clinical courses.
   Golden T01–T10 passed in mock mode; all 128 web tests passed.

## Why existing tests missed it

Most HTTP tests supplied a scripted Interpreter and a canned voice. They verified
the engine and transport contracts but bypassed the deployed unscripted combination.
The new six-course HTTP regression removes that voice override and uses the actual
unscripted Mock provider, checking that questions unlock facts and produce relevant
non-smalltalk replies. Provider tests now distinguish explicit empty scripts from
missing rules instead of requiring the broken implicit-empty success.

## Deployment limitation

This patch improves offline fallback; it does not connect a real model or change
Render's environment. Live AI chat requires server-side provider/model configuration
and a post-deployment check. No real-provider quality, cost or latency is claimed.
