# Action interpreter dev set (T-071)

`actions_th.jsonl` is a held-out, synthetic set for the `DEV-001` engineering fixture. It is **not** clinical content, not the `PP-001` case, and not evidence of model quality. It must never be presented as a real-demo or clinical validation set. The utterances are original, not copied from `DEV-001/actions.yaml` examples.

Each UTF-8 JSONL row has `case_id`, `variant`, `phase`, `text_th`, `action_ids` (zero or more IDs), and `kind`. Kinds cover direct, colloquial, short, misspelled, ambiguous, irrelevant, and multi-intent messages. Empty labels mean that the Interpreter should not infer an Action from the learner chat. Only `HX` and `COM` Action IDs appear: `DEC` actions belong to the Decision Panel, and `DOC` is not an Interpreter chat action. `C03` and `C04` exercise opposite responses to family pressure; `C04` is an unsafe simulated choice, not an endorsed practice.

This dataset is intended for the later T-005 model bench. Its labels are provisional author annotations pending independent Content review. Once Content publishes `PP-001`, create a separately reviewed case-specific set; do not silently relabel these synthetic rows as `PP-001`. Do not tune prompts or lexical examples against these held-out rows and then report performance on the same set. No benchmark metric is claimed here; `make bench` remains unimplemented until T-005.
