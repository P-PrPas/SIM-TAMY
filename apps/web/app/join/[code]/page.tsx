"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { LoadState } from "@/components/institution-bits";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { storyReady } from "@/lib/learning-path";
import { useLoad } from "@/lib/use-load";

export default function JoinCodePage() {
  const code = String(useParams<{ code: string }>().code);
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/join/{code}", { params: { path: { code } } });
    if (!data) throw new Error("empty join");
    return data;
  }, code);
  const reason =
    error instanceof ApiError && error.code === "CLASS_NOT_FOUND"
      ? t("institution.join.notFound")
      : error instanceof ApiError && error.code === "SESSION_EXPIRED"
        ? t("institution.join.expired")
        : null;

  return (
    <main className="mx-auto w-full max-w-xl px-4 py-8 sm:py-12">
      <h1 className="text-2xl font-bold text-stone-950">{t("institution.join.title")}</h1>
      {reason ? (
        <p role="alert" className="mt-4 rounded-lg border border-amber-800 bg-amber-50 p-4 text-amber-950">{reason}</p>
      ) : (
        <LoadState error={error} loading={!data} onRetry={reload} />
      )}
      {data && (
        <>
          <p className="mt-2 text-lg">{t("institution.join.cohort")}: <strong>{data.cohort.name}</strong></p>
          <p className="mt-1 text-stone-700">{t("institution.join.noIntake")}</p>
          {data.assignments.length === 0 ? (
            <p className="mt-4">{t("institution.join.empty")}</p>
          ) : (
            <>
              <h2 className="mt-6 text-lg font-bold">{t("institution.join.pick")}</h2>
              <ul className="mt-3 space-y-3">
                {data.assignments.map((a) => (
                  <li key={a.id} className="rounded-2xl border border-stone-300 bg-white p-4">
                    <p className="text-lg font-bold">{a.title_th}</p>
                    {storyReady(a.story_id) ? <Link
                      href={`/simulate/${a.story_id}?assignment=${a.id}`}
                      className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-brand-900 px-5 font-semibold text-white"
                    >
                      {t("institution.join.start")}
                    </Link> : <p className="mt-3 text-stone-700">{t("platform.notReady")}</p>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </main>
  );
}
