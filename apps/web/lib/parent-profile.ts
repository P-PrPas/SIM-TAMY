import type { components } from "./api/schema";

type Competency = components["schemas"]["FamilyCompetency"];
export type ParentProfile = Exclude<Competency["skill"], "shared_decision"> | "balanced" | "explorer";

/** Presentation of completed engine counts, not a new assessment or personality model. */
export function parentProfile(competencies: readonly Competency[], safetyStatus: string): ParentProfile {
  if (safetyStatus !== "SAFETY_MET") return "explorer";
  const observed = competencies.filter((item): item is Competency & { skill: ParentProfile } => item.skill !== "shared_decision" && item.opportunities > 0 && item.observed > 0);
  if (!observed.length) return "explorer";
  const best = observed.reduce((a, b) => a.observed * b.opportunities >= b.observed * a.opportunities ? a : b);
  const tied = observed.filter((item) => item.observed * best.opportunities === best.observed * item.opportunities);
  return tied.length > 1 ? "balanced" : best.skill;
}
