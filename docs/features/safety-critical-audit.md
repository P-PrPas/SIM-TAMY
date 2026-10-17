# Critical-action audit (FR-SCR-02/05, T-053)

The deterministic critical gate already exists. This feature makes its per-item
results visible in the completed report summary, even when the total is high.
Each critical item shows its rubric ID, competency, engine finding, and event/turn
evidence. Empty evidence is explicitly shown as absent, never inferred.

The top-level effective safety status remains authoritative. When an instructor
override exists, the audit explicitly identifies its rows as original engine results.
No scoring, clinical content, case schema, or play-time response is changed.

Validation: web tests, TypeScript, and lint; backend/content checks use the existing
Makefile targets. The component regression uses a synthetic high-score failure.
