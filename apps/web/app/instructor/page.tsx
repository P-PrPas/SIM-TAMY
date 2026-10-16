"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api/client";
import { instructorApi } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

type Room = components["schemas"]["ClassInfo"];
type Session = components["schemas"]["SessionSummary"];
type Analytics = components["schemas"]["ClassAnalytics"];
type Report = components["schemas"]["ReportResponse"];

export default function InstructorPage() {
  const [draftSecret, setDraftSecret] = useState("");
  const [secret, setSecret] = useState("");
  const [classes, setClasses] = useState<Room[]>([]);
  const [selected, setSelected] = useState<Room | null>(null);
  const [className, setClassName] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [reportError, setReportError] = useState("");
  const [busy, setBusy] = useState(false);

  async function enter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidate = draftSecret.trim();
    if (!candidate) return;
    setBusy(true); setError("");
    try {
      const { data } = await instructorApi(candidate).GET("/v1/instructor/classes");
      if (!data || !Array.isArray(data.items)) throw new Error("Invalid class list");
      setClasses(data.items);
      setSecret(candidate);
      setDraftSecret("");
    } catch (cause) {
      setError(cause instanceof ApiError && ["UNAUTHORIZED", "FORBIDDEN"].includes(cause.code)
        ? t("instructor.invalidSecret") : t("instructor.loadError"));
    } finally { setBusy(false); }
  }

  async function selectClass(room: Room) {
    setSelected(room); setReport(null); setError(""); setBusy(true);
    try {
      const client = instructorApi(secret);
      const [listed, summary] = await Promise.all([
        client.GET("/v1/instructor/sessions", { params: { query: { class_code: room.code, limit: 25 } } }),
        client.GET("/v1/instructor/analytics", { params: { query: { class_code: room.code } } }),
      ]);
      if (!listed.data || !summary.data || !Array.isArray(listed.data.items)) throw new Error("Invalid instructor response");
      setSessions(listed.data.items);
      setNextCursor(listed.data.next_cursor);
      setAnalytics(summary.data);
    } catch { setError(t("instructor.loadError")); }
    finally { setBusy(false); }
  }

  async function createClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = className.trim();
    if (!name || name.length > 80) return;
    setBusy(true); setError("");
    try {
      const { data } = await instructorApi(secret).POST("/v1/classes", { body: { name } });
      if (!data) throw new Error("Invalid class response");
      setClasses((current) => [data, ...current]);
      setClassName("");
    } catch { setError(t("instructor.createError")); }
    finally { setBusy(false); }
  }

  async function loadMore() {
    if (!selected || !nextCursor) return;
    setBusy(true); setError("");
    try {
      const { data } = await instructorApi(secret).GET("/v1/instructor/sessions", {
        params: { query: { class_code: selected.code, limit: 25, cursor: nextCursor } },
      });
      if (!data) throw new Error("Invalid session page");
      setSessions((current) => [...current, ...data.items]);
      setNextCursor(data.next_cursor);
    } catch { setError(t("instructor.loadError")); }
    finally { setBusy(false); }
  }

  async function openReport(sessionId: string) {
    setReport(null); setReportError("");
    try {
      const { data } = await instructorApi(secret).GET("/v1/sessions/{session_id}/report", {
        params: { path: { session_id: sessionId } },
      });
      if (!data || !data.case || !data.effective || !["SAFETY_MET", "SAFETY_NOT_MET"].includes(data.effective.safety_status))
        throw new Error("Invalid report");
      setReport(data);
    } catch { setReportError(t("instructor.reportError")); }
  }

  function logout() {
    setSecret(""); setDraftSecret(""); setClasses([]); setSelected(null);
    setSessions([]); setAnalytics(null); setReport(null); setNextCursor(null);
  }

  return <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
    <header className="mb-8">
      <Link href="/" className="inline-flex rounded-lg border border-teal-800 px-4 py-2 font-semibold text-teal-900">{t("instructor.back")}</Link>
      <h1 className="mt-5 text-3xl font-bold text-slate-950">{t("instructor.title")}</h1>
      <p className="mt-2 text-slate-700">{t("instructor.intro")}</p>
    </header>
    {!secret ? <form onSubmit={(event) => void enter(event)} className="max-w-lg rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <label htmlFor="instructor-secret" className="block font-semibold">{t("instructor.secret")}</label>
      <input id="instructor-secret" type="password" autoComplete="off" value={draftSecret} onChange={(event) => setDraftSecret(event.target.value)} required className="mt-2 w-full rounded-lg border border-slate-400 px-4 py-3" />
      <button type="submit" disabled={busy} className="mt-4 rounded-lg bg-teal-900 px-5 py-3 font-semibold text-white disabled:opacity-50">{t("instructor.enter")}</button>
    </form> : <div className="space-y-8">
      <button type="button" onClick={logout} className="rounded-lg border border-slate-500 px-4 py-2 font-semibold">{t("instructor.logout")}</button>
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">{t("instructor.classes")}</h2>
          <form onSubmit={(event) => void createClass(event)} className="mt-4">
            <label htmlFor="class-name" className="block font-semibold">{t("instructor.className")}</label>
            <input id="class-name" value={className} onChange={(event) => setClassName(event.target.value)} maxLength={80} required className="mt-2 w-full rounded-lg border border-slate-400 px-4 py-3" />
            <button type="submit" disabled={busy} className="mt-3 rounded-lg bg-teal-900 px-4 py-3 font-semibold text-white disabled:opacity-50">{t("instructor.createClass")}</button>
          </form>
          {classes.length === 0 ? <p className="mt-5">{t("instructor.noClasses")}</p> : <ul className="mt-5 space-y-2">
            {classes.map((room) => <li key={room.class_id}><button type="button" onClick={() => void selectClass(room)} aria-pressed={selected?.class_id === room.class_id} className="w-full rounded-lg border border-slate-300 p-3 text-left hover:bg-teal-50 focus:outline-teal-700">
              <span className="block font-semibold">{room.name}</span><span className="text-slate-700">{t("instructor.classCode")}: {room.code}</span>
            </button></li>)}
          </ul>}
        </div>
        {selected && <div className="space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-bold">{t("instructor.analytics")}: {selected.name}</h2>
            {analytics ? <div className="mt-4 space-y-4">
              <dl className="grid gap-3 sm:grid-cols-2">
                <div><dt>{t("instructor.completedCount")}</dt><dd className="text-2xl font-bold">{analytics.sessions_completed}</dd></div>
                <div><dt>{t("instructor.activeCount")}</dt><dd className="text-2xl font-bold">{analytics.sessions_active}</dd></div>
                {analytics.avg_total_score != null && <div><dt>{t("instructor.averageScore")}</dt><dd className="text-2xl font-bold">{analytics.avg_total_score}</dd></div>}
                {analytics.safety_not_met_rate != null && <div><dt>{t("instructor.safetyNotMetRate")}</dt><dd className="text-2xl font-bold">{Math.round(analytics.safety_not_met_rate * 100)}%</dd></div>}
                {analytics.avg_turns != null && <div><dt>{t("instructor.averageTurns")}</dt><dd className="text-2xl font-bold">{analytics.avg_turns}</dd></div>}
              </dl>
              {analytics.sessions_completed === 0 && <p>{t("instructor.noData")}</p>}
              {analytics.competency_avg.length > 0 && <div><h3 className="font-bold">{t("instructor.competencyAverage")}</h3><ul className="mt-2 space-y-1">{analytics.competency_avg.map((item) => <li key={item.id}>{item.name_th}: {item.avg_pct}%</li>)}</ul></div>}
              {analytics.critical_item_fail_rates.length > 0 && <div><h3 className="font-bold">{t("instructor.criticalRates")}</h3><ul className="mt-2 space-y-1">{analytics.critical_item_fail_rates.map((item) => <li key={item.item_id}>{item.label_th}: {Math.round(item.fail_rate * 100)}% ({t("instructor.sampleSize")}: {item.n})</li>)}</ul></div>}
            </div> : <p role="status" className="mt-4">{t("report.loading")}</p>}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-bold">{t("instructor.sessions")}</h2>
            {sessions.length === 0 ? <p className="mt-4">{t("instructor.noSessions")}</p> : <ul className="mt-4 space-y-4">
              {sessions.map((item) => <li key={item.session_id} className="rounded-xl border border-slate-300 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold">{item.learner_name}</h3><StatusBadge status={item.case_status} compact /></div>
                <p className="mt-2 text-slate-700">{t("instructor.case")}: {item.case_id} · {item.variant}</p>
                <p className="text-slate-700">{t("instructor.started")}: <time dateTime={item.started_at}>{new Date(item.started_at).toLocaleString("th-TH")}</time></p>
                <p className="text-slate-700">{t("instructor.turns")}: {item.turns}</p>
                <p className="mt-2 font-semibold">{item.status === "completed" ? (item.safety_status === "SAFETY_NOT_MET" ? t("report.safetyNotMet") : t("report.safetyMet")) : t("instructor.active")}</p>
                {item.status === "completed" && <button type="button" onClick={() => void openReport(item.session_id)} className="mt-3 rounded-lg border border-teal-800 px-4 py-2 font-semibold text-teal-900">{t("instructor.openReport")}</button>}
              </li>)}
            </ul>}
            {nextCursor && <button type="button" onClick={() => void loadMore()} disabled={busy} className="mt-4 rounded-lg border border-teal-800 px-4 py-2 font-semibold text-teal-900">{t("instructor.more")}</button>}
          </section>
        </div>}
      </section>
      {reportError && <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-950">{reportError}</p>}
      {report && <section className="rounded-2xl border border-slate-300 bg-white p-5 shadow-sm" aria-label={t("report.title")}>
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-2xl font-bold">{t("report.title")}</h2><p>{report.case.title_th}</p></div><StatusBadge status={report.case.status} /></div>
        <div role={report.effective.safety_status === "SAFETY_NOT_MET" ? "alert" : "status"} className={`mt-5 rounded-xl p-4 font-bold ${report.effective.safety_status === "SAFETY_NOT_MET" ? "bg-rose-50 text-rose-950" : "bg-emerald-50 text-emerald-950"}`}>{t(report.effective.safety_status === "SAFETY_NOT_MET" ? "report.safetyNotMet" : "report.safetyMet")}</div>
        <h3 className="mt-5 font-bold">{t("report.score")}: {report.effective.total_score}</h3>
        <h3 className="mt-5 font-bold">{t("report.competencies")}</h3>
        <ul>{report.competencies.map((item) => <li key={item.id}>{item.name_th}: {item.score_pct}%</li>)}</ul>
        <h3 className="mt-5 font-bold">{t("report.feedback")}</h3>
        <ul className="mt-2 space-y-2">{report.findings.map((item) => <li key={item.id} className="whitespace-pre-wrap">{item.text_th}</li>)}</ul>
        {report.disclaimers.map((note, index) => <p key={index} role="note" className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950">{note}</p>)}
        <button type="button" onClick={() => setReport(null)} className="mt-5 rounded-lg border border-slate-600 px-4 py-2">{t("instructor.closeReport")}</button>
      </section>}
    </div>}
    {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p>}
  </main>;
}
