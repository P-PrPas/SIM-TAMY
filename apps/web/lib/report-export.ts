import type { components } from "./api/schema";

type IdentifiedReport = { session_id: string; case: { case_id: string } };

function safeFilePart(value: string): string {
  return value.replace(/[^A-Za-z0-9_-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") || "unknown";
}

/** Export exactly the post-completion server payload, with no derived claims or scores. */
export function buildReportExport<T extends IdentifiedReport>(report: T) {
  return {
    filename: `sim-tamy-report-${safeFilePart(report.case.case_id)}-${safeFilePart(report.session_id)}.json`,
    json: JSON.stringify(report, null, 2),
  };
}

export function downloadReportJson(report: components["schemas"]["ReportResponse"]): void {
  const { filename, json } = buildReportExport(report);
  const blob = new Blob([json], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(url);
  }
}
