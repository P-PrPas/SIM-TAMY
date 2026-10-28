"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { LoadState, Stat, field } from "@/components/institution-bits";
import { DemoBadge, useStaff } from "@/components/institution-shell";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

function ratio(numerator: number, n: number) {
  return t("institution.analytics.ratio").replace("{numerator}", String(numerator)).replace("{n}", String(n));
}

function Panel({ cohortId }: { cohortId: string }) {
  const { id } = useStaff();
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/cohorts/{cohort_id}/analytics", {
      params: { path: { cohort_id: cohortId } },
    });
    if (!data) throw new Error("empty analytics");
    return data;
  }, `${id}:${cohortId}`);

  return (
    <div className="mt-4 space-y-6">
      <LoadState error={error} loading={!data} onRetry={reload} />
      {data && (
        <>
          {data.demo && <DemoBadge />}
          <dl className="grid gap-3 sm:grid-cols-3">
            <Stat label={t("institution.analytics.started")} value={data.n_started} />
            <Stat label={t("institution.analytics.finished")} value={data.n_finished} />
            <Stat
              label={t("institution.analytics.safetyTitle")}
              value={data.safety_not_met.n === 0 ? "-" : ratio(data.safety_not_met.numerator, data.safety_not_met.n)}
              hint={data.safety_not_met.n === 0 ? t("institution.analytics.noFinished") : undefined}
            />
          </dl>
          <section aria-labelledby="objectives-title">
            <h3 id="objectives-title" className="text-lg font-bold">{t("institution.analytics.objectivesTitle")}</h3>
            {data.objectives.length === 0 && <p className="mt-2">{t("institution.analytics.objectivesNone")}</p>}
            <ul className="mt-2 space-y-2">
              {data.objectives.map((o) => (
                <li key={o.objective_id} className="rounded-lg border border-stone-300 bg-white p-3">
                  <span className="font-mono font-semibold">{o.objective_id}</span>
                  {": "}
                  {o.suppressed || o.numerator === null ? (
                    <span>{t("institution.analytics.suppressed")}</span>
                  ) : (
                    <span>{t("institution.analytics.objectiveMet")} {ratio(o.numerator, o.n)}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="bystory-title">
            <h3 id="bystory-title" className="text-lg font-bold">{t("institution.analytics.byStoryTitle")}</h3>
            <ul className="mt-2 space-y-2">
              {data.by_story.map((s) => (
                <li key={`${s.story_id}@${s.story_version}`} className="rounded-lg border border-stone-300 bg-white p-3">
                  <span className="font-semibold">{s.story_id}</span>
                  <span>
                    {" · "}{t("institution.analytics.storyVersion")} {s.story_version}
                    {" · "}{t("institution.analytics.finishedCount").replace("{n}", String(s.n_finished))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <p className="text-stone-700">{t("institution.analytics.aggregateNote")}</p>
        </>
      )}
    </div>
  );
}

function AnalyticsInner() {
  const { org_id: orgId, id } = useStaff();
  const preset = useSearchParams().get("cohort") ?? "";
  const [picked, setPicked] = useState(preset);
  const cohorts = useLoad(async () => {
    const { data } = await api().GET("/v1/orgs/{org_id}/cohorts", { params: { path: { org_id: orgId } } });
    if (!data) throw new Error("empty cohorts");
    return data.items;
  }, id);

  return (
    <section aria-labelledby="analytics-title">
      <h2 id="analytics-title" className="text-xl font-bold">{t("institution.analytics.title")}</h2>
      <LoadState error={cohorts.error} loading={!cohorts.data} onRetry={cohorts.reload} />
      {cohorts.data?.length === 0 && <p className="mt-2">{t("institution.analytics.noCohorts")}</p>}
      {cohorts.data && cohorts.data.length > 0 && (
        <div className="mt-3 max-w-md">
          <label htmlFor="analytics-cohort" className="block font-semibold">{t("institution.analytics.pick")}</label>
          <select id="analytics-cohort" value={picked} onChange={(e) => setPicked(e.target.value)} className={field}>
            <option value="">{t("institution.analytics.pickPlaceholder")}</option>
            {cohorts.data.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      )}
      {picked && cohorts.data?.some((c) => c.id === picked) && <Panel cohortId={picked} />}
    </section>
  );
}

export default function AnalyticsPage() {
  return <Suspense fallback={<p>{t("institution.loading")}</p>}><AnalyticsInner /></Suspense>;
}
