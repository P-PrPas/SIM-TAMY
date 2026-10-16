// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import InstructorPage from "../app/instructor/page";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), client: vi.fn() }));
vi.mock("@/lib/api/runtime", () => ({
  instructorApi: (secret: string) => {
    mocks.client(secret);
    return { GET: mocks.get, POST: mocks.post };
  },
}));

const room = { class_id: "room-1", code: "ABC123", name: "Synthetic class", created_at: "2026-10-16T00:00:00Z" };
const row = {
  session_id: "session-1", learner_name: "Synthetic learner", case_id: "DEV-001",
  case_version: "0.1", case_status: "Draft", case_status_label_th: "Draft case",
  variant: "A", status: "completed", started_at: "2026-10-16T00:00:00Z", ended_at: "2026-10-16T00:10:00Z",
  turns: 4, safety_status: "SAFETY_NOT_MET", total_score: 45, competency_pct: { RISK: 50 },
};
const analytics = {
  class_code: "ABC123", sessions_completed: 1, sessions_active: 0,
  avg_total_score: 45, safety_not_met_rate: 1, avg_turns: 4,
  competency_avg: [{ id: "RISK", name_th: "Synthetic risk", avg_pct: 50 }],
  critical_item_fail_rates: [{ item_id: "DEV-001:SYN-1", label_th: "Synthetic critical", fail_rate: 1, n: 1 }],
};
const report = {
  case: { status: "Draft", title_th: "Synthetic case" },
  effective: { safety_status: "SAFETY_NOT_MET", total_score: 45 },
  competencies: [{ id: "RISK", name_th: "Synthetic risk", score_pct: 50 }],
  findings: [{ id: "F1", text_th: "Synthetic finding" }], timeline: [],
  disclaimers: ["Education only"],
};

beforeEach(() => {
  mocks.get.mockReset(); mocks.post.mockReset(); mocks.client.mockReset(); sessionStorage.clear();
  mocks.get.mockImplementation(async (path: string) => {
    if (path === "/v1/instructor/classes") return { data: { items: [room] } };
    if (path === "/v1/instructor/sessions") return { data: { items: [row], next_cursor: null } };
    if (path === "/v1/instructor/analytics") return { data: analytics };
    if (path === "/v1/sessions/{session_id}/report") return { data: report };
    throw new Error("unexpected request");
  });
});
afterEach(() => cleanup());

describe("T-055/T-057 instructor dashboard", () => {
  it("requires a secret, scopes sessions to a class and opens a safety-first report", async () => {
    render(<InstructorPage />);
    expect(mocks.get).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(t("instructor.secret")), { target: { value: "synthetic-secret" } });
    fireEvent.click(screen.getByRole("button", { name: t("instructor.enter") }));
    expect(await screen.findByText("Synthetic class")).toBeTruthy();
    expect(sessionStorage.getItem("instructor-secret")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Synthetic class/ }));
    expect(await screen.findByText("Synthetic learner")).toBeTruthy();
    expect(screen.getByText(t("status.draft"))).toBeTruthy();
    expect(screen.getByText(/Synthetic critical/)).toBeTruthy();
    expect(screen.getByText(`${t("report.score")}: 45`)).toBeTruthy();
    expect(mocks.get).toHaveBeenCalledWith("/v1/instructor/sessions", expect.objectContaining({
      params: { query: expect.objectContaining({ class_code: "ABC123" }) },
    }));
    fireEvent.click(screen.getByRole("button", { name: t("instructor.openReport") }));
    expect(await screen.findByText("Synthetic finding")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain(t("report.safetyNotMet"));
    expect(mocks.client).toHaveBeenCalledWith("synthetic-secret");
  });

  it("creates a class and refreshes the list without exposing the secret", async () => {
    mocks.post.mockResolvedValue({ data: room });
    render(<InstructorPage />);
    fireEvent.change(screen.getByLabelText(t("instructor.secret")), { target: { value: "synthetic-secret" } });
    fireEvent.click(screen.getByRole("button", { name: t("instructor.enter") }));
    await screen.findByText("Synthetic class");
    fireEvent.change(screen.getByLabelText(t("instructor.className")), { target: { value: "Another class" } });
    fireEvent.click(screen.getByRole("button", { name: t("instructor.createClass") }));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/v1/classes", { body: { name: "Another class" } }));
    expect(document.body.textContent).not.toContain("synthetic-secret");
  });

  describe("switching classes", () => {
    const roomB = { ...room, class_id: "room-2", code: "XYZ789", name: "Second class" };
    const rowB = { ...row, session_id: "session-2", learner_name: "Learner of B" };
    const rowA = { ...row, learner_name: "Learner of A" };
    const pending: Record<string, (value: unknown) => void> = {};
    const sessionsFor = (code: string, slowA: boolean) => code === "ABC123"
      ? slowA ? new Promise((resolve) => { pending[code] = resolve; }) : Promise.resolve({ data: { items: [rowA], next_cursor: null } })
      : Promise.resolve({ data: { items: [rowB], next_cursor: null } });

    async function openTwoClasses({ slowA = false, failB = false } = {}) {
      mocks.get.mockImplementation(async (path: string, init?: { params: { query: { class_code: string } } }) => {
        const code = init?.params?.query?.class_code ?? "";
        if (path === "/v1/instructor/classes") return { data: { items: [room, roomB] } };
        if (path === "/v1/instructor/sessions") {
          if (code === "XYZ789" && failB) throw new Error("boom");
          return sessionsFor(code, slowA);
        }
        if (path === "/v1/instructor/analytics") return { data: { ...analytics, class_code: code } };
        throw new Error("unexpected request");
      });
      render(<InstructorPage />);
      fireEvent.change(screen.getByLabelText(t("instructor.secret")), { target: { value: "synthetic-secret" } });
      fireEvent.click(screen.getByRole("button", { name: t("instructor.enter") }));
      await screen.findByText("Second class");
    }

    it("ignores a slow response of the class that was left", async () => {
      await openTwoClasses({ slowA: true });
      fireEvent.click(screen.getByRole("button", { name: /Synthetic class/ }));
      fireEvent.click(screen.getByRole("button", { name: /Second class/ }));
      expect(await screen.findByText("Learner of B")).toBeTruthy();
      pending.ABC123({ data: { items: [rowA], next_cursor: null } });
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(screen.queryByText("Learner of A")).toBeNull();
      expect(screen.getByText("Learner of B")).toBeTruthy();
    });

    it("drops the previous class data when loading the new class fails", async () => {
      await openTwoClasses({ failB: true });
      fireEvent.click(screen.getByRole("button", { name: /Synthetic class/ }));
      expect(await screen.findByText("Learner of A")).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: /Second class/ }));
      expect((await screen.findByRole("alert")).textContent).toContain(t("instructor.loadError"));
      expect(screen.queryByText("Learner of A")).toBeNull();
    });
  });
});
