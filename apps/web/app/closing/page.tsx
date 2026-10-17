"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type SessionView = components["schemas"]["SessionView"];
type CaseStatus = components["schemas"]["CaseStatus"];

export default function ClosingPage() {
  const { push, replace } = useRouter();
  const [session, setSession] = useState<SessionView | null>(null);
  const [status, setStatus] = useState<CaseStatus | null>(null);
  const [note, setNote] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);

  useEffect(() => {
    const active = readSession();
    if (!active) { replace("/"); return; }
    let cancelled = false;
    void Promise.resolve().then(() => { if (!cancelled) setStatus(active.brief.status); });
    void api().GET("/v1/sessions/{session_id}", { params: { path: { session_id: active.id } } })
      .then(({ data }) => {
        if (cancelled) return;
        if (!data) { setError(t("closing.loadError")); return; }
        if (data.phase !== "CLOSING") {
          replace(data.phase === "COMPLETED" ? "/report" : "/chat");
          return;
        }
        setSession(data);
      })
      .catch(() => { if (!cancelled) setError(t("closing.loadError")); });
    return () => { cancelled = true; };
  }, [replace]);

  async function complete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || submitting.current) return;
    if (note.length > 500) { setError(t("closing.tooLong")); return; }
    const active = readSession();
    if (!active || active.id !== session.session_id) { setError(t("closing.loadError")); return; }
    submitting.current = true;
    setInFlight(true);
    setError("");
    try {
      const trimmed = note.trim();
      const { data } = await api().POST("/v1/sessions/{session_id}/complete", {
        params: { path: { session_id: active.id } },
        body: trimmed ? { note_th: trimmed } : {},
      });
      if (!data?.report_ready) throw new Error("Report not ready");
      // Never navigate to report_url supplied by the server; use the local route.
      push("/report");
    } catch {
      setError(t("closing.submitError"));
    } finally {
      submitting.current = false;
      setInFlight(false);
    }
  }

  if (!session) return <main className="mx-auto max-w-3xl px-4 py-8">
    {status && <div className="mb-5"><StatusBadge status={status} /></div>}
    {error ? <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p> : <p role="status">{t("closing.loading")}</p>}
  </main>;

  return <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-bold text-brand-800">{t("closing.eyebrow")}</p>
        <h1 className="mt-2 text-2xl font-bold text-stone-950 sm:text-3xl">{t("closing.title")}</h1>
      </div>
      <StatusBadge status={session.case.status} />
    </header>
    <form onSubmit={(event) => void complete(event)} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
      <label htmlFor="note" className="block font-semibold">{t("closing.note")}</label>
      <textarea id="note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} rows={6} disabled={inFlight} className="mt-3 w-full rounded-xl border border-stone-400 p-3 focus:outline-brand-700 disabled:bg-stone-100" />
      <button type="submit" disabled={inFlight} className="mt-5 rounded-xl bg-brand-900 px-5 py-3 font-bold text-white disabled:opacity-50">{t("closing.complete")}</button>
    </form>
    {error && <p role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p>}
  </main>;
}
