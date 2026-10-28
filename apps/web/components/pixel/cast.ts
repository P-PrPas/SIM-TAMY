import type { Backdrop, CharacterKey } from "./scene-art";

export type SceneKind = "discover" | "choice";
type Role = "mother" | "father";
/** Per story: who plays each role and which backdrop each kind of step uses. */
export type Cast = { mother: CharacterKey; father: CharacterKey; backdrops: Record<SceneKind, Backdrop> };

const DEFAULT: Cast = { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } };

/** A stage PR edits only its own entry below (kept apart so the stages merge without conflicts). */
export const CASTS: Record<string, Cast> = {
  "thai-elements-family": DEFAULT,

  // Stage 2: placeholder until the stage 2 PR sets the real cast and backdrops
  "thai-birth-conversation": { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } },

  // Stage 3: placeholder until the stage 3 PR sets the real cast and backdrops
  "gs-a-postpartum-warning": { mother: "mali", father: "non", backdrops: { discover: "sala", choice: "kitchen" } },

  // Stage 4: placeholder until the stage 4 PR sets the real cast and backdrops
  "thai-milk-family": { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } },
};

/** The player's own character stands on the left; when the speaker is that character, the partner stands there instead. */
export function sceneSetup(storyId: string, role: Role, kind: SceneKind, speaker: CharacterKey) {
  const cast = CASTS[storyId] ?? DEFAULT;
  const own = cast[role];
  const left = own === speaker ? cast[role === "mother" ? "father" : "mother"] : own;
  return { left, backdrop: cast.backdrops[kind] };
}
