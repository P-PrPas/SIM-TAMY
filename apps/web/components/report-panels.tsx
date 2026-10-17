"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";
import { EvidenceReview } from "@/components/evidence-review";

type Report = components["schemas"]["ReportResponse"];
type Message = components["schemas"]["Message"];

export function GlassBoxPanel({ report }: { report: Report }) {
  const [selectedTurn, setSelectedTurn] = useState<number | null>(null);
  const [history, setHistory] = useState<Message[] | null>(null);
  const [error, setError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void api().GET("/v1/sessions/{session_id}", {
      params: { path: { session_id: report.session_id } },
    }).then(({ data }) => {
      if (cancelled) return;
      if (data?.status !== "completed" || !Array.isArray(data.history)
        || !data.history.every((message) => typeof message.text === "string"
          && typeof message.idx === "number"
          && ["learner", "patient", "relative", "system"].includes(message.speaker))) {
        setError(true);
        return;
      }
      setHistory(data.history);
    }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [report.session_id, retryKey]);

  const visibleHistory = history?.filter((message) => selectedTurn === null || message.idx === selectedTurn);
  return <div className="space-y-6">
    <EvidenceReview report={report} onSelectTurn={setSelectedTurn} />
    <div className="grid gap-5 md:grid-cols-2">
      <section aria-label={t("report.conversation")} className="print:hidden rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">{t("report.conversation")}</h2>
        {selectedTurn !== null && <div className="mt-3 rounded-xl bg-brand-50 p-3">
          <p role="status">{t("evidenceReview.selectedTurn")} {selectedTurn}</p>
          <button type="button" onClick={() => setSelectedTurn(null)} className="mt-2 rounded-lg border border-brand-800 px-3 py-3 font-semibold">{t("evidenceReview.showAll")}</button>
        </div>}
        {error && <div className="mt-4">
          <p role="alert">{t("report.historyLoadError")}</p>
          <button type="button" onClick={() => { setError(false); setHistory(null); setRetryKey((key) => key + 1); }} className="mt-3 rounded-lg border border-brand-800 px-3 py-2 font-semibold text-brand-900">{t("report.retry")}</button>
        </div>}
        {!error && history === null && <p role="status" className="mt-4">{t("report.loading")}</p>}
        {visibleHistory && (visibleHistory.length === 0 ? <p className="mt-4">{t("report.noHistory")}</p>
          : <ol className="mt-4 space-y-3">
            {visibleHistory.map((message, index) => <li key={index} className="rounded-xl bg-stone-50 p-3">
              <p className="text-sm font-bold text-brand-900">{t(`report.speaker.${message.speaker}`)} · {t("report.turn")} {message.idx}</p>
              <p className="mt-1 whitespace-pre-wrap break-words">{message.text}</p>
            </li>)}
          </ol>)}
      </section>
      <section aria-label={t("report.facts")} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">{t("report.facts")}</h2>
        {report.glassbox.facts.length === 0 ? <p className="mt-4">{t("report.noFacts")}</p>
          : <ul className="mt-4 space-y-3">
            {report.glassbox.facts.map((fact) => <li key={fact.id} className="rounded-xl border border-stone-200 p-3">
              <p className="whitespace-pre-wrap break-words">{fact.text_th}</p>
              <p className="mt-2 text-sm font-semibold text-stone-700">{fact.kind === "known" ? t("report.knownFact")
                : fact.revealed && fact.revealed_at_idx != null ? `${t("report.unlockedAt")} ${fact.revealed_at_idx}`
                  : t("report.neverAsked")}</p>
            </li>)}
          </ul>}
      </section>
    </div>
    <div className="grid gap-5 md:grid-cols-2">
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">{t("report.riskTimeline")}</h2>
        <ol className="mt-3 space-y-2">
          {report.glassbox.risk_state_timeline.map((point, index) => <li key={index}>
            {t("report.turn")} {point.turn_idx} · {t(`report.risk.${point.risk_state}`)}
          </li>)}
        </ol>
        <h3 className="mt-5 font-bold">{t("report.learnerActions")}</h3>
        <ul className="mt-2 space-y-2">
          {report.glassbox.learner_actions.map((action, index) => <li key={index} className="break-words">
            {t("report.turn")} {action.turn_idx} · {action.label_th}{action.repeated && ` · ${t("report.repeated")}`}
          </li>)}
        </ul>
      </section>
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">{t("report.keyEvents")}</h2>
        <ol className="mt-3 space-y-3">
          {report.timeline.map((entry) => <li key={entry.event_id} className="border-l-4 border-brand-700 pl-3">
            <p className="text-sm font-semibold">{t("report.turn")} {entry.turn_idx}</p>
            <p className="whitespace-pre-wrap break-words">{entry.summary_th}</p>
          </li>)}
        </ol>
      </section>
    </div>
  </div>;
}

export function ConsequenceReplayPanel({ replay }: { replay: Report["replay"] }) {
  return <div className="space-y-5">
    <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-bold">{t("report.scriptedScene")}</h2>
      {replay.timeline_th.length === 0 ? <p className="mt-3">{t("report.noScene")}</p>
        : <ol className="mt-4 space-y-3">
          {replay.timeline_th.map((line, index) => <li key={index} className="border-l-4 border-brand-700 pl-4 whitespace-pre-wrap break-words">{line}</li>)}
        </ol>}
    </section>
    <section className="rounded-2xl border border-amber-300 bg-amber-50 p-5">
      <h2 className="text-lg font-bold text-amber-950">{t("report.missedOpportunities")}</h2>
      {replay.missed_opportunities.length === 0 ? <p className="mt-3">{t(replay.terminal_state === "UnsafeProceed"
        ? "report.missedDataUnavailable" : "report.noMissedOpportunities")}</p>
        : <ol className="mt-4 space-y-3">
          {replay.missed_opportunities.map((marker, index) => <li key={index} className="border-l-4 border-amber-700 pl-4">
            <p className="text-sm font-bold">{t("report.turn")} {marker.turn_idx}</p>
            <p className="mt-1 whitespace-pre-wrap break-words">{marker.note_th}</p>
          </li>)}
        </ol>}
    </section>
  </div>;
}
