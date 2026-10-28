"use client";

import { LoadState } from "@/components/institution-bits";
import { DemoBadge, useStaff } from "@/components/institution-shell";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

export default function StaffPage() {
  const { org_id: orgId, id } = useStaff();
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/demo/accounts");
    return (data?.items ?? []).filter((a) => a.org_id === orgId && a.role !== "learner");
  }, id);

  return (
    <section aria-labelledby="staff-title">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="staff-title" className="text-xl font-bold">{t("institution.staff.title")}</h2>
        <DemoBadge />
      </div>
      <p className="mt-1 text-stone-800">{t("institution.staff.intro")}</p>
      <LoadState error={error} loading={!data} onRetry={reload} />
      <ul className="mt-4 space-y-2">
        {data?.map((a) => (
          <li key={a.id} className="flex flex-wrap justify-between gap-2 rounded-lg border border-stone-300 bg-white p-3">
            <span className="font-semibold">{a.display_name_th}</span>
            <span className="text-stone-800">{t(`institution.staff.role.${a.role}`)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
