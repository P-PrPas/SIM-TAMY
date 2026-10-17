"use client";

import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api/client";
import { api, instructorApi } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

export function PilotFeedbackForm({ sessionId }: { sessionId: string }) {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    const role = form.get("role");
    if (form.get("consent") !== "on") return;
    if (role !== "learner" && role !== "instructor" && role !== "practitioner") return;
    setBusy(true); setError(false);
    try {
      const { data } = await api().POST("/v1/sessions/{session_id}/feedback", { params: { path: { session_id: sessionId } }, body: { role, usefulness: Number(form.get("usefulness")), realism: Number(form.get("realism")), comment: String(form.get("comment") ?? ""), consent: true } });
      if (!data) throw new Error("Missing feedback receipt");
      setSent(true);
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "IDEMPOTENCY_CONFLICT") setSent(true);
      else setError(true);
    } finally { setBusy(false); }
  }
  return <section className="print:hidden mt-8 rounded-2xl border border-brand-300 bg-white p-5 shadow-sm" aria-label={t("pilot.title")}>
    <h2 className="text-xl font-bold">{t("pilot.title")}</h2>
    <p className="mt-3 leading-7 text-stone-700">{t("pilot.intro")}</p>
    {sent ? <p role="status" className="mt-4 font-bold text-brand-900">{t("pilot.sent")}</p> : <form onSubmit={(event) => void submit(event)} className="mt-5 space-y-4">
      <label className="block font-semibold">{t("pilot.role")}<select name="role" defaultValue="" required className="mt-2 block w-full rounded-lg border border-stone-400 p-3"><option value="" disabled>{t("pilot.choose")}</option>{["learner", "instructor", "practitioner"].map((role) => <option key={role} value={role}>{t(`pilot.roles.${role}`)}</option>)}</select></label>
      <p className="text-sm text-stone-700">{t("pilot.scale")}</p>
      {["usefulness", "realism"].map((field) => <label key={field} className="block font-semibold">{t(`pilot.${field}`)}<select name={field} defaultValue="" required className="mt-2 block w-full rounded-lg border border-stone-400 p-3"><option value="" disabled>{t("pilot.choose")}</option>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>)}
      <label className="block font-semibold">{t("pilot.comment")}<textarea name="comment" maxLength={500} rows={3} className="mt-2 block w-full rounded-lg border border-stone-400 p-3" /></label>
      <label className="flex items-start gap-3 leading-7"><input name="consent" type="checkbox" required className="mt-1 h-5 w-5 shrink-0" />{t("pilot.consent")}</label>
      <button disabled={busy} className="rounded-lg bg-brand-900 px-5 py-3 font-bold text-white disabled:opacity-50">{t(busy ? "pilot.sending" : "pilot.send")}</button>
      {error && <p role="alert" className="text-rose-900">{t("pilot.error")}</p>}
    </form>}
  </section>;
}

type Feedback = components["schemas"]["ClassPilotFeedback"];

export function InstructorPilot({ secret, classCode, onOpenReport }: { secret: string; classCode: string; onOpenReport: (id: string) => void }) {
  const [data, setData] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function load() {
    if (busy) return;
    setBusy(true); setError(false); setData(null);
    try {
      const { data } = await instructorApi(secret).GET("/v1/instructor/feedback", { params: { query: { class_code: classCode } } });
      if (!data || !Array.isArray(data.items) || !Number.isInteger(data.total) || data.total < 0) throw new Error("Invalid feedback list");
      setData(data);
    } catch { setError(true); }
    finally { setBusy(false); }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ class_code: classCode, exported_at: new Date().toISOString(), ...data }, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = `pilot-${classCode}.json`;
    document.body.appendChild(link);
    try { link.click(); } finally { link.remove(); URL.revokeObjectURL(url); }
  }
  return <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm" aria-label={t("pilot.instructorTitle")}>
    <h2 className="text-xl font-bold">{t("pilot.instructorTitle")}</h2>
    <p className="mt-3 leading-7 text-stone-700">{t("pilot.sampleNote")}</p>
    <button type="button" disabled={busy} onClick={() => void load()} className="mt-4 rounded-lg border border-brand-800 px-4 py-3 font-semibold disabled:opacity-50">{t(busy ? "report.loading" : "pilot.load")}</button>
    {error && <p role="alert" className="mt-3 text-rose-900">{t("pilot.loadError")}</p>}
    {data && <div className="mt-5 space-y-4">
      <p className="font-bold">{t("pilot.responses")}: {data.total}</p>
      {data.total === 0 ? <p>{t("pilot.empty")}</p> : <>
        <p>{t("pilot.usefulness")}: {data.usefulness_avg?.toFixed(1) ?? "—"} / 5 · {t("pilot.realism")}: {data.realism_avg?.toFixed(1) ?? "—"} / 5</p>
        <p className="text-sm">{t("pilot.latest")}: {data.items.length}</p>
        <ul className="space-y-3">{data.items.map((item) => <li key={item.session_id} className="rounded-xl border border-stone-200 p-4"><p className="font-bold">{t(`pilot.roles.${item.role}`)}</p><time className="text-sm" dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("th-TH")}</time><p className="mt-2">{t("pilot.usefulness")}: {item.usefulness}/5 · {t("pilot.realism")}: {item.realism}/5</p>{item.comment && <p className="mt-2 whitespace-pre-wrap break-words">{item.comment}</p>}<button type="button" onClick={() => onOpenReport(item.session_id)} className="mt-3 rounded-lg border border-brand-800 px-3 py-3 font-semibold">{t("instructor.openReport")}</button></li>)}</ul>
      </>}
      <button type="button" onClick={download} className="rounded-lg bg-brand-900 px-4 py-3 font-semibold text-white">{t("pilot.download")}</button>
    </div>}
  </section>;
}
