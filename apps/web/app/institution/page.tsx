"use client";

import { LoadState, Stat } from "@/components/institution-bits";
import { DemoBadge, useStaff } from "@/components/institution-shell";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

export default function OverviewPage() {
  const { org_id: orgId, id } = useStaff();
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/orgs/{org_id}/overview", { params: { path: { org_id: orgId } } });
    if (!data) throw new Error("empty overview");
    return data;
  }, id);

  return (
    <section aria-labelledby="overview-title">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="overview-title" className="text-xl font-bold">{t("institution.overview.title")}</h2>
        {data?.demo && <DemoBadge />}
      </div>
      <LoadState error={error} loading={!data} onRetry={reload} />
      {data && (
        <>
          <p className="mt-2 text-stone-800">{data.org.name_th}</p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            <Stat label={t("institution.overview.cohorts")} value={data.cohort_count} />
            <Stat label={t("institution.overview.assignments")} value={data.assignment_count} />
            <Stat
              label={t("institution.overview.finished")}
              value={data.finished_attempts}
              hint={t("institution.overview.finishedHint")}
            />
          </dl>
        </>
      )}
    </section>
  );
}
