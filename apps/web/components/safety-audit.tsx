import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Report = components["schemas"]["ReportResponse"];

export function SafetyAudit({ report }: { report: Report }) {
  const critical = report.items.filter((item) => item.critical);
  return <section aria-label={t("safetyAudit.title")} className="rounded-2xl border border-brand-300 bg-white p-5 shadow-sm">
    <p className="text-sm font-bold text-brand-800">{t("safetyAudit.eyebrow")}</p>
    <h2 className="mt-2 text-xl font-bold">{t("safetyAudit.title")}</h2>
    <p className="mt-3 leading-7 text-stone-700">{t("safetyAudit.explanation")}</p>
    {report.overrides.length > 0 && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-amber-950">{t("safetyAudit.original")}</p>}
    {critical.length === 0 ? <p className="mt-4">{t("safetyAudit.empty")}</p>
      : <ul className="mt-5 space-y-3">
        {critical.map((item) => {
          const finding = report.findings.find((entry) => entry.rubric_item_id === item.id);
          return <li key={item.id} className={`rounded-xl border p-4 ${item.result === "fail" ? "border-rose-300 bg-rose-50" : "border-stone-200 bg-stone-50"}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="font-bold break-words">{item.id}</h3>
              <span className="font-semibold">{t(`safetyAudit.results.${item.result}`)}</span>
            </div>
            {finding && <p className="mt-2 whitespace-pre-wrap leading-7">{finding.text_th}</p>}
            <p className="mt-2 text-sm text-stone-700">{t("safetyAudit.competency")}: {report.competencies.find((entry) => entry.id === item.competency)?.name_th ?? item.competency}</p>
            <p className="mt-2 text-sm">{t("safetyAudit.evidence")}: {item.evidence.length
              ? item.evidence.map((entry) => `${t("report.turn")} ${entry.turn_idx} · #${entry.event_id}`).join(", ")
              : t("safetyAudit.noEvidence")}</p>
          </li>;
        })}
      </ul>}
  </section>;
}
