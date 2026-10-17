# Measured validation dashboard (T-070, FR-SCR-04, FR-VAL-01)

`/validation` displays a dated snapshot of four measured offline regression groups:
lexical paraphrases/dev-set, deterministic rescoring, critical decisions, and
Generator/Validator consistency boundaries. It is not a real-provider benchmark,
clinical validation, complete golden evaluation, or evidence of expert approval.

Run `make build-validation-report` after changing the assessed engine, AI, content,
or regression tests. The standard-library runner executes pytest and reads JUnit
outcomes; failed, errored, skipped and missing results cannot become passes. The
download includes timestamp, base source revision and SHA-256 of assessed sources.
The recorded source revision precedes committing the generated artifact; the
fingerprint identifies the measured code. The page explicitly labels a snapshot,
so its date must be reviewed before presenting it as current evidence.

CI regenerates and uploads a separate measured artifact; it does not rewrite the
committed/deployed snapshot. Commit a fresh report to publish updated measurements.
No learner transcript, credentials, or live LLM call is included in the output.
