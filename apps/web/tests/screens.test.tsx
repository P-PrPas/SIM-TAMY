// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import JoinPage from "../app/page";
import BriefingPage from "../app/briefing/page";
import ChatPage from "../app/chat/page";
import { StatusBadge } from "../components/status-badge";
import { ApiError } from "../lib/api/client";
import { readSession, saveSession } from "../lib/flow";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push, replace: mocks.replace }) }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ GET: mocks.get, POST: mocks.post }) }));

const caseSummary = {
  case_id: "PP-001", version: "0.1", title_th: "Case PP-001", status: "Draft" as const,
  status_label_th: t("status.draftFull"), variants_available: ["A", "C"] as Array<"A" | "C">,
};
const caseBrief = {
  ...caseSummary, patient_display_th: "Opening patient information",
  learning_objectives: [{ id: "risk", label_th: "Recognize risk" }],
  decision_options: [{ id: "refer", label_th: "Refer" }], disclaimer_th: "Educational simulation",
};
const sessionView = {
  session_id: "session-1", case: { case_id: "PP-001", version: "0.1", status: "Draft", status_label_th: caseSummary.status_label_th },
  variant: "A", status: "active", phase: "INTERVIEW", turn_idx: 0, turns_remaining: 40,
  decision: { committed: false }, history: [], limits: { max_turns: 40, max_text_chars: 500 },
  created_at: "2026-10-12T00:00:00Z", last_activity_at: "2026-10-12T00:00:00Z",
};

beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); mocks.push.mockReset(); mocks.replace.mockReset(); sessionStorage.clear(); });
afterEach(() => cleanup());

describe("S1 Join and S2 Briefing", () => {
  it("renders the draft badge and starts a session with a nickname", async () => {
    mocks.get.mockResolvedValue({ data: { items: [caseSummary] } });
    mocks.post.mockResolvedValue({ data: { session_id: "session-1", token: "secret-token", case: caseBrief } });
    render(<JoinPage />);
    await screen.findByText(caseSummary.status_label_th);
    fireEvent.change(screen.getByLabelText(t("join.nickname")), { target: { value: "Learner" } });
    fireEvent.click(screen.getByRole("button", { name: t("join.start") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/briefing"));
    expect(mocks.post.mock.calls[0]?.[1].body).toMatchObject({ case_id: "PP-001", variant: "A", learner_name: "Learner" });
    expect(sessionStorage.getItem("sim-tamy-session")).toContain("secret-token");
    expect(readSession()?.brief).toEqual(caseBrief);
  });

  it("shows case briefing and its draft status", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    render(<BriefingPage />);
    expect(await screen.findByText("Opening patient information")).toBeTruthy();
    expect(screen.getByText(caseSummary.status_label_th)).toBeTruthy();
    expect(screen.getByText("Recognize risk")).toBeTruthy();
    expect(screen.getByRole("link", { name: t("briefing.begin") }).getAttribute("href")).toBe("/chat");
  });

  it("shows a clear error for an unknown class code", async () => {
    mocks.get.mockResolvedValue({ data: { items: [caseSummary] } });
    mocks.post.mockRejectedValue(new ApiError("CLASS_NOT_FOUND", 404));
    render(<JoinPage />);
    await screen.findByText(caseSummary.status_label_th);
    fireEvent.change(screen.getByLabelText(t("join.nickname")), { target: { value: "Learner" } });
    fireEvent.change(screen.getByLabelText(t("join.classCode")), { target: { value: "ABC123" } });
    fireEvent.click(screen.getByRole("button", { name: t("join.start") }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", t("join.classNotFound"));
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it("rejects a malformed class code before calling the API", async () => {
    mocks.get.mockResolvedValue({ data: { items: [caseSummary] } });
    render(<JoinPage />);
    await screen.findByText(caseSummary.status_label_th);
    fireEvent.change(screen.getByLabelText(t("join.nickname")), { target: { value: "Learner" } });
    fireEvent.change(screen.getByLabelText(t("join.classCode")), { target: { value: "A" } });
    fireEvent.click(screen.getByRole("button", { name: t("join.start") }));
    expect(screen.getByText(t("join.invalidCode"))).toBeTruthy();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("lets the learner retry a failed case list load", async () => {
    mocks.get.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: { items: [caseSummary] } });
    render(<JoinPage />);
    fireEvent.click(await screen.findByRole("button", { name: t("join.retry") }));
    expect(await screen.findByText(caseSummary.status_label_th)).toBeTruthy();
    expect(mocks.get).toHaveBeenCalledTimes(2);
  });

  it("does not start when the case list is empty", async () => {
    mocks.get.mockResolvedValue({ data: { items: [] } });
    render(<JoinPage />);
    expect(await screen.findByText(t("join.empty"))).toBeTruthy();
    expect(screen.getByRole("button", { name: t("join.start") }).hasAttribute("disabled")).toBe(true);
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("keeps the selected variant after a failed start attempt", async () => {
    mocks.get.mockResolvedValue({ data: { items: [caseSummary] } });
    mocks.post.mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { session_id: "session-1", token: "secret-token", case: caseBrief } });
    render(<JoinPage />);
    await screen.findByText(caseSummary.status_label_th);
    fireEvent.change(screen.getByLabelText(t("join.nickname")), { target: { value: "Learner" } });
    fireEvent.change(screen.getByLabelText(t("join.variant")), { target: { value: "C" } });
    fireEvent.click(screen.getByRole("button", { name: t("join.start") }));
    expect(await screen.findByText(t("join.startError"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: t("join.start") }));
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/briefing"));
    expect(mocks.post.mock.calls[1]?.[1].body.variant).toBe("C");
  });

  it("redirects Briefing without a session", async () => {
    render(<BriefingPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/"));
  });

  it("keeps showing the case version the session was created with after a newer one is published", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    const newer = { ...caseBrief, version: "0.2", patient_display_th: "Newer patient information" };
    mocks.get.mockImplementation((path: string) => Promise.resolve({ data: path.includes("/v1/cases/") ? newer : sessionView }));
    const briefing = render(<BriefingPage />);
    expect(await screen.findByText("Opening patient information")).toBeTruthy();
    expect(screen.queryByText("Newer patient information")).toBeNull();
    expect(mocks.get).not.toHaveBeenCalled();
    briefing.unmount();
    render(<ChatPage />);
    expect(await screen.findByText("Opening patient information")).toBeTruthy();
    expect(screen.queryByText("Newer patient information")).toBeNull();
    expect(mocks.get.mock.calls.every(([path]) => !String(path).includes("/v1/cases/"))).toBe(true);
  });

  it("renders localized badges for every review status", () => {
    const view = render(<StatusBadge status="In Review" />);
    expect(screen.getByText(t("status.inReview"))).toBeTruthy();
    view.rerender(<StatusBadge status="Approved" />);
    expect(screen.getByText(t("status.approved"))).toBeTruthy();
  });
});

describe("S3 Chat", () => {
  it("shows optimistic text, typing, and retries a failed turn with the same ID", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    mocks.get.mockResolvedValue({ data: sessionView });
    let rejectFirst: (error: Error) => void = () => {};
    mocks.post.mockImplementationOnce(() => new Promise((_, reject) => { rejectFirst = reject; }));
    mocks.post.mockResolvedValueOnce({ data: { turn_idx: 1, replies: [{ speaker: "patient", text: "Patient reply" }], phase: "INTERVIEW", clarification: false, turns_remaining: 39, degraded: false } });
    render(<ChatPage />);
    await screen.findByText("Opening patient information");
    fireEvent.change(screen.getByLabelText(t("chat.messageLabel")), { target: { value: "Question?" } });
    fireEvent.click(screen.getByRole("button", { name: t("chat.send") }));
    expect(screen.getByText("Question?")).toBeTruthy();
    expect(screen.getByText(t("chat.typing"))).toBeTruthy();
    rejectFirst(new Error("offline"));
    fireEvent.click(await screen.findByRole("button", { name: t("chat.retry") }));
    expect(await screen.findByText("Patient reply")).toBeTruthy();
    expect(mocks.post).toHaveBeenCalledTimes(2);
    expect(mocks.post.mock.calls[0]?.[1].body.client_turn_id).toBe(mocks.post.mock.calls[1]?.[1].body.client_turn_id);
    expect(screen.getByText(new RegExp(t("chat.turnsRemaining"))).textContent).toContain("39");
  });

  it("resumes visible chat history and guards blank input", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    const resumed = { ...sessionView, history: [{ idx: 1, speaker: "learner", text: "Earlier question", created_at: "2026-10-12T00:00:00Z" }, { idx: 1, speaker: "patient", text: "Earlier answer", created_at: "2026-10-12T00:00:00Z" }] };
    mocks.get.mockResolvedValue({ data: resumed });
    render(<ChatPage />);
    expect(await screen.findByText("Earlier question")).toBeTruthy();
    expect(screen.getByText("Earlier answer")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(t("chat.messageLabel")), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: t("chat.send") }));
    expect(screen.getByText(t("chat.invalidMessage"))).toBeTruthy();
    expect(mocks.post).not.toHaveBeenCalled();
  });

  it("sends a completed session straight to its report instead of a dead chat", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    mocks.get.mockResolvedValue({ data: { ...sessionView, phase: "COMPLETED", status: "completed" } });
    render(<ChatPage />);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/report"));
    expect(screen.queryByLabelText(t("chat.messageLabel"))).toBeNull();
  });

  it("shows a safe loading error when session history cannot be fetched", async () => {
    saveSession({ id: "session-1", token: "secret-token", caseId: "PP-001", brief: caseBrief });
    mocks.get.mockRejectedValue(new Error("offline"));
    render(<ChatPage />);
    expect(await screen.findByText(t("chat.loadError"))).toBeTruthy();
    expect(mocks.post).not.toHaveBeenCalled();
  });
});

describe("session storage", () => {
  it("rejects malformed saved session data", () => {
    sessionStorage.setItem("sim-tamy-session", "not-json");
    expect(readSession()).toBeNull();
    sessionStorage.setItem("sim-tamy-session", JSON.stringify({ id: "one", token: 4, caseId: "PP-001" }));
    expect(readSession()).toBeNull();
    sessionStorage.setItem("sim-tamy-session", JSON.stringify({ id: "one", token: "t", caseId: "PP-001" }));
    expect(readSession()).toBeNull(); // no brief kept: start a new session instead of guessing the version
  });
});
