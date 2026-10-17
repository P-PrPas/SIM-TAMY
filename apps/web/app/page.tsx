"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { normalizeClassCode, saveSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseSummary = components["schemas"]["CaseSummary"];
type Variant = components["schemas"]["Variant"];

const AUDIENCE_ORDER = ["dad", "mom", "staff"] as const;

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
      const items = (data?.items ?? []).filter((item) => item.case_id !== "DEV-001");
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

  return <main className="join-page">
    <section className="hero">
      <div className="hero-copy">
        <p className="eyebrow"><span className="eyebrow-dot" aria-hidden="true" />{t("join.eyebrow")}</p>
        <h1>{t("join.title")}</h1>
        <p className="hero-description">{t("join.description")}</p>
        <div className="hero-actions">
          <a href="#practice" className="button-primary">{t("join.heroCta")}<span aria-hidden="true"> ↗</span></a>
          <Link href="/replay" className="button-text">{t("replay.switch")}<span aria-hidden="true"> →</span></Link>
        </div>
        <p className="hero-note"><span aria-hidden="true">✓</span> {t("join.heroNote")}</p>
      </div>
      <div className="hero-art">
        <div className="art-orbit art-orbit-one" /><div className="art-orbit art-orbit-two" />
        <span className="art-spark" aria-hidden="true">✳</span>
        <p className="art-kicker">{t("join.artLabel")}</p>
        <Image src="/brand/logo.png" width={290} height={290} alt="" priority className="hero-logo" />
        <div className="art-caption"><span className="art-line" /><p>{t("join.artTitle")}<small>{t("join.artNote")}</small></p></div>
      </div>
    </section>
    <section className="learning-features" aria-label={t("join.heroSecondary")}>
      {[1, 2, 3].map((number) => <article key={number}>
        <span className="feature-number" aria-hidden="true">0{number}</span>
        <div><h2>{t(`join.feature${number}Title`)}</h2><p>{t(`join.feature${number}Text`)}</p></div>
      </article>)}
    </section>
    <section id="practice" className="practice-section" aria-labelledby="practice-title">
      <div className="section-heading"><div><p className="eyebrow">{t("join.sectionEyebrow")}</p><h2 id="practice-title">{t("join.sectionTitle")}</h2></div><p>{t("join.sectionDescription")}</p></div>
      <form onSubmit={(event) => void start(event)} className="enrollment-form">
        <div className="enrollment-fields">
          <div className="form-intro"><h3>{t("join.formTitle")}</h3><p>{t("join.formDescription")}</p></div>
          <div className="space-y-5">
            <div>
              <label htmlFor="nickname" className="mb-2 block font-semibold">{t("join.nickname")}</label>
              <input id="nickname" value={nickname} onChange={(event) => setNickname(event.target.value)} maxLength={30} required autoComplete="nickname" placeholder={t("join.nicknamePlaceholder")} className="w-full rounded-xl border border-stone-400 px-4 py-3 outline-offset-2 focus:outline-brand-700" />
            </div>
            <div>
              <label htmlFor="class-code" className="mb-2 block font-semibold">{t("join.classCode")}</label>
              <input id="class-code" value={classCode} onChange={(event) => setClassCode(event.target.value)} maxLength={6} autoCapitalize="characters" placeholder={t("join.classCodePlaceholder")} className="w-full rounded-xl border border-stone-400 px-4 py-3 uppercase outline-offset-2 focus:outline-brand-700" />
            </div>
            <div>
              <label htmlFor="case" className="mb-2 block font-semibold">{t("join.case")}</label>
              <select id="case" value={caseId} onChange={(event) => {
                setCaseId(event.target.value);
                setVariant(cases.find((item) => item.case_id === event.target.value)?.variants_available[0] ?? "A");
              }} disabled={loading || cases.length === 0} className="w-full rounded-xl border border-stone-400 bg-white px-4 py-3 focus:outline-brand-700">
                {cases.some((item) => item.audience)
                  ? [...AUDIENCE_ORDER, null].map((audience) => {
                    const group = cases.filter((item) => (item.audience ?? null) === audience);
                    return group.length > 0 && (
                      <optgroup key={audience ?? "other"} label={t(`audience.${audience ?? "other"}`)}>
                        {group.map((item) => <option key={item.case_id} value={item.case_id}>{item.title_th}</option>)}
                      </optgroup>
                    );
                  })
                  : cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.title_th}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="variant" className="mb-2 block font-semibold">{t("join.variant")}</label>
              <select id="variant" value={variant} onChange={(event) => setVariant(event.target.value as Variant)} disabled={!selectedCase} className="w-full rounded-xl border border-stone-400 bg-white px-4 py-3 focus:outline-brand-700">
                {selectedCase?.variants_available.map((item) => <option key={item} value={item}>{t(item === "A" ? "join.variantA" : "join.variantC")}</option>)}
              </select>
            </div>
          </div>
        </div>
        <div className="case-preview">
          <div>
            <span className="preview-mark" aria-hidden="true">↗</span>
            <p className="preview-label">{t("join.previewLabel")}</p>
            <p className="preview-title" aria-live="polite">{selectedCase?.title_th ?? (loading ? t("join.loading") : t("join.empty"))}</p>
            {selectedCase && <div className="mt-4"><StatusBadge status={selectedCase.status} /></div>}
            <p className="preview-note">{t("join.previewNote")}</p>
          </div>
          <div className="mt-8">
            {error && <p role="alert" className="mb-4 rounded-lg bg-rose-50 p-3 text-rose-950">{error}</p>}
            {error === t("join.loadError") && <button type="button" onClick={() => { setLoading(true); setError(""); setRetryKey((key) => key + 1); }} className="mb-3 w-full rounded-xl border border-white px-4 py-3 font-semibold">{t("join.retry")}</button>}
            <button type="submit" disabled={!selectedCase || submitting} aria-busy={submitting} className="button-gold w-full">{t(submitting ? "join.starting" : "join.start")}<span aria-hidden="true"> →</span></button>
            <p className="preview-privacy">{t("join.privacyNote")}</p>
          </div>
        </div>
      </form>
    </section>
  </main>;
}
