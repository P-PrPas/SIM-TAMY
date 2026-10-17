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
decision for the other role. Each response contains only its caller's private
brief, the current scene and shared past exchanges. Feedback, source references
and competency counts are returned only once the story is complete.

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

The existing Generator duty can choose between the selected reply's authored
wording alternatives. It receives only the grandmother persona, chosen learner
utterance and those allowed replies. An exact allowlist validator rejects every
other output; after at most two regenerations or a provider failure the canonical
script is used. No unrestricted AI conversation or clinical synthesis is claimed.
Co-op and Parenthood remain fully scripted and make no LLM calls. Mock mode works
without a key; real provider behaviour/latency still needs explicit validation.

Migration `0004` adds a nullable reply column. Earlier events fall back to their
pinned script. New exchanges persist the accepted wording and LLM call metadata
in the decision transaction; retries and reads never regenerate a response.
Only choice IDs drive the deterministic report. Retention also removes unlinked
family LLM metadata. Expert review of all new scenarios remains outstanding.
