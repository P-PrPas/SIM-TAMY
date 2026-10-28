import { FamilySimulator } from "@/components/family-simulator";
import { StoryGate } from "@/components/platform/not-ready";

export default function FamilyPage() {
  return <StoryGate id="first-night"><FamilySimulator storyId="first-night" /></StoryGate>;
}
