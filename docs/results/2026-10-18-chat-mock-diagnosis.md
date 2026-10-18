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
8. Full API suite: 777 passed against isolated PostgreSQL. After the user supplied
   a screenshot, the exact DAD-001 pain question was added to the HTTP regression;
   all six course cases passed again, including the expected pain fact and reply.

## Why existing tests missed it

Most HTTP tests supplied a scripted Interpreter and a canned voice. They verified
the engine and transport contracts but bypassed the deployed unscripted combination.
The new six-course HTTP regression removes that voice override and uses the actual
unscripted Mock provider, checking that questions unlock facts and produce relevant
non-smalltalk replies. Provider tests now distinguish explicit empty scripts from
missing rules instead of requiring the broken implicit-empty success.

## Deployment limitation

This patch improves offline fallback; it does not connect a real model or change
Render's running environment. No real-provider quality, cost or latency is claimed.

## Operator follow-up: previously working live provider

The operator confirmed that the key/models were already configured and live chat
previously worked. Git history shows `LLM_PROVIDER: mock` in the Blueprint since
`7a85fd2`; `e2b2504` later edited that Blueprint to enable replay. There are no
changes to provider selection, turn routing, image startup or web API routing
between `6fed131` and deployed `5217d87` (the latest #78–#85 feature stack).

[Render's Blueprint specification](https://render.com/docs/blueprint-spec) says
Blueprints can modify existing environment variables, whereas `sync: false`
variables are ignored on subsequent updates. A Blueprint sync is therefore a
plausible overwrite path. Without Render Environment/sync history, this is not
proof of which deployment changed the value. Public health proves only the
current provider is mock, not when or why it changed.

The Blueprint now uses `sync: false` for provider selection, with a regression
test that failed against the hard-coded value and passes after the change.
This prevents subsequent Blueprint overwrites but does not restore a value already
changed to mock. The operator must restore `LLM_PROVIDER=openai_like` on the actual
API service and redeploy, retaining the existing key, base URL and model values,
then verify health and a live synthetic chat. No credential needs to be re-entered
if it remains configured. Existing development/mock defaults remain unchanged.
