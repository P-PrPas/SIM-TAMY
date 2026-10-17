// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InstructorPilot, PilotFeedbackForm } from "../components/pilot-feedback";
import { t } from "../lib/i18n";

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), instructor: vi.fn() }));
vi.mock("@/lib/api/runtime", () => ({ api: () => ({ POST: mocks.post }), instructorApi: (secret: string) => { mocks.instructor(secret); return { GET: mocks.get }; } }));
beforeEach(() => { mocks.get.mockReset(); mocks.post.mockReset(); mocks.instructor.mockReset(); });
afterEach(cleanup);

it("requires consent, retains failed form values, and sends actual ratings with the own-session request", async () => {
  mocks.post.mockRejectedValueOnce(new Error("private failure")).mockResolvedValueOnce({ data: { session_id: "session-1" } });
  const view = render(<PilotFeedbackForm sessionId="session-1" />);
  fireEvent.change(screen.getByRole("combobox", { name: t("pilot.role") }), { target: { value: "instructor" } });
  for (const field of ["usefulness", "realism"]) fireEvent.change(screen.getByRole("combobox", { name: t(`pilot.${field}`) }), { target: { value: "4" } });
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Actual pilot feedback" } });
  fireEvent.submit(view.container.querySelector("form")!);
  expect(mocks.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(view.container.querySelector("form")!);
  await screen.findByRole("alert");
  expect((screen.getByRole("textbox") as HTMLTextAreaElement).value).toBe("Actual pilot feedback");
  expect(screen.queryByText("private failure")).toBeNull();
  fireEvent.submit(view.container.querySelector("form")!);
  await screen.findByText(t("pilot.sent"));
  expect(mocks.post).toHaveBeenLastCalledWith("/v1/sessions/{session_id}/feedback", { params: { path: { session_id: "session-1" } }, body: { role: "instructor", usefulness: 4, realism: 4, comment: "Actual pilot feedback", consent: true } });
});

it("loads only the chosen class with instructor auth and opens its individual report", async () => {
  const open = vi.fn();
  mocks.get.mockResolvedValueOnce({ data: { total: 1, usefulness_avg: 4, realism_avg: 3, items: [{ session_id: "inside", role: "learner", usefulness: 4, realism: 3, comment: "Measured response", created_at: "2026-10-18T00:00:00Z", consent: true }] } });
  render(<InstructorPilot classCode="ABC123" secret="private" onOpenReport={open} />);
  expect(mocks.get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: t("pilot.load") }));
  await screen.findByText("Measured response");
  expect(mocks.instructor).toHaveBeenCalledWith("private");
  expect(mocks.get).toHaveBeenCalledWith("/v1/instructor/feedback", { params: { query: { class_code: "ABC123" } } });
  fireEvent.click(screen.getByRole("button", { name: t("instructor.openReport") }));
  expect(open).toHaveBeenCalledWith("inside");
  expect(screen.queryByText("private")).toBeNull();
});

it("keeps empty pilot averages absent and offers a retry after load errors", async () => {
  mocks.get.mockRejectedValueOnce(new Error("private detail")).mockResolvedValueOnce({ data: { total: 0, usefulness_avg: null, realism_avg: null, items: [] } });
  render(<InstructorPilot classCode="ABC123" secret="private" onOpenReport={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: t("pilot.load") }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: t("pilot.load") }));
  await screen.findByText(t("pilot.empty"));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(screen.queryByText(/0\.0/)).toBeNull();
});
