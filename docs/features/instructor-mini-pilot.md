# Instructor mini pilot (FR-INS-02/05, T-055)

The existing instructor mode already provides class-scoped individual reports and
cohort analytics. This adds voluntary post-completion feedback, class-level measured
averages, report links and JSON export. Roles are self-reported, not verified credentials.
Counts represent responding training sessions, not unique people or market adoption.

## Run a real pilot

1. Deploy migration `0002` with `make migrate` before releasing the new frontend.
2. Create a dedicated pilot class in instructor mode and share its class code with
   invited learners/instructors/practitioners. Use pseudonyms and synthetic cases only.
3. Ask participants to complete a session and voluntarily submit ratings/comments on
   the completed report. Do not supply answers or invent feedback for absent users.
4. Open the class's feedback panel, inspect individual reports, and export the actual
   feedback. Keep a separate record of invitations, research context and follow-up
   actions; do not treat per-session ratings as a representative market survey.

No real pilot was conducted by engineering. Recruitment and expert review remain
human work; this feature provides collection and review tools only.

## Data and release contract

- `POST /v1/sessions/{session_id}/feedback`: learner Bearer token, completed own session,
  explicit consent; 1–5 strict integer ratings and optional sanitized comment ≤500 chars.
  One immutable response per session; identical retries return the original receipt,
  changed retries return `IDEMPOTENCY_CONFLICT`. Feedback never changes scores/events.
- `GET /v1/instructor/feedback?class_code=…`: existing instructor secret, class-scoped
  totals/averages and newest 100 responses. Empty averages are null. Export explicitly
  includes only those newest responses; aggregates include all responses in the class.
- New `pilot_feedback` table references sessions with `ON DELETE CASCADE`, so existing
  session retention removes feedback too. No learner name, transcript or API secret is
  copied into feedback. Comments are stored only in the database and authorized exports.
- Migration is additive. Do not downgrade `0002` on a deployed database with collected
  feedback without a separate human data-loss decision.

Tests cover consent/input limits, own-session authorization, completion, idempotency,
class isolation, empty metrics, retention and client retry behavior. Local PostgreSQL
is unavailable; migration and integration verification run against disposable CI DBs.
