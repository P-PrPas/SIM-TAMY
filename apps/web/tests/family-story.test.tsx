// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { FamilyChapterGate, FamilyJournal, FamilyStoryboard } from "@/components/family-story";
import { t } from "@/lib/i18n";

afterEach(cleanup);
const turn = { idx: 1, role: "mother" as const, speaker_th: "Relative", prompt_th: "Public context", text_th: "Chosen reply", reply_th: "Recorded response" };

it("requires a deliberate chapter continuation without committing a new decision", () => {
  const { rerender } = render(<FamilyChapterGate chapter="First"><button>Decision</button></FamilyChapterGate>);
  expect(screen.getByRole("button", { name: "Decision" })).not.toBeNull();
  rerender(<FamilyChapterGate chapter="Second"><button>Decision</button></FamilyChapterGate>);
  expect(screen.queryByRole("button", { name: "Decision" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("experience.enterChapter") }));
  expect(screen.getByRole("button", { name: "Decision" })).not.toBeNull();
});

it("records only committed public statements with their actual actor", () => {
  render(<FamilyJournal turns={[turn]} coop waiting="Waiting for partner" />);
  expect(screen.getByText("Chosen reply")).not.toBeNull();
  expect(screen.getByText(t("family.mother"))).not.toBeNull();
  expect(screen.getByText("Waiting for partner")).not.toBeNull();
  expect(screen.queryByText("Recorded response")).toBeNull();
});

it("replays recorded wording with matched findings and sources, and starts a separate run", () => {
  const restart = vi.fn();
  render(<FamilyStoryboard turns={[turn, { ...turn, idx: 2, text_th: "Later choice", reply_th: "Later recorded response" }]} grandmother={false} onRestart={restart}
    report={{ safety_status: "SAFETY_NOT_MET", competencies: [], evidence: [{ idx: 1, text_th: turn.text_th, feedback_th: "Engine finding", safe: false, source_ids: ["REF"] }], sources: [{ id: "REF", title_th: "Relevant source", url: "https://example.org", summary_th: "Scope", category: "guidance" }] }} />);
  expect(screen.getByText("Recorded response")).not.toBeNull();
  expect(screen.getByText("Engine finding")).not.toBeNull();
  expect(screen.getByRole("link", { name: "Relevant source" }).getAttribute("href")).toBe("#source-REF");
  fireEvent.click(screen.getByRole("button", { name: t("experience.next"), exact: true }));
  expect(screen.getByText("Later recorded response")).not.toBeNull();
  expect(screen.queryByText("Engine finding")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("experience.restart") }));
  expect(restart).toHaveBeenCalledOnce();
});
