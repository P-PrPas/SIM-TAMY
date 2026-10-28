# Demo playbook: live script, fallback tiers, pre-stage checklist (C05)

For the Final round. Everything here is something the repo can do today; where a step is not
verified on the real stage setup it says so. UI labels are the Thai strings from
`apps/web/lib/i18n/th.json`. SIM-TAMY is an education simulator: say that out loud once, early,
and never describe a score as a pass or as a certification of competence.

## 1. The 7-minute golden path

Rehearse on the same devices and network you will use. Device 1 is the laptop on the projector
(solo, then the family host). Device 2 is a phone at 360 px width (the family partner).
The browser flows below are what `make test-e2e-demo` automates, so the click path is known to work
against a local API + PostgreSQL with the mock LLM.

| Time | Do | Say / point at |
|---|---|---|
| 0:00 | Open the web URL on device 1. | The problem in one sentence: learners must recognise red flags and stop and refer. This is practice, not a medical device. |
| 0:30 | Choose case `PP-001`, variant A, nickname `DEMO`, press "ไปเตรียมพร้อมก่อนฝึก", then "เริ่มสนทนา". | A synthetic patient; no real patient data anywhere. |
| 1:00 | Chat: ask the blood-loss and dizziness questions (the same wording as `eval/golden/pp001/T11.yaml`, items 5 and 6). | The patient only reveals facts the learner actually unlocked. Nothing about risk or score is shown while playing. |
| 2:30 | "ตัดสินใจ" -> choose refer -> "ตรวจทานการตัดสินใจ" -> "ยืนยันการตัดสินใจ" -> "จบเคสและดูรายงาน". | The decision is committed through the panel, not guessed from chat. It is irreversible. |
| 3:15 | Report: show the safety banner first. Then the tab "เบื้องหลังการเรียนรู้" (facts, what was never asked, learner actions). | Critical Safety is a gate, not a score: a failed critical item can never read as passing. The score and findings come from the deterministic engine; the language model only phrases text. |
| 4:00 | Tab "ภาพเหตุการณ์จำลอง": step through the scenes with the next-scene button. | The consequence of the decision, scripted by the content team. |
| 4:30 | Device 1: open "ฝึกเป็นครอบครัว" -> pick a role -> "สร้างห้องฝึก" -> "คัดลอกลิงก์เชิญ" and send the link to device 2 (the app has no QR; make one outside it, see section 3). Device 2: open the link, "เข้าร่วมห้อง". | Two phones, two roles, each sees only its own private information. |
| 5:15 | Alternate choosing a reply and pressing "ยืนยันคำตอบและคุยต่อ" on each device (four decisions in the shipped story). | Turn-taking is enforced by the server; refresh keeps the room. |
| 6:15 | Both devices land on "สิ่งที่ครอบครัวได้เรียนรู้" with sources. | The report shows observed behaviours in this activity, not readiness to parent. |
| 6:45 | Close: honest limits (section 5) and the next step. | Do not quote a metric that is not in `docs/results/` (section 5). |

If anything stalls for more than ten seconds, go to the next tier (section 2) without apologising
at length; say which tier you are on.

## 2. Fallback tiers

State the tier you are on. Never present a lower tier as a higher one.

| Tier | What | When to drop to it | Label to say |
|---|---|---|---|
| A | Live, two devices (solo + family co-op) on the deployed API. | Default. | "Live." |
| B | Live, solo only (the section 1 solo path), one device. Skip the family minutes; if time remains, open the in-app example gallery ("ดูตัวอย่างการฝึก", `/replay`). | The second device, Wi-Fi to the phone, or the family room fails. | "Live, solo only." |
| C | Pre-recorded video of the golden path, plus the in-app example gallery served from static recordings. | The API is unreachable or cold-starting past patience, or the venue network is down. | "This is a recording, not a live system." Put that caption on the first frame and say it. |

Notes:

- The example gallery (`/replay`) plays static JSON from `recordings/`. It needs no database and no
  language model, but it still needs the API process that serves it. The recordings are authored
  examples (`content/examples/dialogues_th.yaml`), not live learner sessions; say so.
- The recorded video for tier C is **not in the repo**. Record it yourself from the tier A run, keep
  the file on the laptop (not only in cloud storage), and keep the caption.
- Offline stack on the laptop (no Docker, no network provider): `make demo` runs the API and web
  with `LLM_PROVIDER=mock` and `ENABLE_REPLAY=true` (see `scripts/demo.sh`). The mock provider is a
  limited offline exercise: unmatched wording can get a generic reply (RUNBOOK section 6). The
  engine, report and safety gate are the same code as with a real model.
- Switching the deployed API between real and mock: Render dashboard -> `sim-tamy-api` ->
  Environment -> `LLM_PROVIDER` = `mock` (or `openai_like` with the keys already stored there),
  then confirm `llm_provider` in `/health` (RUNBOOK section 6). Never paste a key into chat or the repo.

## 3. Pre-stage checklist

Do this the evening before and again 30 minutes before going on.

URL and SSL

- [ ] Open the final web URL on the stage devices over HTTPS; no browser warning, no mixed content.
- [ ] `https://<api>/health` shows `"status":"ok"`, `"db":"ok"` and the `llm_provider` you intend to show.
- [ ] CORS: the prestage check below includes the preflight from the web origin.
- [ ] QR code of the web URL (and of the family invite page) printed or on the phone; test a scan from the stage distance.

Server warm-up (Render free tier cold start)

- [ ] Render free web services sleep after about 15 minutes idle; the first request can take tens of seconds (RUNBOOK section 4). Hit `/health` repeatedly from 15 minutes before the slot, or run `make prestage ... WAIT=120`, which prints how long the first answer took.
- [ ] Confirm the keep-awake monitor shows recent pings and the free database is under 30 days old (RUNBOOK section 4).

Check script (read-only; creates no session or room)

```
make prestage URL=https://<api> WEB_URL=https://<web> WAIT=120
```

It prints PASS/FAIL for API health (with the cold-start time), web reachable, case list, family stories,
the replay gallery and CORS, and exits non-zero on any FAIL. It prints no tokens or keys.

Data and reset

- [ ] Reset the demo class on a **demo** database only: `make demo-reset DEMO_DB=1` (deletes and re-seeds the `DEMO01` class and nothing else; refuses without the flag). Do not run it against a database holding data you care about.
- [ ] Open `/instructor` with the secret from your password manager; the class `DEMO01` shows five synthetic sessions.

Devices and venue

- [ ] Fonts: the Thai font is bundled in the web app (`apps/web/app/fonts`), so no font download is needed; still look at one Thai screen on each device.
- [ ] API quotas: if you will show a real model, check the provider's remaining quota and rate limit that day; otherwise run with `mock` and say so.
- [ ] Battery above 80 percent and chargers plugged in; do-not-disturb on; notifications off; browser zoom 100 percent; phone brightness up.
- [ ] Both devices on a network you tested; a phone hotspot as a second path.
- [ ] Recorded video (tier C) on the laptop disk, and the `make demo` stack tested once offline.

Last deploy

- [ ] After the final deploy, run the critical path once against the production URLs: `python scripts/smoke.py https://<api> --wait 120 --expect-sha <deployed commit>` (RUNBOOK section 8) and click the section 1 path by hand. `make test-e2e-demo` starts its own local stack and cannot target the deployed site.
- [ ] Freeze: no deploys in the last hour before the slot.

## 4. Offline and recorded-mode verification (what was actually run)

On 2026-10-26 the repo's `make test-e2e-demo` flow ran with `LLM_PROVIDER=mock` and `ENABLE_REPLAY=true`
and opened a shipped example from the replay gallery after the solo journey. That exercises the static
recordings path with no model. It was run on a developer laptop against a local PostgreSQL, not on the
stage network or the Render deployment. See the PR description for the exact results.

The spec starts `next dev`, and on a few runs (all right after a fresh dev-server start) the example
gallery list did not render within the retry window, so the spec is not flake-free. For the stage use a
production build (`npm run build` then `npm start` in `apps/web`), not `next dev`.

## 5. Release notes and limitations (say these honestly)

- **Draft content.** Case content (for example `PP-001`) is a draft supplied by the Content team and
  has not been clinically reviewed. Learner screens deliberately omit review badges and education
  disclaimers (product owner decision, 2026-10-18); the real review status stays in the data and in
  the instructor tools. Do not describe any case as expert-approved.
- **Mock versus real language model.** With `LLM_PROVIDER=mock` the patient wording, action matching
  and debrief come from a deterministic offline provider (a lexical fallback), which is a limited
  exercise and not free-form AI chat. With a real provider the wording is model-generated, still
  gated by the Validator. Scoring, state transitions and the safety gate never use a model.
- **No pilot data.** No study with real learners has been run. There is no accuracy, learning-gain
  or pass-rate claim, and none should be made.
- **Measured numbers that exist** (`docs/results/`, single runs, 20 simulated learners, 6 turns each,
  the files describe their own environment and say a single run is not a stable figure):
  2026-10-17 `loadcheck-mock`: 0 of 200 requests failed, turn p95 3029 ms with the mock provider;
  2026-10-17 `loadcheck-real-run2`: 0 of 200 requests failed, turn p95 7888 ms with `openai_like`.
  Quote them only with those dates and caveats, or not at all.
- **Hosting.** Free-tier API and database: cold starts, a 30-day database expiry and no backups
  (RUNBOOK sections 1 and 4).
- **Education tool, not a medical device.** It never diagnoses, recommends treatment or certifies
  competence. A "safety met" result means the simulated case's critical items were met, nothing more.
- **Family co-op.** The shipped co-op story is the current `first-night` story. The joint-decision
  and `golden-first-night` story from Sprint B are not covered by this script until they merge; update
  section 1 and the e2e fixme then.
