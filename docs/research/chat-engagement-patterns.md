# Chat-preserving engagement patterns

Research date: 2026-10-18. Scope: brainstorm only; no product implementation or clinical-content approval.

## What was verified

First-party public documentation and illustrated product descriptions were opened and read. Authenticated lessons, mobile apps, embedded games, and subscription features were not played. A documented feature is evidence that a platform describes that interaction, not evidence that the interaction will improve SIM-TAMY outcomes. Availability can differ by platform, language, subscription, and rollout. No vendor efficacy percentages are adopted here.

| Platform | Verified interaction pattern | Primary source and boundary |
|---|---|---|
| Duolingo Adventures | A defined real-world task, recurring characters, movement around a scene, object interaction, dialogue choices, and clarification inside the story rather than only external correction. | [Adventures product article](https://blog.duolingo.com/adventures/), especially “What are Adventures?”, “Don’t be afraid to make mistakes”, and “Dive into the story”. An official illustrated description; no direct app session performed. |
| Duolingo Roleplay / Video Call | Scenario conversations with characters; feedback after Roleplay; a character-focused call view and later transcript. Duolingo says humans write Roleplay scenario setup and opening messages. | [Max product article](https://blog.duolingo.com/duolingo-max/) and [Video Call article](https://blog.duolingo.com/video-call/). Useful presentation precedents; neither justifies adding unrestricted AI or voice to SIM-TAMY. |
| Brilliant | Visual models and hands-on problems interleave explanation and immediate feedback. Its tutor offers stepwise help rather than simply revealing an answer. | [Official FAQ](https://brilliant.org/faq/), “What is Brilliant?”, “What is Koji?”, and “How does learning on Brilliant work?”. Public description only. Its broad efficacy claim is not evaluated or reused. |
| Labster | Narrative context, moment-to-moment decisions, practice tasks, quiz questions, feedback, and opportunities to retry. | [Official engagement page](https://www.labster.com/solution/engagement), “Boost Student Engagement”. This is a marketing page; the interaction description is useful, but vendor outcome metrics are not evidence for our audience or implementation. |
| H5P Branching Scenario | Authored choices control subsequent content, branches, and endings; text, images, hotspots, and video can be combined. | [Official type documentation](https://h5p.org/branching-scenario), description and features. Its page also lists a nursing home-visit example. This verifies the supported format, not clinical validity of our stories. |
| H5P Interactive Video | Questions/resources appear inside video, can pause it, and can route to another segment; bookmarks and final interactive summaries are supported. | [Official type documentation](https://h5p.org/interactive-video), description and features. A short illustrated scene could borrow the interruption pattern without requiring video production or the H5P dependency. |

## Six proposed applications

Everything below is a SIM-TAMY design hypothesis, not a feature claim about another platform or a promised learning benefit. Existing family artwork, chapter progress, role briefings, and history disclosures already provide a foundation; the proposals extend those elements rather than relabeling them as new.

### 1. A small stage above the chat — first priority

Borrow the scene-and-character framing of Duolingo Adventures. Keep chat as the main interaction, but show an illustrated setting and the current speaker: a living room at night, the same family the next morning, or a grandmother visiting. A chapter transition changes the scene; a new line briefly highlights its speaker. On mobile the stage becomes a shallow, collapsible strip rather than pushing the conversation below the fold.

Thai application: “คืนแรกที่บ้าน” as an authored scene title, with mother/father/grandmother portraits that persist across chapters. The hypothesis is stronger orientation and character attachment. Do not infer facial distress or relief from hidden risk, correctness, or a model's emotion guess. Expressions must be explicitly authored, public story cues, otherwise remain neutral.

### 2. A conversation rhythm: read, act, hear the response — first priority

Borrow short applied tasks from Brilliant and narrative decisions from Labster. Interleave a few chat exchanges with a clearly signposted decision moment, then return immediately to the character's response. Use existing choices as larger action cards, with a separate explicit commit control. A shared-household planning task can let players assign content-approved task cards to roles, with equivalent tap/select controls instead of mandatory dragging.

Thai application: a “แผนของคืนนี้” card that records the players' own agreed responsibilities. This is not a second scoring system or a medical recommendation. New task mechanics or scoring need separate design approval; existing choice-based tasks can initially remain unchanged underneath the presentation.

### 3. Earned story moments, without correctness meters — first priority

Borrow authored branching presentation from H5P. After a committed decision or chapter boundary, show a compact visual story beat and a transition button. Use only the public consequence text already allowed at that moment. A chapter map can show where the family is in the story, not unrevealed future branches.

Thai application: a brief “เช้าวันถัดมา” transition using the same family illustration, followed by chat recalling an earlier, visible agreement. No live “family happiness”, “baby safety”, or correctness gauges. Those would invent outcomes or leak assessment and could pressure real parents.

### 4. Two-player presence through an agreement card

Combine scenario task framing with our existing Co-op roles. Give each participant an explicit “อ่านแล้ว / พร้อมคุยต่อ” acknowledgement and a shared summary of the decisions actually committed. Show who is expected to act, rather than falsely claiming a participant is online. Do not reveal the other role's private brief.

Thai application: “เราตกลงกันว่า…” with only public choices and voluntary acknowledgements. This exact feature is our proposal, not a verified feature of the researched platforms. The hypothesis is clearer cooperation and less passive waiting. It needs synchronized state design, not simulated presence animation.

### 5. Optional voice for authored dialogue — later

Borrow the character presence of Duolingo Video Call, without recreating its live generative call. A small play button can read the currently visible, approved family line using recorded audio. Chat text remains complete and immediately readable; no automatic audio, forced listening, microphone permission, or artificial typing delay.

The hypothesis is greater emotional presence and accessibility choice. It adds recording, versioning, and content-review work; therefore test a visual stage first. This does not require restoring the removed grandmother LLM.

### 6. A visual replay after the story — second priority

Borrow feedback/retry from Labster and authored alternative paths from H5P. Present a post-completion storyboard: the learner's choice, the character's recorded response, and the engine-produced finding with the precise reference. Offer a separate replay session for another choice, keeping the original event log intact. Do not imply that either branch predicts a real baby's health.

Thai application: “ลองอีกวิธีในการสนทนา” after completion. Alternative clinical/cultural outcomes must be reviewed authored content. A hypothetical improvement is easier reflection, to be tested with users, not asserted as increased competency.

## Recommended first experiment

Prototype one existing story with ideas 1–3: a compact scene, speaker presence, and a deliberate decision beat. Keep the chat transcript and assessment logic unchanged. Compare with the current version using a small usability study: can users explain their role, locate the next action, recall the agreement, and finish comfortably? Observe confusion, scrolling, voluntary replay, and reading behavior; do not equate longer time on page or faster completion with learning.

Use the existing cream/brown/gold theme. Honor reduced motion, keyboard operation, clear focus, text alternatives, and 360px layouts. Full dialogue must remain available without animation or audio. Do not add countdown pressure, parent leaderboards, punitive streaks, competitive scores, fabricated physiological visuals, or celebration that contradicts Critical Safety. Rendering can be local and deterministic, with no additional LLM calls; this is not a claim that synchronized two-device rooms can work without a server/network.

## Open decisions

- Can a neutral scene and speaker highlight create enough presence before producing recorded voice?
- Which authored public scene cues are already available, and which would need Content review?
- Should the first test target Co-op waiting/coordination or single-player chapter immersion?
- Should optional hints exist only in an explicitly separate practice mode? Live assessment hints can disclose rubric criteria and must not be added casually.

No production changes, source-content edits, new LLM duties, or scoring changes were made for this research.
