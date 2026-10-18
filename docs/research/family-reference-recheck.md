# Family references: claim-level recheck

Rechecked 2026-10-18 after the user reported that the report showed only broad WHO / UNICEF articles. This supersedes the mappings in [the earlier audit](family-reference-audit.md); that audit correctly identified real documents but accepted broad principles where direct guidance was available. Real links alone were insufficient for the user's requested traceability.

## What changed

All six story files are version 1.2. Only `version`, `sources`, and step `source_ids` changed. Dialogue, choices, feedback, skills, flags, critical/safe fields and Draft status are unchanged. Content review TODOs remain. References are research provenance, not expert approval or validation of the scoring instrument.

For parenthood, generic WHO news links and the general UNICEF sleep article are replaced by separate primary guidance on partner communication, family boundaries, respite, preparing questions and voluntary consent. The report can still show fewer articles than decision steps: multiple exercises may apply the same explicitly named section. More domains is not itself evidence of better support.

## Directly opened primary-source register

Each URL below was opened and its actual page text read, rather than accepted from a search snippet. Locators refer to headings or printed/PDF pages, not invented paragraph numbers.

| ID | Source and exact locator | Supports / does not establish |
|---|---|---|
| NHS-PARTNER | [NHS — บอกความต้องการและแบ่งงานดูแลลูกกับคู่ครอง](https://www.nhs.uk/baby/support-and-services/relationships-after-having-a-baby/), **Take time to listen to your partner** | Express needs instead of assuming mind-reading; share household and childcare work. Does not prescribe our prenatal worksheet, schedule, dialogue, branching or assessment. |
| NHS-FAMILY | [NHS — คุยกับญาติให้ชัดว่าต้องการความช่วยเหลือแบบไหน](https://www.nhs.uk/baby/support-and-services/relationships-after-having-a-baby/), **Relationships with family and friends** | State the kind of help wanted rather than accepting unwanted help resentfully. Does not evaluate Thai traditions or prove that our specific conversation repairs conflict. |
| NHS-REST | [NHS — แบ่งเวลาดูแลและขอคนที่ไว้ใจช่วยให้ได้พัก](https://www.nhs.uk/baby/support-and-services/sleep-and-tiredness-after-having-a-baby/), **Share the nights if you can; Ask friends and relatives for extra support; Where to get further help** | Partner help, trusted respite and professional support when struggling. No guaranteed infant sleep pattern; no UK helplines or feeding instructions added to the story. |
| NHS-QUESTIONS | [NHS — เตรียมคำถามและชวนคนในครอบครัวไปปรึกษาด้วยกัน](https://www.nhs.uk/nhs-services/gps/what-to-ask-your-doctor/), **Treatment; Top tips / Before your appointment** | Ask about efficacy, risks and alternatives, prepare questions and medicine/supplement information, and bring a supporter. General consultation preparation, not clearance for a traditional procedure. Page review is dated 2023 with a review due in January 2026; stable communication guidance, not current clinical contraindication guidance. |
| NHS-CONSENT | [NHS — ตัดสินใจโดยเข้าใจข้อมูลและไม่ถูกครอบครัวกดดัน](https://www.nhs.uk/tests-and-treatments/consent-to-treatment/), **Defining consent** | Voluntary informed decisions without family pressure, with benefits/risks/alternatives explained. UK consent guidance supports this principle; not a statement of Thai law. Review due December 2025, so do not use as a current legal authority. |
| NHS-BABY-HELP | [NHS — ขอความช่วยเหลือเมื่อกังวลว่าลูกไม่สบาย](https://www.nhs.uk/baby/health/when-to-get-urgent-medical-help-for-babies-and-children-under-5/), **Trust your instincts; Urgent advice** | Seek help when seriously concerned or unsure what to do. Only the help-seeking principle is cited; UK phone numbers, symptom thresholds and service pathways are not imported into Thai simulation scoring. |
| NHS-DIET | [NHS — อาหารที่หลากหลายและการขอคำปรึกษาช่วงให้นม](https://www.nhs.uk/baby/breastfeeding-and-bottle-feeding/breastfeeding-and-lifestyle/diet/), **Opening paragraphs under Breastfeeding and diet** | A varied healthy diet and access to nutrition advice. Does not establish any Thai food taboo, prove/disprove a particular milk-boosting dish, or prescribe a diet. |
| NHS-HERBS | [NHS — สมุนไพรช่วงให้นมและการปรึกษาแพทย์หรือเภสัชกร](https://www.nhs.uk/baby/breastfeeding-and-bottle-feeding/breastfeeding-and-lifestyle/medicines/), **Is there anything I cannot take while I'm breastfeeding?; For more information** | Insufficient information to guarantee herbal remedy safety and advice to consult qualified professionals. Not evidence that every herb is harmful or a product-specific safety assessment. |
| DTAM-CULTURE | [DTAM ICD-10-TM](https://www.dtam.moph.go.th/wp-content/uploads/2023/11/DL0003-15062558-ICD-10-TM.pdf#page=77), printed p.69 / PDF p.77, codes 900-77-14 and 900-77-20 | Names postpartum herbal compression and fire-based care. Terminology/cultural context only; classification descriptions are not adopted as contemporary efficacy evidence or personal clearance. |
| DTAM-TRIAL | [DTAM registry 3351](https://rdtam.dtam.moph.go.th/th/data_collections/3351), abstract: methods and milk-volume results | 99 participants / three groups; reported milk-volume differences were not statistically significant. Its positive conclusion is stronger than that result. Does not prove no effect or assess all compresses. No dose or procedure copied. |
| LACTMED-SUPPLEMENTS | [NIH LactMed, About Dietary Supplements](https://www.ncbi.nlm.nih.gov/sites/books/NBK547438/pdf/Bookshelf_NBK547438.pdf), p.1 formulation, extrapolation and combination paragraphs | Mixture composition varies and ingredient evidence does not automatically transfer to a commercial mixture; individual advice remains necessary. US regulatory passages are not Thai law. |
| UNICEF-FOOD | [UNICEF Maternal nutrition](https://www.unicef.org/nutrition/maternal), challenge / food access and affordability; Nutrition during breastfeeding | Food access, cost and social context affect nutrition. Retained only for the budget/access exercise, alongside direct household-sharing guidance. Does not prescribe allocation of cooking work or prove a dish increases milk. |

WHO's [2022 guideline publication page](https://www.who.int/publications/i/item/9789240045989) was also opened: its overview genuinely supports family information/support and cultural context. It is no longer used as a substitute for direct practical guidance in these step mappings. NHS England's shared-decision page returned a JavaScript robot check, NICE NG197 returned 403, and an initially guessed NHS doctor-question URL returned 404. None of those inaccessible pages was used as verified evidence; the working NHS URL above was subsequently opened successfully.

## Every decision step

These are authored teaching applications. No cited organization wrote the dialogue, approved the rubric, established the critical gate, or validated family-readiness prediction. Sources explain the principle the learner practises; they are not quotations matching each option word for word.

| Story / step | Reference IDs | Specific connection |
|---|---|---|
| first-night / say-how-you-feel | NHS-PARTNER | State tiredness and ask for concrete help. |
| first-night / offer-specific-help | NHS-PARTNER, NHS-REST | Share practical care work and make room for rest. |
| first-night / make-a-backup | NHS-REST | Identify a trusted person for respite; availability check is our planning exercise. |
| first-night / agree-help-seeking | NHS-BABY-HELP, NHS-QUESTIONS | Do not dismiss concern; seek professional input and prepare questions. |
| parenthood / before-plan | NHS-PARTNER | Discuss expectations and who takes which work; prenatal timing/worksheet are authored. |
| parenthood / before-support | NHS-REST, NHS-QUESTIONS | Distinguish practical respite from professional advice. |
| parenthood / first-night-plan | NHS-PARTNER, NHS-REST | Express current needs and adapt care work; remembered flags are authored mechanics. |
| parenthood / first-night-backup | NHS-REST | Ask a trusted helper for relief; schedule negotiation is authored. |
| parenthood / family-listening | NHS-FAMILY | Tell relatives what help is wanted while acknowledging intention. |
| parenthood / family-check | NHS-QUESTIONS, NHS-CONSENT | Gather questions, consult together and avoid family pressure. |
| bridge-fire / listen | DTAM-CULTURE, NHS-FAMILY | Documented practice name plus stating wanted family support. |
| bridge-fire / clarify | DTAM-CULTURE, NHS-QUESTIONS | Documented practice name plus questions about risks, alternatives and personal context. |
| bridge-fire / agree | NHS-CONSENT, NHS-QUESTIONS, NHS-FAMILY | No pressured consent; ask qualified advice and offer a wanted practical role. |
| bridge-compress / listen | DTAM-CULTURE, NHS-FAMILY | Documented compress name plus family communication. |
| bridge-compress / ask-details | DTAM-TRIAL, NHS-QUESTIONS | Check exactly what the trial studied and ask about evidence, risks and context. |
| bridge-compress / consult | DTAM-TRIAL, NHS-CONSENT, NHS-QUESTIONS | Uncertain trial results do not equal clearance; voluntary consent and qualified discussion. |
| bridge-food / understand | NHS-FAMILY, NHS-DIET | Express preferences; varied diet is distinct from family custom. |
| bridge-food / share-work | UNICEF-FOOD, NHS-PARTNER | Food affordability/access plus sharing domestic work. |
| bridge-food / check-claim | NHS-DIET, NHS-QUESTIONS | Separate a nutrition principle from an efficacy guarantee; ask specific questions. |
| bridge-herbs / receive | LACTMED-SUPPLEMENTS, NHS-CONSENT | A received mixed product is not permission to use it; clarify evidence first. |
| bridge-herbs / identify | LACTMED-SUPPLEMENTS | Ingredient findings cannot automatically establish safety of a mixture. |
| bridge-herbs / decide | NHS-HERBS, NHS-QUESTIONS, NHS-CONSENT | Do not use under social pressure when information is incomplete; seek product-specific advice. |

## Existing rooms and release verification

Rooms persist a pinned story snapshot at creation. Updating YAML does **not** rewrite a completed or active room's historical sources, choices or score. An old room may therefore legitimately retain the two older links shown in the screenshot even after a deployment; create a new round to inspect version 1.2. Do not silently replace historical evidence or delete event logs. New-room version/report assertions should verify all six stories, source-ID resolution and unchanged gameplay fields.

The remaining expert task is clinical/cultural review of authored content, particularly efficacy wording and the distinction between cultural documentation and evidence quality. This research does not supply that sign-off. No clinical contraindication, dose, temperature, treatment or new safety criterion was added.

Verified locally: content validator passed all seven clinical cases and six family stories; `test_family_catalog.py` and `test_family_engine.py` passed (7 tests). A semantic comparison against Git HEAD confirmed every field except version, sources and step source IDs is identical in all six stories, and all 22 steps resolve non-empty source IDs. `git diff --check` passed for these changes. No real-user session was accessed or rewritten.

