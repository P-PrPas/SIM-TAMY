"""Fixed session limits (PRD FR-SES-03, openapi `Limits`). Constants: they never vary."""

MAX_TURNS = 40
MAX_TEXT_CHARS = 500
IDLE_TIMEOUT_S = 1800
MAX_RATIONALE_CHARS = 300
MAX_NOTE_CHARS = 500
MAX_BODY_BYTES = 65536  # the largest legitimate request is a few KB of JSON
PRESSURE_MAX_TURNS = 2  # learner turns allowed in the pressure scene (FR-ENG-05)
