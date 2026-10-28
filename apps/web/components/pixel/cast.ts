import type { Backdrop, CharacterKey } from "./scene-art";

export type SceneKind = "discover" | "choice";
type Role = "mother" | "father";
/** Per story: who plays each role and which backdrop each kind of step uses. */
export type Cast = { mother: CharacterKey; father: CharacterKey; backdrops: Record<SceneKind, Backdrop> };

const DEFAULT: Cast = { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } };

/** A stage PR sets the real cast and backdrops of its story here (the entries below are placeholders). */
export const CASTS: Record<string, Cast> = {
  "thai-elements-family": DEFAULT,
  "thai-birth-conversation": { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } },
  "gs-a-postpartum-warning": { mother: "mali", father: "non", backdrops: { discover: "sala", choice: "kitchen" } },
  "thai-milk-family": { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } },
};

/** The player's own character stands on the left; when the speaker is that character, the partner stands there instead. */
export function sceneSetup(storyId: string, role: Role, kind: SceneKind, speaker: CharacterKey) {
  const cast = CASTS[storyId] ?? DEFAULT;
  const own = cast[role];
  const left = own === speaker ? cast[role === "mother" ? "father" : "mother"] : own;
  return { left, backdrop: cast.backdrops[kind] };
}
