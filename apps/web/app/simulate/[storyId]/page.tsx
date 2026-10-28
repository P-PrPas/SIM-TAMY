import { FamilySimulator } from "@/components/family-simulator";
import { StoryGate } from "@/components/platform/not-ready";

/** Family simulator for any story ID (2.0 Golden Scenarios first); unknown IDs show the unavailable notice. */
export default async function SimulatePage({ params }: { params: Promise<{ storyId: string }> }) {
  const { storyId } = await params;
  return <StoryGate id={storyId}><FamilySimulator storyId={storyId} /></StoryGate>;
}
