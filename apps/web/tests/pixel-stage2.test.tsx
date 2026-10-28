import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { LESSON_UNITS_2 } from "@/components/pixel/art/lesson-stage2";
import { CASTS, sceneSetup } from "@/components/pixel/cast";
import { ART, claimArt } from "@/components/pixel/lesson-art";
import { isPixelLesson, isPixelStory } from "@/components/pixel/registry";
import { BACKDROPS, CARD_SLOTS, ICONS, itemFor } from "@/components/pixel/scene-art";
import { characterOf } from "@/components/pixel/scene-view";
import { t } from "@/lib/i18n";

const STORY = "thai-birth-conversation";
const UNIT = "KB-IP-HERITAGE-001";
const read = (rel: string) => readFileSync(resolve(__dirname, "../../../content", rel), "utf-8");
const unit = read(`knowledge/units/${UNIT}.yaml`);
const story = read(`family/${STORY}.yaml`);

/** Claim blocks of the unit yaml: id -> its text and hotspot lines (no YAML dependency in the web package). */
const claims = unit.split(/^ {2}- id: /m).slice(1).map((block) => ({
  id: block.split("\n")[0]!,
  text: /^ {4}text_th: (.*)$/m.exec(block)![1]!,
  hotspots: [...block.matchAll(/^ {6}- \{id: (h\d+), label_th: ([^,]+), text_th: ([^}]+)\}$/gm)].map((m) => ({ id: m[1]!, label: m[2]!, text: m[3]! })),
}));
const choices = [...story.matchAll(/^ {6}- \{id: ([\w-]+), text_th: .*$/gm)].map((m) => m[0]);

describe("stage 2 lesson", () => {
  it("has hotspots on every claim, each lit by its own illustration tap", () => {
    expect(claims).toHaveLength(4);
    expect(LESSON_UNITS_2[UNIT]).toHaveLength(claims.length);
    claims.forEach((claim, i) => {
      expect(claim.hotspots.length, claim.id).toBeGreaterThan(0);
      expect(new Set(claim.hotspots.map((h) => h.id)).size).toBe(claim.hotspots.length);
      const art = ART[claimArt(UNIT, i)];
      expect(art.taps, claim.id).toBeGreaterThanOrEqual(claim.hotspots.length);
      const off = art.draw(Array(art.taps).fill(false));
      expect(off).toHaveLength(64);
      expect(off.every((row) => row.length === 96)).toBe(true);
      for (let tap = 0; tap < claim.hotspots.length; tap++) {
        const lit = art.draw(Array.from({ length: art.taps }, (_, j) => j === tap));
        expect(lit, `${claim.id} tap ${tap}`).not.toEqual(off);
      }
    });
  });

  it("keeps hotspots short and plain, each a shortening of its own claim", () => {
    for (const claim of claims) for (const h of claim.hotspots) {
      expect([...h.label].length).toBeLessThanOrEqual(25);
      expect([...h.text].length).toBeLessThanOrEqual(75);
      expect(h.text.length).toBeLessThan(claim.text.length);
    }
  });
});

describe("stage 2 scene", () => {
  it("gives every choice a short label (<= 30) and a valid icon", () => {
    expect(choices).toHaveLength(6);
    for (const line of choices) {
      const short = /short_th: ([^,}]+)/.exec(line)?.[1];
      const icon = /icon: (\w+)\}$/.exec(line)?.[1];
      expect(short, line).toBeTruthy();
      expect([...short!].length).toBeLessThanOrEqual(30);
      expect(Object.keys(ICONS)).toContain(icon);
    }
  });

  it("resolves the cast, the backdrop, its name and its speakers", () => {
    const cast = CASTS[STORY]!;
    for (const b of Object.values(cast.backdrops)) {
      expect(BACKDROPS[b]).toBeDefined();
      expect(t(`pixelSim.backdrop.${b}`)).not.toContain("pixelSim.backdrop");
    }
    expect(characterOf(t("pixelSim.name.yai"))).toBe("yai");
    expect(sceneSetup(STORY, "mother", "choice", "yai")).toEqual({ left: "ploy", backdrop: cast.backdrops.choice });
    expect(sceneSetup(STORY, "mother", "choice", "ton").left).toBe("ploy");
  });

  it("leaves its props on the veranda only and has card slots there", () => {
    // other stages may map the same icons to their own props; each prop shows only on its stage's backdrop
    for (const icon of ["heart", "talk"] as const) {
      expect(itemFor(icon, "veranda")).toBeDefined();
      expect(itemFor(icon, "kitchen")).not.toBe(itemFor(icon, "veranda"));
    }
    expect(CARD_SLOTS.veranda!.length).toBeGreaterThan(0);
  });

  it("is registered as a pixel story and lesson", () => {
    expect(isPixelStory(STORY)).toBe(true);
    expect(isPixelLesson(UNIT)).toBe(true);
  });
});
