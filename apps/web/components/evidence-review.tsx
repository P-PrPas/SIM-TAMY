import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Report = components["schemas"]["ReportResponse"];

export function EvidenceReview({ report, onSelectTurn }: { report: Report; onSelectTurn: (turn: number) => void }) {
  return <section aria-label={t("evidenceReview.title")} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
    <p className="text-sm font-bold text-brand-800">{t("evidenceReview.eyebrow")}</p>
    <h2 className="mt-2 text-xl font-bold">{t("evidenceReview.title")}</h2>
    <p className="mt-3 text-stone-700">{t("evidenceReview.source")} {report.engine_version} · {t("evidenceReview.rubric")} {report.rubric_version}</p>
    <p className="mt-1 break-all text-sm text-stone-700" data-testid="report-trace">
      {t("evidenceReview.session")} {report.session_id} · {t("evidenceReview.caseVersion")} {report.case.case_id} {report.case.version} · {t("evidenceReview.caseHash")} {report.case.hash.slice(0, 12)}
    </p>
    {report.overrides.length > 0 && <p className="mt-3">{t("evidenceReview.original")}</p>}
    {report.items.length === 0 ? <p className="mt-4">{t("evidenceReview.empty")}</p> : <ul className="mt-5 space-y-4">
      {report.items.map((item) => {
        const findings = report.findings.filter((entry) => entry.rubric_item_id === item.id);
        const references = report.references.filter((entry) => findings.some((finding) => finding.reference_ids?.includes(entry.id)));
        return <li key={item.id} className="rounded-xl border border-stone-200 p-4">
          <h3 className="font-bold">{item.id} · {t(`evidenceReview.results.${item.result}`)}</h3>
          <p className="mt-1 text-sm">{item.earned} / {item.points} · {report.competencies.find((entry) => entry.id === item.competency)?.name_th ?? item.competency}{item.critical && ` · ${t("evidenceReview.critical")}`}</p>
          {findings.map((finding) => <p key={finding.id} className="mt-3 whitespace-pre-wrap leading-7">{finding.text_th}</p>)}
          {item.evidence.length === 0 ? <p className="mt-3 text-stone-700">{t("evidenceReview.noEvidence")}</p> : <ul className="mt-3 space-y-2">
            {item.evidence.map((evidence) => <li key={evidence.event_id}>
              <button type="button" onClick={() => onSelectTurn(evidence.turn_idx)} className="rounded-lg border border-brand-800 px-3 py-3 text-left font-semibold text-brand-900">
                {t("evidenceReview.openTurn")} {evidence.turn_idx} · #{evidence.event_id}
              </button>
              <p className="mt-1 whitespace-pre-wrap text-stone-700">{report.timeline.find((event) => event.event_id === evidence.event_id)?.summary_th ?? t("evidenceReview.eventUnavailable")}</p>
            </li>)}
          </ul>}
          <h4 className="mt-4 font-semibold">{t("report.references")}</h4>
          {references.length === 0 ? <p className="mt-1 text-stone-700">{t("evidenceReview.noReferences")}</p> : <ul className="mt-2 list-disc space-y-1 pl-5">
            {references.map((reference) => <li key={reference.id}>{reference.title_th}{reference.locator && ` · ${reference.locator}`}</li>)}
          </ul>}
        </li>;
      })}
    </ul>}
  </section>;
}
