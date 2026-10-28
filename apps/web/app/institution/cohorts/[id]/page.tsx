"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { LoadState, button, field } from "@/components/institution-bits";
import { useStaff } from "@/components/institution-shell";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { useLoad } from "@/lib/use-load";

export default function CohortDetailPage() {
  const cohortId = String(useParams<{ id: string }>().id);
  const router = useRouter();
  const { org_id: orgId, id: accountId } = useStaff();
  const [storyId, setStoryId] = useState("");
  const [cloneName, setCloneName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const cohort = useLoad(async () => {
    const { data } = await api().GET("/v1/orgs/{org_id}/cohorts", { params: { path: { org_id: orgId } } });
    const found = data?.items.find((c) => c.id === cohortId);
    if (!found) throw new Error("cohort not found");
    return found;
  }, `${accountId}:${cohortId}`);
  const assignments = useLoad(async () => {
    const { data } = await api().GET("/v1/cohorts/{cohort_id}/assignments", {
      params: { path: { cohort_id: cohortId } },
    });
    if (!data) throw new Error("empty assignments");
    return data.items;
  }, `${accountId}:${cohortId}`);
  const stories = useLoad(async () => {
    const { data } = await api().GET("/v1/family/stories");
    return data ?? [];
  }, "stories");

  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!storyId) return;
    setBusy(true);
    setMessage("");
    try {
      await api().POST("/v1/cohorts/{cohort_id}/assignments", {
        params: { path: { cohort_id: cohortId } },
        body: { story_id: storyId },
      });
      setMessage(t("institution.cohort.assigned"));
      assignments.reload();
    } catch {
      setMessage(t("institution.actionError"));
    } finally {
      setBusy(false);
    }
  }

  async function clone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = cloneName.trim();
    if (!name) return;
    setBusy(true);
    setMessage("");
    try {
      const { data } = await api().POST("/v1/cohorts/{cohort_id}/clone", {
        params: { path: { cohort_id: cohortId } },
        body: { name },
      });
      if (!data) throw new Error("empty clone");
      setCloneName("");
      setMessage(t("institution.cohort.cloned"));
      router.push(`/institution/cohorts/${data.id}`);
    } catch {
      setMessage(t("institution.actionError"));
    } finally {
      setBusy(false);
    }
  }

  const joinPath = cohort.data ? `/join/${cohort.data.code}` : "";
  const joinUrl = typeof window === "undefined" ? joinPath : `${window.location.origin}${joinPath}`;

  return (
    <section aria-labelledby="cohort-title" className="space-y-8">
      <div>
        <Link href="/institution/cohorts" className="inline-flex min-h-11 items-center font-semibold text-brand-900 underline">
          {t("institution.cohort.back")}
        </Link>
        <LoadState error={cohort.error} loading={!cohort.data} onRetry={cohort.reload} />
        {cohort.data && (
          <>
            <h2 id="cohort-title" className="mt-2 text-xl font-bold">{cohort.data.name}</h2>
            <div className="mt-4 rounded-2xl border-2 border-brand-900 bg-white p-5">
              <h3 className="font-semibold">{t("institution.cohort.joinTitle")}</h3>
              <p aria-label={t("institution.cohorts.code")} className="mt-2 font-mono text-5xl font-bold tracking-widest text-stone-950">
                {cohort.data.code}
              </p>
              <p className="mt-3 text-stone-800">{t("institution.cohort.joinLink")}:</p>
              <p className="break-all font-mono text-lg font-semibold">{joinUrl}</p>
              <p className="mt-2 text-stone-700">{t("institution.cohort.joinHint")}</p>
            </div>
            <Link
              href={`/institution/analytics?cohort=${cohort.data.id}`}
              className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-brand-900 px-4 font-semibold text-brand-900"
            >
              {t("institution.cohort.viewAnalytics")}
            </Link>
          </>
        )}
      </div>

      <div>
        <h3 className="text-lg font-bold">{t("institution.cohort.assignmentsTitle")}</h3>
        <LoadState error={assignments.error} loading={!assignments.data} onRetry={assignments.reload} />
        {assignments.data?.length === 0 && <p className="mt-2">{t("institution.cohort.noAssignments")}</p>}
        <ul className="mt-2 space-y-2">
          {assignments.data?.map((a) => (
            <li key={a.id} className="rounded-lg border border-stone-300 bg-white p-3">
              <span className="font-semibold">{a.title_th}</span>
              <span className="text-stone-700"> · {t("institution.cohort.version")} {a.story_version}</span>
            </li>
          ))}
        </ul>
        <form onSubmit={(event) => void assign(event)} className="mt-4 max-w-md">
          <label htmlFor="assign-story" className="block font-semibold">{t("institution.cohort.storyLabel")}</label>
          <select id="assign-story" value={storyId} onChange={(e) => setStoryId(e.target.value)} className={field}>
            <option value="">{t("institution.cohort.storyPlaceholder")}</option>
            {stories.data?.map((s) => <option key={s.id} value={s.id}>{s.title_th}</option>)}
          </select>
          <button type="submit" disabled={busy || !storyId} className={`${button} mt-3`}>{t("institution.cohort.assign")}</button>
        </form>
      </div>

      <form onSubmit={(event) => void clone(event)} className="max-w-md">
        <h3 className="text-lg font-bold">{t("institution.cohort.cloneTitle")}</h3>
        <p className="text-stone-700">{t("institution.cohort.cloneHint")}</p>
        <label htmlFor="clone-name" className="mt-3 block font-semibold">{t("institution.cohort.cloneName")}</label>
        <input id="clone-name" value={cloneName} onChange={(e) => setCloneName(e.target.value)} maxLength={80} required className={field} />
        <button type="submit" disabled={busy} className={`${button} mt-3`}>{t("institution.cohort.clone")}</button>
      </form>
      <p role="status" className="text-stone-800">{message}</p>
    </section>
  );
}
