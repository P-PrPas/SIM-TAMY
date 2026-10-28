"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type SessionView = components["schemas"]["SessionView"];
type DecisionOption = components["schemas"]["DecisionOption"];

export default function DecisionPage() {
  const { push, replace } = useRouter();
  const [session, setSession] = useState<SessionView | null>(null);
  const [options, setOptions] = useState<DecisionOption[]>([]);
  const [selected, setSelected] = useState("");
  const [rationale, setRationale] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);

  useEffect(() => {
    const active = readSession();
    if (!active) { replace("/lab/solo"); return; }
    let cancelled = false;
    void api().GET("/v1/sessions/{session_id}", { params: { path: { session_id: active.id } } })
      .then(({ data }) => {
        if (cancelled) return;
        if (!data) { setError(t("decision.loadError")); return; }
        if (data.phase !== "INTERVIEW") {
          replace(data.phase === "CLOSING" ? "/closing" : data.phase === "COMPLETED" ? "/report" : "/chat");
          return;
        }
        setSession(data);
        setOptions(active.brief.decision_options);
      })
      .catch(() => { if (!cancelled) setError(t("decision.loadError")); });
    return () => { cancelled = true; };
  }, [replace]);

  function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!options.some((option) => option.id === selected)) { setError(t("decision.selectError")); return; }
    if (rationale.length > 300) { setError(t("decision.tooLong")); return; }
    setError("");
    setReviewing(true);
  }

  async function confirm() {
    if (!session || !selected || submitting.current) return;
    const active = readSession();
    if (!active || active.id !== session.session_id) { setError(t("decision.loadError")); return; }
    submitting.current = true;
    setInFlight(true);
    setError("");
    try {
      const reason = rationale.trim();
      const { data } = await api().POST("/v1/sessions/{session_id}/decision", {
        params: { path: { session_id: active.id } },
        body: { option_id: selected, ...(reason ? { rationale_th: reason } : {}) },
      });
      if (data?.phase === "PRESSURE") push("/chat");
      else if (data?.phase === "CLOSING") push("/closing");
      else throw new Error("Unexpected decision response");
    } catch {
      setError(t("decision.submitError"));
    } finally {
      submitting.current = false;
      setInFlight(false);
    }
  }

  if (!session) return <main className="mx-auto max-w-3xl px-4 py-8">
    {error ? <p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p> : <p role="status">{t("decision.loading")}</p>}
  </main>;

  return <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-bold text-brand-800">{t("decision.eyebrow")}</p>
        <h1 className="mt-2 text-2xl font-bold text-stone-950 sm:text-3xl">{t("decision.title")}</h1>
      </div>
    </header>
    {reviewing ? <section className="rounded-2xl border border-amber-300 bg-amber-50 p-5">
      <h2 className="text-xl font-bold">{t("decision.selected")}</h2>
      <p className="mt-3 break-words">{options.find((option) => option.id === selected)?.label_th}</p>
      {rationale.trim() && <p className="mt-3 whitespace-pre-wrap break-words">{rationale.trim()}</p>}
      <p className="mt-4 font-semibold text-amber-950">{t("decision.irreversible")}</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" onClick={() => { setReviewing(false); setError(""); }} disabled={inFlight} className="rounded-xl border border-stone-500 px-5 py-3 font-semibold disabled:opacity-50">{t("decision.change")}</button>
        <button type="button" onClick={() => void confirm()} disabled={inFlight} className="rounded-xl bg-brand-900 px-5 py-3 font-bold text-white disabled:opacity-50">{t("decision.confirm")}</button>
      </div>
    </section> : <form onSubmit={review} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
      <fieldset>
        <legend className="text-xl font-bold">{t("decision.select")}</legend>
        <div className="mt-4 space-y-3">
          {options.map((option) => <label key={option.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-stone-300 p-4 transition-colors hover:border-brand-600 has-checked:border-brand-700 has-checked:bg-brand-50">
            <input type="radio" name="decision" value={option.id} checked={selected === option.id} onChange={() => setSelected(option.id)} className="mt-1 size-5 accent-brand-900" />
            <span className="break-words">{option.label_th}</span>
          </label>)}
        </div>
      </fieldset>
      <label htmlFor="rationale" className="mt-6 block font-semibold">{t("decision.rationale")}</label>
      <textarea id="rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} maxLength={300} rows={3} className="mt-2 w-full rounded-xl border border-stone-400 p-3 focus:outline-brand-700" />
      <button type="submit" className="mt-5 rounded-xl bg-brand-900 px-5 py-3 font-bold text-white">{t("decision.review")}</button>
    </form>}
    {error && <p role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-950">{error}</p>}
  </main>;
}
