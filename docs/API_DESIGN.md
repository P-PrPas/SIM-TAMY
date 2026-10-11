# SIM-TAMY — API Design Guide

คู่มือประกอบ `openapi.yaml` (OpenAPI 3.1.0, 18 operations)
**ลำดับความสำคัญของเอกสาร:** `docs/PRD.md` → `openapi.yaml` (contract ที่เครื่องอ่านได้) → เอกสารนี้ (อธิบายเหตุผลและวิธีใช้)
ถ้า spec กับ PRD ขัดกัน ให้ดู §11 (Deltas) แล้วอัปเดต PRD §8 ใน PR เดียวกับที่แก้ spec

---

## 1. หลักการออกแบบ

| # | หลักการ | เหตุผล |
|---|---|---|
| P1 | **ไม่รั่วระหว่างเล่น** — response ช่วง `INTERVIEW/PRESSURE/CLOSING` ห้ามมี `revealed_fact_ids`, `risk_state`, detected `actions`, hidden facts, คะแนน (ยกเว้น `GLASS_BOX_LIVE=true`) | Non-negotiable #5 ผู้เรียนต้องตัดสินใจโดยไม่รู้เฉลย |
| P2 | **Engine ตัดสิน ไม่ใช่ client** — client ส่งแค่ข้อความและ `option_id` จาก Decision Panel; phase/state เปลี่ยนที่ server เท่านั้น | Determinism, ป้องกันการโกง |
| P3 | **Event Log เป็น source of truth** — ทุก endpoint ที่เปลี่ยน state เขียน event แบบ append-only ใน transaction เดียว | re-score ต้องได้ผลเดิม |
| P4 | **Idempotent และ retry-safe** — `client_turn_id`, decision ซ้ำ option เดิม, `complete` ซ้ำ | เครือข่ายมือถือไม่เสถียร |
| P5 | **Degrade ไม่ล้ม** — LLM ล่มแล้วยังตอบ 200 พร้อม `degraded: true` | กัน demo พัง |
| P6 | **Contract-first** — แก้ `openapi.yaml` ก่อน แล้ว generate type ฝั่ง web / schema test ฝั่ง api | ลด drift ระหว่าง FE/BE |

## 2. Conventions

- **Base path:** `/v1` (ยกเว้น `/health`). breaking change = `/v2`; เพิ่ม field แบบ optional ไม่ถือเป็น breaking
- **Format:** JSON UTF-8, `snake_case`, เวลาเป็น ISO-8601 UTC (`2026-10-12T09:30:00Z`), ID เป็น string
- **Content-Type:** `application/json`; stream ใช้ `text/event-stream`
- **Request ID:** server ใส่ `X-Request-ID` ทุก response (และ `error.request_id`) — client ควรแสดงให้ผู้ใช้ตอน error เพื่อ debug
- **Cache:** response ของ session ทั้งหมดส่ง `Cache-Control: no-store`
- **Pagination:** cursor-based (`?limit=&cursor=`) → `{items:[], next_cursor: string|null}`
- **Language:** ข้อความที่ผู้ใช้เห็นเป็นไทยอยู่ใน field `*_th` หรือมาจาก content; `error.message` เป็นอังกฤษสำหรับนักพัฒนา — FE map `error.code` → ข้อความไทยจาก `th.json`
- **Extensions:** `x-priority` (Must/Should/Could) และ `x-fr` (FR IDs) บนทุก operation เพื่อ trace กลับ PRD

### 2.1 Error envelope

```json
{
  "error": {
    "code": "TURN_IN_PROGRESS",
    "message": "Another turn is still being processed for this session.",
    "details": {},
    "request_id": "req_01J..."
  }
}
```

`code` เป็น enum ปิด (`ErrorCode`, 21 ค่า) — FE ใช้ `code` ตัดสินพฤติกรรม ไม่ parse `message`

## 3. Authentication & Authorization

| Scheme | ใช้กับ | วิธีส่ง | หมายเหตุ |
|---|---|---|---|
| ไม่มี | `/health`, `/v1/cases*`, `/v1/classes/{code}`, `POST /v1/sessions` | — | public เพราะเป็น synthetic content + การสร้าง session แบบ anonymous/class code |
| `SessionToken` | session ของตัวเอง | `Authorization: Bearer <token>` | opaque, ได้ **ครั้งเดียว** ตอน `POST /v1/sessions`, server เก็บแค่ hash; ผูกกับ session เดียว |
| `InstructorSecret` | `/v1/classes` (POST), `/v1/instructor/*`, และอ่าน session ใดก็ได้ | `X-Instructor-Secret: <secret>` | MVP ใช้ shared secret จาก env `INSTRUCTOR_SECRET`; ย้ายไป account-based auth ใน post-hackathon (ADR ใหม่) |

กฎ:
- token ผิด/หาย → `401 UNAUTHORIZED`; token ถูกแต่ session ไม่ใช่ของตัวเอง → `404 NOT_FOUND` (ไม่เปิดเผยว่า session มีอยู่)
- instructor ใช้ endpoint ผู้เรียนได้เฉพาะแบบ **อ่าน** (`getSession`, `getReport`, `getLiveGlassBox`) ห้ามส่ง turn/decision แทนผู้เรียน
- Secret/token ห้ามอยู่ใน URL หรือ log; FE เก็บ learner token ใน `sessionStorage` (หายเมื่อปิดแท็บ — ยอมรับได้สำหรับ MVP) ไม่ใช้ `localStorage`

## 4. Endpoint overview

| Tag | Method & Path | operationId | Auth | Priority | Phase ที่เรียกได้ |
|---|---|---|---|---|---|
| System | `GET /health` | getHealth | – | Must | – |
| Cases | `GET /v1/cases` | listCases | – | Must | – |
| Cases | `GET /v1/cases/{case_id}` | getCase | – | Must | – |
| Cases | `GET /v1/classes/{code}` | checkClassCode | – | Should | – |
| Sessions | `POST /v1/sessions` | createSession | – | Must | – (สร้าง → `INTERVIEW`) |
| Sessions | `GET /v1/sessions/{id}` | getSession | Session / Instructor | Must | ทุก phase |
| Sessions | `POST /v1/sessions/{id}/turns` | sendTurn | Session | Must | `INTERVIEW`, `PRESSURE` |
| Sessions | `POST /v1/sessions/{id}/decision` | commitDecision | Session | Must | `INTERVIEW` |
| Sessions | `POST /v1/sessions/{id}/complete` | completeSession | Session | Must | `CLOSING` |
| Reports | `GET /v1/sessions/{id}/report` | getReport | Session / Instructor | Must | `COMPLETED` |
| Reports | `GET /v1/sessions/{id}/glassbox` | getLiveGlassBox | Session / Instructor | Could | ทุก phase (ต้อง `GLASS_BOX_LIVE`) |
| Instructor | `POST /v1/classes` | createClass | Instructor | Should | – |
| Instructor | `GET /v1/instructor/classes` | listClasses | Instructor | Should | – |
| Instructor | `GET /v1/instructor/sessions` | listInstructorSessions | Instructor | Should | – |
| Instructor | `GET /v1/instructor/analytics` | getClassAnalytics | Instructor | Could | – |
| Instructor | `POST /v1/instructor/sessions/{id}/overrides` | createOverride | Instructor | Could | `COMPLETED` |
| Replay | `GET /v1/replay/recordings` | listRecordings | – | Must | – (ต้อง `ENABLE_REPLAY`) |
| Replay | `GET /v1/replay/recordings/{id}` | getRecording | – | Must | – (ต้อง `ENABLE_REPLAY`) |

## 5. Session lifecycle และ Phase/Permission matrix

```
createSession ─► INTERVIEW ──commitDecision──► CLOSING ──completeSession──► COMPLETED
                    │  ▲ sendTurn (≤ max_turns)    ▲
                    │  └──────────┘                │
                    └──commitDecision (Variant C + refer)──► PRESSURE ──(ใช้ครบ pressure_turns_allowed)──► CLOSING
                                                       sendTurn (≤ pressure_turns_allowed)
```

| Endpoint | INTERVIEW | PRESSURE | CLOSING | COMPLETED | หมายเหตุ |
|---|---|---|---|---|---|
| sendTurn | ✅ | ✅ | `409 INVALID_PHASE` | `409 SESSION_COMPLETED` | เกิน `max_turns` → `409 TURN_LIMIT` (ผู้เรียนยังตัดสินใจได้) |
| commitDecision | ✅ | `409 INVALID_PHASE` | `409 INVALID_PHASE` / ซ้ำ option เดิม = 200 idempotent | เหมือน CLOSING | option อื่น → `409 DECISION_ALREADY_COMMITTED` |
| completeSession | `409 INVALID_PHASE` | `409 INVALID_PHASE` | ✅ | ✅ (คืนผลเดิม) | |
| getReport | `409 REPORT_NOT_READY` | `409 REPORT_NOT_READY` | `409 REPORT_NOT_READY` | ✅ | |
| getSession | ✅ | ✅ | ✅ | ✅ | |
| createOverride | ✗ | ✗ | ✗ | ✅ | instructor เท่านั้น |

Session หมดอายุเมื่อ idle เกิน `limits.idle_timeout_s` (ค่าเริ่ม 1800 วินาที) → `410 SESSION_EXPIRED`

> **ทำไม phase ไม่รวม INTRO:** INTRO ยุบเข้า `INTERVIEW` ในระดับ public API (ข้อความเปิดเป็นบรรทัด `system` ที่ `idx = 0` ใน `SessionView.history`; `createSession` ไม่ส่ง history กลับมา ให้ FE เรียก `getSession` ต่อทันที) เพื่อให้ FE มี state น้อยลง

## 6. Field exposure matrix (ช่วงเล่น vs. หลังจบ)

| ข้อมูล | ระหว่างเล่น | หลัง COMPLETED | เหตุผล |
|---|---|---|---|
| ข้อความสนทนา (`Message`) | ✅ | ✅ | |
| `phase`, `turns_remaining`, `clarification`, `degraded` | ✅ | ✅ | UI ต้องใช้ |
| ตัวเลือก Decision Panel | ✅ (จาก `getCase`/`createSession`) | ✅ | |
| `case.status` badge + notices | ✅ | ✅ | Rule #9 |
| `revealed_fact_ids` / hidden facts | ❌ | ✅ (`glassbox.facts`) | ป้องกันเฉลย |
| `risk_state` | ❌ (ยกเว้น `GLASS_BOX_LIVE`) | ✅ | |
| Detected `actions` | ❌ (ยกเว้น `GLASS_BOX_LIVE`) | ✅ (`timeline`, `evidence`) | |
| คะแนน / `safety_status` / `items` | ❌ | ✅ | |
| ผลของ unsafe action | ❌ (ไม่บอกใน `commitDecision`) | ✅ (`findings`) | |
| Rubric/branch rules/outcome scripts | ❌ ไม่เคยเปิดผ่าน `getCase` | เปิดเฉพาะผลที่ engine คำนวณ | |

**วิธีตรวจ (CI):** `scripts/leakcheck.py` — เดินทุก `$ref` ของ schema ช่วงเล่น (`SessionView`, `TurnResponse`, `Reply`, `CreateSessionResponse`, `DecisionResponse`, `CompleteResponse`, `Message`, `DecisionState`, `Notice`, `CaseBrief`, `CaseSummary`) แล้ว fail ถ้าเจอชื่อฟิลด์ต้องห้าม ผลรันปัจจุบัน: สะอาด ยกเว้น `TurnResponse.glassbox.risk_state` ซึ่งเป็น `null` เมื่อ `GLASS_BOX_LIVE=false` (ตั้งใจ) — เพิ่ม integration test ยืนยันว่าเป็น `null` ตอน flag ปิด

## 7. Turn pipeline และ SSE protocol

### 7.1 Request

```http
POST /v1/sessions/{id}/turns?stream=true
Authorization: Bearer <token>
Content-Type: application/json

{ "text": "ช่วงนี้เลือดออกมากแค่ไหนคะ", "client_turn_id": "c0a8b3f2-7d1e-4f55-9a0e-3b3a1c2d4e5f" }
```

- `text`: 1–500 ตัวอักษร (เกิน → `422 VALIDATION_ERROR`/`TEXT_TOO_LONG`)
- `client_turn_id`: 8–64 ตัวอักษร, client สร้างใหม่ต่อข้อความ (UUID v4 แนะนำ) และ **ใช้ซ้ำเมื่อ retry ข้อความเดิม**

### 7.2 Server pipeline (1 transaction ต่อ turn)

```
validate request ─► lock session (1 in flight) ─► Interpreter (LLM, temp 0)
  ─► post-process (ทิ้ง ID ที่ไม่รู้จัก, ตรวจ evidence_span, confidence policy)
  ─► Engine.apply (pure) ─► Generator (LLM, allowed facts only)
  ─► Validator (≤ 2 regenerations, แล้ว canned fallback)
  ─► persist turn + events + llm_calls + state ─► respond
```

### 7.3 SSE (buffer-then-chunk)

Server รอจน Validator ยอมรับข้อความ **ก่อน** แล้วค่อยแบ่งเป็น chunk ส่ง — ไม่มีข้อความที่ถูก reject หลุดไปถึง client

```
event: delta
data: {"seq":0,"speaker":"patient","text":"ช่วงสองสามชั่วโมงนี้"}

event: delta
data: {"seq":1,"speaker":"patient","text":"เปลี่ยนผ้าอนามัยไปสามผืนแล้วค่ะ"}

: ping

event: done
data: {"turn_idx":3,"replies":[{"speaker":"patient","text":"ช่วงสองสามชั่วโมงนี้เปลี่ยนผ้าอนามัยไปสามผืนแล้วค่ะ"}],"phase":"INTERVIEW","clarification":false,"turns_remaining":37,"degraded":false,"glassbox":null}
```

กฎสำหรับ client:
- เพราะเป็น POST ใช้ `fetch` + `ReadableStream` (ไม่ใช้ `EventSource`)
- `delta.seq` เรียงต่อเนื่อง; ถ้าขาดช่วง ให้รอ `done` แล้วใช้ `replies` เป็นข้อความจริง (`done` คือ source of truth)
- `error` event → stream ปิด; ใช้ `error.code` ตัดสินว่าจะ retry อย่างไร (§9)
- `: ping` ทุก 15 วินาทีเป็น keep-alive ให้ข้ามไป
- ถ้า connection หลุดก่อน `done` → **retry ด้วย `client_turn_id` เดิม** (server คืนผลที่เก็บไว้ถ้าประมวลผลเสร็จแล้ว พร้อม header `Idempotent-Replay: true`)
- โหมด non-stream (`stream` ไม่ระบุ) คืน `TurnResponse` JSON ทีเดียว — ใช้เป็น fallback เมื่อ proxy/เครือข่ายบัฟเฟอร์ SSE

### 7.4 กรณีพิเศษ

| สถานการณ์ | พฤติกรรม |
|---|---|
| Interpreter confidence 0.5–0.75 | `clarification: true`; คนไข้ถามกลับ ไม่ปลดล็อกข้อเท็จจริง |
| confidence < 0.5 | ไม่นับ action; คนไข้ตอบทั่วไป |
| Action ซ้ำ | ไม่ปลดล็อกอีก แต่บันทึก `ACTION_REPEATED` (ไม่เห็นใน response ช่วงเล่น) |
| LLM ล่ม/ช้า | lexical fallback + canned reply → 200 `degraded: true`; FE แสดงแถบเล็กๆ แต่เล่นต่อได้ |
| แม้ fallback ก็ตอบไม่ได้ | `503 LLM_UNAVAILABLE` (retryable) |
| Prompt injection ในข้อความผู้เรียน | ถือเป็นข้อมูล ไม่ใช่คำสั่ง; Validator ตรวจ role-break/leak; ไม่มีผลต่อ state นอกเหนือ action ที่ถูกต้อง |

## 8. Idempotency และ Concurrency

| กลไก | รายละเอียด |
|---|---|
| `client_turn_id` | (session_id, client_turn_id) unique; ซ้ำ+ข้อความเดิม → ผลเดิม + `Idempotent-Replay: true`; ซ้ำ+ข้อความต่าง → `409 IDEMPOTENCY_CONFLICT` |
| One-in-flight | ระหว่างประมวลผล turn ถ้ามี turn ใหม่เข้ามา → `409 TURN_IN_PROGRESS` (retryable หลังรอสั้นๆ); FE ควร disable ช่องกรอกระหว่างรอ |
| `state_version` | optimistic locking ภายใน DB (ไม่เปิดใน API); conflict ระหว่างสอง request → ตัวหลังได้ `TURN_IN_PROGRESS` |
| Decision | option เดิมซ้ำ = 200 ผลเดิม; option ต่าง = `409 DECISION_ALREADY_COMMITTED` |
| Complete | เรียกซ้ำหลังจบ = คืนผลเดิม (ไม่คำนวณใหม่) |
| Rate limit | 10 req/นาที/session; เกิน → `429 RATE_LIMITED` + `Retry-After`; ทุก response มี `X-RateLimit-Limit/Remaining` |

## 9. Error catalog

| code | HTTP | Retry | FE ควรทำ |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | ไม่ | แสดงข้อความตรวจสอบฟอร์ม; `details` ระบุ field |
| `TEXT_TOO_LONG` | 422 | ไม่ | ตัดความยาว/แจ้ง 500 ตัวอักษร |
| `TURN_LIMIT` | 409 | ไม่ | ปิดช่องแชท ชี้ไปที่ Decision Panel |
| `TURN_IN_PROGRESS` | 409 | ได้ (หน่วง 1–2 วิ) | รอ/แสดง typing ต่อ ไม่ส่งซ้ำด้วย ID ใหม่ |
| `SESSION_COMPLETED` | 409 | ไม่ | พาไปหน้า report |
| `SESSION_EXPIRED` | 410 | ไม่ | แจ้งหมดเวลา เสนอเริ่มใหม่ |
| `INVALID_PHASE` | 409 | ไม่ | `getSession` แล้ว sync UI กับ `phase` จริง |
| `DECISION_ALREADY_COMMITTED` | 409 | ไม่ | แสดงผลที่ commit ไปแล้ว |
| `DECISION_OPTION_INVALID` | 422 | ไม่ | bug ฝั่ง client — log + รีเฟรชตัวเลือก |
| `IDEMPOTENCY_CONFLICT` | 409 | ไม่ | สร้าง `client_turn_id` ใหม่เมื่อข้อความต่างกัน |
| `REPORT_NOT_READY` | 409 | หลัง `complete` | พาไปเรียก `complete` ก่อน |
| `UNAUTHORIZED` | 401 | ไม่ | ล้าง token → หน้า Join |
| `FORBIDDEN` | 403 | ไม่ | instructor secret ผิด |
| `GLASSBOX_DISABLED` | 403 | ไม่ | ซ่อน UI Live Glass Box |
| `NOT_FOUND` | 404 | ไม่ | แสดงหน้าไม่พบ |
| `CASE_NOT_AVAILABLE` | 404/409 | ไม่ | เคสถูกซ่อน (เช่น Draft ถูกปิด) |
| `VARIANT_NOT_AVAILABLE` | 422 | ไม่ | เลือก variant ที่เคสรองรับ |
| `CLASS_NOT_FOUND` | 404 | ไม่ | แจ้งรหัสห้องผิด |
| `RATE_LIMITED` | 429 | ได้ (ตาม `Retry-After`) | แสดงข้อความรอ |
| `LLM_UNAVAILABLE` | 503 | ได้ (backoff) | ปุ่ม retry โดยไม่เสีย turn |
| `INTERNAL_ERROR` | 500 | ได้ 1 ครั้ง | แสดง `request_id` |

> HTTP status แน่นอนของแต่ละ code ให้ยึดตาม response component ใน `openapi.yaml`; ตารางนี้เป็นแนวทางสำหรับ FE

## 10. Sequence flows

### 10.1 Variant A (ภาวะอันตรายจริง) — happy path

```
Learner/Web                              API                                  Engine/AI
   │ POST /sessions {case_id, learner_name, variant:A}
   │──────────────────────────────────────►│ สร้าง session + token (hash)
   │◄── 201 {session_id, token, token_type, case, variant, phase, limits, notices} ─┤
   │ GET /sessions/{id}   (ดึง history รวมบรรทัดเปิด idx 0)
   │ POST /turns (SSE) "เลือดออกมากแค่ไหน"   │
   │──────────────────────────────────────►│ Interpreter→Engine→Generator→Validator
   │◄── delta… / done {replies, phase:INTERVIEW} ──────────────────┤
   │ … (หลาย turn) …                        │
   │ POST /decision {option_id:"refer", rationale_th}               │
   │──────────────────────────────────────►│ บันทึก DECISION_COMMITTED, branch → CLOSING
   │◄── 200 {phase:CLOSING, decision:{option_id,committed_at_idx}, replies, pressure_turns_allowed:null}
   │       (ไม่เปิดคะแนน/ผลของ unsafe action)                         │
   │ POST /complete {note_th?}              │
   │──────────────────────────────────────►│ score จาก Event Log → report + debrief
   │◄── 200 {status:"completed", report_ready:true, report_url}     │
   │ GET /report                            │
   │◄── 200 {safety_status, items, glassbox, replay, debrief, …}    │
```

### 10.2 Variant C (ผู้ป่วยลดความสำคัญ + ญาติกดดัน)

```
… INTERVIEW เหมือนเดิม …
POST /decision {option_id:"refer"}
◄── 200 {phase:PRESSURE, replies:[{speaker:"relative", …scripted…}], pressure_turns_allowed:3}
POST /turns ×N (N ≤ pressure_turns_allowed)       # ผู้เรียนโน้มน้าวญาติ — คำพูดญาติใน replies เป็น scripted
◄── turn สุดท้าย: {phase:"CLOSING", …}              # server เปลี่ยน phase เองเมื่อใช้โควตาครบ
POST /complete
GET  /report        # ตรวจ ESC/COMM รวม "ยืนยันคำตัดสินเมื่อถูกกดดัน"
```

### 10.3 Instructor

```
POST /v1/classes {name}                         ─► code 6 ตัว [A-Z0-9] (แจก code ให้ผู้เรียน)
ผู้เรียน: GET /classes/{code} → POST /sessions {case_id, learner_name, class_code}
GET /instructor/sessions?class_code=…&case_id=&variant=&status=&safety_status=&limit=20&cursor=   ─► รายการ + cursor
GET /sessions/{id}/report  (InstructorSecret)             ─► ดูรายงานรายคน
GET /instructor/analytics?class_code=…                    ─► สถิติห้อง
POST /instructor/sessions/{id}/overrides {rubric_item_id, new_result, new_earned?, reason}   ─► คะแนน effective ถูกคำนวณใหม่
```

Override **ไม่แก้ผลดิบของ engine** — เก็บในตาราง `score_overrides` และ `report.effective` คำนวณใหม่; `report.overrides` แสดงรายการ override ทั้งหมดเพื่อความโปร่งใส และ Critical Safety ยังคงเป็น gate ตามกติกา (ดู Open Q1)

### 10.4 Replay Mode (ใช้ตอน demo ไม่มีเน็ต/LLM)

```
GET /replay/recordings           ─► [{recording_id, title_th, case_id, variant, description_th, steps_count}]
GET /replay/recordings/{id}      ─► {…summary, case, steps:[{t_ms, type, speaker?, text?, option_id?, phase?}], report}
                                    type ∈ learner | reply | decision | phase_change | complete
```
เปิดได้เฉพาะเมื่อ `ENABLE_REPLAY=true`; FE เล่น step ตาม `t_ms` (หน่วงก่อนเล่นแต่ละ step เทียบกับ step ก่อนหน้า) และแสดงป้าย "Replay" ชัดเจน — **ห้ามอ้างว่าเป็น session สด**

## 11. Deltas จาก PRD §8 (ต้อง feed กลับ PRD/AGENTS)

| # | รายการ | แก้ที่ |
|---|---|---|
| D1 | เพิ่ม env `ENABLE_REPLAY` (gate `/v1/replay/*`) | PRD §6.5, `.env.example`, AGENTS.md (key env vars) |
| D2 | เพิ่ม error codes ที่ PRD ยังไม่มี: `IDEMPOTENCY_CONFLICT`, `GLASSBOX_DISABLED`, `VARIANT_NOT_AVAILABLE`, `CLASS_NOT_FOUND`, `DECISION_OPTION_INVALID` (รวม enum ครบ 21 ค่า) | PRD §8.x error table |
| D3 | `error.request_id` และ header `X-Request-ID` ทุก response | PRD §8 conventions, T-081 (observability) |
| D4 | SSE event `error` และ keep-alive `: ping` 15 วินาที | PRD FR-CHAT-03 |
| D5 | Header `Idempotent-Replay: true` | PRD §8 turns |
| D6 | `checkClassCode` เป็น endpoint สาธารณะแยก (คืนเฉพาะชื่อห้อง) | PRD FR-INS-01 |
| D7 | `report.effective` + `report.overrides` (คำนวณ override แยกจากผลดิบ) | PRD FR-INS-04 |
| D8 | `x-priority`/`x-fr` เป็น extension ใน OpenAPI | – (เอกสาร) |

## 12. Frontend integration notes

- **Generate types:** `npx openapi-typescript openapi.yaml -o apps/web/lib/api/schema.d.ts`; ห้ามเขียน type response มือ
- **Client wrapper** (`apps/web/lib/api/client.ts`): แนบ token, parse error envelope เป็น `ApiError{code,status,requestId}`, retry อัตโนมัติเฉพาะ `LLM_UNAVAILABLE` / `TURN_IN_PROGRESS` / network error (≤ 2 ครั้ง, backoff 1s→2s) โดยใช้ `client_turn_id` เดิม
- **Optimistic UI:** แสดงข้อความผู้เรียนทันทีสถานะ "กำลังส่ง"; ล้มเหลว → ปุ่ม "ส่งอีกครั้ง" (ไม่ต้องพิมพ์ใหม่, ใช้ ID เดิม)
- **Resume:** เมื่อรีเฟรช เรียก `getSession` (token จาก `sessionStorage`) เพื่อกู้ messages + phase + decision state
- **Phase-driven routing:** FE ไม่ derive phase เอง — ใช้ `phase` จาก response เท่านั้น
- **Banners:** render `notices[]` + case status badge ทุกหน้าที่เห็นเนื้อหาเคส
- **a11y:** ข้อความใหม่ใส่ `aria-live="polite"`; ปุ่ม Decision Panel ใช้งานด้วยคีย์บอร์ดและยืนยันก่อน commit (irreversible)
- **Report page:** ถ้า `safety_status = SAFETY_NOT_MET` ห้ามแสดงคำว่า "ผ่าน/pass" ที่ใดทั้งสิ้น แม้คะแนนรวมสูง

## 13. Contract testing และ tooling

| งาน | เครื่องมือ | ทำเมื่อ |
|---|---|---|
| Validate spec | `openapi-spec-validator` (รันแล้ว: ผ่าน, 18 ops, operationId ไม่ซ้ำ) | CI ทุก PR |
| Fuzz/contract test API | `schemathesis run openapi.yaml --base-url http://localhost:8000 --checks all` (ตั้ง auth header; ข้าม SSE) | CI nightly + ก่อน demo |
| Mock server ให้ FE เริ่มงานก่อน BE เสร็จ | `prism mock openapi.yaml` | M0–M1 |
| Leak check | `scripts/leakcheck.py` (§6) + test ที่ยิง session จริงแล้วเทียบ JSON กับ allow-list | CI ทุก PR |
| Breaking-change diff | `oasdiff breaking main.yaml openapi.yaml` | CI ทุก PR ที่แตะ spec |
| FastAPI ↔ spec drift | export `app.openapi()` แล้ว diff กับ `openapi.yaml` (ต้องตรงกันในส่วน path/schema) | CI |

**สำคัญ:** FastAPI จะ generate OpenAPI ของตัวเอง — ให้ถือ `openapi.yaml` เป็น contract และเขียน Pydantic model ให้ตรง ไม่ใช่ปล่อยให้ auto-gen เป็นตัวกำหนด

## 14. Open questions (ต้องตัดสินใจกับทีม)

| # | คำถาม | ข้อเสนอของผม |
|---|---|---|
| Q1 | Instructor override กับ Critical Safety: ให้ override item `critical` ได้หรือไม่? | ไม่ให้ใน MVP (แตะ scoring semantics = ask-first); ต้องมี ADR ถ้าจะเปิด |
| Q2 | `getRecording` และ `listRecordings` เปิด public ได้หรือไม่ในโหมด production | ได้เฉพาะเมื่อ `ENABLE_REPLAY=true`; ปิดโดยค่าเริ่มต้นนอก demo |
| Q3 | เก็บ learner free text นานเท่าไร (retention) | ตาม PRD §15/OD — ต้องมีค่าชัดก่อน pilot |
| Q4 | ฉาก PRESSURE: ผู้เรียนอยากจบก่อนใช้โควตาครบได้หรือไม่? | ตอนนี้ spec ให้จบได้ต่อเมื่อใช้โควตาครบ (server เปลี่ยนเป็น `CLOSING` เอง); ถ้าต้องการปุ่ม "จบฉาก" ต้องเพิ่ม endpoint/พารามิเตอร์ใหม่ — ผมแนะนำไม่ทำใน MVP |

## 15. Checklist ก่อน merge PR ที่แตะ API

- [ ] แก้ `openapi.yaml` ก่อนโค้ด และ `openapi-spec-validator` ผ่าน
- [ ] `oasdiff breaking` ไม่เจอ breaking change (หรือมี ADR + bump `/v2`)
- [ ] ไม่มี hidden field ใน schema ช่วงเล่น (`leakcheck` ผ่าน)
- [ ] error ใหม่ถูกเพิ่มใน `ErrorCode` และตาราง §9
- [ ] test ครอบคลุม idempotency/phase matrix ของ endpoint ที่แก้
- [ ] อัปเดต PRD §8 / AGENTS.md หากเปลี่ยน contract
