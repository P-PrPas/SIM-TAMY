"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/status-badge";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/flow";
import { t } from "@/lib/i18n";

type CaseBrief = components["schemas"]["CaseBrief"];
type Notice = components["schemas"]["Notice"];

export default function BriefingPage() {
  const { replace } = useRouter();
  const [brief, setBrief] = useState<CaseBrief | null>(null);
  const [notices, setNotices] = useState<Notice[]>([]);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve(readSession()).then((session) => { // same async shape as the chat page
      if (cancelled) return;
      if (!session) { replace("/"); return; }
      setBrief(session.brief); // the version this session was created with, not the latest case
      setNotices((session.notices ?? []).filter((notice) =>
        notice.code === "PRIVACY_LLM" || notice.code === "NO_REAL_PII"));
    });
    return () => { cancelled = true; };
  }, [replace]);

  return <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
    {!brief ? <p role="status">{t("briefing.loading")}</p>
      : <>
        <p className="text-sm font-bold tracking-wide text-brand-800">{t("briefing.eyebrow")}</p>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-stone-950 sm:text-4xl">{brief.title_th}</h1>
          </div>
          <StatusBadge status={brief.status} />
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <section className="rounded-2xl border border-brand-950 bg-brand-950 p-6 text-brand-50 shadow-sm sm:p-8">
            <h2 className="text-xl font-bold">{t("briefing.patient")}</h2>
            <p className="mt-4 whitespace-pre-wrap leading-8 text-brand-100">{brief.patient_display_th}</p>
          </section>
          <section className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="text-xl font-bold">{t("briefing.objectives")}</h2>
            <ul className="mt-4 list-disc space-y-3 pl-5 text-stone-700">
              {brief.learning_objectives.map((objective) => <li key={objective.id}>{objective.label_th}</li>)}
            </ul>
          </section>
        </div>
        <p role="note" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 font-semibold text-amber-950">{brief.disclaimer_th || t("banner.educationOnly")}</p>
        {notices.map((notice) => <p key={notice.code} role="note" className="mt-3 rounded-xl border border-stone-300 bg-stone-50 p-4 text-stone-800">{notice.text_th}</p>)}
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link href="/chat" className="rounded-xl bg-brand-900 px-6 py-3 font-bold text-white hover:bg-brand-800">{t("briefing.begin")}</Link>
          <Link href="/" className="rounded-xl border border-stone-400 px-6 py-3 font-semibold text-stone-800">{t("briefing.back")}</Link>
        </div>
      </>}
  </main>;
}
