"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

import { ConsequenceReplayPanel, GlassBoxPanel } from "@/components/report-panels";
import { SafetyAudit } from "@/components/safety-audit";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/flow";
import { t } from "@/lib/i18n";
import { downloadReportJson } from "@/lib/report-export";
import { PilotFeedbackForm } from "@/components/pilot-feedback";

type Report = components["schemas"]["ReportResponse"];
type Tab = "summary" | "timeline" | "glassBox" | "consequenceReplay" | "review";

export default function ReportPage() {
  const { replace } = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [tab, setTab] = useState<Tab>("summary");
  const [printing, setPrinting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const request = useRef(0);

  const load = useCallback(async (id: string) => {
    const current = ++request.current;
    setLoading(true);
    setError("");
    try {
      const { data } = await api().GET("/v1/sessions/{session_id}/report", {
        params: { path: { session_id: id } },
      });
      if (!data || data.session_id !== id || !data.effective || !data.case
        || !["SAFETY_MET", "SAFETY_NOT_MET"].includes(data.effective.safety_status)
        || typeof data.effective.total_score !== "number"
        || !Number.isFinite(data.effective.total_score)
        || data.effective.total_score < 0 || data.effective.total_score > 100
        || !["Draft", "In Review", "Approved"].includes(data.case.status)
        || !Array.isArray(data.competencies)
        || !Array.isArray(data.items) || !Array.isArray(data.overrides)
        || !Array.isArray(data.findings) || !Array.isArray(data.timeline)
        || !Array.isArray(data.references) || !Array.isArray(data.debrief?.paragraphs)
        || !Array.isArray(data.glassbox?.facts)
        || !Array.isArray(data.glassbox?.risk_state_timeline)
        || !Array.isArray(data.glassbox?.learner_actions)
        || !Array.isArray(data.replay?.timeline_th)
        || !Array.isArray(data.replay?.missed_opportunities)
        || typeof data.replay?.disclaimer_th !== "string"
        || !Array.isArray(data.disclaimers)) throw new Error("Invalid report response");
      if (current === request.current) setReport(data);
    } catch (cause) {
      if (current === request.current) {
        setError(cause instanceof ApiError && cause.code === "REPORT_NOT_READY"
          ? t("report.notReady") : t("report.loadError"));
      }
    } finally {
      if (current === request.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const active = readSession();
    if (!active) { replace("/"); return; }
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (cancelled) return;
      void load(active.id);
    });
    return () => { cancelled = true; };
  }, [load, replace]);

  useEffect(() => {
    if (!printing) return;
    const done = () => setPrinting(false);
    window.addEventListener("afterprint", done, { once: true });
    window.print();
    return () => window.removeEventListener("afterprint", done);
  }, [printing]);

  function retry() {
    const active = readSession();
    if (!active) { replace("/"); return; }
    void load(active.id);
  }

  if (!report) return <main className="mx-auto w-full max-w-4xl px-4 py-8">
    {error ? <div className="rounded-xl bg-rose-50 p-5 text-rose-950">
      <p role="alert">{error}</p>
      <button type="button" onClick={retry} className="mt-4 rounded-lg border border-rose-800 px-4 py-2 font-semibold">{t("report.retry")}</button>
    </div> : <p role="status">{t("report.loading")}</p>}
  </main>;

  const safetyNotMet = report.effective.safety_status === "SAFETY_NOT_MET";
  const needsReview = report.findings.filter((finding) => finding.polarity === "improve");
  const tabs: Tab[] = ["summary", "timeline", "glassBox", "consequenceReplay", "review"];
  // Printing renders every panel, because the tab bar is hidden on paper.
  const shown = (id: Tab) => printing || tab === id;
  const title = (id: Tab) => printing && <h2 className="mb-3 mt-8 text-xl font-bold text-stone-950">{t(`report.${id}`)}</h2>;

  function onTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % tabs.length
      : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length
        : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    const target = tabs[next];
    if (!target) return;
    event.preventDefault();
    setTab(target);
    event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=tab]")[next]?.focus();
  }

  return <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12 print:max-w-none print:p-0">
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-bold text-brand-800">{t("report.eyebrow")}</p>
        <h1 className="mt-2 text-2xl font-bold text-stone-950 sm:text-3xl">{t("report.title")}</h1>
        <p className="mt-2 text-stone-700">{report.case.title_th}</p>
      </div>
    </header>
    <section role={safetyNotMet ? "alert" : "status"} className={`rounded-2xl border p-5 text-lg font-bold ${safetyNotMet ? "border-rose-500 bg-rose-50 text-rose-950" : "border-emerald-500 bg-emerald-50 text-emerald-950"}`}>
      {t(safetyNotMet ? "report.safetyNotMet" : "report.safetyMet")}
    </section>
    <div className="mt-5 flex flex-wrap gap-3 print:hidden">
      <button type="button" onClick={() => downloadReportJson(report)} className="rounded-xl border border-brand-800 bg-white px-4 py-3 font-semibold text-brand-900">{t("report.downloadJson")}</button>
      <button type="button" onClick={() => setPrinting(true)} className="rounded-xl border border-brand-800 bg-white px-4 py-3 font-semibold text-brand-900">{t("report.print")}</button>
    </div>
    <div role="tablist" aria-label={t("report.title")} className="print:hidden mt-6 flex flex-wrap gap-2 border-b border-stone-300 pb-3">
      {tabs.map((item, index) => <button key={item} id={`tab-${item}`} type="button" role="tab" aria-selected={tab === item} aria-controls={`panel-${item}`} tabIndex={tab === item ? 0 : -1} onClick={() => setTab(item)} onKeyDown={(event) => onTabKeyDown(event, index)} className={`rounded-xl px-4 py-3 font-semibold ${tab === item ? "bg-brand-900 text-white" : "bg-stone-100 text-stone-900"}`}>{t(`report.${item}`)}</button>)}
    </div>
    <section id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} className="mt-6">
      {shown("summary") && <div className="space-y-6">
        {title("summary")}
        <SafetyAudit report={report} />
        <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">{t("report.score")}</h2>
          <p className="mt-2 text-4xl font-bold text-stone-950">{report.effective.total_score}</p>
        </section>
        <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">{t("report.competencies")}</h2>
          <ul className="mt-4 space-y-4">
            {report.competencies.map((entry) => <li key={entry.id} className="flex flex-wrap justify-between gap-2 border-b border-stone-100 pb-3">
              <span className="break-words">{entry.name_th}</span>
              <span className="font-bold">{entry.score_pct}%</span>
            </li>)}
          </ul>
        </section>
        {report.debrief.paragraphs.length > 0 && <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">{t("report.feedback")}</h2>
          {report.debrief.paragraphs.map((paragraph, index) => <p key={index} className="mt-3 whitespace-pre-wrap break-words leading-7">{paragraph.text_th}</p>)}
        </section>}
      </div>}
      {shown("timeline") && <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        {title("timeline")}
        {report.timeline.length === 0 ? <p>{t("report.noTimeline")}</p> : <ol className="space-y-4">
          {report.timeline.map((entry, index) => <li key={entry.event_id} className="practice-event-card">
            <span aria-hidden="true">{index + 1}</span><div><p className="text-sm font-semibold text-stone-700">{t("report.turn")} {entry.turn_idx}</p>
            <p className="mt-1 whitespace-pre-wrap break-words">{entry.summary_th}</p></div>
          </li>)}
        </ol>}
      </section>}
      {shown("glassBox") && <>{title("glassBox")}<GlassBoxPanel report={report} /></>}
      {shown("consequenceReplay") && <>{title("consequenceReplay")}<ConsequenceReplayPanel replay={report.replay} timeline={report.timeline} /></>}
      {shown("review") && <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        {title("review")}
        {needsReview.length === 0 ? <p>{t("report.noReview")}</p> : <ul className="space-y-6">
          {needsReview.map((finding) => {
            const references = report.references.filter((reference) => finding.reference_ids?.includes(reference.id));
            return <li key={finding.id} className="border-b border-stone-200 pb-5 last:border-0 last:pb-0">
              <p className="whitespace-pre-wrap break-words font-semibold">{finding.text_th}</p>
              {references.length > 0 && <div className="mt-3">
                <h3 className="text-sm font-bold">{t("report.references")}</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {references.map((reference) => <li key={reference.id} className="break-words">{reference.title_th}{reference.locator && <span className="ml-2 text-stone-700">{reference.locator}</span>}</li>)}
                </ul>
              </div>}
            </li>;
          })}
        </ul>}
      </section>}
    </section>
    <PilotFeedbackForm key={report.session_id} sessionId={report.session_id} />
    {loading && <p role="status" className="mt-4">{t("report.loading")}</p>}
  </main>;
}
