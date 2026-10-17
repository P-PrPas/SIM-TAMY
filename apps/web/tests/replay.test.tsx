// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import JoinPage from "../app/page";
import ReplayPage from "../app/replay/page";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get, POST: mocks.post }) }));

const recording = {
  recording_id: "dev-001", title_th: "Synthetic engineering replay", case_id: "PP-001",
  variant: "A", steps_count: 3,
  case: { case_id: "PP-001", version: "0.1", title_th: "Synthetic case", status: "Draft",
    status_label_th: "Draft", variants_available: ["A"], patient_display_th: "Synthetic patient",
    learning_objectives: [], decision_options: [], disclaimer_th: "Education only" },
  steps: [
    { t_ms: 0, type: "learner", speaker: "learner", text: "First question" },
    { t_ms: 10, type: "reply", speaker: "patient", text: "Synthetic reply" },
    { t_ms: 10, type: "complete" },
  ],
  report: { effective: { safety_status: "SAFETY_NOT_MET", total_score: 20 },
    debrief: { source: "template", paragraphs: [{ finding_ids: [], text_th: "Practice again" }] },
    disclaimers: ["Education only"] },
};

beforeEach(() => {
  mocks.get.mockReset(); mocks.post.mockReset();
  mocks.get.mockImplementation((path: string) => Promise.resolve({ data: path === "/v1/replay/recordings"
    ? { items: [{ ...recording, status: "Draft", status_label_th: "Draft" }] } : recording }));
});
afterEach(() => cleanup());

describe("T-073 Replay Mode", () => {
  it("keeps engineering recordings out of the learner gallery", async () => {
    mocks.get.mockResolvedValue({ data: { items: [{ ...recording, case_id: "DEV-001", status: "Draft" }] } });
    render(<ReplayPage />);
    expect(await screen.findByText(t("replay.empty"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("replay.open") })).toBeNull();
  });

  it("offers a Demo switch from Join without starting a learner session", async () => {
    render(<JoinPage />);
    expect(screen.getByRole("link", { name: t("replay.switch") }).getAttribute("href")).toBe("/replay");
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("plays recorded steps in order, labels replay, and shows gated report only at the end", async () => {
    render(<ReplayPage />);
    expect(await screen.findByText("Synthetic engineering replay")).toBeTruthy();
    expect(screen.getByText(t("replay.label"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("replay.open") }));
    expect(await screen.findByText("First question")).toBeTruthy();
    expect(screen.getByText(t("status.draft"))).toBeTruthy();
    expect(screen.queryByText("Practice again")).toBeNull();
    expect(await screen.findByText("Synthetic reply")).toBeTruthy();
    expect(await screen.findByText("Practice again")).toBeTruthy();
    expect(screen.getByText(t("report.safetyNotMet"))).toBeTruthy();
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("shows the case status badge on every recording row before it is opened", async () => {
    mocks.get.mockImplementation(() => Promise.resolve({ data: { items: [
      { ...recording, recording_id: "a", title_th: "Row A", status: "Draft", status_label_th: "Draft" },
      { ...recording, recording_id: "b", title_th: "Row B", status: "In Review", status_label_th: "In Review" },
    ] } }));
    render(<ReplayPage />);
    const rows = (await screen.findAllByRole("listitem"));
    expect(rows).toHaveLength(2);
    expect(rows[0]?.textContent).toContain(t("status.draft"));
    expect(rows[1]?.textContent).toContain(t("status.inReview"));
  });

  it("handles disabled replay as a safe unavailable state", async () => {
    mocks.get.mockRejectedValue(new Error("private detail"));
    render(<ReplayPage />);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(t("replay.unavailable")));
    expect(screen.queryByText("private detail")).toBeNull();
  });

  it("fails closed on an invalid safety result instead of showing met language", async () => {
    mocks.get.mockImplementation((path: string) => Promise.resolve({ data: path === "/v1/replay/recordings"
      ? { items: [{ ...recording, status: "Draft", status_label_th: "Draft" }] } : { ...recording, report: { ...recording.report,
        effective: { safety_status: "UNKNOWN", total_score: 99 } } } }));
    render(<ReplayPage />);
    await screen.findByText("Synthetic engineering replay");
    fireEvent.click(screen.getByRole("button", { name: t("replay.open") }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", t("replay.loadError"));
    expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
  });
});
