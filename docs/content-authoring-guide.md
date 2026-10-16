# คู่มือเขียนเคส SIM-TAMY (T-012)

คู่มือนี้สำหรับทีม Content ที่เขียนข้อมูลจำลองเพื่อการศึกษา ไม่ใช่คำแนะนำทางการแพทย์หรือเกณฑ์รับรองความสามารถ ห้ามใส่ข้อมูลผู้ป่วยจริง และให้ผู้เชี่ยวชาญตรวจความถูกต้องทางคลินิกก่อนเปลี่ยนสถานะเป็น `Approved` ทีม Engineering ดูแลโมเดลและ schema; ทีม Content ดูแล `content/cases/**` เท่านั้น

## โครงสร้างไฟล์

สร้างโฟลเดอร์ `content/cases/<case_id>/` โดยชื่อโฟลเดอร์ต้องตรงกับ `case_id` ใน `case.yaml` และมีไฟล์ครบสามไฟล์:

| ไฟล์ | เนื้อหา | JSON Schema สำหรับ editor |
|---|---|---|
| `case.yaml` | สถานะเคส, persona/variants, facts, decision options, branch rules, outcome scripts และ references | `content/schemas/case.schema.json` |
| `actions.yaml` | รายการ Action ID, ประเภท, ตัวอย่างคำถาม/การกระทำ และแหล่งอ้างอิง | `content/schemas/actions.schema.json` |
| `rubric.yaml` | competencies, รายการประเมิน, checks, findings และแหล่งอ้างอิง | `content/schemas/rubric.schema.json` |

`DEV-001` เป็น fixture สังเคราะห์สำหรับทดสอบระบบเท่านั้น ไม่ใช่เคสทางคลินิกหรือเนื้อหาสำหรับ Demo จริง ใช้ดูโครงสร้างไฟล์ได้ แต่ห้ามนำเนื้อหาไปอ้างเป็นหลักฐานทางคลินิก รายละเอียด contract อยู่ใน [PRD §7 และ §14](PRD.md)

## เปิด autocomplete ใน editor

JSON Schema ทั้งสามไฟล์สร้างจาก Pydantic models ที่ตัวโหลดใช้จริง สำหรับ VS Code ที่ติดตั้ง YAML extension ของ Red Hat ให้เปิดโฟลเดอร์ repo เป็น workspace เดียว แล้วเพิ่ม mapping นี้ใน workspace settings ของเครื่อง (ไม่ต้องแก้ไฟล์เคส):

```json
{
  "yaml.schemas": {
    "content/schemas/case.schema.json": "content/cases/*/case.yaml",
    "content/schemas/actions.schema.json": "content/cases/*/actions.yaml",
    "content/schemas/rubric.schema.json": "content/cases/*/rubric.yaml"
  }
}
```

การใช้ `yaml.schemas` กับ path ภายใน workspace เป็นรูปแบบที่ [YAML Language Server ระบุไว้](https://github.com/redhat-developer/yaml-language-server/blob/main/README.md#associating-schemas) Editor อื่นที่รองรับ JSON Schema สามารถผูกไฟล์สามชนิดนี้ในลักษณะเดียวกันได้ Schema ช่วย autocomplete และจับชนิด/ชื่อ field; กฎข้ามไฟล์และความถูกต้องทางคลินิกยังต้องตรวจแยก

## ขั้นตอนเขียนและตรวจ

1. ตกลง Action IDs, ขอบเขตเคส, variants และผู้ตรวจทางคลินิกกับทีมก่อนเขียน ห้ามเดาอาการ เกณฑ์อันตราย หรือผลจำลองเอง
2. เขียน `case.yaml`: `patient_profile.known_facts` อ้างเฉพาะ fact แบบ `known`; hidden fact ทุกตัวมี `unlock_on`, `leak_terms_th` และ `fallback_utterances_th`; decision option ทุกตัวต้องมี branch rule และทุกเส้นทางที่เข้าถึงได้ต้องไปถึง `COMPLETED`
3. เขียน `actions.yaml`: ID ที่ `case.yaml` และ `rubric.yaml` อ้างต้องมีจริง Action แบบ `critical_info` ต้องมี `examples_th` อย่างน้อย 5 ตัวอย่างตาม contract ปัจจุบัน
4. เขียน `rubric.yaml`: น้ำหนัก competencies รวมเป็น 100; check อ้าง Action/fact/decision option ที่มีจริง; ใส่ findings และ references ให้ตรวจย้อนกลับได้ Critical Safety เป็น gate ไม่ใช่คะแนนรวม
5. ใส่ `source` ที่ตรวจสอบได้ให้ hidden facts, critical actions และ rubric items แล้วให้ผู้เชี่ยวชาญทบทวนเนื้อหา รวมถึง forbidden/leak terms, fallback utterances, outcome scripts และสถานะ `Draft` → `In Review` → `Approved`
6. รันคำสั่งด้านล่างจากราก repo; แก้ error ตามชื่อไฟล์และ path ที่ validator รายงาน ก่อนเปิด content PR ด้วย [template สำหรับ Content](../.github/PULL_REQUEST_TEMPLATE/content.md)

```sh
make validate-content
make validate-content STRICT=1
make check-content-schemas
make eval  # เมื่อแก้ actions/rubric; ต้องมี PostgreSQL สำหรับ eval
```

`validate-content` ตรวจรูปแบบ Pydantic และกฎข้ามไฟล์ ส่วน `STRICT=1` เพิ่มการบังคับแหล่งอ้างอิงตาม FR-CASE-04 การผ่าน validator หรือ Golden Tests ไม่ใช่การรับรองความถูกต้องทางคลินิก หากผลทดสอบไม่ตรงกับความหมายของเนื้อหา ให้ส่งประเด็นให้ทีม Content/ผู้เชี่ยวชาญพิจารณา ไม่แก้ expected results เพื่อให้ผ่าน

## เมื่อ contract เปลี่ยน

ทีม Content ไม่แก้ `content/schemas/*.schema.json` โดยตรง ทีม Engineering ต้องขอการตัดสินใจจากมนุษย์ก่อนเปลี่ยน Case/Rubric schema แล้วรัน `make gen-content-schemas` เพื่อสร้างไฟล์ใหม่ ตรวจด้วย `make check-content-schemas` และ commit schema พร้อม code ใน PR เดียวกัน CI ตรวจ drift ให้อัตโนมัติ
