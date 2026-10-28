import type { components } from "../api/schema";
import base from "./th.json";
// 2.0 streams each own one namespace file (ADR-15), so parallel work never edits the same JSON.
import institution from "./v2/institution.json";
import knowledge from "./v2/knowledge.json";
import lab from "./v2/lab.json";
import platform from "./v2/platform.json";
// pixel visual mode: one namespace per parallel PR (scene, lesson, house)
import pixelHouse from "./v2/pixel-house.json";
import pixelLesson from "./v2/pixel-lesson.json";
import pixelSim from "./v2/pixel-sim.json";

const th = { ...base, knowledge, lab, institution, platform, pixelSim, pixelLesson, pixelHouse };

/** Look up a Thai string by dotted key, e.g. t("app.title"). Throws on a missing key. */
export function t(key: string): string {
  let node: unknown = th;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null || !(part in node)) {
      throw new Error(`Missing i18n key: ${key}`);
    }
    node = (node as Record<string, unknown>)[part];
  }
  if (typeof node !== "string") throw new Error(`i18n key is not a string: ${key}`);
  return node;
}

export function patientLabel(audience?: components["schemas"]["Audience"] | null): string {
  return t(audience === "dad" ? "chat.wife" : audience === "mom" ? "chat.friend" : "chat.patient");
}
