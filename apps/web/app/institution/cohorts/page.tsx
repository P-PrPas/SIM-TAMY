"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";

import { LoadState, button, field } from "@/components/institution-bits";
import { useStaff } from "@/components/institution-shell";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";
import { RemoveSetting } from "@/components/remove-setting";

export default function CohortsPage() {
  const { org_id: orgId, id } = useStaff();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/orgs/{org_id}/cohorts", { params: { path: { org_id: orgId } } });
    if (!data) throw new Error("empty cohorts");
    return data.items;
  }, id);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setBusy(true);
    setMessage("");
    try {
      await api().POST("/v1/orgs/{org_id}/cohorts", {
        params: { path: { org_id: orgId } },
        body: { name: trimmed },
      });
      setName("");
      setMessage(t("institution.cohorts.created"));
      reload();
    } catch {
      setMessage(t("institution.actionError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="cohorts-title">
      <h2 id="cohorts-title" className="text-xl font-bold">{t("institution.cohorts.title")}</h2>
      <form onSubmit={(event) => void create(event)} className="mt-4 max-w-md">
        <label htmlFor="cohort-name" className="block font-semibold">{t("institution.cohorts.name")}</label>
        <input id="cohort-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required className={field} />
        <button type="submit" disabled={busy} className={`${button} mt-3`}>{t("institution.cohorts.create")}</button>
      </form>
      <p role="status" className="mt-2 text-stone-800">{message}</p>
      <LoadState error={error} loading={!data} onRetry={reload} />
      {data && data.length === 0 && <p className="mt-4">{t("institution.cohorts.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="mt-4 space-y-3">
          {data.map((cohort) => (
            <li key={cohort.id} className="rounded-2xl border border-stone-300 bg-white p-4">
              <p className="text-lg font-bold">{cohort.name}</p>
              <p className="text-stone-800">
                {t("institution.cohorts.code")}: <span className="font-mono font-semibold">{cohort.code}</span>
                {" · "}
                {t("institution.cohorts.assignmentCount")}: {cohort.assignment_count}
              </p>
              <Link
                href={`/institution/cohorts/${cohort.id}`}
                className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-brand-900 px-4 font-semibold text-brand-900"
              >
                {t("institution.cohorts.open")}
              </Link>
              <div className="mt-3"><RemoveSetting name={cohort.name} remove={() => api().DELETE("/v1/cohorts/{cohort_id}", { params: { path: { cohort_id: cohort.id } } })} onRemoved={() => { setMessage(t("institution.manage.removed")); reload(); }} /></div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
