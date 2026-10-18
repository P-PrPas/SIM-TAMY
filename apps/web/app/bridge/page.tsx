import Link from "next/link";

import { FamilySimulator } from "@/components/family-simulator";
import { t } from "@/lib/i18n";

const topics = ["fire", "compress", "food", "herbs"] as const;

export default async function BridgePage({ searchParams }: { searchParams: Promise<{ topic?: string }> }) {
  const { topic: requested } = await searchParams;
  const topic = topics.find((item) => item === requested) ?? "fire";
  return <FamilySimulator key={topic} storyId={`bridge-${topic}`}>
    <nav aria-label={t("family.bridgeTopics.label")} className="my-6 grid gap-3 sm:grid-cols-2">
      {topics.map((item) => <Link key={item} href={`/bridge?topic=${item}`} aria-current={topic === item ? "page" : undefined} className={`rounded-2xl border p-4 ${topic === item ? "border-amber-600 bg-amber-50 font-semibold" : "border-stone-300"}`}>{t(`family.bridgeTopics.${item}`)}</Link>)}
    </nav>
  </FamilySimulator>;
}
