"use client";

import { LoadState } from "@/components/institution-bits";
import { api } from "@/lib/api/runtime";
import { t } from "@/lib/i18n";
import { storyReady } from "@/lib/learning-path";
import { useLoad } from "@/lib/use-load";

export default function LibraryPage() {
  const { data, error, reload } = useLoad(async () => {
    const { data } = await api().GET("/v1/family/stories");
    return data ?? [];
  }, "stories");

  return (
    <section aria-labelledby="library-title">
      <h2 id="library-title" className="text-xl font-bold">{t("institution.library.title")}</h2>
      <p className="mt-1 text-stone-800">{t("institution.library.intro")}</p>
      <LoadState error={error} loading={!data} onRetry={reload} />
      {data?.length === 0 && <p className="mt-3">{t("institution.library.empty")}</p>}
      <ul className="mt-4 space-y-3">
        {data?.map((story) => (
          <li key={story.id} className="rounded-2xl border border-stone-300 bg-white p-4">
            <p className="text-lg font-bold">{story.title_th}</p>
            <p className="text-stone-800">{story.description_th}</p>
            <p className="mt-1 text-stone-700">{t(`institution.library.mode.${story.mode}`)}</p>
            {!storyReady(story.id) && <p className="mt-1 text-stone-700">{t("platform.notReadyLearners")}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
