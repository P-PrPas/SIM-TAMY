"use client";

import Link from "next/link";

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
  const cohorts = useLoad(async () => {
    const { data } = await api().GET("/v1/orgs/{org_id}/cohorts", { params: { path: { org_id: orgId } } });
    if (!data) throw new Error("empty cohorts");
    return data.items;
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
          <div className="dashboard-panels">
            <section className="pf-card"><h3>{t("institution.overview.recent")}</h3>
              <LoadState error={cohorts.error} loading={!cohorts.data} onRetry={cohorts.reload} />
              {cohorts.data?.length === 0 && <p className="pf-note">{t("institution.cohorts.empty")}</p>}
              <ul className="pf-list">{cohorts.data?.slice(0, 5).map((cohort) => <li key={cohort.id}>
                <Link href={`/institution/cohorts/${cohort.id}`} className="pf-link">{cohort.name}<span aria-hidden="true">→</span></Link>
                <p className="pf-meta">{t("institution.cohorts.assignmentCount")}: {cohort.assignment_count}</p>
              </li>)}</ul>
              <Link href="/institution/cohorts" className="button-secondary">{t("institution.overview.manage")}</Link>
            </section>
            <section className="pf-card"><h3>{t("institution.overview.next")}</h3>
              <p className="pf-muted">{t("institution.overview.nextText")}</p>
              <div className="pf-stack"><Link href="/institution/cohorts" className="button-primary">{t("institution.cohorts.create")}</Link>
                <Link href="/institution/analytics" className="pf-link">{t("institution.nav.analytics")}</Link></div>
            </section>
          </div>
        </>
      )}
    </section>
  );
}
