# Family learning simulations

## Family Co-op (FR-FAM-01)

`/family` is a two-device, turn-based room for the authored `first-night` story.
The creator chooses a role and shares a fragment-only invitation link. The second
participant receives the other role. Invitations grant that role once; a retry
with the same participant token is idempotent. Keep the link private. Role tokens
stay in each browser's sessionStorage and only hashes are stored server-side.
Opening a fresh tab requires its invitation or retained session; closing the
browser can lose access. Rooms are retained for `LOG_RETENTION_DAYS` and the
existing purge CLI removes old rooms and their events by cascade.

The API polls every three seconds. This is asynchronous turn-taking, not a live
chat service. A database row lock serializes joining and decisions. Optimistic
`state_version` prevents stale decisions; `client_turn_id` prevents duplicate
events. Decisions are inserted only, never edited. Neither role can submit a
decision for the other role. Event `idx` starts at 1; `state_version` starts at 0.
Each response contains only its caller's private
brief, the current scene and shared past exchanges. Feedback, source references
and competency counts are returned only once the story is complete.

Story references were rechecked at version 1.2 against directly read guidance sections;
see [the claim-level source map](research/family-reference-recheck.md). New rooms use
the new references. Existing rooms retain their original story/reference snapshot,
so start a new round to verify updated sources after deployment. Historical reports
and event logs are not rewritten. Reference provenance does not approve Draft content.

The four competencies count observed authored choices / opportunities. These are
formative indicators within this activity, not a validated readiness scale.
Any missed critical help-seeking checkpoint yields `SAFETY_NOT_MET`, even if all
other choices support the family. These new exercises do not modify clinical
Case/Rubric scoring, existing patient sessions or existing golden expectations.

## Content authoring

`content/family/*.yaml` is content-owned and validated by `make validate-content`
alongside existing cases. Stories are pinned as full JSON when rooms are created,
so an update cannot change an ongoing session's feedback. New schema lives in
`app/domain/family.py`; existing Case and Rubric schemas are unchanged.

- `roles`: separate private role briefings, never send the whole story to clients.
- `steps`: ordered role turns, authored dialogue, choices, feedback and citations.
- `skills`: explicit content-authored indicators, not inferred from keywords.
- `critical` + choice `safe`: independent help-seeking gate.
- `flags` + later `prompt_if`: authored memory of earlier choices. Flags cannot
  reference future steps. Neither flags nor future choices are returned live.
- `sources`: HTTPS references with a bounded summary and evidence category.

All new stories are **Draft** pending qualified clinical, cultural and educational
review. No expert approval or user pilot is claimed. Authoring research is in
`docs/research/family-simulations.md`. Learner screens follow the product decision
to omit review badges; real review status remains pinned in server-side content.
Dialogue is original synthetic writing and choice-led, not an unrestricted chat.
Never invent a clinical outcome or claim that a good family choice prevents an
illness, guarantees sleep, or predicts the family's future.

## API and deployment

Contracts and generated frontend types: `docs/openapi.yaml`.

- `GET /v1/family/stories`: descriptions only, no private briefs or scoring.
- `POST /v1/family/rooms`: story ID and creator role; returns token and invitation.
- `POST /v1/family/rooms/{id}/join`: invitation and caller-generated opaque token.
- `GET /v1/family/rooms/{id}`: bearer token, role-isolated resumable view.
- `POST /v1/family/rooms/{id}/decisions`: bearer token, version, choice and UUID.

Migration `0003` creates separate room/event tables. Standard Docker startup runs
it automatically. No new package, service or credential is required. Requests
use the standard error envelope; token/brief responses are `no-store`.

## 100 Days of Parenthood (FR-FAM-02)

`/parenthood` is the three-chapter MVP: before birth, the first night home, and
family pressure. It is a solo, choice-led story with a scripted family partner;
either parent role can play every turn. Individual rooms reject invitations to
another participant. No new migration is required: mode and choices are pinned
in the same story/event contracts.

Earlier choices set content-owned flags. Later prompts explicitly recall an
unmade plan or missing support network; making a new plan changes the later
conversation again. This is authored narrative continuity, not a prediction of
clinical outcomes or a real-time 100-day health tracker. All 64 paths are tested
for both parent roles. Reload resumes the event-derived position and narrative.
Future chapter titles are public, but future dialogue, flags and feedback remain
server-side. The final report uses the same independent safety gate and citations.

## Generational Bridge (FR-FAM-03)

`/bridge` offers four complete, original three-turn stories: อยู่ไฟ, herbal
compresses, postpartum food, and herbal products while breastfeeding. Each has a
distinct grandmother motivation, a respectful listening choice, a verification
choice and a critical consent/help-seeking decision. Sources identify cultural
context, institutional guidance and limited evidence separately. Classification
documents establish practice names, not efficacy; an inconclusive trial is not
presented as proven benefit. No procedure, dosage or individual clearance is given.

All three family experiences use their content-authored canonical replies directly.
Family decisions make no LLM calls, including while the room row is locked.
Persona and alternative wording remain content metadata for editorial review;
they do not trigger generation or clinical synthesis.

Migration `0004` adds a nullable reply column. Earlier events fall back to their
pinned script. New exchanges persist the canonical wording in the decision transaction;
retries and reads never regenerate a response. Previously persisted wording is
retained for existing rooms.
Only choice IDs drive the deterministic report. Retention also removes unlinked
family LLM metadata. Expert review of all new scenarios remains outstanding.

## Co-sim: joint decisions, shared facts, presence, knowledge cards (Sprint B)

All additions are optional in the story schema, so existing stories and pinned rooms are unchanged.

- **Joint decision (B03).** A step with `joint: true` needs both roles. `POST /decisions` is reused:
  each role's choice is stored as a `vote` event. A role never sees the partner's vote before
  casting its own. If the two votes match the decision locks and the story advances; if not, the
  scene reports `vote.disagreement` (both choices, only after both voted) and both vote again.
  Never random. `state_version` counts all events except one pending vote, so the partner's
  vote does not make the other role's view stale. A `critical` joint step feeds the same
  Critical Safety gate.
- **Share fact (B02).** `facts[]` (id, role, text, skills) are content-defined items from a role's
  private brief. `POST /shares {fact_id, client_turn_id}` appends a `share` event. Only the
  owning role may share a fact; the API returns the caller's own `my_facts` and the `shared_facts`
  timeline, never the partner's unshared facts. Re-sharing is a no-op. A `prompt_if` key
  `fact:<id>` recalls a shared fact. Skills (including `shared_decision`) are counted from events.
- **Presence (CO-03).** Migration `0005` adds `host_seen_at` / `partner_seen_at` (updated on GET,
  share and decision). The view exposes only `partner_online` (seen within 10 s), no timestamps.
- **Knowledge cards (B05).** A step may carry `card` (tradition, learning point, `evidence_status`
  one of `traditional_practice | supported_by_guidance | insufficient_evidence | caution`,
  precautions, when to consult, source IDs). The UI renders an expandable card for the current
  step. The four bridge stories now carry cards; their dialogue is unchanged.
- **Golden story.** `golden-first-night` is the featured entry (`/golden`, linked from the home
  page); the other modules stay separate. Research notes: `docs/research/golden-first-night.md`.
  It is Draft, gives no diagnosis or treatment, and claims no expert review.

Event kinds: `decision`, `vote`, `share` (column `family_events.kind`, default `decision`).
