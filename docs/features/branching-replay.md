# Decision-to-consequence replay (FR-REP-01, T-054)

Branch rules and pressure phases already run in the deterministic engine. This
feature exposes the actual terminal branch, decision/phase/unsafe event trace and
keyboard-operable scene navigation after completion. It uses only the stored
case-authored outcome script; it does not invent an alternate clinical outcome.
Missed-opportunity markers remain visible below the replay.

Referral does not imply that the safety gate was met: the top-level report keeps
the independent safety result. No case, scoring, branch or schema is changed.

Validation: web tests and TypeScript; existing engine replay/pressure tests verify
that different decisions and yielding under pressure reach different scripts.
