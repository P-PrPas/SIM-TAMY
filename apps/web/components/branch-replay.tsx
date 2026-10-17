"use client";

import { useState } from "react";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Report = components["schemas"]["ReportResponse"];

export function BranchReplay({ replay, timeline = [] }: { replay: Report["replay"]; timeline?: Report["timeline"] }) {
  const [step, setStep] = useState(0);
  const terminal = replay.terminal_state === "Referral" ? "referral"
    : replay.terminal_state === "UnsafeProceed" ? "unsafe" : "other";
  const decisions = timeline.filter((event) => ["DECISION_COMMITTED", "UNSAFE_ACTION", "PHASE_CHANGED"].includes(event.type));
  return <section aria-label={t("branchReplay.title")} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
    <p className="text-sm font-bold text-brand-800">{t("branchReplay.eyebrow")}</p>
    <h2 className="mt-2 text-xl font-bold">{t("branchReplay.title")}</h2>
    <p className={`mt-4 rounded-xl border p-4 font-bold ${terminal === "unsafe" ? "border-rose-300 bg-rose-50 text-rose-950" : "border-brand-300 bg-brand-50 text-brand-950"}`}>{t(`branchReplay.${terminal}`)}</p>
    <p className="mt-3 leading-7 text-stone-700">{t("branchReplay.source")}</p>
    {decisions.length > 0 && <ol className="mt-5 space-y-3" aria-label={t("branchReplay.decisions")}>
      {decisions.map((event) => <li key={event.event_id} className="border-l-4 border-brand-700 pl-4">
        <p className="text-sm font-bold">{t("report.turn")} {event.turn_idx}</p>
        <p className="whitespace-pre-wrap break-words">{event.summary_th}</p>
      </li>)}
    </ol>}
    <h3 className="mt-6 font-bold">{t("report.scriptedScene")}</h3>
    {replay.timeline_th.length === 0 ? <p className="mt-3">{t("report.noScene")}</p> : <>
      <div className="mt-4 flex flex-wrap items-center gap-3 print:hidden">
        <button type="button" disabled={step === 0} onClick={() => setStep((value) => value - 1)} className="rounded-lg border border-brand-800 px-4 py-3 font-semibold disabled:opacity-50">{t("branchReplay.previous")}</button>
        <p role="status" aria-live="polite">{t("branchReplay.scene")} {step + 1} / {replay.timeline_th.length}</p>
        <button type="button" disabled={step >= replay.timeline_th.length - 1} onClick={() => setStep((value) => value + 1)} className="rounded-lg bg-brand-900 px-4 py-3 font-semibold text-white disabled:opacity-50">{t("branchReplay.next")}</button>
      </div>
      <ol className="mt-4 space-y-3">
        {replay.timeline_th.map((line, index) => <li key={index} aria-current={index === step ? "step" : undefined} className={`rounded-xl border p-4 whitespace-pre-wrap break-words ${index === step ? "border-brand-700 bg-brand-50" : "border-stone-200"}`}>{line}</li>)}
      </ol>
    </>}
  </section>;
}
