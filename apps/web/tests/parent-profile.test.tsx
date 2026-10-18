// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { parentProfile } from "@/lib/parent-profile";
import { ParentProfileCard } from "@/components/parent-profile";
import { FamilyReportPanel } from "@/components/family-report";
import { t } from "@/lib/i18n";
import type { components } from "@/lib/api/schema";

type Competency = components["schemas"]["FamilyCompetency"];
const item = (skill: Competency["skill"], observed: number, opportunities: number): Competency => ({ skill, observed, opportunities });
// Actual engine counts for the reviewed six-choice Parenthood path.
const report = { safety_status: "SAFETY_NOT_MET", competencies: [item("communication", 1, 5), item("responsibility", 2, 5), item("safety", 1, 2), item("support", 1, 5)], evidence: [], sources: [] };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("uses exploration when the critical gate fails despite safety being the leading domain", () => {
  expect(parentProfile(report.competencies, "SAFETY_MET")).toBe("safety");
  expect(parentProfile(report.competencies, "SAFETY_NOT_MET")).toBe("explorer");
  expect(parentProfile(report.competencies, "UNKNOWN")).toBe("explorer");
});

it.each(["communication", "responsibility", "safety", "support"] as const)("uses the completed observed proportion for %s", (skill) => {
  expect(parentProfile([item(skill, 1, 1), item(skill === "support" ? "communication" : "support", 3, 4)], "SAFETY_MET")).toBe(skill);
});

it("treats equal proportions as a combined style independently of order or raw counts", () => {
  const tied = [item("communication", 2, 4), item("support", 1, 2), item("safety", 0, 1)];
  expect(parentProfile(tied, "SAFETY_MET")).toBe("balanced");
  expect(parentProfile(tied.toReversed(), "SAFETY_MET")).toBe("balanced");
});

it("does not infer a trait from no opportunities or no observed choices", () => {
  expect(parentProfile([], "SAFETY_MET")).toBe("explorer");
  expect(parentProfile([item("support", 0, 0), item("communication", 0, 4)], "SAFETY_MET")).toBe("explorer");
});

it.each([false, true])("copies only the round profile, including critical review context; clipboard failure=%s", async (fails) => {
  const writeText = vi.fn().mockImplementation(() => fails ? Promise.reject(new Error("Unavailable")) : Promise.resolve());
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<ParentProfileCard report={report} coop />);
  expect(screen.getByText(t("profiles.team"))).not.toBeNull();
  expect(screen.queryByText(t("profiles.personal"))).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: t("profiles.copy") }));
  await screen.findByText(t(fails ? "profiles.manual" : "profiles.copied"));
  const copied = writeText.mock.calls[0]?.[0] as string;
  expect(copied).toContain(t("family.safetyReview"));
  expect(copied).toContain(t("profiles.explorer.title"));
  expect(copied).not.toContain(t("profiles.safety.title"));
  if (fails) expect((screen.getByRole("textbox") as HTMLTextAreaElement).value).toBe(copied);
});

it("retains the safety gate above the profile and does not mutate assessment data", () => {
  const before = JSON.stringify(report);
  render(<FamilyReportPanel report={report} turns={[]} grandmother={false} coop={false} onRestart={vi.fn()} />);
  const warning = screen.getByRole("alert");
  const profile = screen.getByRole("heading", { name: t("profiles.explorer.title") });
  expect(screen.queryByRole("heading", { name: t("profiles.safety.title") })).toBeNull();
  expect(screen.getByText(t("profiles.safetyGate"))).not.toBeNull();
  expect(warning.textContent).toContain(t("family.safetyReview"));
  expect(warning.compareDocumentPosition(profile) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByText(t("family.safetyObserved"))).toBeNull();
  expect(JSON.stringify(report)).toBe(before);
});
