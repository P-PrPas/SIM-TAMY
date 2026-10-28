
# SIM-TAMY 2.0
## Product Transformation & Implementation Blueprint
**Thai Midwifery Simulation & Education Platform**  
**ฉบับสำหรับทีม Product, Engineering, AI Agent, Content Reviewer และ Pitch Team**  
**เวอร์ชันเอกสาร:** 2.1 — AI Implementation Addendum (ผลิตภัณฑ์ยังชื่อ **SIM-TAMY 2.0**) | **วันที่:** 28 ตุลาคม 2569 | **สถานะ:** แผนเสนอพัฒนา ไม่ใช่หลักฐานว่าได้สร้างหรือรับรองแล้ว

> **Executive decision:** ยุบหน้าตาฟีเจอร์เดิมที่ซ้ำซ้อนเป็น 4 Product Pillars: (1) Thai Midwifery Learning Paths (2) Interactive Family Simulation (3) Evidence & Learning Assessment (4) Institutional Learning Workspace. แกนความแตกต่างคือ **Thai Midwifery Decision Practice** ที่อิงข้อมูลอนุมัติ ตรวจสอบย้อนกลับได้ และใช้ได้ทั้งในบ้านและโรงเรียนพ่อแม่
>
> **AI implementation decision (เพิ่ม 28 ต.ค. 2569):** ยืนยัน Architecture **AI-assisted + deterministic safety** โดยเพิ่มและทำให้ครบทั้ง 3 ความสามารถ: **AI-01 Context-aware Roleplay**, **AI-02 Evidence-grounded Generation**, **AI-03 Personalized Debrief**. ทั้งสามเป็น **scope ที่ต้องส่งมอบใน SIM-TAMY 2.0 ฉบับสมบูรณ์ (P0)** ไม่ใช่ optional / future idea; คง P0/P1/P2 และฟีเจอร์อื่นทั้งหมดของ Blueprint เดิมไว้ ไม่ลดขอบเขตตามความกังวลด้านเวลา. อ่านสัญญาข้อมูลและงานที่ตรวจรับได้ใน **§09A–09E** และตาราง Sprint/Tests ที่เพิ่มแล้ว

## 01 / ข้อค้นพบจากตำราใหม่: มีอะไรเปลี่ยนความคิดเรา?
Catalog ฉบับทีมรวบรวมรายการ **84 รายการ**: M ตำราหลัก 26, S ตำราเฉพาะ 20, T ผดุงครรภ์ไทย/คัมภีร์ 10, P คู่มือโรงเรียนพ่อแม่ 9, I ตำราต่างประเทศ 7, G มาตรฐาน/แนวทาง 12 รายการ [C1]. รายการนี้เป็น **bibliographic catalog** ไม่ใช่ full-text clinical knowledge base หรือหลักฐานว่าใช้เนื้อหาได้อย่างเสรี และไม่เท่ากับเอกสารใดผ่านการตรวจทางวิชาชีพแล้ว

### ไอเดียใหม่ที่ได้เพิ่มจาก Catalog — สิ่งที่ควรสร้างจริง
1. **Knowledge Provenance & Rights Gate (ใหม่ / P0):** ทุกข้อความในบทเรียนอ้างกลับไปยังต้นฉบับที่เข้าถึงอย่างถูกสิทธิได้ ระบุ edition, chapter/page, ผู้ตรวจ, วันทบทวน และสถานะสิทธิ์ ห้ามอัปโหลดหนังสือมีลิขสิทธิ์เข้า RAG โดยไม่มีสิทธิ์
2. **Thai Wisdom Lens (ใหม่ / P0):** ในทุกฉากที่มีความรู้ไทย ให้ผู้ใช้เห็น 3 มุม *ภูมิปัญญาและที่มา / ความปลอดภัยและข้อจำกัด / สิทธิและช่องทางปรึกษาวิชาชีพ* ไม่ลดความเป็นไทยให้เหลือแค่เรื่องอันตราย
3. **Competency-to-Scenario Compiler (ใหม่ / P1):** แปลง learning objective ที่ผู้สอนเลือกเป็นรายการฉากที่ผ่าน review + rubric ที่เกี่ยวข้อง ไม่ให้ LLM คิดข้อสอบ/กติกาคลินิกใหม่เอง
4. **Content Coverage & Freshness Monitor (ใหม่ / P1):** แสดง coverage ของหลักสูตรและรายการที่รอตรวจทาน/ใกล้ครบกำหนดทบทวน เป็นคุณค่าต่อองค์กรที่ซื้อซ้ำ ไม่ใช่หน้าอ่านหนังสือธรรมดา
5. **Dual-case Demo (ใหม่ / P0):** มีทั้งฉาก “ต้องหยุดและส่งต่อ” และฉาก “เรียนรู้บริการไทยอย่างเหมาะสมในเหตุการณ์ไม่ฉุกเฉิน” เพื่อไม่ทำให้ผดุงครรภ์ไทยถูกนำเสนอเป็นสิ่งที่ต้องปฏิเสธเสมอ

**ข้อค้นพบเชิงผลิตภัณฑ์:** ตำราที่เยอะขึ้นไม่ได้ทำให้ AI ปลอดภัยขึ้นโดยอัตโนมัติ; สิ่งที่เป็นสินทรัพย์ของ SIM-TAMY คือ *reviewed knowledge units + designed scenarios + evidence-linked assessment*, ไม่ใช่จำนวน PDF ใน vector database

## 02 / Product strategy และกลุ่มลูกค้า
**Positioning:** แพลตฟอร์มฝึกตัดสินใจสำหรับครอบครัวบนฐานความรู้ผดุงครรภ์ไทยและสุขภาพแม่เด็กที่ตรวจทานได้; หน่วยบริการสุขภาพสามารถจัดบทเรียน มอบหมาย ติดตาม และปรับปรุงการสอนได้

| บทบาท | Job-to-be-done | สิ่งที่จ่าย/ได้รับ | ตัววัดความสำเร็จ |
|---|---|---|---|
| พ่อแม่/ผู้ดูแล (B2C user) | ฝึกถาม สื่อสาร รู้ขอบเขตบริการไทย ขอความช่วยเหลือถูกจังหวะ | ประสบการณ์จำลองที่เข้าใจง่าย | completion, safe-decision performance |
| ผู้สอนโรงเรียนพ่อแม่ (operator) | เลือกบทที่เหมาะกับคลาส ส่งให้เรียนในเวลาน้อย | class assignment, gap report | time-to-assign, return to teaching |
| ผู้บริหาร/ผู้ซื้อ (economic buyer) | จัดการเรียนรู้ให้ผู้รับบริการรุ่นใหม่อย่างต่อเนื่อง | usage, educational value, evidence | cohorts/year, renewal intent |
| ผู้ตรวจเนื้อหา | ตรวจความถูกต้องและขอบเขตไทย/สมัยใหม่ | review queue, traceability | approved coverage, issue turnaround |

**Business boundary:** B2B2C-first แต่ Family user journey ยังเป็น core; การจ่ายเงิน License เป็นสมมติฐานต้องทดสอบกับผู้ซื้อจริง. ระบบไม่เป็น EMR/HIS, ไม่รับรองความสามารถประกอบวิชาชีพ, ไม่วินิจฉัยหรือจ่ายการรักษา

## 03 / ตัด–เก็บ–สร้างใหม่จาก 5 ฟีเจอร์เดิม
| ของเดิม | การตัดสินใจ | เหตุผล / งานย้ายข้อมูล |
|---|---|---|
| History-taking Chat | **เก็บความสามารถ / ยุบเป็น interaction ใน Simulation** | ลดเมนูซ้ำ; ย้าย conversation events เข้า session engine |
| Family Co-sim | **เก็บเป็นโหมดหลัก** | asymmetric information + joint decision คือความต่าง; reuse room/session |
| 100 Days | **ถอดจาก top-level / เปลี่ยนเป็น Learning Paths** | เน้น competency ไม่สัญญา 100 บท; mapping บทเดิมเข้าหมวด |
| Generational Bridge | **ถอดจาก standalone / สร้าง Thai Wisdom Decision Lab** | wisdom context เข้าในสถานการณ์และ evidence card |
| Your Persona | **ยุบเป็น optional delight / ยกระดับเป็น Learning Passport** | ใช้ rubric ที่ trace ได้, safety flag ไม่ถูกเฉลี่ยกลบ |
| Institution tools | **สร้างใหม่** | เป็นเหตุผลที่ B2B2C ใช้งานต่อทุก cohort |
| Knowledge governance | **สร้างใหม่/ยกระดับ** | ข้อมูลจาก Catalog ต้องผ่าน licensing and clinical review |

**Migration policy:** feature flag เดิมยังใช้ได้ช่วงเปลี่ยนผ่าน; ไม่ลบข้อมูล session หรือผลเดิมก่อนกำหนด migration schema และ QA; persona เดิมไม่ยกระดับเป็น clinical outcome

## 04 / Target Information Architecture
**หน้าครอบครัว:** Home / Learning Journey / Simulation Lab / My Learning Passport / Knowledge & Sources (อ่านง่าย)  
**หน้าสถาบัน:** Overview / Cohorts / Assignments / Analytics / Curriculum Library / Staff & Settings  
**หน้าผู้ตรวจ:** Knowledge Queue / Scenario Review / Version History / Publication Gate  
**ไม่สร้างตอนนี้:** full LMS, billing portal, SSO, HIS, VR, live diagnostic assistant, public clinical authoring

## 05 / Pillar 1: Thai Midwifery Learning Paths
**Pain:** เนื้อหาเดิมอยู่กระจัดกระจาย สถาบันไม่รู้ว่าเนื้อหาบทใดตรง learning objective หรือคู่มือใด; พ่อแม่ไม่เห็นเส้นทางความรู้ที่ต่อเนื่อง  
**Solution:** Curriculum hierarchy `Stage -> Module -> Objective -> Knowledge Unit -> Scenario -> Rubric`; ครอบครัวใช้ stage-based journey, ผู้สอน assign reusable tracks

### Proposed public-facing Stages (เชื่อม 8 modules จากรายงานก่อนหน้า)
| Stage | โมดูลอ้างอิงจาก Knowledge Base | Thai Midwifery-specific element | ตัวอย่าง task |
|---|---|---|---|
| 1 เตรียมครอบครัว | M1–M2 | ตรวจความเข้าใจและข้อจำกัดคำแนะนำ/สมุนไพรในบริบทไทย | ตั้งคำถามที่ควรนำไปปรึกษาผู้เชี่ยวชาญ |
| 2 เตรียมคลอด | M3–M5 | บริบทความเชื่อข้ามรุ่น สิทธิผู้คลอด แผนรับบริการ | ร่วมเลือกแผนสื่อสาร/ส่งต่อ |
| 3 หลังคลอดและฟื้นฟู | M6 | บริการฟื้นฟูแบบไทย ความเหมาะสม/ข้อห้าม/ผู้มีสิทธิให้บริการ | Thai Wisdom Decision Lab |
| 4 ทารกและครอบครัว | M7–M8 | ครอบครัวข้ามรุ่น การสนับสนุนนมแม่และการขอความช่วยเหลือ | case ของผู้ดูแลสองคน |

**P0 MVP:** 4 stage cards, 3 reviewed learning objectives, 2 complete scenarios, lesson-to-scenario crosslink, source citations, progress per user. **P1:** educator curriculum mapping + reusable sequence. **P2:** more modules after review

**User stories:** `LP-01` พ่อแม่เข้า Learning Path รู้วัตถุประสงค์และเวลาฝึก; `LP-02` ผู้สอนเลือก objective แล้วเห็นฉากที่ approved; `LP-03` เล่นจบแล้ว passport อัปเดตจาก attempt จริง; `LP-04` ยังไม่ approved ไม่ถูกเผยแพร่

**Acceptance:** ไม่มี chapter/book ที่เผยแพร่แล้วไร้ provenance; ทุก learning objective เชื่อม rubric; “completed” ต้องมาจาก finished attempt; ไม่เผยแพร่เนื้อหาวิชาชีพเฉพาะแก่ผู้ใช้ทั่วไป

## 06 / Pillar 2: Interactive Family Simulation & Thai Wisdom Decision Lab
**Pain:** การอ่านข้อความไม่เท่ากับฝึกตัดสินใจ ผู้ใช้ต้องเผชิญข้อมูลไม่ครบและข้อเสนอที่ขัดกัน  
**Solution:** **Context-aware AI Interpreter** -> deterministic Scenario State & Safety Controller -> **Approved Knowledge Retrieval** + allowed facts -> **Grounded AI Response Generator** -> validator/fallback -> event log -> rubric -> **AI-assisted Personalized Debrief**. AI ทำให้บทสนทนาธรรมชาติและ Feedback เหมาะกับเหตุการณ์จริง แต่ **ห้าม** เปลี่ยน outcome/safety/rubric หรือสร้างข้อเท็จจริง/คำแนะนำทางคลินิกเอง; รายละเอียด implementation อยู่ใน §09A–09E

### Golden Scenario 2.0 (สองเหตุการณ์คู่กัน)
**GS-A / 'เมื่อครอบครัวเสนอการอยู่ไฟ แต่แม่มีอาการที่ต้องประเมิน'** — เน้นค้นพบข้อมูลสำคัญ ขอความช่วยเหลืออย่างเหมาะสม เคารพแม่และคนในบ้าน (critical-safety route). ตัวละครและอาการสมมติต้องผ่าน reviewer; ห้ามแสดงผลลัพธ์ที่ชี้นำให้ชะลอความช่วยเหลือในภาวะเสี่ยง

**GS-B / 'เลือกบริการฟื้นฟูแบบไทยอย่างเข้าใจ'** — ไม่มีอาการเร่งด่วนตามสถานการณ์ที่ผู้เชี่ยวชาญออกแบบ ฝึกตั้งคำถามด้านวัตถุประสงค์ ขอบเขต ความปลอดภัย คุณสมบัติผู้ให้บริการ ความยินยอม และการประสานดูแล (positive-value route). ไม่ให้คำแนะนำทำหัตถการด้วยตนเอง

| Step | Family side | Rule / logged evidence |
|---|---|---|
| S0 Start | อ่านว่าเป็นเหตุการณ์สมมติ เลือก solo/pair | consent scope, scenario_version |
| S1 Discover | ซักถามตัวละครที่มีข้อมูลแตกต่างกัน | revealed_fact_ids, interpreter confidence |
| S2 Consult | แลกเปลี่ยนกับคู่/ผู้ใหญ่ผ่านบทสนทนาที่กำหนด | shared facts, communication events |
| S3 Decide | เลือกและยืนยันการตอบสนอง | joint votes, deterministic transition |
| S4 Consequence | ดูผลลัพธ์เน้นการเรียนรู้ | branch_id, clinical-approved script |
| S5 Debrief | ดู Thai Wisdom Lens + evidence + retry | rubric_version, citations, missed actions |

**Co-sim P0:** role-specific data จำกัดที่ API (ไม่ส่งความลับของอีกคนลง client); join code, reconnect, disagreement state, decision lock. **Solo fallback:** ระบุ solo ชัด ไม่แสร้งว่าเป็น Co-sim

**Acceptance:** คู่เล่นสองอุปกรณ์จบได้, outcome เดิม replay จาก events แล้วเหมือนเดิม, unapproved text ไม่ถูกอ้างเป็น fact, สถานการณ์ฉุกเฉินไม่เปิดทางให้สอนรักษาเอง, ทั้ง GS-A และ GS-B มีผลต่างชัดและปลอดภัย

## 07 / Pillar 3: Evidence, Assessment & Learning Passport
**Pain:** chatbot score อย่างเดียวไม่มีความหมายต่อครอบครัวหรือผู้สอน หากอธิบายไม่ได้ว่าอ้างจากอะไร  
**Solution:** Report แบบ `behavior -> event -> rubric -> approved knowledge -> explanation` และแยก `critical safety result` จาก engagement/persona. เพิ่ม **AI-03 Personalized Debrief (P0)** ที่เรียบเรียงเหตุผลจาก AssessmentResult และ Event Log ที่ตรวจแล้วเท่านั้น โดยเป็น *explanation generator* ไม่ใช่ *scoring engine*; ห้ามเปลี่ยนคะแนน สรุปเหตุการณ์ที่ไม่มีอยู่ หรือให้การรักษาเฉพาะบุคคล (ดู §09D)

**Rubric draft (ต้องให้ reviewer approve):** (ก) information discovery 25%, (ข) decision/referral 35%, (ค) communication & consent 25%, (ง) evidence & scope 15%. เป็นตัวเลขออกแบบเพื่อทดสอบ **ไม่ใช่มาตรฐานวิชาชีพ**; หาก critical safety fail ต้องแสดงธงแยก ไม่ให้คะแนนอื่นหักล้างได้

**หน้าผู้เรียน:** learning goals, topic badges (ไม่ใช่ certificate), attempt history, relevant evidence card, missed information, replay/transfer case. **หน้าผู้สอน:** summary ต่อ objective และ class; ค่าเฉลี่ยหรือเปอร์เซ็นต์ต้องมี denominator, n และ version

**Acceptance:** คะแนน trace ถึง `event_id, scenario_version, rubric_version, knowledge_version`, safety flag ไม่ถูกเฉลี่ย, source card แสดง metadata ถูกต้อง, export รายงานไม่เผยข้อมูลระบุตัวบุคคลโดยไม่จำเป็น

## 08 / Pillar 4: Institutional Learning Workspace (B2B2C)
**Pain:** ครอบครัวรุ่นใหม่เข้ามาทุกเดือน แต่ผู้สอนต้องการมอบหมายบทฝึกและติดตามผลโดยไม่จัดการบัญชีทีละคน ผู้บริหารต้องเห็นคุณค่าการใช้ระบบซ้ำ  
**Solution:** Institution -> Cohort -> Assignment -> QR Join -> Simulation Attempt -> Aggregate Analytics -> Educator Intervention -> Next Cohort

| Subfeature | Priority | User story | Acceptance | Business metric |
|---|---|---|---|---|
| Org + Staff Role | P0 | admin จัดพื้นที่ให้หน่วยงาน | tenant isolation, staff revocation | setup success |
| Create/Clone Cohort | P0 | educator สร้างรุ่นใหม่ | no cross-cohort bleed, clone template | cohorts/year |
| Assign approved Scenario | P0 | educator เลือกบท | unapproved blocked | time-to-assign |
| QR/Code Guest Join | P0 | parents เริ่มได้เร็ว | no medical intake required, expires | scan-to-start |
| Basic Analytics | P0 | เห็น completion และ skill gaps | real event-derived numerators | dashboard usage |
| Learning Intervention | P1 | assign transfer case | pre/post separated | follow-up completion |
| PDF/CSV institutional report | P1 | buyer ประเมินการใช้ | privacy-safe aggregate export | export/renewal interest |
| White-label, SSO, billing | P2 | enterprise deployment | pilot demand first | contract expansion |

**UX demo moment:** Educator creates class and QR -> two parents complete GS -> learner sees explanation -> educator refreshes and sees one completed anonymized attempt. ห้ามใช้ mock dashboard โดยไม่ได้ติดป้ายข้อมูลสาธิต

**Security:** minimum 3 roles (org_admin, educator, learner); reviewer role separated; backend policy enforcement; only necessary events collected; analytics aggregate and suppressed at small `n` per policy; export audit; retention and delete flows

## 09 / Knowledge Architecture: Catalog ≠ Approved Knowledge Base
### Three-layer source architecture
1. **Source Registry**: 84 catalog records (title, code, publisher, ISBN, version, URL, rights/access); discovery metadata only
2. **Reviewed Knowledge Units**: reviewer-authored short claims with exact page/section and evidence status, restrictions, audience, care stage, expiry/review date
3. **Released Learning Assets**: scenarios, knowledge cards, explainers, rubrics, references; only approved snapshot can be consumed by app

### Source hierarchy / recommended first reading
| Purpose | Prioritized catalog IDs | Rule |
|---|---|---|
| การแพทย์แผนไทยและบริบทคัมภีร์ | T01, T02, T05, T09 | historical claims != current clinical claim |
| โรงเรียนพ่อแม่ | P01–P05 (และ P06–P09 ในระยะขยาย) | map age/stage; do not copy text wholesale |
| Safety postpartum | G06, G07, G08, M04, S04, S13 | latest authoritative clinical guidance reviewed |
| หลักสูตร/สมรรถนะวิชาชีพ | G01, G02, G03 | do not award license or competence to parents |
| การสื่อสารและบริบท | S15, G05, T09 | respect, consent, referral |

**ข้อจำกัดที่ต้องเขียนในระบบ:** catalog ให้ *ชื่อและคำอธิบายหนังสือ* ไม่ได้ให้เนื้อหาภายในแต่ละบททั้งหมด; ต้อง obtain source / license / verify passage ก่อนสร้าง approved unit; copyright and licensing check เป็น blocker ที่ปล่อยผ่านไม่ได้

### Knowledge Unit contract (ตัวอย่างโครงสร้าง ไม่ใช่ clinical fact)
```json
{
  "knowledge_id": "KB-TM-POST-001",
  "title": "การตัดสินใจเกี่ยวกับบริการฟื้นฟูหลังคลอดแบบไทย",
  "audience": "parent",
  "care_stage": "postpartum",
  "claim_text": "[REVIEWER_WRITTEN_AND_VERIFIED_TEXT]",
  "catalog_refs": ["T01", "T09", "G06"],
  "source_locators": [{"source_id":"T09","edition":"2026","section":"[VERIFY]"}],
  "evidence_status": "needs_review",
  "rights_status": "metadata_only",
  "professional_scope": "education_only",
  "contraindications": "[REVIEW_REQUIRED]",
  "escalation_rule_ids": [],
  "review": {"thai_midwifery":"pending","maternal_health":"pending"},
  "version": "0.1.0",
  "publish_status": "draft"
}
```

### Pipeline สำหรับ AI Agent / Reviewer
**Discover** catalog -> **Acquire** full source legally -> **Extract** relevant passage + page -> **Draft** atomic knowledge unit -> **Cross-check** modern/Thai professional scope -> **Review** domain specialist -> **Approve** versioned unit -> **Bind** to scenario/rubric -> **Publish** immutable snapshot -> **Monitor** revisions

**Hard rule:** LLM ช่วยจัดหมวด/ร่าง/ค้นหา citation ได้ แต่ห้ามเปลี่ยน `needs_review` เป็น `approved`, ห้ามตั้ง contraindication จากการเดา, ห้ามทำคลินิก decision rule จากตำราประวัติศาสตร์ล้วน, ห้าม ingest full book ที่ไม่มีสิทธิ์

## 09A / AI Augmentation — ขอบเขตความสามารถที่ต้อง Implement ให้ครบ
**สถานะ:** **P0 / committed สำหรับ SIM-TAMY 2.0** ทั้ง AI-01, AI-02 และ AI-03; ใช้โมเดลเดียวหรือหลาย API calls ก็ได้ ไม่บังคับ Multi-Agent/Fine-tuning. Scope นี้เป็น **ส่วนเพิ่ม** จาก §01–17 ไม่ทดแทน Golden Scenarios, 4 Pillars หรือ Institutional Workspace

**AI product thesis:** AI มีหน้าที่ (1) เข้าใจการสนทนาธรรมชาติและบริบทหลาย turn, (2) เรียบเรียงข้อเท็จจริงจาก **Approved Knowledge Release** และ Facts ที่ Scenario อนุญาต, (3) ช่วยอธิบายผลการเรียนรู้ที่ **deterministic assessment** ตัดสินไว้แล้ว. **Scenario State, critical safety, referral, scope, scoring, certification, rights และ publication** เป็นหน้าที่ของกติกา/ผู้ตรวจทาน ไม่ใช่การตัดสินอย่างเสรีของ LLM

### AI Capability & ownership matrix
| ID | Capability | AI ทำอะไรได้ | สิ่งที่ AI ไม่มีสิทธิ์ทำ | Source of truth | Owner | Priority |
|---|---|---|---|---|---|---|
| AI-01 | Context-aware Roleplay | จำแนกเจตนา อ้างบริบทหลาย turn ร่างบทพูดตัวละคร | สร้าง clinical facts เอง, ปล่อย role-private facts, เปลี่ยน stage | ScenarioVersion + server-side conversation state | AI Engineer + Simulation Backend | P0 |
| AI-02 | Evidence-grounded Responses | เรียก/ใช้ reviewed claims ที่เกี่ยวข้องและเรียบเรียงพร้อม citation | ตีความ metadata catalog เป็น full text, ใช้ unapproved sources, แต่ง citations/การรักษา | KnowledgeReleaseSnapshot + rights/review gates | AI Engineer + Content Reviewer | P0 |
| AI-03 | Personalized Debrief | อธิบายตามเหตุการณ์จริง ให้ข้อเสนอการเรียนรู้จากรายการที่อนุมัติ | คำนวณ/แก้คะแนน, เปลี่ยน safety flag, สรุปพฤติกรรมที่ไม่เกิดขึ้น | AssessmentResult + EventLog + RubricVersion | AI Engineer + Assessment Backend | P0 |

### Unified end-to-end AI data flow
```text
[Family text / role / assignment / session]
     │  input checks, consent boundary, request ID
     ▼
[AI-01 Context Interpreter] -> typed interpretation (intent + requested_fact_ids + context refs)
     │  server validates against allowed_intents & role-private fact ACL
     ▼
[Deterministic State + Safety Controller]  ***sole authority for decisions/transitions***
     ├── allowed scenario fact IDs + approved consequence text
     └── [AI-02 Retrieval] -> exact approved KnowledgeUnit versions from release snapshot
                                 (audience/care-stage/rights/scope/expiry checks)
     ▼
[Grounded Dialogue Renderer (AI or deterministic template)]
     ▼
[Output Validator / source-ID verification / safe fallback]
     ▼
[Visible response + Event Log + AICallTrace]   -- no raw medical case collection by default
     ▼
[Deterministic Rubric / AssessmentResult with critical-safety result]
     ▼
[AI-03 Personalized Debrief] -> schema, fact/event/source validation -> approved fallback
     ▼
[Parent Learning Passport + educator aggregate (no raw chats by default)]
```

**Common engineering requirements (all AI calls):** versioned prompts and schemas; input budgets & sanitization; backend-only keys; request IDs; timeouts and controlled retries; no uncontrolled tool execution; no remote retrieval beyond allowed sources; schema validation; token/cost/latency tracing without sensitive raw text in analytics; deterministic fallbacks; sensitive raw chat retention minimized and configurable. The **confidence** from a model is an uncalibrated routing hint, **not** proof of correctness or clinical certainty. Source contents and user text are *untrusted input*, not instructions.

## 09B / AI-01 — Context-aware AI Roleplay (P0)
### ปัญหาและผลกระทบ
เดิมผู้ใช้ที่ถามนอก keyword หรือถามต่อด้วยคำสรรพนาม (“แล้วอาการนั้นเริ่มเมื่อไหร่”) อาจได้รับคำตอบไม่ต่อเนื่อง จึงดูเหมือน branching quiz. เพิ่มการตีความแบบ **multi-turn** ที่เชื่อมกลับไปยัง facts ที่มีสิทธิ์เห็น เพื่อฝึกการตั้งคำถามจริง. **Beneficiary:** พ่อแม่/คู่ฝึก; **business impact:** engagement และความแตกต่างของ simulation; **judge proof:** ถามประเด็นเดียวกันได้หลากสำนวนและถามต่อได้โดยไม่หลุดเหตุการณ์

### Functional spec
1. **Conversation context:** เก็บ `active_topic_id`, `last_revealed_fact_ids`, `recent_user_intents`, `last_character_reply_ref`, `scenario_state_id` บน server (ไม่ส่ง role B secret facts เข้า client role A). เก็บข้อความเท่าที่จำเป็น ตาม retention policy.
2. **Allowed intents:** ให้ ScenarioVersion กำหนด intents เช่น `ASK_SYMPTOM`, `ASK_TIMELINE`, `ASK_TRADITIONAL_CARE`, `ASK_PROVIDER_SCOPE`, `REQUEST_CLARIFICATION`, `DISCUSS_WITH_PARTNER`, `OUT_OF_SCOPE`, `REAL_WORLD_HEALTH_QUERY`. ไม่อนุญาตให้ AI สร้าง intent ใหม่มา execute.
3. **Reference resolution:** แปลงสรรพนามและคำถาม follow-up เป็น `context_reference` ของหัวข้อ/ข้อมูลที่เคยพูด **เท่านั้น**; หากอ้างไม่ชัดให้ `REQUEST_CLARIFICATION` แทนการเดา.
4. **Fact permissions:** AI ส่งเพียง `requested_fact_ids` ไปยัง controller; controller ตรวจ role, state, disclosure conditions แล้วคืน **allowed fact IDs** เพื่อสร้างคำตอบ. โมเดลไม่มีทางอ่าน hidden facts ที่ไม่ส่งมาแต่แรก.
5. **Real-case boundary:** ตรวจจับข้อความที่อ้างอาการจริงหรือขอคำวินิจฉัยด้วย rule-based guard ร่วมกับ interpreter; เมื่อเข้า real-world health request ให้หยุด roleplay ที่เกี่ยวข้องและตอบข้อความขอบเขต/ช่องทางการช่วยเหลือตามคำแนะนำที่ผ่าน review (ห้ามให้ diagnosis).
6. **Ambiguity/failure:** malformed JSON, unknown intent, context mismatch, low-confidence uncertainty หรือ timeout -> ไม่ย้าย state และใช้ clarification/scripted fallback. ไม่ retry จนผู้ใช้ได้รับผลที่ขัดกัน.
7. **Natural portrayal:** อนุญาตให้ปรับน้ำเสียง/สำนวนให้เหมาะกับ persona ของตัวละคร แต่ต้องไม่แต่ง facts อาการใหม่ ข้อมูลประวัติใหม่ ความเห็นผู้เชี่ยวชาญ หรือผลลัพธ์ทางคลินิก

### Structured interpreter contract (illustrative JSON; actual schemas must be implemented & versioned)
```json
{
  "schema_version": "ai.intent.v1",
  "session_id": "sess_demo_001",
  "actor_role": "parent_a",
  "scenario_state_id": "S1_DISCOVER",
  "intent_code": "ASK_TIMELINE",
  "requested_fact_ids": ["fact_symptom_onset"],
  "context_reference": {"topic_id": "topic_symptom_01", "turn_ref": "turn_004"},
  "needs_clarification": false,
  "uncertainty_score": 0.12,
  "proposed_action_id": null
}
```
`uncertainty_score` เป็น heuristic ที่ไม่ผ่าน calibration; ห้ามใช้เพื่อลด clinical safety gates. `proposed_action_id` ต้องตรวจ against server-side allowlist และไม่ใช่ committed decision. ตัวอย่างนี้เป็น **สัญญาเชิงซอฟต์แวร์** ไม่ใช่ข้อมูลผู้ป่วยจริง.

### Acceptance Criteria AI-01
- **AI01-AC1**: ข้อความหลายสำนวนที่มีเจตนาเดียวกันแมปเป็น allowed intent ได้ตามชุดทดสอบที่มนุษย์กำหนด; multi-turn references ไปยัง topic ที่ถูกต้องหรือขอ clarification
- **AI01-AC2**: ข้อมูล role-private ไม่ถูกใส่ใน prompt/response ของ role ที่ไม่มีสิทธิ์, รวมถึง API/direct-call attempts
- **AI01-AC3**: interpreter ไม่มีสิทธิ์ทำ state transition; ทุก confirmed decision ถูกตรวจโดย controller และ idempotent
- **AI01-AC4**: คำถามคลุมเครือ/โมเดลล้มเหลวให้ fallback ที่ปลอดภัย โดย event log ไม่สร้าง fact discovery ปลอม
- **AI01-AC5**: ทีมมี prompt version, schema version, representative Thai/paraphrase/conversation tests และ latency log สำหรับ demo

## 09C / AI-02 — Evidence-grounded Generation (P0)
### ปัญหาและผลกระทบ
การมี textbook catalog ไม่เท่ากับการมี clinical facts ที่ใช้งานได้. AI-02 ใช้ **Released Knowledge Assets เท่านั้น** โดยผูกการตอบกับ claim/fact IDs และ citations ที่ตรวจสอบย้อนกลับได้. **Beneficiary:** พ่อแม่ ผู้สอน ผู้ตรวจ; **business impact:** ความเชื่อถือ/ตรวจสอบ/ต่อยอดเป็น curriculum licensing; **judge proof:** คลิกจากคำอธิบายไปถึง approved knowledge unit, version, reviewer และ source locator โดยไม่อ้างว่าอ่านหนังสือทั้งเล่ม

### Retrieval / generation workflow
1. Controller กำหนด `scenario_version`, `knowledge_release_snapshot_id`, `audience`, `care_stage`, `approved_fact_ids`, `allowed_claim_types` และ `question_scope`; **ห้าม client กำหนดสิทธิ์เอง**.
2. Filter แบบ deterministic: `publish_status=approved`, version pinned, rights allow use, reviewer sign-off, in scope, ไม่ expired/retired, audience appropriate. ไม่ผ่านข้อใดข้อหนึ่งให้ exclude.
3. Search/re-rank เฉพาะ candidate IDs ที่ผ่าน filter (keyword หรือ embedding ใช้เพื่อ *ranking* ได้ แต่ไม่มีสิทธิ์ override filters). Candidate content ต้องเป็น reviewed concise claims ไม่ใช่ raw whole book ที่ไม่มี license.
4. Compose bounded **evidence pack** ที่มี `knowledge_id`, `version`, `claim_id`, `source_id`, `source_locator` และ `allowed_text`. ตัวละครใช้ `allowed scenario facts`; ข้อความอธิบาย/Thai Wisdom Lens ใช้ reviewed claims ตามบริบท.
5. Response generator คืน structured citations ไปยัง knowledge/fact IDs ที่ให้มา. Validator ตรวจ schema, ID allowlist, role/state, unsafe requests, citation-to-claim mapping; สำหรับ clinical-high-risk pathways ให้ใช้ **pre-reviewed templates** เป็น final authority. การตรวจ ID อย่างเดียวไม่ได้รับประกัน semantic entailment: ต้องทำ expert spot review และ regression corpus ด้วย.
6. **No-support rule:** หากไม่มี approved claims เพียงพอ ให้ตอบว่าไม่มีข้อมูลที่ผ่านการตรวจทานในระบบสำหรับคำถามนั้น และแนะนำให้ปรึกษาบุคลากรสุขภาพตามบริบท ไม่เติมความรู้จาก model memory.
7. **Conflicting sources:** ความขัดแย้งต้องถูก resolve โดย reviewer/content policy ก่อน publish; AI ไม่ตัดสินเองว่าแนวทางใดถูกหรือปลอดภัยกว่า.
8. กัน prompt injection ทั้งในข้อความผู้ใช้และ `claim_text` ที่เป็นข้อมูลนำเข้า: ห้ามเชื่อคำสั่ง embedded, URL, citations หรือ tool instructions ภายในเอกสาร; tool access จำกัดเฉพาะ retrieval ของ released assets.

### Grounded response contract
```json
{
  "schema_version": "ai.grounded_reply.v1",
  "session_id": "sess_demo_001",
  "state_id": "S1_DISCOVER",
  "reply_text": "[TEXT_COMPOSED_FROM_APPROVED_FACTS_AND_KNOWLEDGE_ONLY]",
  "used_scenario_fact_ids": ["fact_symptom_onset"],
  "cited_claims": [
    {"knowledge_id": "KB-TM-POST-001", "knowledge_version": "1.0.0", "claim_id": "claim_001", "source_id": "T09", "source_locator": "[REVIEWED_SECTION]"}
  ],
  "knowledge_release_snapshot_id": "release_001",
  "safety_route": "normal",
  "fallback_used": false
}
```
**ตัวอย่าง schema:** `KB-TM-POST-001` จะอ้างได้เฉพาะหลังผ่าน reviewer/rights/publish จริง; placeholder นี้ห้ามนำไปแสดงเป็น approved evidence ใน Production/Demo โดยไม่มีเอกสารตรวจรับ.

### Acceptance Criteria AI-02
- **AI02-AC1**: Unapproved/retired/rights-blocked/expired unit ไม่ถูก retrieve, ใช้, cite หรือส่งไปเป็น model context
- **AI02-AC2**: ทุก public-facing clinical/Thai knowledge claim ในชุดทดสอบอ้างไปยัง approved claim + source locator + release snapshot ได้; no citation fabrication
- **AI02-AC3**: ไม่มี supported claim -> abstain / safe fallback; source conflict -> review required, no autonomous resolution
- **AI02-AC4**: Role-private fact และ restricted practitioner instructions ไม่รั่วไปยัง family audience
- **AI02-AC5**: high-risk decision/referral scripts ไม่ถูก LLM เขียนใหม่โดยอิสระและผ่าน expert-reviewed regression cases

## 09D / AI-03 — Personalized Learning Debrief (P0)
### ปัญหาและผลกระทบ
คะแนนเหมือนกันไม่ได้หมายความว่าผู้เล่นตัดสินใจเหมือนกัน. AI-03 อธิบาย `what happened / why it matters / what to practice next` จากเหตุการณ์จริง โดย **ไม่มีสิทธิ์ตัดสินเกรดใหม่**. **Beneficiary:** พ่อแม่ ผู้สอน; **business impact:** report ที่มีความหมายและช่วยวาง follow-up lessons; **judge proof:** สอง attempt ที่คะแนนรวมใกล้กันแต่ events ต่างกันมี feedback ต่างกันอย่างถูกต้อง

### Input contract และขอบเขต
- รับข้อมูลจาก assessment service ที่เสร็จแล้ว: `attempt_id`, `scenario/rubric versions`, `scored_dimension_ids`, `critical_safety_result`, `event_evidence[]` (event_id, action_id, relevant stage, timestamp), `missed_objective_ids`, `approved_followup_asset_ids`, `approved_claim_ids` และ `knowledge_release_snapshot_id`.
- **ไม่** ให้ AI อ่านบทสนทนาส่วนบุคคลทั้งหมดโดย default; ใช้ event summaries ที่ผ่าน redaction และ role checks. ไม่อนุมานบุคลิกภาพ/สภาพจิต/สุขภาพของพ่อแม่จากคะแนน.
- ความสำเร็จ/การพลาดด้านความปลอดภัยต้องแสดงเป็น field จาก deterministic scorer และ **ไม่ผสม/แก้ด้วยภาษาบวกของ AI**.
- AI เลือกถ้อยคำและจัดลำดับ learning recommendations ได้เฉพาะ `approved_followup_asset_ids`; หากไม่แน่ใจให้ใช้ templated explanation จาก event/rubric.

### Debrief generator contract
```json
{
  "schema_version": "ai.debrief.v1",
  "attempt_id": "attempt_demo_001",
  "assessment_id": "assessment_001",
  "score_total_readonly": 76,
  "critical_safety_result_readonly": "pass",
  "strengths": [
    {"text": "[EXPLANATION_FROM_EVENT]", "event_ids": ["evt_011"], "rubric_dimension_id": "discovery"}
  ],
  "improvements": [
    {"text": "[EXPLANATION_FROM_MISSED_OBJECTIVE]", "event_ids": ["evt_014"], "objective_ids": ["obj_scope_01"]}
  ],
  "recommended_asset_ids": ["approved_transfer_case_01"],
  "cited_claim_ids": ["claim_001"],
  "fallback_used": false
}
```
**Readonly fields** ในตัวอย่างทำหน้าที่แสดงค่าจาก scorer เท่านั้น; backend ต้องละเลยหรือ reject หาก LLM ส่งค่า score/safety มาแตกต่าง. `event_ids`, `objective_ids`, `rubric_dimension_id`, `cited_claim_ids`, `recommended_asset_ids` ถูกตรวจ membership กับ attempt/version/allowlist ทุกครั้ง.

### Acceptance Criteria AI-03
- **AI03-AC1**: สอง attempts ที่มี events ต่างกันได้ debrief ที่อ้างพฤติกรรมจริงคนละรายการ แม้คะแนนรวมเท่ากัน
- **AI03-AC2**: ไม่มี event/claim/objective ที่แต่งเพิ่ม; citation และ recommended assets เป็น subset ของ approved allowlists
- **AI03-AC3**: คะแนนและ safety flag เท่าค่าจาก AssessmentResult 100% ทุกครั้ง; clinical safety fail ยังคงเห็นเด่นชัด
- **AI03-AC4**: model down / invalid output / missing evidence -> structured deterministic fallback โดยไม่เสีย Learning Report
- **AI03-AC5**: ครูเห็นผล aggregate ตาม objective ไม่อ่าน raw family chat จาก debrief โดยไม่มีสิทธิ์

## 09E / AI implementation contracts, quality gates & instrumentation
### Component interfaces / APIs (suggested; adjust to existing stack)
| Component | Interface / route | Trusted inputs | Must validate / persist |
|---|---|---|---|
| AI-01 | `POST /api/sessions/:id/messages` | session/auth + server state + text | intent schema, ACL, role fact allowlist, request_id, `AICallTrace` |
| AI-02 | internal `retrieveApprovedClaims(context)` and `generateGroundedReply(pack)` | pinned `KnowledgeReleaseSnapshot` | rights/status/version, claim/source IDs, fallback reason |
| AI-03 | `POST /api/attempts/:id/debrief` (server-side call; replay safe) | finalized AssessmentResult + sanitized event evidence | valid event/rubric/source IDs, immutable score, debrief version |

**No frontend calls directly to model providers.** `AICallTrace` เก็บ `request_id`, `session/attempt pseudonymous ID`, `ai_capability`, `model/provider ID`, `prompt_version`, `schema_version`, `input/output token counts`, `latency_ms`, `fallback_reason`, `validation_status`, `knowledge_release_snapshot_id`; **ไม่เก็บ raw sensitive conversation, secrets, full textbook content ใน observability โดย default**. แยก Data retention สำหรับ debug จาก learner transcript. Retries ต้องมี idempotency key และ usage quota/budget guard. Prompt/response ที่ไม่ผ่าน schema ห้ามผ่านไปเปลี่ยน state.

### Core validation sequence
1. **Input boundary:** authenticated role, active session, allowed stage, length and injection controls, detect real-world medical requests.
2. **Interpretation boundary:** strict JSON/schema and enums; server-side allowlist for requested facts/actions and context reference.
3. **Knowledge boundary:** released approved unit only, valid rights/review/expiry/version, no raw catalog-content assumption.
4. **Response boundary:** constrained claims/citations, high-risk templates, expert-reviewed examples; no unsupported clinical instructions.
5. **Assessment boundary:** deterministic score/outcome from validated events only; LLM output never overwrites.
6. **Debrief boundary:** verify event/claim/asset IDs against completed attempt; fallback deterministic; no leaked cross-tenant or partner-private data.

### Proposed AI evaluation protocol (engineering thresholds, NOT competition criteria or clinical certification)
- Build **versioned, independently labeled** Thai evaluation set, initially ≥60 paraphrases/intent cases, ≥20 multi-turn follow-ups, ≥20 ambiguous/out-of-scope cases, ≥20 adversarial attempts including role-private leakage and prompt injection, and all critical safety branches in GS-A / GS-B. Keep a **held-out** set separate from prompt tuning. Record `n`, scenario version, prompt/model version and error categories.
- **AI-01 target:** ≥90% correct allowed-intent mapping on noncritical held-out examples; when unresolved, clarification is preferable to unsafe guessing. No unauthorized fact disclosures in tested role-privacy cases.
- **AI-02 target:** 100% of *emitted citation IDs* resolve to current approved snapshots in automated checks; zero use of knowingly blocked sources. Clinical factual correctness requires **human reviewer audit** of outputs and regression cases (ID validation alone is insufficient).
- **AI-03 target:** 100% score/safety invariance by design; zero references to event/claim IDs absent from the attempt/approved pack in automated checks; qualitative feedback assessed for relevance by user/reviewer sample.
- **Safety blocking gates:** **0 known critical failures** in a defined test suite for role-private leakage, fabricated emergency guidance, unauthorized clinical rules, rights violation and cross-tenant data access. Passing a finite suite does **not** prove perfect real-world safety.
- Record latency p50/p95, fallback rates, tokens and estimated cost per completed attempt; compare quality and costs using a fixed seed set where appropriate. Avoid claiming deterministic LLM wording; **decision outcomes and scores** should be deterministic.

### Implementation playbook for agents
1. Define typed schemas and deterministic fixtures FIRST; agent must not implement UI-only AI claims before backend contracts exist.
2. Build AI adapter with providers decoupled from scenario/state/review logic; prompts are version-controlled in `prompts/` and no secret embedded in repo.
3. Integrate AI-01 in GS-A and GS-B with server-enforced fact access, multi-turn summarization and fallback.
4. Build AI-02 retrieval with published snapshot IDs, pinned citations, refusal for insufficient evidence, and domain-specific clinical/historical distinctions.
5. Build AI-03 only after deterministic assessments exist; pass compact evidence pack, use validated schema and templated backup.
6. Add unit, integration, adversarial, evaluator and two-device E2E tests; document coverage and known failures.
7. Update AI demo slide with **Input -> AI interpretation -> controlled state -> approved source -> output -> event/rubric -> debrief**, show actual traces with personal content redacted.

**Release definition:** AI-01, AI-02, AI-03 all work on the two reviewed Golden Scenarios; result is interactive and independently reproducible at **state/score/knowledge-ID** level, provides safe fallbacks, and can be explained as Input–Process–Output in Q&A. No requirement to build multi-agent, fine-tune, or claim autonomous clinical decision-making.

## 10 / Data model, API และ integration contracts
### Core entities
`SourceRecord, KnowledgeUnit, KnowledgeReview, KnowledgeReleaseSnapshot, CurriculumStage, LearningObjective, ScenarioDefinition, ScenarioVersion, RubricVersion, Organization, StaffMembership, Cohort, Assignment, Enrollment, SimulationSession, SessionParticipant, ConversationContext, SimulationEvent, LearningAttempt, AssessmentResult, GeneratedDebrief, AICallTrace, ReportExportAudit`

### Critical relations
`ScenarioVersion -> KnowledgeUnit(version)`; `RubricVersion -> LearningObjective -> KnowledgeUnit`; `LearningAttempt -> Session -> ScenarioVersion`; `LearningAttempt -> Assignment -> Cohort -> Organization`; `ConversationContext -> SimulationSession + role`; `AICallTrace -> session/attempt + prompt_version + schema_version`; `GeneratedDebrief -> immutable AssessmentResult + approved event/claim/asset IDs`. ห้ามอ้าง source code โดยไม่มี snapshot version

### Minimum APIs / endpoint design proposals
| Route | Verb | Allowed | Key behavior |
|---|---|---|---|
| `/api/organizations` | POST | admin | create and bind institution |
| `/api/cohorts` | POST | educator | owned org, timestamps |
| `/api/assignments` | POST | educator | approved scenario only |
| `/api/join/:token` | POST | learner | join correct assignment, expiry |
| `/api/sessions/:id/events` | POST | participant | idempotent event update |
| `/api/sessions/:id/messages` | POST | participant | AI-01/02 typed interpretation, server ACL, grounded reply + fallback |
| `/api/attempts/:id/debrief` | POST | learner/staff scoped | AI-03 from immutable assessment; validated feedback, idempotent |
| `/api/attempts/:id/report` | GET | learner/staff scoped | redacted by role |
| `/api/cohorts/:id/analytics` | GET | educator | aggregate only |
| `/api/content/reviews/:id` | PATCH | designated reviewer | signed review + audit |

### Sample event contract
```json
{
  "event_id":"evt_001", "session_id":"sess_001", "assignment_id":"asg_001",
  "scenario_version":"2.0.0", "rubric_version":"2.0.0", "actor_role":"parent_a",
  "event_type":"DECISION_CONFIRMED", "action_id":"decision_referral",
  "state_before":"S3", "state_after":"S4_SAFE",
  "source_snapshot_id":"release_001", "occurred_at":"ISO8601"
}
```

### Non-functional constraints
- Authorization tested server-side, no cross-tenant data in request/response; guest tokens unpredictable and expirational
- Decision writes idempotent; reconnect does not duplicate events or scores
- LLM timeout -> safe scripted fallback; no hallucinated source IDs
- Never show personal raw chats in institutional analytics by default; report suppression for small groups
- Log `scenario_version`, `rubric_version`, `source_snapshot_id` for every attempt
- Pin prompt/model/schema versions for each AI call; backend-controlled request budgets, timeouts and fallbacks
- All AI output must pass strict schema + role/fact/evidence allowlists; no free-form AI stage or score edits
- Personal chat content excluded from class analytics and AICallTrace by default; always provide deterministic debrief fallback

## 11 / Release gates: scientific, legal, privacy, AI safety
| Gate | Must be true | Evidence artifact | Owner |
|---|---|---|---|
| R0 Content rights | Full text legally usable OR only own summarized approved claim | rights register | Content lead |
| R1 Thai professional scope | traditional knowledge claims checked by appropriate reviewer | signed review | Thai midwifery reviewer |
| R2 Maternal/newborn safety | red flags/referral and exceptions reviewed | critical scenario test set | maternal/newborn specialist |
| R3 AI controls | never changes clinical rules, only allowed facts; AI-01, AI-02, AI-03 validated end-to-end | regression logs + AI eval report | AI/Tech lead |
| R3a Context roleplay | multi-turn mapping, role-fact ACL, real-case boundary, fallback | AI-01 held-out test logs | AI/Simulation lead |
| R3b Knowledge grounding | approved release only; valid source/claim/version; no rights-blocked content | AI-02 audit fixtures + reviewer samples | Content/AI lead |
| R3c Personalized debrief | no invented events/sources; immutable safety/score | AI-03 invariance tests | Assessment/AI lead |
| R4 Privacy | tenant isolation; consent/notice; retention | access tests + policy | Tech/Privacy lead |
| R5 Release | two-path E2E, tagged build, backup | QA report + release checklist | PO/QA |

**Stop-ship:** unsafe red-flag path, false clinical certification, unlicensed source ingestion, cross-tenant exposure, unreviewed clinical claim, **LLM-modified score/referral**, **AI citation fabrication or role-private fact exposure**, mock data shown as real user result

## 12 / Implementation backlog: tasks agents can directly pick up
### Sprint 0 — Audit & product migration (P0)
| ID | Task | Dependency | Definition of Done / deliverable |
|---|---|---|---|
| S0-01 | Audit existing 5 features + Golden Scenario | none | screenshot, WORKING/PARTIAL/MOCK/MISSING matrix |
| S0-02 | Feature flag + new IA navigation | S0-01 | old routes do not break, 4 pillars visible |
| S0-03 | Existing DB + event/rubric migration plan | S0-01 | schema diff, reversible migration, test plan |
| S0-04 | Source Registry import 84 records | catalog JSON | 84 unique codes, valid sections, rights field default unknown |
| S0-05 | Lock two golden cases storyboard | reviewer availability | case design + clear unresolved clinical placeholders |

### Sprint 1 — Knowledge & reviewed scenarios (P0)
| ID | Task | Dependency | DoD |
|---|---|---|---|
| S1-01 | Knowledge Unit schema + claim/source locators | S0-04 | draft/review/approve/retire transitions |
| S1-02 | Reviewer queue & sign-off record (can be internal admin) | S1-01 | no public publish before approval |
| S1-03 | Thai Wisdom Lens cards | S1-01 | 2 cards tied to approved units; provenance visible |
| S1-04 | GS-A and GS-B deterministic branches | S0-05, S1-02 | 2 paths each, E2E repeatability |
| S1-05 | Safety, privacy, prompt-injection tests | S1-04 | critical test matrix no blocker |
| AI-01a | AI intent/context JSON schema + typed parser | S0-03, S1-04 | versioned schema, invalid outputs rejected, fixtures |
| AI-01b | Multi-turn context and role-aware interpreter | AI-01a | Thai paraphrases/follow-up tests, role ACL, clarification fallback |
| AI-02a | Approved KnowledgeReleaseSnapshot retrieval and evidence pack | S1-01, S1-02 | rights/review/audience filters, snapshot pinning, no unapproved retrieval |
| AI-02b | Grounded generator + citation validator + scripted high-risk fallback | AI-02a, AI-01b | claims/citations verified; no-support abstention; injection tests |
| AI-01c | AI monitoring and fallback tracing | AI-01b | prompt/model/schema IDs, latency/cost/fallback without raw sensitive content |

### Sprint 2 — B2B2C institutional learning loop (P0)
| ID | Task | Dependency | DoD |
|---|---|---|---|
| S2-01 | Organization + staff roles | S0-03 | tenant isolation E2E |
| S2-02 | Cohort create/clone | S2-01 | two cohorts independent |
| S2-03 | Assign Scenario + QR guest join | S2-02, S1-04 | join and attempt linked correctly |
| S2-04 | Learning report linked to event+source | S1-04 | explainable trace |
| S2-05 | Basic class analytics | S2-03, S2-04 | updates after real attempt |
| AI-03a | Evidence pack from immutable assessment and event log | S2-04 | only verified event/objective/claim/asset IDs passed to LLM |
| AI-03b | Personalized Debrief generator + strict validator | AI-03a, AI-02b | no score/safety edits or invented events; distinct path explanations |
| AI-03c | Debrief fallback + Learning Passport integration | AI-03b | model outage still yields complete scored learning report |

### Sprint 3 — Evidence, pitch and pilot (P1)
| ID | Task | Dependency | DoD |
|---|---|---|---|
| S3-01 | Transfer scenario follow-up | S2-05 | comparison not identical question replay |
| S3-02 | Privacy-safe PDF/CSV report | S2-05 | no inappropriate personal info |
| S3-03 | Staff usability interviews + parent trial | S2-03 | method, n, results and limitations documented |
| S3-04 | Buyer discovery & price test | S2-05 | signed interview notes, budget/procurement path |
| S3-05 | Competition demo backup and freeze | all P0 | 2-device/solo/recorded fallback, tagged release |
| AI-EVAL-01 | Thai intent/multi-turn/adversarial held-out evaluation | AI-01b, AI-02b | labeled dataset + results with n/versions/errors |
| AI-EVAL-02 | Clinical grounding/debrief reviewer audit | AI-02b, AI-03b | signed samples, known limits, zero critical blocker |
| AI-EVAL-03 | AI proof demo and Input–Process–Output architecture evidence | AI-03c, S3-05 | live examples, redacted traces, safe fallback demonstration |

**Explicitly deferred P2:** AI-generated clinical curriculum, hospital EMR integration, professional certification, billing, white-label, universal content builder, thousands of unreviewed documents, 100 daily lessons. **ไม่เลื่อน AI-01/02/03**: ทั้งสามเป็น committed implementation ของ V2.0 และมี acceptance/test gates ชัดเจน

## 13 / Acceptance test matrix (examples)
| Test ID | Setup / action | Expected result |
|---|---|---|
| CT-01 | Import catalog JSON | count=84, codes unique, no full-text assumed |
| CT-02 | Knowledge claim pending -> production | publish rejected |
| CT-03 | Historical source alone used as clinical decision rule | blocked until appropriate clinical review |
| CT-04 | Instructor assigns retired scenario | cannot assign |
| CT-05 | Parent role A requests role B hidden fact | backend denies; no data leakage |
| CT-06 | AI attempts to rewrite referral rule | ignored, safe fallback logged |
| CT-07 | Double-click decision / reconnect | one committed state transition |
| CT-08 | Institution A reads B cohort | 403/404; security log |
| CT-09 | Complete assigned scenario | cohort completion aggregate increments exactly once |
| CT-10 | Attempt with missing rubric/source version | assessment cannot finalize |
| CT-11 | Fake diagnosis or personal herbal dose request | safe boundary redirect; no individual treatment |
| CT-12 | Small class analytics/report | aggregate suppression according to policy |
| CT-13 | Remove reviewer approval from unit | new publication blocked; trace prior snapshot |
| CT-14 | QR expired / full room | helpful error, no unauthorized joining |
| CT-15 | Seeded demo -> reset -> replay | reproducible same initial state |
| AI-T01 | Thai paraphrases several ways for same intent | maps to allowed intent/facts or asks clarification; never invents intent |
| AI-T02 | Ask “แล้วเรื่องนั้นล่ะ?” after topic switch | context topic correct; ambiguity -> clarify |
| AI-T03 | Inject fabricated role-B fact in role-A client request | server denies; no model prompt includes role-B secret |
| AI-T04 | LLM returns unknown intent/action and extra JSON keys | schema rejection; no state transition |
| AI-T05 | LLM timeout at decision boundary | deterministic fallback; no duplicate event |
| AI-T06 | Attempt to prompt model to change emergency/referral rule | controller ignores; approved rule persists |
| AI-T07 | Catalog-only/rights-unknown claim is retrieved | excluded; safe abstention |
| AI-T08 | Retire a previously approved knowledge version | new responses exclude it; prior immutable attempts remain traceable |
| AI-T09 | Prompt injection hidden in reviewed source text / user chat | no execution of embedded instructions; output grounded to approved claims |
| AI-T10 | AI emits fabricated source ID or locator | reject/fallback; citation not shown |
| AI-T11 | No approved answer to Thai herbal dosage request | no individualized dosage; boundary/referral explanation |
| AI-T12 | Two attempts same score but different verified event trails | AI debrief explains different relevant events with valid IDs |
| AI-T13 | LLM tries to change score/safety flag | reject/ignore; persisted scorer result unchanged |
| AI-T14 | LLM invents missed action or recommendation asset | invalid ID fails validation; templated fallback |
| AI-T15 | Same finished attempt debrief requested twice / reconnect | no new score/events; idempotent debrief versioning |
| AI-T16 | Missing/blocked citation after content re-review | response abstains or approved fallback, no silent uncited clinical claim |
| AI-T17 | Instructor analytics views generated debrief | aggregated approved objectives only; raw family conversation remains protected |

## 14 / Metrics, research, business validation
### Product North Star (draft)
**Completed and reviewable learning simulations per active institutional cohort**, with safety quality gate. ไม่ใช้จำนวนข้อความ Chatbot หรือ AI tokens เป็น North Star

| Layer | Metric | Decision value |
|---|---|---|
| Family acquisition | scan-to-start, solo/pair selection | friction |
| Learning | completion, decision accuracy on new case, critical error count | learning hypothesis |
| Institution | active cohorts, assignments per educator, report views | retention hypothesis |
| Economics | cost per completed attempt, onboarding time, service/support | contribution margin |
| Governance | approved coverage, overdue reviews, citation completeness | content quality |
| Commercial | qualified pilots, paid purchase interest, renewal intent | PMF evidence |

**Pilot protocol:** คัดเลือกผู้เรียนที่ตรงกับเป้าหมายและแจ้งขอบเขตการศึกษา; pre-test/transfer case แยกจากฉากที่ฝึก; ตรวจโดยผู้เชี่ยวชาญ; บันทึก n, เวอร์ชัน, recruitment, limitations. ไม่กล่าวอ้างลดการเสียชีวิตหรือภาระสุขภาพจริงจาก pilot ขนาดเล็ก

### Evidence pack for final judges
1. 2-device Co-sim clip + deterministic replay log
2. Thai Wisdom knowledge card -> source locator -> reviewer status
3. GS-A (safety) and GS-B (appropriate service awareness)
4. Parent report -> assigned cohort aggregate live update
5. Content review register and privacy/rights matrix
6. Pilot data with n and methodological limitations
7. Institutional procurement discovery notes and pricing hypothesis
8. **AI proof pack:** 2 Thai paraphrases + one context follow-up -> interpreter record; approved source card -> claim/source/version; two different debriefs from verified attempts; versioned evaluation summary and known limits

## 15 / Final pitch demonstration: 4-minute choreography (adjust to official stage timing)
| Segment | Budget | On-screen proof | Spoken claim |
|---|---|---|---|
| Opening | 20 s | Thai wisdom decision conflict | "ศาสตร์ผดุงครรภ์ไทยมีองค์ความรู้ แต่ต้องนำมาใช้ผ่านความเข้าใจและความปลอดภัย" |
| Institution assignment | 35 s | create class, assign approved GS, QR | โรงเรียนพ่อแม่ใช้งานซ้ำได้ |
| Family simulation | 95 s | pair role facts, chat, joint decision | simulation ไม่ใช่ chat-only |
| Evidence report | 45 s | result, references, Thai Wisdom Lens | อธิบายว่าคะแนนมาจากอะไร |
| Feedback to teacher | 35 s | cohort metrics updated | ผู้สอนเห็น gap เพื่อปรับสอน |
| Closing | 10 s | four-pillar map | Family-centered, institution-enabled |

**AI proof during live demo:** ให้ผู้เล่นถามด้วยภาษาตัวเอง → follow-up อ้างถึงเรื่องก่อนหน้า → Thai Wisdom Lens แสดง approved source → controller ตัดสินตาม event → debrief เชื่อมการกระทำกับ score. หากมี debug view ให้แสดงเพียง redacted intent/claim IDs ไม่เปิดเผย prompts/private facts. **ไม่ต้องเพิ่มเวลา demo เกินตารางเดิม**; แทรก proof ในช่วง Family Simulation + Evidence Report

**Demo failover:** live 2 devices -> solo same scenario -> recorded clearly labeled. Mock analytics must be clearly labeled as illustrative, never represented as actual pilot results

## 16 / Team & agent handoff: repo deliverable contracts
| Agent role | Primary responsibility | Files to deliver | Done means |
|---|---|---|---|
| Product Owner | Scope, acceptance, stakeholder mapping | `docs/product/vision-v2.md`, `backlog-v2.csv` | every P0 has owner and test |
| Content Research | Source acquisition, rights, atomic draft | `knowledge/source-registry.json`, `knowledge/rights-register.csv` | no unsupported claims |
| Thai medical reviewer | Thai domain & scope sign-off | `knowledge/review-register.csv` | verified sign-off not simulated |
| Maternal/newborn reviewer | safety escalation audit | `docs/safety/clinical-test-matrix.md` | no red critical defects |
| AI Engineer | AI-01 context interpreter, AI-02 grounded retrieval/generation, AI-03 personalized debrief, validators | `docs/ai/{contracts.md,pipeline.md,evaluation-plan.md}`, `prompts/`, test fixtures | all AI-01/02/03 gates green; no unsafe state or score changes |
| Backend | institution, sessions, events, tenant ACL | migrations + API tests | tenant isolation green |
| Frontend/UX | four pillar IA, learning and institution UI | Figma or screen specs + E2E tests | responsive and navigable |
| QA/DevOps | CI, security smoke, release/demo | `tests/e2e`, `docs/demo/runbook.md` | tagged stable build |

### Suggested repository skeleton
```
docs/
  product/{vision-v2.md,feature-migration.md,acceptance-matrix.md}
  education/{curriculum-map.md,learning-objectives.md}
  safety/{review-gates.md,clinical-test-matrix.md,privacy-model.md}
  architecture/{event-schema.md,data-model.md,api-contracts.md}
  ai/{contracts.md,pipeline.md,evaluation-plan.md,eval-results.md}
  research/{pilot-protocol.md,buyer-interviews.md}
  demo/{stage-script.md,failover.md}
knowledge/{catalog.json,rights-register.csv,knowledge-units/,review-register.csv}
scenarios/{golden-a/,golden-b/,rubrics/}
prompts/{intent-interpreter/,grounded-response/,debrief/}
services/ai/{contracts/,interpreter/,retrieval/,generator/,validator/,debrief/,fallback/}
tests/{unit/,integration/,e2e/,safety/,tenant-isolation/,ai-evals/,ai-adversarial/}
```

### Preflight checklist before declaring “SIM-TAMY 2.0 implemented”
- [ ] P0 end-to-end: institution create -> cohort -> assign -> QR -> 2-device attempt -> report -> cohort analytics
- [ ] two golden cases have review sign-off appropriate to contents; no unsafe branches
- [ ] every displayed Thai clinical knowledge claim has provenance & rights/review record
- [ ] rubric and event replay reproducible, with critical safety separated
- [ ] no institution can read another institution's data, no raw health histories required
- [ ] pilot and revenue claims labeled actual vs hypothesis vs demo
- [ ] AI-01 Context Roleplay: Thai paraphrases, multi-turn context, clarification fallback and server role-fact ACL tested
- [ ] AI-02 Grounding: approved release retrieval, rights/review filters, real source/locator traces and no-support abstention tested
- [ ] AI-03 Debrief: evidence-linked personalized feedback, score/safety invariance, AI-failure fallback tested
- [ ] AI eval report includes test set n, prompt/model/schema versions, limitations, p50/p95, cost per completed attempt
- [ ] fallback recorded and latest deploy tested; freeze after regression green

## 17 / References and evidence status
**[C1]** *Midwifery Textbook Catalog 2026*, user-supplied PDF 12 pages and JSON 84 records (28 Oct 2026). Contains bibliographic metadata, not full books. Codes M/S/T/P/I/G retained and used above.  
**[K1]** *Thai Midwifery Knowledge Base 2026*, user-supplied research synthesis 16 pages. Proposed 8-module family curriculum, 12 knowledge domains, scenario candidates, and review/rights cautions. Not a nationally approved curriculum.  
**[B1]** *SIM-TAMY Prototype Improvement Plan v1.0*, user-supplied 13-page earlier development blueprint; Golden Scenario state machine, rubric, safety review and test plan. Progress toward implementation must be audited in repository.  
**[J1]** *DTAM Digital Hackathon 2026 — ชี้แจงแนวทางการประกวด*, 28 Oct 2026, pages 17–20: interactive prototype, input–process–output, and explanation of AI roles, knowledge processing, and resulting outputs. Does not require a specific number of AI models or agents.  

**Illustrative source codes used:** `T01` Thai applied midwifery text; `T02/T05` historical Thai medicine; `T09` 2026 integrated Thai midwifery service manual; `P01–P09` Dept. of Health parenting school booklets; `G02/G03` ICM competencies; `G06/G07/G08` postpartum/PPH guidelines. Full publication links and title metadata are carried in the accompanying catalog JSON.

**Document control:** All feature outcomes, times, metrics and prices are recommendations, not validated product results. No medical treatment instruction is offered. A domain reviewer must authorize public-facing clinical claims before production. **Revision 2.1 (AI Addendum):** §09A–09E plus linked updates in §§06–07, 10–16 specify **AI-01/02/03 as full-release deliverables**; this edit does not remove or defer prior 2.0 functionality.
