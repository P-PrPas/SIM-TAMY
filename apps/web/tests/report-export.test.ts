import { describe, expect, it } from "vitest";

import { buildReportExport } from "../lib/report-export";

describe("T-059 report export", () => {
  it("serializes the complete server report without changing its safety result", () => {
    const report = {
      session_id: "synthetic-session", case: { case_id: "DEV-001", status: "Draft" },
      effective: { safety_status: "SAFETY_NOT_MET", total_score: 99 },
      disclaimers: ["Education only"], glassbox: { facts: [{ id: "synthetic" }] },
    };
    const result = buildReportExport(report);
    expect(result.filename).toBe("sim-tamy-report-DEV-001-synthetic-session.json");
    expect(JSON.parse(result.json)).toEqual(report);
    expect(JSON.parse(result.json).effective.safety_status).toBe("SAFETY_NOT_MET");
  });

  it("keeps the session, case version/hash and rubric version in the export", () => {
    const report = {
      session_id: "s1", rubric_version: "0.3", case: { case_id: "DEV-001", version: "1.2", hash: "abc" },
    };
    const parsed = JSON.parse(buildReportExport(report).json);
    expect([parsed.session_id, parsed.rubric_version, parsed.case.version, parsed.case.hash]).toEqual(["s1", "0.3", "1.2", "abc"]);
  });

  it("sanitizes identifiers used in the suggested filename", () => {
    const result = buildReportExport({
      session_id: "a/../b", case: { case_id: "../../unsafe" },
    });
    expect(result.filename).not.toContain("/");
    expect(result.filename).not.toContain("..");
  });
});
