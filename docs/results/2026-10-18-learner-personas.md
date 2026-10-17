# Learner relationships, examples, and presentation update

The product owner requested removal of learner review labels and education disclaimers,
repair of the example gallery, and course-specific patient personas on 2026-10-18.
These display changes do not approve draft content or change scoring semantics.

## Diagnosis and evidence

1. A regression calling the shipped replay endpoints with default configuration returned
   404. The existing enabled/disabled endpoint tests passed (2 tests), distinguishing
   the feature flag from a broken reader. Replay was disabled by default in Settings,
   Compose, and `.env.example`, with no enabling setting in the Render Blueprint.
2. The only shipped snapshot was DEV-001, which the learner gallery deliberately filters.
   Enabling the flag alone would therefore have left an empty gallery.
3. Course-persona regressions showed that relationship context was missing in most variant
   styles. The generator only received short wording instructions; the displayed patient
   profile, which described the learner as a husband, was not passed to it. Passing that
   entire profile/case would violate the allowed-facts boundary.
4. The generator prompt had no explicit learner relationship or addressing rule, and the
   validator did not reject an invented professional title. New regressions verify the
   relationship metadata in the generated prompt and the three-attempt/fallback path for
   an incorrect title. Mentioning a doctor as a third party remains allowed.

## Implementation

- Each of the six course files now names the character's relationship, self-reference,
  way of addressing the learner, and tone for both A and C. The two father courses use
  wife/husband conversation, the two mother courses use close-friend conversation, and
  PP-001/STF-002 use client/staff conversation. Staff is not assumed to mean doctor.
- Chat and example speaker labels also use wife/friend for the corresponding course,
  with neutral conversation labels for input and loading feedback.
- `VoiceRequest.learner_audience` carries only trusted audience metadata. The Generator
  still receives allowed facts only, not the full case, rubric, hidden facts, or prior
  patient answers. Learner text cannot redefine the relationship.
- The hard validator detects configured, unverified medical forms of address. Failure
  uses the existing regeneration and validated fallback path. Engine/scoring are unchanged.
- Course versions advance to 0.2; only titles and persona wording changed. Parsed comparison
  with the previous commit confirmed that all other case fields are identical, including
  clinical facts, safety rules, scripts, and branch rules. Actions/rubrics/golden expectations
  were not edited.
- Six static examples are reproducibly generated from existing golden conversations with
  the lexical matcher, real engine, canned Generator, and real Validator. No live LLM,
  patient data, or learner transcript was used. Snapshot reports are engine-produced.
- Replay is explicitly enabled in deployment configuration; application defaults remain
  disabled. Existing deployments that set `ENABLE_REPLAY=false` must change that setting
  to true. Transient gallery failures
  now have a retry action.
- Learner screens omit status badges and disclaimers; instructor tools and exports retain
  actual status. Course-title review suffixes were removed. PRD and AGENTS document this
  explicit owner decision.
- `brand.scope` was removed. `banner.educationOnly` is intentionally retained solely as
  the exact wording used by negative UI regression checks; no learner component renders it.

## Initial validation

- Backend pytest: 527 passed, 172 database-dependent tests skipped; engine coverage 99%.
- Ruff lint/format and mypy: passed.
- All seven content cases passed strict validation; exported schemas and leakcheck passed.
- Frontend unit tests: 84 passed.
- Browser suite: 22 passed against Prism/mocked session data, including mobile axe,
  responsive layout, motion, and playback of the shipped examples. Five chat/example checks
  were rerun after the final course-label changes and passed.
- The accessibility run exposed transient low text contrast during fade-in. Entrances now
  preserve text opacity while moving into place; an axe regression freezes the hero at the
  first animation frame and verifies its contrast. No accessibility gate was weakened.
- TypeScript and production build passed. ESLint has one pre-existing unused-variable warning.
- GNU make is absent; target commands were run directly using the repo virtual environment
  and npm scripts. The required mock golden evaluation was attempted but could not start:
  PostgreSQL rejected the standard local test account. No golden result is claimed.
- Real-provider conversation quality and deployment are unverified. Restart training after
  deployment to use the new version; open sessions remain pinned to their previous content,
  and an old pinned version may be unavailable after an API restart.

## Senior review follow-up

- Addressed review items 2–8; the owner explicitly excluded the content-approval objection.
  No case content or snapshots changed in this follow-up.
- Reproduced three missed whitespace vocatives before fixing the shared Validator rule.
  The regression table covers all five reviewer examples and a spaced third-person mention.
  Neutral title matching requires a word ending after whitespace to preserve doctor mentions
  embedded in a sentence; direct vocatives also match after whitespace.
- Restored replay's disabled application default and full instructor Draft badges, with
  regression coverage. Deployment flags remain explicitly enabled.
- Replay assembly now receives its session ID and description from callers. Course snapshot
  equality tests confirm that deterministic recording output is unchanged.
- Shared the patient speaker label helper, removed six JSX gaps and unused `brand.scope`,
  and documented the retained negative-test banner wording above.
- Backend: 533 passed, 172 PostgreSQL-dependent skips; engine coverage 99%. Focused persona,
  Validator, course recording, and replay API tests: 56 passed.
- Frontend: 89 unit tests passed; TypeScript passed; ESLint has the same existing warning.
- Browser suite: 22 passed against Prism/mocked data, including accessibility and examples.
- Ruff lint/format, mypy, strict validation of seven cases, schema drift, and leakcheck passed.
- Local mock golden evaluation was attempted again; the local PostgreSQL test account still
  fails authentication. Real-provider conversations remain unverified.

## Local artifacts

Task-owned pytest scratch and Playwright artifacts were removed after verification,
including those remaining from the prior frontend work. Pytest directory symlinks were
unlinked before deleting their containing scratch directories. Existing user changes in
AGENTS.md, `.agents/`, `apps/api/.pytest-merge-check/`, and `docs/logo/` remain intact.
