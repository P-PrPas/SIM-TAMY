import type { components } from "./api/schema";

type Competency = components["schemas"]["FamilyCompetency"];
export type ParentProfile = Competency["skill"] | "balanced" | "explorer";

/** Presentation of completed engine counts, not a new assessment or personality model. */
export function parentProfile(competencies: readonly Competency[]): ParentProfile {
  const observed = competencies.filter((item) => item.opportunities > 0 && item.observed > 0);
  if (!observed.length) return "explorer";
  const best = observed.reduce((a, b) => a.observed * b.opportunities >= b.observed * a.opportunities ? a : b);
  const tied = observed.filter((item) => item.observed * best.opportunities === best.observed * item.opportunities);
  return tied.length > 1 ? "balanced" : best.skill;
}
