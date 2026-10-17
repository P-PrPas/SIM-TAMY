"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Recording = components["schemas"]["Recording"];
type Summary = components["schemas"]["RecordingListItem"];
type Step = components["schemas"]["RecordingStep"];

function stepLabel(step: Step, recording: Recording): string {
  if (step.type === "decision") {
    return `${t("replay.decision")}: ${recording.case.decision_options.find((option) => option.id === step.option_id)?.label_th ?? step.option_id ?? ""}`;
  }
  if (step.type === "phase_change") return `${t("replay.phase")}: ${step.phase ?? ""}`;
  if (step.type === "complete") return t("replay.complete");
  return step.text ?? "";
}

export default function ReplayPage() {
  const [items, setItems] = useState<Summary[]>([]);
  const [recording, setRecording] = useState<Recording | null>(null);
  const [index, setIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void api().GET("/v1/replay/recordings").then(({ data }) => {
      if (!cancelled) setItems((data?.items ?? []).filter((item) => item.case_id !== "DEV-001"));
    }).catch(() => { if (!cancelled) setError(t("replay.unavailable")); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [retryKey]);

  useEffect(() => {
    if (!recording || !playing || index >= recording.steps.length - 1) return;
    const next = index + 1;
    const timer = window.setTimeout(() => {
      setIndex(next);
      if (next === recording.steps.length - 1) setPlaying(false);
    }, recording.steps[next]?.t_ms ?? 0);
    return () => window.clearTimeout(timer);
  }, [recording, index, playing]);

  async function open(id: string) {
    setError("");
    setLoading(true);
    try {
      const { data } = await api().GET("/v1/replay/recordings/{recording_id}", {
        params: { path: { recording_id: id } },
      });
      if (!data || !Array.isArray(data.steps) || !data.report?.effective || !data.case?.status
        || !["SAFETY_MET", "SAFETY_NOT_MET"].includes(data.report.effective.safety_status)
        || !Number.isFinite(data.report.effective.total_score)
        || data.report.effective.total_score < 0 || data.report.effective.total_score > 100) {
        throw new Error("Invalid replay response");
      }
      setRecording(data);
      setIndex(-1);
      setPlaying(true);
    } catch {
      setError(t("replay.loadError"));
    } finally {
      setLoading(false);
    }
  }

  const done = recording && (recording.steps.length === 0 || index === recording.steps.length - 1);
  const report = done ? recording.report : null;
  const safetyNotMet = report?.effective.safety_status === "SAFETY_NOT_MET";
  const patientLabel = t(recording?.case.audience === "dad" ? "chat.wife" : recording?.case.audience === "mom" ? "chat.friend" : "chat.patient");

  return <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
    <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="font-bold text-brand-800">{t("replay.label")}</p>
        <h1 className="mt-2 text-2xl font-bold sm:text-3xl">{t("replay.title")}</h1>
      </div>
    </header>
    <Link href="/" className="inline-flex rounded-lg border border-stone-500 px-3 py-2 font-semibold">{t("replay.back")}</Link>
    {error && <div className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-950">
      <p role="alert">{error}</p>
      <button type="button" onClick={() => { setError(""); setLoading(true); setRetryKey((key) => key + 1); }} className="mt-3 rounded-lg border border-rose-800 px-4 py-2 font-semibold">{t("join.retry")}</button>
    </div>}
    {loading && <p role="status" className="mt-5">{t("replay.loading")}</p>}
    {!recording && !loading && !error && items.length === 0 && <p className="mt-5">{t("replay.empty")}</p>}
    {!recording && <ul className="mt-6 space-y-3">
      {items.map((item) => <li key={item.recording_id} className="rounded-xl border border-stone-300 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="font-semibold">{item.title_th}</p>

        </div>
        {item.description_th && <p className="mt-1 text-stone-700">{item.description_th}</p>}
        <button type="button" onClick={() => void open(item.recording_id)} disabled={loading}
          className="mt-3 rounded-lg bg-brand-900 px-4 py-2 font-semibold text-white disabled:opacity-50">{t("replay.open")}</button>
      </li>)}
    </ul>}
    {recording && <>
      <p className="mt-5 text-lg font-semibold">{recording.title_th}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {!done && <button type="button" onClick={() => setPlaying((value) => !value)}
          className="rounded-lg border border-brand-800 px-4 py-2 font-semibold text-brand-950">{t(playing ? "replay.pause" : "replay.resume")}</button>}
        <button type="button" onClick={() => { setIndex(-1); setPlaying(true); }}
          className="rounded-lg border border-stone-500 px-4 py-2 font-semibold">{t("replay.restart")}</button>
      </div>
      <ol aria-live="polite" className="mt-5 space-y-3">
        {recording.steps.slice(0, index + 1).map((step, position) => <li key={position}
          className="rounded-xl border border-stone-300 bg-white p-4">
          <p className="text-sm font-semibold text-brand-800">{step.speaker === "patient" ? patientLabel : step.speaker ? t(`chat.${step.speaker}`) : t(`replay.${step.type}`)}</p>
          <p className="mt-1 whitespace-pre-wrap break-words">{stepLabel(step, recording)}</p>
        </li>)}
      </ol>
      {report && <section className="mt-7 space-y-4" aria-label={t("report.title")}>
        <h2 className="text-xl font-bold">{t("report.title")}</h2>
        <p role={safetyNotMet ? "alert" : "status"}
          className={`rounded-xl border p-4 font-bold ${safetyNotMet ? "border-rose-500 bg-rose-50 text-rose-950" : "border-emerald-500 bg-emerald-50 text-emerald-950"}`}>
          {t(safetyNotMet ? "report.safetyNotMet" : "report.safetyMet")}
        </p>
        <p className="text-lg font-semibold">{t("report.score")}: {report.effective.total_score}</p>
        {report.debrief.paragraphs.map((paragraph, paragraphIndex) => <p key={paragraphIndex} className="whitespace-pre-wrap break-words">{paragraph.text_th}</p>)}
      </section>}
    </>}
  </main>;
}
