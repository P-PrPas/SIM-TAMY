// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ReportPage from "../app/report/page";
import { ApiError } from "../lib/api/client";
import { saveSession } from "../lib/flow";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), replace: vi.fn(), download: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get }) }));
vi.mock("@/lib/report-export", () => ({ downloadReportJson: mocks.download }));

const brief = {
  case_id: "PP-001", version: "0.1", title_th: "Synthetic case", status: "Draft" as const,
  status_label_th: "Draft case", variants_available: ["A" as const],
  patient_display_th: "Synthetic patient", learning_objectives: [], disclaimer_th: "Education only",
  decision_options: [{ id: "refer", label_th: "Refer" }],
};

const report = {
  session_id: "session-1", generated_at: "2026-10-15T00:00:00Z", engine_version: "1.0",
  rubric_version: "0.1", variant: "A", case: { case_id: "PP-001", version: "0.1", hash: "synthetic-hash", status: "Draft", status_label_th: "Draft case", title_th: "Synthetic case" },
  safety_status: "SAFETY_MET", total_score: 99,
  effective: { safety_status: "SAFETY_NOT_MET", total_score: 54.5 },
  competencies: [
    { id: "RISK", name_th: "Risk recognition", weight: 25, score_pct: 40, earned: 4, possible: 10 },
    { id: "DEC", name_th: "Decision", weight: 30, score_pct: 60, earned: 6, possible: 10 },
  ],
  items: [],
  findings: [
    { id: "F-1", polarity: "improve", rubric_item_id: "R-1", text_th: "Review this decision", evidence_refs: [41], reference_ids: ["REF1"] },
    { id: "F-2", polarity: "strength", rubric_item_id: "R-2", text_th: "Strong communication", evidence_refs: [42], reference_ids: ["REF2"] },
  ],
  debrief: { source: "template", paragraphs: [{ finding_ids: ["F-1"], text_th: "Synthetic feedback" }] },
  timeline: [{ event_id: 41, turn_idx: 3, type: "FACT_REVEALED", summary_th: "Synthetic timeline event" }],
  glassbox: { facts: [], risk_state_timeline: [], learner_actions: [] },
  replay: { terminal_state: "Referral", timeline_th: [], missed_opportunities: [], disclaimer_th: "Education only" },
  references: [{ id: "REF1", title_th: "Review source", locator: "Section 2" }, { id: "REF2", title_th: "Strength source", locator: "Section 3" }],
  overrides: [], disclaimers: ["Education only"],
};

beforeEach(() => {
  mocks.get.mockReset(); mocks.replace.mockReset(); mocks.download.mockReset(); sessionStorage.clear();
  saveSession({ id: "session-1", token: "synthetic-token", caseId: "PP-001", brief });
});
afterEach(() => cleanup());

describe("T-053 Report", () => {
  it("exports the exact completed report and offers print without changing safety wording", async () => {
    mocks.get.mockResolvedValue({ data: report });
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(<ReportPage />);
    await screen.findByText(t("report.safetyNotMet"));
    fireEvent.click(screen.getByRole("button", { name: t("report.downloadJson") }));
    expect(mocks.download).toHaveBeenCalledWith(report);
    fireEvent.click(screen.getByRole("button", { name: t("report.print") }));
    expect(print).toHaveBeenCalledOnce();
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
    print.mockRestore();
  });

  it("supports arrow keys, Home and End in the report tablist", async () => {
    mocks.get.mockResolvedValue({ data: report });
    render(<ReportPage />);
    const summary = await screen.findByRole("tab", { name: t("report.summary") });
    const timeline = screen.getByRole("tab", { name: t("report.timeline") });
    const review = screen.getByRole("tab", { name: t("report.review") });
    summary.focus();
    fireEvent.keyDown(summary, { key: "ArrowRight" });
    expect(timeline.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(timeline);
    fireEvent.keyDown(timeline, { key: "End" });
    expect(review.getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(review, { key: "Home" });
    expect(summary.getAttribute("aria-selected")).toBe("true");
  });

  it("puts effective safety-not-met before the effective score and never shows met language", async () => {
    mocks.get.mockResolvedValue({ data: report });
    render(<ReportPage />);
    const warning = await screen.findByRole("alert");
    expect(warning.textContent).toContain(t("report.safetyNotMet"));
    const score = screen.getByText("54.5");
    expect(warning.compareDocumentPosition(score) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByText("99")).toBeNull();
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
    expect(screen.getByText(t("status.draft"))).toBeTruthy();
    expect(screen.getByText("Risk recognition")).toBeTruthy();
    expect(mocks.get).toHaveBeenCalledWith("/v1/sessions/{session_id}/report", { params: { path: { session_id: "session-1" } } });
  });

  it("shows timeline and only improvement references in their respective tabs", async () => {
    mocks.get.mockResolvedValue({ data: report });
    render(<ReportPage />);
    await screen.findByText(t("status.draft"));
    fireEvent.click(screen.getByRole("tab", { name: t("report.timeline") }));
    expect(screen.getByText("Synthetic timeline event")).toBeTruthy();
    expect(screen.getByText(`${t("report.turn")} 3`)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: t("report.review") }));
    expect(screen.getByText("Review this decision")).toBeTruthy();
    expect(screen.getByText("Review source")).toBeTruthy();
    expect(screen.getByText("Section 2")).toBeTruthy();
    expect(screen.queryByText("Strength source")).toBeNull();
  });

  it("shows met wording only when effective safety status is met", async () => {
    mocks.get.mockResolvedValue({ data: { ...report, effective: { safety_status: "SAFETY_MET", total_score: 99 } } });
    render(<ReportPage />);
    expect(await screen.findByText(t("report.safetyMet"))).toBeTruthy();
    expect(screen.queryByText(t("report.safetyNotMet"))).toBeNull();
  });

  it("redirects without a saved session and does not request a report", async () => {
    sessionStorage.clear();
    render(<ReportPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/"));
    expect(mocks.get).not.toHaveBeenCalled();
  });

  it("shows a safe not-ready state and retries a failed load without raw errors", async () => {
    mocks.get.mockRejectedValueOnce(new ApiError("REPORT_NOT_READY", 409))
      .mockRejectedValueOnce(new Error("private server detail"))
      .mockResolvedValueOnce({ data: report });
    render(<ReportPage />);
    expect(await screen.findByText(t("report.notReady"))).toBeTruthy();
    expect(screen.getByText(t("status.draft"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("report.retry") }));
    expect(await screen.findByText(t("report.loadError"))).toBeTruthy();
    expect(screen.queryByText("private server detail")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: t("report.retry") }));
    expect(await screen.findByText("Risk recognition")).toBeTruthy();
    expect(mocks.get).toHaveBeenCalledTimes(3);
  });

  it("shows a safe error for a malformed report response", async () => {
    mocks.get.mockResolvedValue({ data: { session_id: "session-1", phase: "CLOSING" } });
    render(<ReportPage />);
    expect(await screen.findByText(t("report.loadError"))).toBeTruthy();
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
  });

  it("fails closed when the API returns an unknown safety status", async () => {
    mocks.get.mockResolvedValue({ data: { ...report, effective: { safety_status: "UNKNOWN", total_score: 99 } } });
    render(<ReportPage />);
    expect(await screen.findByText(t("report.loadError"))).toBeTruthy();
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
  });
});
