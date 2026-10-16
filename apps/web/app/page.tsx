"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { normalizeClassCode, saveSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseSummary = components["schemas"]["CaseSummary"];
type Variant = components["schemas"]["Variant"];

export default function JoinPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseId] = useState("");
  const [variant, setVariant] = useState<Variant>("A");
  const [nickname, setNickname] = useState("");
  const [classCode, setClassCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const selectedCase = cases.find((item) => item.case_id === caseId);

  useEffect(() => {
    let cancelled = false;
    void api().GET("/v1/cases").then(({ data }) => {
      if (cancelled) return;
      const items = data?.items ?? [];
      setCases(items);
      setCaseId(items[0]?.case_id ?? "");
      setVariant(items[0]?.variants_available[0] ?? "A");
    }).catch(() => { if (!cancelled) setError(t("join.loadError")); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [retryKey]);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const name = nickname.trim();
    const code = normalizeClassCode(classCode);
    if (!name || name.length > 30) { setError(t("join.invalidName")); return; }
    if (code === null) { setError(t("join.invalidCode")); return; }
    if (!selectedCase || !selectedCase.variants_available.includes(variant)) return;
    setSubmitting(true);
    try {
      const { data } = await api().POST("/v1/sessions", {
        body: { case_id: caseId, variant, learner_name: name, ...(code ? { class_code: code } : {}) },
      });
      if (!data) throw new Error("Missing session response");
      saveSession({ id: data.session_id, token: data.token, caseId, brief: data.case, notices: data.notices });
      router.push("/briefing");
    } catch (cause) {
      setError(cause instanceof ApiError && cause.code === "CLASS_NOT_FOUND"
        ? t("join.classNotFound") : t("join.startError"));
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
    <div className="mb-8 max-w-2xl">
      <Link href="/replay" className="mb-4 inline-flex rounded-lg border border-teal-800 px-3 py-2 font-semibold text-teal-900">{t("replay.switch")}</Link>
      <p className="mb-2 text-sm font-bold tracking-wide text-teal-800">{t("join.eyebrow")}</p>
      <h1 className="text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">{t("join.title")}</h1>
      <p className="mt-3 text-slate-700">{t("join.description")}</p>
    </div>
    <form onSubmit={(event) => void start(event)} className="grid gap-7 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-5">
        <div>
          <label htmlFor="nickname" className="mb-2 block font-semibold">{t("join.nickname")}</label>
          <input id="nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} maxLength={30} required placeholder={t("join.nicknamePlaceholder")} className="w-full rounded-xl border border-slate-400 px-4 py-3 outline-offset-2 focus:outline-teal-700" />
        </div>
        <div>
          <label htmlFor="class-code" className="mb-2 block font-semibold">{t("join.classCode")}</label>
          <input id="class-code" value={classCode} onChange={(event) => setClassCode(event.target.value)} maxLength={6} autoCapitalize="characters" placeholder={t("join.classCodePlaceholder")} className="w-full rounded-xl border border-slate-400 px-4 py-3 uppercase outline-offset-2 focus:outline-teal-700" />
        </div>
        <div>
          <label htmlFor="case" className="mb-2 block font-semibold">{t("join.case")}</label>
          <select id="case" value={caseId} onChange={(event) => {
            setCaseId(event.target.value);
            setVariant(cases.find((item) => item.case_id === event.target.value)?.variants_available[0] ?? "A");
          }} disabled={loading || cases.length === 0} className="w-full rounded-xl border border-slate-400 bg-white px-4 py-3 focus:outline-teal-700">
            {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.title_th}</option>)}
          </select>
          {selectedCase && <div className="mt-3"><StatusBadge status={selectedCase.status} /></div>}
        </div>
        <div>
          <label htmlFor="variant" className="mb-2 block font-semibold">{t("join.variant")}</label>
          <select id="variant" value={variant} onChange={(event) => setVariant(event.target.value as Variant)} disabled={!selectedCase} className="w-full rounded-xl border border-slate-400 bg-white px-4 py-3 focus:outline-teal-700">
            {selectedCase?.variants_available.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
      </div>
      <div className="flex flex-col justify-between rounded-2xl bg-teal-950 p-5 text-white sm:p-7">
        <div>
          <p className="text-sm font-semibold text-teal-200">SIM-TAMY</p>
          <p className="mt-4 text-xl font-semibold leading-relaxed">{selectedCase?.title_th ?? (loading ? t("join.loading") : t("join.empty"))}</p>
          {selectedCase && <p className="mt-3 text-sm text-teal-100">{selectedCase.case_id} · {selectedCase.version}</p>}
        </div>
        <div className="mt-8">
          {error && <p role="alert" className="mb-4 rounded-lg bg-rose-50 p-3 text-rose-950">{error}</p>}
          {error === t("join.loadError") && <button type="button" onClick={() => { setLoading(true); setError(""); setRetryKey((key) => key + 1); }} className="mb-3 w-full rounded-xl border border-white px-4 py-3 font-semibold">{t("join.retry")}</button>}
          <button type="submit" disabled={!selectedCase || submitting} className="w-full rounded-xl bg-amber-300 px-4 py-3 font-bold text-slate-950 hover:bg-amber-200 disabled:opacity-50">{t("join.start")}</button>
        </div>
      </div>
    </form>
  </main>;
}
