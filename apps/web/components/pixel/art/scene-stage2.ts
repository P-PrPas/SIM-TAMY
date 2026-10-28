import type { Frame } from "../sprite";
import { blank, box, outlined, planks, put, type Rect } from "./draw";

// Stage 2 pixel scene art. Keep every addition in this file.
// Backdrops need a `pixelSim.backdrop.<key>` string; items are keyed by `ItemKey`; `ITEM_OF` maps a choice icon to an item.
type ItemDef = { art: Frame; at: readonly [x: number, y: number]; scale?: number; on?: readonly string[] };

/** A Thai wooden house veranda (chan ban) in daylight: garden and sky behind a rail, a woven mat on the floor. */
const veranda: Rect[] = [
  [0, 0, 320, 100, "p"], [30, 24, 40, 6, "x"], [20, 30, 30, 5, "x"], [262, 56, 40, 6, "x"], [274, 50, 22, 6, "x"],
  [226, 18, 14, 22, "y"], [222, 22, 22, 14, "y"],
  [0, 84, 90, 14, "g"], [200, 78, 120, 20, "g"], [0, 96, 320, 32, "g"],
  [152, 40, 4, 58, "w"], [138, 36, 32, 5, "g"], [144, 31, 20, 5, "g"], [132, 42, 12, 4, "g"], [164, 42, 12, 4, "g"],
  [0, 0, 320, 14, "d"], [0, 14, 320, 3, "w"],
  [60, 17, 1, 14, "k"], [54, 31, 13, 8, "w"], [52, 26, 17, 5, "g"], [56, 22, 9, 4, "g"],
  [14, 98, 292, 4, "w"], ...Array.from({ length: 24 }, (_, i): Rect => [20 + i * 12, 102, 3, 26, "w"]),
  [0, 14, 14, 114, "w"], [306, 14, 14, 114, "w"], [0, 14, 2, 114, "d"], [312, 14, 2, 114, "d"],
  [0, 128, 320, 52, "o"], ...planks(128, 52, 13, "w"),
  [88, 138, 144, 30, "w"], [90, 140, 140, 26, "c"], [90, 146, 140, 1, "y"], [90, 153, 140, 1, "y"], [90, 160, 140, 1, "y"],
  [22, 108, 18, 12, "r"], [24, 106, 14, 2, "w"], [26, 96, 4, 10, "g"], [32, 92, 4, 14, "g"],
];
export const STAGE2_BACKDROPS = { veranda } satisfies Record<string, readonly Rect[]>;

/** Flower garland (phuang malai) hung from the beam. */
const GARLAND: Frame = (() => {
  const g = blank(48, 16);
  const keys = ["r", "y", "x", "r", "g"];
  for (let i = 0; i < 12; i++) {
    const x = 2 + i * 4;
    const y = Math.round(10 - Math.abs(5.5 - i) * 1.5);
    box(g, x, y, 3, 3, keys[i % keys.length]!);
  }
  put(g, 1, 0, "k"); put(g, 46, 0, "k");
  return outlined(g);
})();

/** A paper list of questions lying on the mat. */
const LIST: Frame = (() => {
  const g = blank(12, 14);
  box(g, 0, 0, 12, 14, "x");
  for (const j of [2, 5, 8, 11]) { put(g, 1, j, "g"); box(g, 3, j, 7, 1, "m"); }
  return outlined(g);
})();

export const STAGE2_ITEMS = {
  garland: { art: GARLAND, at: [112, 17], scale: 2, on: ["veranda"] },
  questions: { art: LIST, at: [188, 134], scale: 2, on: ["veranda"] },
} satisfies Record<string, ItemDef>;
/** Choice icon -> prop left behind (only on the veranda). */
export const STAGE2_ITEM_OF = { heart: "garland", talk: "questions" } as const satisfies Record<string, string>;
/** Where collected knowledge cards sit on the mat. */
export const STAGE2_CARD_SLOTS = {
  veranda: Array.from({ length: 5 }, (_, i) => [100 + i * 16, 147] as const),
} satisfies Record<string, readonly (readonly [number, number])[]>;
