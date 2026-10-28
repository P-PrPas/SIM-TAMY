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
import pixelSimBase from "./v2/pixel-sim.json";
// Stage 2-4 speaker and backdrop names live in their own files so the stage PRs never edit the same lines.
import pixelSimStage2 from "./v2/pixel-sim-stage2.json";
import pixelSimStage3 from "./v2/pixel-sim-stage3.json";
import pixelSimStage4 from "./v2/pixel-sim-stage4.json";

const stages = [pixelSimStage2, pixelSimStage3, pixelSimStage4];
const pixelSim = {
  ...pixelSimBase,
  name: Object.assign({}, pixelSimBase.name, ...stages.map((x) => x.name)) as Record<string, string>,
  backdrop: Object.assign({}, pixelSimBase.backdrop, ...stages.map((x) => x.backdrop)) as Record<string, string>,
};

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
