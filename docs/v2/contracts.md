# SIM-TAMY 2.0 — shared contracts for parallel work

Status: binding for all 2.0 streams (ADR-15). Source: `docs/SIM-TAMY_2.0_AI_Updated_Blueprint_v2.1.md`
(task IDs `S0-*`..`S3-*`, `AI-*`, tests `CT-*`, `AI-T*`). Change a contract only in a PR that updates
this file, the code it names, and every consumer.

Already on `main` from the contracts PR (do not redefine): `app/domain/knowledge.py`,
`app/ai/contracts.py`, migration `0006` (+ models in `app/db/models.py`, `app/db/family.py`),
i18n namespace files `apps/web/lib/i18n/v2/*.json`, `apps/web/lib/demo-account.ts` and the
`X-Demo-Account` header in `lib/api/client.ts`.

## 1. Streams, ownership, merge order

| Stream | Blueprint tasks | Owns (create/edit) | Reads only |
|---|---|---|---|
| **A Knowledge** | S0-04, S1-01, S1-03, AI-02a, CT-01..03, CT-13, AI-T07/T08 | `content/knowledge/**`, `content/curriculum/**`, `app/content/knowledge.py`, `app/services/knowledge.py` (`retrieve_claims`), `app/api/v1/knowledge.py`, i18n `knowledge` | family engine |
| **B Golden + AI** | S0-05, S1-04, S1-05, AI-01a/b/c, AI-02b, AI-03a/b/c, AI-EVAL-01, CT-05..07, CT-10/11, AI-T01..T06, T09..T17 | `content/family/gs-*.yaml`, `app/domain/family.py`, `app/engine/family.py`, `app/content/family.py`, `app/services/family.py`, `app/api/v1/family*.py`, `app/ai/**` (new modules + `prompts/v2/`), `eval/v2/`, web `components/family-*.tsx`, route `/simulate/[storyId]`, i18n `lab` | `retrieve_claims` from A |
| **C Institution** | S2-01..S2-05, CT-04, CT-08, CT-09, CT-12, CT-14 | `content/demo/institutions.yaml`, `app/services/institution.py`, `app/api/v1/institution.py`, web `/institution/**`, `/join/[code]`, i18n `institution` | family rooms/report (read) |
| **D Platform IA** | S0-02, LP-01..04, Passport UI (§07), S3-05 | web `/`, `/learn/**`, `/lab`, `/passport`, `/knowledge/**`, nav/layout components, i18n `platform` | APIs of A, B, C |

Shared rules:
- Merge order **A → B → C → D**. Before merging, rebase on `main`, then run `make gen-api` and the
  full gates. `docs/openapi.yaml` is the hand-kept contract (drift-tested): add your paths/schemas in
  your own block and resolve rebase conflicts by keeping both sides. `apps/web/lib/api/schema.d.ts` is
  generated: never hand-merge it, regenerate it.
- Nobody edits `apps/web/lib/i18n/th.json` except to fix an existing key; new strings go to the
  stream's namespace file and are read as `t("<namespace>.<key>")`.
- A stream that needs a DB change beyond `0006` adds `0007+` after rebasing on the latest `main`.
- Legacy routes (`/family`, `/golden`, `/bridge`, `/parenthood`, `/briefing`..`/report`, `/replay`,
  `/instructor`) keep working; D removes them from the top navigation only.
  Submission cleanup (2026-10-29): the standalone recorded-example player is retired;
  `/replay` now permanently redirects to `/lab`. Its entry points are removed from Home,
  the lab and solo practice. Report consequence timelines and deterministic engine replay
  remain available. Static recording APIs and builders remain engineering tools.

## 2. Content files

| File | Owner | Schema | Notes |
|---|---|---|---|
| `content/knowledge/sources.yaml` | A | `list[SourceRecord]` | all 84 catalog records (`rights_status: metadata_only`) + KB sources `S01`..`S40` (`public_web`). Catalog section `S` codes (`S01`..`S20` in the JSON) are stored as **`CS01`..`CS20`** because `S01`..`S40` already name KB sources; every other catalog code is unchanged (`SOURCE_ID` accepts `CSnn`) |
| `content/knowledge/units/<id>.yaml` | A | `KnowledgeUnit` | claim text is our own Thai summary of the KB report → `rights_status: own_summary`, `publish_status: published`, `review_basis: knowledge_base_2026`; every claim has ≥1 locator (`source_id` + section/page) |
| `content/curriculum/paths.yaml` | A | `stages[]` → `objectives[]` | 4 stages (Blueprint §05); objective `{id: OBJ-<STAGE>-NN, title_th, unit_ids, story_ids, dimension}` |
| `content/family/gs-a-*.yaml`, `gs-b-*.yaml` | B | extended `FamilyStory` (§3) | GS-A critical-safety route, GS-B positive Thai-service route; `knowledge_unit_ids` scope the evidence pack |
| `content/demo/institutions.yaml` | C | `orgs[]`, `accounts[]` | `account {id, org_id, display_name_th, role: org_admin|educator|reviewer|learner}`; all labeled demo |

Knowledge unit IDs: `KB-<AREA>-<TOPIC>-NNN`, areas `TM` (Thai midwifery), `ANC`, `IP`, `PP`, `NB`, `BF`,
`RIGHTS`. A loader error (unknown source ID, duplicate ID, objective → unknown unit/story) fails
`make validate-content`.

## 3. Family story extension (B implements, others read)

`FamilyStory` gains optional fields (older stories stay valid):
- `stage: 1..4`, `objective_ids: [OBJ-*]`, `knowledge_unit_ids: [KB-*]`
- `rubric: [{id: discovery|decision|communication|evidence_scope, weight}]`, default 25/35/25/15
  (Blueprint §07 draft weights; test values, not a professional standard)

`FamilyStep` gains `kind: choice | discover` (default `choice`):
- **choice** (existing): learners may type instead of pressing a button. AI-01 maps the text to one of
  `step.choices` or asks to clarify. A non-critical, non-joint step may commit from text (uncertainty
  ≤ 0.25); **`critical` and `joint` steps commit only through the explicit choice/vote buttons.**
- **discover** (new): the role questions a character. Fields: `character_th`, `intents: [{id: ^[A-Z_]+$,
  label_th, examples_th[], reveals: [fact_id], unit_ids: [KB-*], dimension}]`, `min_reveals`.
  Revealed facts join that role's `my_facts` and can be shared as today.
- Choices and intents carry `dimension` for the rubric. Critical Safety stays the existing gate.

Implementation notes from stream B (binding for consumers):
- Intents also carry `reply_th` (authored answer: validator fallback, and the only text when
  `high_risk: true`); a discover step has `abstain_th` and exactly one `continue` choice; a story may
  carry `boundary_th`; a card may carry a three-part `lens {wisdom_th, safety_th, rights_th}`.
  `knowledge_unit_ids` may be unvalidated here: the knowledge stream's validator checks them.
- `ask` events keep the intent ID in `choice_id`; `continue` needs `min_reveals` distinct revealing
  intents. Rubric scores (`score_total`, per-dimension earned/possible) exist only in the finished
  `FamilyReport`; the Critical Safety gate is separate and never averaged.
- `POST /messages` clarification options: on a discover step the client re-sends the option text as
  a new message; on a choice step the client commits through `/decisions`. The retry of an
  already-handled `client_turn_id` returns the current view and the stored reply, if any.
- Pixel scene (LP-01): `FamilyExchange.mood` (`warm | open`) is the coarse reaction to the committed
  choice: `warm` iff the choice has non-empty `skills` and `safe` is true, else `open`. Skills,
  feedback, dimension, `safe` and scores are never exposed during play. `FamilyScene.examples_th`
  lists the first example question of each intent for the current discover step (sample strings only,
  no intent IDs or labels); empty on other steps.
- Pixel stage (LP-01): `FamilyChoice` gains optional display-only `short_th` (non-blank, <= 30 chars, a faithful shortening of that choice's `text_th`) and `icon` (`book|notebook|pot|talk|pause|menu|arrow`). Play-time `FamilyOption` exposes only these two beside `id`/`text_th`; skills, feedback, dimension and `safe` stay hidden. Without `short_th` the web shows `text_th`; the full sentence is always readable before committing. The web's consequence beat uses only `mood`, the committed choice's `icon` and step.
- Pixel stage registry (LP-01): `apps/web/components/pixel/registry.ts` (`PIXEL_STORIES`, `isPixelStory`) is the single list of stories drawn with the pixel stage; each stage PR only adds its id. Co-op stories use the same stage: the dialogue panel starts with a `<details>` "what you know" (role-private brief, my facts with the share action, shared timeline; open while unshared facts remain), the HUD shows partner presence, and the status strip carries the waiting/turn text. No API change.
- `app/ai/evidence.py::evidence_pack` is the only consumer of `retrieve_claims`; with no release it
  returns `release_id="none"` and knowledge answers abstain.

Events (`family_events.kind`): existing `decision | vote | share`, plus `ask` (`choice_id` = intent ID,
`reply_th` = the validated reply that was shown). A decision typed as text is a normal `decision`
event; the text itself is a `family_messages` row. Engine replay stays the only source of state and
score. Event IDs exposed to AI-03 and the UI: `"<room_id>:<idx>"`.

## 4. API (all under `/v1`, standard error envelope)

Migration `0008` adds nullable `archived_at` to classes and assignments. Removal returns 204 and
archives settings instead of deleting evidence. Active counts exclude archived settings; organization
finished-attempt totals and account passports retain their recorded history. Archived cohorts reject
new join-code access, and archived cohorts/assignments reject new room creation. Existing rooms work.

| Route | Verb | Owner | Behavior |
|---|---|---|---|
| `/knowledge/sources` | GET | A | registry, filter `?kind=` |
| `/knowledge/units`, `/knowledge/units/{id}` | GET | A | published units of the current release, with sources resolved (code, title, url, locator) |
| `/knowledge/release` | GET | A | `{id, unit_count}` |
| `/learning-paths` | GET | A | stages → objectives → unit and story IDs |
| `/family/rooms` | POST | B | + optional `assignment_id`; stores `X-Demo-Account` as host account; pins `release_id` |
| `/family/rooms/{id}/join` | POST | B | stores `X-Demo-Account` as partner account |
| `/family/rooms/{id}/messages` | POST | B | `{text, state_version, client_turn_id}` → `{view, reply?, clarification?}`; reply = `{speaker_th, text_th, citations[]}`; idempotent per `client_turn_id` |
| `/family/rooms/{id}/debrief` | POST | B | AI-03 for a finished room; returns stored debrief if one exists for this `debrief_version` |
| `/demo/accounts` | GET | C | mock accounts for the profile picker |
| `/orgs/{org_id}/overview`, `/orgs/{org_id}/cohorts` | GET/POST | C | cohorts of that org only |
| `/cohorts/{id}/clone`, `/cohorts/{id}/assignments` | POST | C | assignable: stories in the catalog (Draft allowed while `ALLOW_DRAFT_CASES=true`) |
| `/cohorts/{id}` | DELETE | C | owning organization's staff only; archive cohort, retain learning evidence |
| `/cohorts/{id}/assignments/{assignment_id}` | DELETE | C | archive only an assignment of that cohort; retain existing rooms and analytics |
| `/cohorts/{id}/analytics` | GET | C | from finished rooms only; every rate shows numerator, `n`, story version; per-objective rates hidden when `n < 3` |
| `/join/{code}` | GET | C | class + active assignments; expired → helpful error (CT-14) |
| `/passport/{account_id}` | GET | C | finished attempts of that account, objectives touched, safety result per attempt (never averaged); `attempts[].strong` (display only) and `lessons: [{unit_id, completed_at}]` |
| `/passport/{account_id}/lessons/{unit_id}` | POST | C | records that the account finished that lesson (table `passport_lessons`, migration 0007; not the `events` log). 200 `{unit_id, completed_at}`; repeating it changes nothing and returns the first time. Unknown unit (not in the current release) or unknown account: 404 `NOT_FOUND` |

C implementation notes (exact shapes are in `docs/openapi.yaml`, tag `Institution`): staff routes read `X-Demo-Account` (missing or unknown: 401; not educator/org_admin of that org: 403; another org's cohort: 404). `GET /cohorts/{id}/assignments` also exists. `join` errors: unknown code `CLASS_NOT_FOUND` (404), expired assignments `SESSION_EXPIRED` (410). Analytics replay finished rooms through the family engine; `objectives[].numerator` counts finished attempts that met the Critical Safety gate for stories carrying that `objective_id`, and is `null` with `suppressed: true` when `n < 3`. `score_total` is null until the family report exposes it.

`X-Demo-Account` is trusted as-is (prototype). Play-time responses keep AGENTS rule 5: no revealed
fact IDs, scores or partner-private data before the report.

## 5. AI pipeline (B)

Schemas: `app/ai/contracts.py`. Prompts: `app/ai/prompts/v2/{intent,grounded_reply,debrief}.md`, each
starting with a `prompt_version:` line. Every call goes through `LLMClient` and writes `llm_calls` with
`capability` (`ai01|ai02|ai03`), `prompt_version`, `schema_version`, `validation_status`,
`fallback_reason`, `release_id`, `room_id`; never raw text.

1. **Input boundary:** length cap, rule-based real-world health guard (`REAL_WORLD_HEALTH_QUERY` →
   boundary text from content, no roleplay reply).
2. **AI-01:** prompt gets the step's allowed intent/choice IDs, this role's last 6 messages and
   revealed topics; output `IntentInterpretation`. Unknown IDs dropped; uncertainty ≤ 0.25 accept,
   ≤ 0.5 clarify (show the allowed options as buttons), else ignore. Never a state change by itself.
3. **Controller (engine):** decides reveals/transitions from the accepted intent.
4. **AI-02:** `retrieve_claims(release, unit_ids, care_stage, audience, tags) -> EvidencePack`
   (A owns; deterministic filter then tag ranking, ≤ 5 items). Generator gets allowed facts + pack,
   returns `GroundedReply`. Validator: existing patient rules + `used_scenario_fact_ids ⊆ allowed` +
   every citation `pack.cites(...)`. Critical steps use content templates (`high_risk_template`).
   No support → abstain text from content. 2 failures → fallback, citations hidden.
5. **AI-03:** input = finished assessment + event evidence + allowlists; output `DebriefOutput`;
   readonly score/safety overwritten from the scorer; any unknown event/objective/claim/asset ID →
   template debrief. Stored in `family_debriefs`.

Mock provider must cover every path so CI stays offline. Eval set `eval/v2/` (≥60 paraphrase, ≥20
multi-turn, ≥20 ambiguous/out-of-scope, ≥20 adversarial; separate held-out file) with `make eval-v2`;
results reported only as measured (AGENTS rule 11).

## 6. Web routes

| Route | Owner | Content |
|---|---|---|
| `/` | D | family home: 4 pillars, continue where you left off, profile picker |
| `/learn`, `/learn/[stage]` | D | Learning Journey: stage cards → objectives → lesson units → linked scenarios |
| `/lab` | D | Simulation Lab: GS-A, GS-B first, then other stories and solo cases |
| `/simulate/[storyId]` | B | room for any family story (typed chat, discover, share, vote, report, debrief) |
| `/passport` | D | Learning Passport from `/passport/{account_id}` |
| `/knowledge`, `/knowledge/[id]` | D | readable units with Thai Wisdom Lens and sources |
| `/institution/**` | C | Overview, Cohorts, Assignments + QR, Analytics, Curriculum Library, Staff (demo) |
| `/join/[code]` | C | QR landing → assignment → `/simulate/[storyId]?assignment=` |

Demo data is labeled on screen (AGENTS rule 9). Mobile-first 360px, the existing a11y audit applies.

## 7. Out of scope (prototype)

Real auth, passwords, SSO, billing, white-label, tenant hardening, PDF export beyond print/CSV,
pilot study, buyer interviews, EMR/HIS, AI-generated curriculum.

### Focused family learning path (LP-01..04)

`apps/web/lib/learning-path.ts` curates navigation priority only. Stage 1 links
`thai-elements-family`, stage 2 `thai-birth-conversation`, stage 3 GS-A and GS-B,
and stage 4 `thai-milk-family`. API availability still controls every link.
`golden-first-night` remains a follow-up; other family stories, role-specific
solo cases and instructor tools remain accessible through collapsed sections
in `/lab`. Existing routes, sessions, objective progress and scoring are unchanged.
The knowledge index combines preconception and antenatal references into one
navigation group and collapses the source registry; unit detail metadata and
citations retain their original meaning. This does not retire or approve content.

### Ready registry (LP-01, LP-04)

`apps/web/lib/learning-path.ts` (`CORE_PATH`) is the single list of what learners can open: one lesson and one
scenario per stage (stage 1 `KB-TM-ELEMENT-001` + `thai-elements-family`, stage 2 `KB-IP-HERITAGE-001` +
`thai-birth-conversation`, stage 3 `KB-PP-WARN-001` + `gs-a-postpartum-warning`, stage 4 `KB-BF-COLOSTRUM-001` +
`thai-milk-family`). `unitReady()` / `storyReady()` gate the stage page, lab, knowledge index and unit page, home,
join-code assignments, the story routes and the course tabs. Everything else is listed greyed out with an availability
label (not a review label, rule 9) and direct URLs show a notice. `NEXT_PUBLIC_SHOW_ALL_CONTENT=true` opens everything
(dev, CI and the e2e web servers). Content, APIs, sessions and scoring are unchanged.

### Adding a stage to the pixel mode (LP-01)

Each stage is one lesson plus one scenario (`lib/learning-path.ts`). A stage PR touches only its own files:
- `components/pixel/art/scene-stageN.ts`: backdrops (also add `pixelSim.backdrop.<key>`), table/scene props (`ITEMS`, `ITEM_OF`: choice icon to prop) and knowledge-card slots; drawing helpers live in `art/draw.ts`.
- `components/pixel/art/lesson-stageN.ts`: 96x64 illustrations (helpers in `lesson-draw.ts`) and `unit id -> kind per claim`.
- `components/pixel/cast.ts` (your story's entry only): who plays mother and father and which backdrop each step kind uses. The player's own character stands on the left; when the speaker is that character the partner stands there instead.
- `components/pixel/scene-art.ts`: only to refine a character look (`LOOKS`) or add a choice icon. Choice icons are an enum in `FamilyIcon` (domain/family.py), `docs/openapi.yaml` and `schema.d.ts`: book, notebook, pot, talk, pause, menu, arrow, phone, baby, house, heart, help.
- `components/pixel/registry.ts` (your `STAGEN` block only): add the story id and the unit id. The nursery-house zone for that stage opens when both are registered.
- `lib/i18n/v2/pixel-sim-stageN.json`: `name` (speaker keys) and `backdrop` (backdrop keys); merged into `pixelSim` by `lib/i18n/index.ts`.
- Content: `hotspots` on each claim and `short_th` / `icon` on each choice.
Speaker names map to sprites through `pixelSim.name.<key>` (`characterOf` in `scene-view.tsx`); a new speaker needs a `name` key and an entry in `characterOf`. Stage PRs do not edit this file; describe changes in the PR body.

### Pixel nursery house and end-of-chapter reveal (LP-03)

`/learn` renders a code-drawn "บ้านต้อนรับลูก" with four open stage zones, each backed by its lesson/scenario
pair in `CORE_PATH` and the pixel registry. Items come only from `GET /passport/{account_id}`: each zone's
scenario item needs a finished attempt for that zone's story and upgrades when a finished attempt is `strong`;
the lesson item fills when `lessons` contains that zone's unit. The pixel lesson posts the completion when the learner finishes the cards and the
sort game (best effort: a failed call neither blocks the lesson nor stores anything locally; no call without a
picked mock profile). No local storage is used.

`strong` is derived on the server from the attempt's replayed choices: every decision step ended on an option
that carries a non-empty `skills` list (scripted `discover` steps only continue, so they do not count). It is
display only, post-completion, never in play views, and scoring, rubric and `safety_status` do not read it, so a
`strong` attempt can still be `SAFETY_NOT_MET`.
`FamilyEvidence` in the finished `FamilyReport` (post-completion only, never in play views) gains
`skills`, `dimension`, `critical`, `kind` so the web reveal can replay each choice. The three meters are a
visual reflection, not a score; scoring, rubric and `safety_status` are unchanged.

Lesson hotspots (LP-01, additive): a `KnowledgeClaim` may carry `hotspots: [{id: ^h\d+$, label_th, text_th}]`
(ids unique per claim, label/text non-blank). Each is a short, faithful shortening of its own claim's
`text_th` (label 1-3 words, one plain sentence) shown in the pixel lesson's tap-to-learn sheet; provenance is
the claim's `locators`. `GET /v1/knowledge/units/{id}` returns them as `claims[].hotspots` (default `[]`).
