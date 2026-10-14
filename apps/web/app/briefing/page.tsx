"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api/runtime";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseBrief = components["schemas"]["CaseBrief"];

export default function BriefingPage() {
  const { replace } = useRouter();
  const [brief, setBrief] = useState<CaseBrief | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const session = readSession();
    if (!session) { replace("/"); return; }
    let cancelled = false;
    void api().GET("/v1/cases/{case_id}", { params: { path: { case_id: session.caseId } } })
      .then(({ data }) => { if (!cancelled) { if (data) setBrief(data); else setError(true); } })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [replace]);

  return <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
    {error ? <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-950">{t("briefing.loadError")}</div>
      : !brief ? <p role="status">{t("briefing.loading")}</p>
      : <>
        <p className="text-sm font-bold tracking-wide text-teal-800">{t("briefing.eyebrow")}</p>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-950 sm:text-4xl">{brief.title_th}</h1>
            <p className="mt-2 text-slate-600">{brief.case_id} · {brief.version}</p>
          </div>
          <StatusBadge status={brief.status} />
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold">{t("briefing.patient")}</h2>
            <p className="mt-4 whitespace-pre-wrap leading-8 text-slate-700">{brief.patient_display_th}</p>
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold">{t("briefing.objectives")}</h2>
            <ul className="mt-4 list-disc space-y-3 pl-5 text-slate-700">
              {brief.learning_objectives.map((objective) => <li key={objective.id}>{objective.label_th}</li>)}
            </ul>
          </section>
        </div>
        <p role="note" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 font-semibold text-amber-950">{brief.disclaimer_th || t("banner.educationOnly")}</p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link href="/chat" className="rounded-xl bg-teal-900 px-6 py-3 font-bold text-white hover:bg-teal-800">{t("briefing.begin")}</Link>
          <Link href="/" className="rounded-xl border border-slate-400 px-6 py-3 font-semibold text-slate-800">{t("briefing.back")}</Link>
        </div>
      </>}
  </main>;
}
