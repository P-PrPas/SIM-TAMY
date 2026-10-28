import type { Backdrop, CharacterKey } from "./scene-art";

export type SceneKind = "discover" | "choice";
type Role = "mother" | "father";
/** Per story: who plays each role and which backdrop each kind of step uses. */
export type Cast = { mother: CharacterKey; father: CharacterKey; backdrops: Record<SceneKind, Backdrop> };

const DEFAULT: Cast = { mother: "ploy", father: "ton", backdrops: { discover: "sala", choice: "kitchen" } };

/** A stage PR edits only its own entry below (kept apart so the stages merge without conflicts). */
export const CASTS: Record<string, Cast> = {
  "thai-elements-family": DEFAULT,

  // Stage 2: ploy and ton on a veranda; the grandmother (yai) visits as speaker
  "thai-birth-conversation": { mother: "ploy", father: "ton", backdrops: { discover: "veranda", choice: "veranda" } },

  // Stage 3: Mali and Non at home in the family's wooden house at night; reflection in the room, decisions in the hall
  "gs-a-postpartum-warning": { mother: "mali", father: "non", backdrops: { discover: "postpartumRoom", choice: "postpartumHall" } },

  // Stage 4: the counsellor talks in a quiet room; the other steps happen in the living room with the grandmother on a video call.
  "thai-milk-family": { mother: "ploy", father: "ton", backdrops: { discover: "consult", choice: "livingroom" } },
};

/** The player's own character stands on the left; when the speaker is that character, the partner stands there instead. */
export function sceneSetup(storyId: string, role: Role, kind: SceneKind, speaker: CharacterKey) {
  const cast = CASTS[storyId] ?? DEFAULT;
  const own = cast[role];
  const left = own === speaker ? cast[role === "mother" ? "father" : "mother"] : own;
  return { left, backdrop: cast.backdrops[kind] };
}
