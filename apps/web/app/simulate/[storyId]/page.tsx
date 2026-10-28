import { FamilySimulator } from "@/components/family-simulator";

/** Family simulator for any story ID (2.0 Golden Scenarios first); unknown IDs show the unavailable notice. */
export default async function SimulatePage({ params }: { params: Promise<{ storyId: string }> }) {
  const { storyId } = await params;
  return <FamilySimulator storyId={storyId} />;
}
