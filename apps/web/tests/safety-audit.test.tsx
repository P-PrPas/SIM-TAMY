// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SafetyAudit } from "../components/safety-audit";
import type { components } from "../lib/api/schema";
import { t } from "../lib/i18n";
import { syntheticReport } from "../e2e/fixtures/report";

afterEach(cleanup);

it("exposes a failed critical action even with a high total and excludes noncritical items", () => {
  const report: components["schemas"]["ReportResponse"] = {
    ...syntheticReport,
    variant: "A",
    case: { ...syntheticReport.case, status: "Draft" },
    safety_status: "SAFETY_NOT_MET",
    effective: { safety_status: "SAFETY_NOT_MET", total_score: 99 },
    findings: [], timeline: [], competencies: [], debrief: { source: "template", paragraphs: [] },
    items: [
      { id: "CRITICAL", competency: "RISK", critical: true, result: "fail", points: 1, earned: 0, evidence: [{ event_id: 7, turn_idx: 3, type: "DECISION_COMMITTED" }] },
      { id: "OPTIONAL", competency: "RISK", critical: false, result: "pass", points: 99, earned: 99, evidence: [] },
    ],
  };
  render(<SafetyAudit report={report} />);
  expect(screen.getByText("CRITICAL")).toBeTruthy();
  expect(screen.getByText(t("safetyAudit.results.fail"))).toBeTruthy();
  expect(screen.getByText(/#7/).textContent).toContain("3");
  expect(screen.queryByText("OPTIONAL")).toBeNull();
  expect(screen.queryByText(t("report.safetyMet"))).toBeNull();
});
