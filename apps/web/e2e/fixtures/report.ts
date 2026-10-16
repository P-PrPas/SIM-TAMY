/** Synthetic, contract-shaped report for browser tests only. */
export const syntheticReport = {
  session_id: "session-1", generated_at: "2026-10-15T00:00:00Z", engine_version: "1.0", rubric_version: "0.1",
  case: { case_id: "PP-001", version: "0.1", hash: "synthetic-hash", status: "Draft", status_label_th: "Draft case", title_th: "Synthetic case" },
  variant: "A", safety_status: "SAFETY_MET", total_score: 99,
  effective: { safety_status: "SAFETY_NOT_MET", total_score: 54.5 },
  competencies: [{ id: "RISK", name_th: "Risk recognition", weight: 25, score_pct: 40, earned: 4, possible: 10 }],
  items: [], findings: [{ id: "F-1", polarity: "improve", rubric_item_id: "R-1", text_th: "Review this decision", evidence_refs: [41], reference_ids: ["REF1"] }],
  debrief: { source: "template", paragraphs: [] },
  timeline: [{ event_id: 41, turn_idx: 3, type: "FACT_REVEALED", summary_th: "Synthetic timeline event" }],
  glassbox: { facts: [], risk_state_timeline: [], learner_actions: [] },
  replay: { terminal_state: "Referral", timeline_th: [], missed_opportunities: [], disclaimer_th: "Education only" },
  references: [{ id: "REF1", title_th: "Review source", locator: "Section 2" }],
  overrides: [], disclaimers: ["Education only"],
};
