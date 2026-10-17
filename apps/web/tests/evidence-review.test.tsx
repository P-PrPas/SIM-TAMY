// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GlassBoxPanel } from "../components/report-panels";
import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";
import { syntheticReport } from "../e2e/fixtures/report";

const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: get }) }));
afterEach(cleanup);

it("connects rubric evidence and document locators to the completed conversation turn", async () => {
  const report: components["schemas"]["ReportResponse"] = {
    ...syntheticReport, variant: "A", safety_status: "SAFETY_NOT_MET",
    case: { ...syntheticReport.case, status: "Draft" },
    effective: { safety_status: "SAFETY_NOT_MET", total_score: 50 },
    competencies: [], debrief: { source: "template", paragraphs: [] },
    findings: [{ id: "F1", polarity: "improve", rubric_item_id: "R1", text_th: "Synthetic finding", evidence_refs: [41], reference_ids: ["REF1"] }],
    timeline: [{ event_id: 41, turn_idx: 3, type: "ACTIONS_DETECTED", summary_th: "Evidence event" }],
    items: [{ id: "R1", competency: "RISK", critical: true, result: "fail", points: 1, earned: 0, evidence: [{ event_id: 41, turn_idx: 3, type: "ACTIONS_DETECTED" }] }],
  };
  get.mockResolvedValue({ data: { status: "completed", history: [{ idx: 1, speaker: "learner", text: "Earlier turn" }, { idx: 3, speaker: "learner", text: "Evidence question" }, { idx: 3, speaker: "patient", text: "Evidence answer" }] } });
  render(<GlassBoxPanel report={report} />);
  await screen.findByText("Earlier turn");
  expect(screen.getByText("Review source · Section 2")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /#41/ }));
  expect(screen.queryByText("Earlier turn")).toBeNull();
  expect(screen.getByText("Evidence question")).toBeTruthy();
  expect(screen.getByText("Evidence answer")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: t("evidenceReview.showAll") }));
  expect(screen.getByText("Earlier turn")).toBeTruthy();
});

it("does not render history from an active session", async () => {
  get.mockResolvedValue({ data: { status: "active", history: [{ idx: 1, speaker: "learner", text: "Private active text" }] } });
  render(<GlassBoxPanel report={{ ...syntheticReport, variant: "A", safety_status: "SAFETY_MET", effective: { safety_status: "SAFETY_NOT_MET", total_score: 0 }, case: { ...syntheticReport.case, status: "Draft" }, competencies: [], findings: [], timeline: [], debrief: { source: "template", paragraphs: [] } }} />);
  await screen.findByRole("alert");
  expect(screen.queryByText("Private active text")).toBeNull();
});
