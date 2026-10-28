// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DecisionPage from "../app/decision/page";
import ClosingPage from "../app/closing/page";
import ChatPage from "../app/chat/page";
import { saveSession } from "../lib/flow";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push, replace: mocks.replace }) }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get, POST: mocks.post }) }));

const brief = {
  case_id: "PP-001", version: "0.1", title_th: "Synthetic case", status: "Draft" as const,
  status_label_th: "Draft case", variants_available: ["A", "C"] as Array<"A" | "C">,
  patient_display_th: "Synthetic patient", learning_objectives: [], disclaimer_th: "Education only",
  decision_options: [{ id: "refer", label_th: "Refer" }, { id: "proceed_service", label_th: "Proceed" }],
};

function session(phase: "INTERVIEW" | "PRESSURE" | "CLOSING" | "COMPLETED" = "INTERVIEW", variant = "A") {
  return {
    session_id: "session-1", case: { case_id: "PP-001", version: "0.1", status: "Draft", status_label_th: "Draft case" },
    variant, status: phase === "COMPLETED" ? "completed" : "active", phase, turn_idx: 1,
    turns_remaining: 3, decision: { committed: phase !== "INTERVIEW", option_id: "refer" }, history: [],
    limits: { max_turns: 40, max_text_chars: 500, max_rationale_chars: 300, max_note_chars: 500 },
    created_at: "2026-10-12T00:00:00Z", last_activity_at: "2026-10-12T00:00:00Z",
  };
}

beforeEach(() => {
  mocks.get.mockReset(); mocks.post.mockReset(); mocks.push.mockReset(); mocks.replace.mockReset();
  sessionStorage.clear();
  saveSession({ id: "session-1", token: "synthetic-token", caseId: "PP-001", brief });
});
afterEach(() => cleanup());

describe("T-052 Decision Panel", () => {
  it("redirects without a saved session and never calls the API", async () => {
    sessionStorage.clear();
    render(<DecisionPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/lab/solo"));
    expect(mocks.get).not.toHaveBeenCalled();
  });

  it.each([
    ["PRESSURE", "/chat"], ["CLOSING", "/closing"], ["COMPLETED", "/report"],
  ] as const)("redirects a %s session to %s", async (phase, path) => {
    mocks.get.mockResolvedValue({ data: session(phase) });
    render(<DecisionPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(path));
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("requires an option and displays a safe load error without publishing internal review labels", async () => {
    mocks.get.mockResolvedValue({ data: session() });
    const view = render(<DecisionPage />);
    await screen.findByRole("radio", { name: "Refer" });
    fireEvent.click(screen.getByRole("button", { name: t("decision.review") }));
    expect(screen.getByRole("alert").textContent).toBe(t("decision.selectError"));
    view.unmount();
    mocks.get.mockRejectedValue(new Error("private error"));
    render(<DecisionPage />);
    expect(await screen.findByText(t("decision.loadError"))).toBeTruthy();
    expect(screen.queryByText(t("status.draftFull"))).toBeNull();
    expect(screen.queryByText("private error")).toBeNull();
  });

  it("requires two explicit steps and commits the selected option through the decision endpoint", async () => {
    mocks.get.mockResolvedValue({ data: session() });
    mocks.post.mockResolvedValue({ data: { phase: "CLOSING", decision: { option_id: "refer", committed_at_idx: 1 }, replies: [] } });
    render(<DecisionPage />);
    await screen.findByRole("radio", { name: "Refer" });
    fireEvent.click(screen.getByRole("radio", { name: "Refer" }));
    fireEvent.change(screen.getByLabelText(t("decision.rationale")), { target: { value: "Reason" } });
    fireEvent.click(screen.getByRole("button", { name: t("decision.review") }));
    expect(mocks.post).not.toHaveBeenCalled();
    expect(screen.getByText(t("decision.irreversible"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("decision.confirm") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/closing"));
    expect(mocks.post).toHaveBeenCalledWith("/v1/sessions/{session_id}/decision", {
      params: { path: { session_id: "session-1" } },
      body: { option_id: "refer", rationale_th: "Reason" },
    });
  });

  it("returns Variant C to pressure chat after referral", async () => {
    mocks.get.mockResolvedValue({ data: session("INTERVIEW", "C") });
    mocks.post.mockResolvedValue({ data: { phase: "PRESSURE", decision: { option_id: "refer", committed_at_idx: 1 }, replies: [{ speaker: "relative", text: "Synthetic pressure" }], pressure_turns_allowed: 2 } });
    render(<DecisionPage />);
    await screen.findByRole("radio", { name: "Refer" });
    fireEvent.click(screen.getByRole("radio", { name: "Refer" }));
    fireEvent.click(screen.getByRole("button", { name: t("decision.review") }));
    fireEvent.click(screen.getByRole("button", { name: t("decision.confirm") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/chat"));
  });

  it("preserves the selection after a failed commit and blocks overlong rationale", async () => {
    mocks.get.mockResolvedValue({ data: session() });
    mocks.post.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: { phase: "CLOSING", decision: { option_id: "refer", committed_at_idx: 1 }, replies: [] } });
    render(<DecisionPage />);
    await screen.findByRole("radio", { name: "Refer" });
    fireEvent.click(screen.getByRole("radio", { name: "Refer" }));
    fireEvent.change(screen.getByLabelText(t("decision.rationale")), { target: { value: "x".repeat(301) } });
    fireEvent.click(screen.getByRole("button", { name: t("decision.review") }));
    expect(mocks.post).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toBe(t("decision.tooLong"));
    fireEvent.change(screen.getByLabelText(t("decision.rationale")), { target: { value: "Reason" } });
    fireEvent.click(screen.getByRole("button", { name: t("decision.review") }));
    fireEvent.click(screen.getByRole("button", { name: t("decision.confirm") }));
    expect(await screen.findByText(t("decision.submitError"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("decision.confirm") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/closing"));
    expect(mocks.post).toHaveBeenCalledTimes(2);
  });
});

describe("T-052 Closing and pressure handoff", () => {
  it("redirects without a saved session and guards phases that cannot complete", async () => {
    sessionStorage.clear();
    const empty = render(<ClosingPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/lab/solo"));
    expect(mocks.get).not.toHaveBeenCalled();
    empty.unmount();
    saveSession({ id: "session-1", token: "synthetic-token", caseId: "PP-001", brief });
    mocks.get.mockResolvedValue({ data: session("PRESSURE", "C") });
    render(<ClosingPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/chat"));
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("redirects a completed case to its report and hides raw load errors", async () => {
    mocks.get.mockResolvedValue({ data: session("COMPLETED") });
    const complete = render(<ClosingPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/report"));
    complete.unmount();
    mocks.get.mockRejectedValue(new Error("private error"));
    render(<ClosingPage />);
    expect(await screen.findByText(t("closing.loadError"))).toBeTruthy();
    expect(screen.queryByText(t("status.draftFull"))).toBeNull();
    expect(screen.queryByText("private error")).toBeNull();
  });

  it("allows an empty note and navigates only to the local report route", async () => {
    mocks.get.mockResolvedValue({ data: session("CLOSING") });
    mocks.post.mockResolvedValue({ data: { status: "completed", report_ready: true, report_url: "javascript:alert(1)" } });
    render(<ClosingPage />);
    await screen.findByRole("button", { name: t("closing.complete") });
    fireEvent.click(screen.getByRole("button", { name: t("closing.complete") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/report"));
    expect(mocks.post).toHaveBeenCalledWith("/v1/sessions/{session_id}/complete", {
      params: { path: { session_id: "session-1" } }, body: {},
    });
  });

  it("keeps a failed note for retry and validates the 500-character limit", async () => {
    mocks.get.mockResolvedValue({ data: session("CLOSING") });
    mocks.post.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: { status: "completed", report_ready: true, report_url: "/v1/sessions/session-1/report" } });
    render(<ClosingPage />);
    await screen.findByRole("button", { name: t("closing.complete") });
    fireEvent.change(screen.getByLabelText(t("closing.note")), { target: { value: "x".repeat(501) } });
    fireEvent.click(screen.getByRole("button", { name: t("closing.complete") }));
    expect(screen.getByRole("alert").textContent).toBe(t("closing.tooLong"));
    expect(mocks.post).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(t("closing.note")), { target: { value: "Summary" } });
    fireEvent.click(screen.getByRole("button", { name: t("closing.complete") }));
    expect(await screen.findByText(t("closing.submitError"))).toBeTruthy();
    expect((screen.getByLabelText(t("closing.note")) as HTMLTextAreaElement).value).toBe("Summary");
    fireEvent.click(screen.getByRole("button", { name: t("closing.complete") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/report"));
  });

  it("keeps the pressure chat open after the interview used all 40 turns, and closes the interview", async () => {
    mocks.get.mockResolvedValue({ data: { ...session("PRESSURE", "C"), turn_idx: 40, turns_remaining: 0 } });
    const pressure = render(<ChatPage />);
    await screen.findByText("Synthetic patient");
    expect(screen.queryByText(t("chat.turnsRemaining"), { exact: false })).toBeNull();
    fireEvent.change(screen.getByLabelText(t("chat.messageLabel")), { target: { value: "Response" } });
    expect(screen.getByRole("button", { name: t("chat.send") })).toHaveProperty("disabled", false);
    pressure.unmount();

    mocks.get.mockResolvedValue({ data: { ...session("INTERVIEW"), turn_idx: 40, turns_remaining: 0 } });
    render(<ChatPage />);
    await screen.findByText("Synthetic patient");
    expect(screen.getByRole("button", { name: t("chat.send") })).toHaveProperty("disabled", true);
  });

  it("lets the learner continue pressure chat then enter Closing", async () => {
    mocks.get.mockResolvedValue({ data: session("PRESSURE", "C") });
    mocks.post.mockResolvedValue({ data: { turn_idx: 2, replies: [{ speaker: "relative", text: "Synthetic reply" }], phase: "CLOSING", clarification: false, turns_remaining: 0 } });
    render(<ChatPage />);
    await screen.findByText("Synthetic patient");
    expect(screen.getByText(t("chat.pressure"))).toBeTruthy();
    fireEvent.change(screen.getByLabelText(t("chat.messageLabel")), { target: { value: "Response" } });
    fireEvent.click(screen.getByRole("button", { name: t("chat.send") }));
    expect(await screen.findByText("Synthetic reply")).toBeTruthy();
    expect(screen.getByRole("link", { name: t("chat.toClosing") }).getAttribute("href")).toBe("/closing");
  });
});
