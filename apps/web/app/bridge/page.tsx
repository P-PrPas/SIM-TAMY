import Link from "next/link";

import { FamilySimulator } from "@/components/family-simulator";
import { FamilyIcon } from "@/components/family-art";
import { t } from "@/lib/i18n";

const topics = ["fire", "compress", "food", "herbs"] as const;

export default async function BridgePage({ searchParams }: { searchParams: Promise<{ topic?: string }> }) {
  const { topic: requested } = await searchParams;
  const topic = topics.find((item) => item === requested) ?? "fire";
  return <FamilySimulator key={topic} storyId={`bridge-${topic}`}>
    <nav aria-label={t("family.bridgeTopics.label")} className="family-topics">
      {topics.map((item) => <Link key={item} href={`/bridge?topic=${item}`} aria-current={topic === item ? "page" : undefined}><FamilyIcon name={item === 'food' ? 'heart' : 'leaf'} /><span>{t(`family.bridgeTopics.${item}`)}</span></Link>)}
    </nav>
  </FamilySimulator>;
}
