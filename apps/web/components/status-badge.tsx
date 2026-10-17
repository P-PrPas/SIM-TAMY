import type { components } from "@/lib/api/schema";
import { statusKey } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseStatus = components["schemas"]["CaseStatus"];

export function StatusBadge({ status, compact = false }: { status: CaseStatus; compact?: boolean }) {
  const classes: Record<CaseStatus, string> = {
    Draft: "border-amber-300 bg-amber-50 text-amber-950",
    "In Review": "border-sky-300 bg-sky-50 text-sky-950",
    Approved: "border-emerald-300 bg-emerald-50 text-emerald-950",
  };
  return <span className={`inline-flex max-w-full rounded-full border px-3 py-1 text-sm font-semibold ${classes[status]}`}>
    {t(status === "Draft" && !compact ? "status.draftFull" : statusKey(status))}
  </span>;
}
