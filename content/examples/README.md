# Authored learning examples

`dialogues_th.yaml` is presentation wording for the six static gallery examples.
Husband/wife, close-friend and client/staff dialogue is written for each course.
Clinical facts remain in `content/cases/`; the dialogue only paraphrases those facts
and adds non-clinical conversational acknowledgments. Unknown details stay unknown.

- `case_version` pins the wording to the case version; review it when a case changes.
- Turns correspond one-to-one with the selected golden conversation's learner turns.
  Rephrasing must preserve the exact detected action sequence and all assessment data.
- `fact_ids` declares the current turn's allowed facts used by the patient reply.
- `observation_fact_ids` moves a newly allowed measurement into a system observation.
  The compiler copies its text directly from the source fact and validates both the
  observation and patient reply. No clinical measurement is invented.
- Support/acknowledgment turns may omit fact IDs. Do not add symptoms, treatments,
  timings, reassurance about safety, or outcomes absent from the case.

Run `make build-course-replays` then tests. All dialogue is validated before any
snapshot is written. No model call or canned fallback is used. This changes neither
case review status nor clinical approval, and does not change the live-chat generator.
