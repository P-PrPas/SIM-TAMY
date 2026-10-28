import type { Frame } from "../sprite";
import { blank, box, outlined, planks, slats, type Rect } from "./draw";

// Stage 4 pixel scene art (thai-milk-family). Keep every addition in this file.
// Backdrops need a `pixelSim.backdrop.<key>` string; items are keyed by `ItemKey`; `ITEM_OF` maps a choice icon to an item.
type ItemDef = { art: Frame; at: readonly [x: number, y: number]; scale?: number; on?: readonly string[] };

/** Round table at the same height as the kitchen's, so knowledge cards sit on it in the same way. */
const table = (top: number): Rect[] => [
  [88, top, 144, 8, "y"], [88, top + 8, 144, 3, "w"], [96, top + 11, 6, 28, "d"], [218, top + 11, 6, 28, "d"],
];

export const STAGE4_BACKDROPS = {
  // Discover step: a quiet room with a window, a framed picture and a tea set (no clinical objects).
  consult: [
    [0, 0, 320, 128, "p"], ...slats(0, 128, 20, "c"), [0, 84, 320, 44, "c"], [0, 84, 320, 3, "w"],
    [112, 20, 96, 60, "d"], [116, 24, 88, 52, "b"], [116, 52, 88, 24, "g"], [116, 24, 88, 6, "x"], [160, 24, 4, 52, "d"], [116, 48, 88, 4, "d"], [184, 30, 9, 9, "y"],
    [102, 20, 10, 64, "r"], [208, 20, 10, 64, "r"], [102, 20, 116, 3, "w"],
    [24, 28, 56, 44, "d"], [27, 31, 50, 38, "p"], [47, 38, 14, 12, "y"], [41, 52, 26, 10, "g"], [31, 62, 42, 3, "o"],
    [236, 44, 64, 4, "d"], [240, 32, 8, 12, "o"], [252, 34, 8, 10, "g"], [264, 32, 8, 12, "y"], [276, 35, 10, 9, "r"],
    [296, 96, 14, 32, "g"], [292, 118, 22, 10, "w"],
    [0, 128, 320, 52, "w"], ...planks(128, 52, 13, "d"),
    [96, 142, 128, 12, "g"], [100, 145, 120, 6, "c"],
    ...table(110),
    [200, 104, 14, 6, "x"], [202, 100, 3, 4, "x"], [212, 102, 6, 8, "l"], [214, 100, 2, 2, "l"], [222, 104, 6, 6, "x"],
  ],
  // Choice steps: a living room where the grandmother appears on a tablet video call.
  livingroom: [
    [0, 0, 320, 128, "c"], ...slats(0, 128, 20, "p"), [0, 96, 320, 32, "l"], [0, 96, 320, 3, "d"],
    [20, 24, 66, 52, "d"], [24, 28, 58, 44, "b"], [24, 52, 58, 20, "g"], [51, 28, 4, 44, "d"], [24, 48, 58, 3, "d"], [66, 33, 9, 9, "y"],
    [102, 26, 20, 24, "d"], [105, 29, 14, 18, "x"], [108, 34, 8, 8, "g"], [130, 30, 16, 20, "d"], [133, 33, 10, 14, "x"], [136, 36, 4, 6, "r"],
    [238, 26, 24, 24, "d"], [241, 29, 18, 18, "x"], [250, 33, 2, 7, "k"], [250, 38, 5, 2, "k"],
    [96, 66, 128, 14, "w"], [100, 60, 120, 8, "o"], [92, 74, 14, 54, "w"], [214, 74, 14, 54, "w"], [106, 80, 108, 26, "o"], [106, 100, 108, 6, "w"],
    [112, 84, 24, 16, "y"], [194, 84, 24, 16, "r"],
    [296, 74, 14, 54, "g"], [292, 118, 22, 10, "w"],
    [0, 128, 320, 52, "w"], ...planks(128, 52, 13, "d"),
    [96, 142, 128, 12, "b"], [100, 145, 120, 6, "c"],
    ...table(110),
    // Tablet on a stand: the grandmother's video call.
    [140, 82, 40, 28, "k"], [142, 84, 36, 24, "d"], [144, 86, 32, 20, "x"],
    [156, 90, 8, 8, "s"], [155, 88, 10, 3, "l"], [158, 85, 4, 4, "l"], [152, 98, 16, 7, "m"], [157, 94, 1, 1, "k"], [161, 94, 1, 1, "k"],
    [146, 88, 3, 3, "g"], [170, 100, 4, 4, "r"], [155, 108, 10, 2, "k"],
  ],
} satisfies Record<string, readonly Rect[]>;

const frame = (w: number, h: number, paint: (g: string[][]) => void): Frame => {
  const g = blank(w, h);
  paint(g);
  return outlined(g);
};

export const STAGE4_ITEMS = {
  // A cup of tea (a warm thank-you).
  tea: { on: ["livingroom"], at: [124, 100], art: frame(9, 8, (g) => {
    box(g, 0, 3, 7, 5, "x"); box(g, 7, 4, 2, 3, "x"); box(g, 1, 3, 5, 1, "o");
    box(g, 2, 0, 1, 2, "l"); box(g, 4, 0, 1, 2, "l");
  }) },
  // A chart on the wall: who helps when.
  chart: { on: ["livingroom"], at: [166, 24], scale: 1, art: frame(30, 26, (g) => {
    box(g, 0, 0, 30, 26, "p"); box(g, 0, 0, 30, 5, "o");
    for (let i = 0; i < 3; i++) { box(g, 3, 8 + i * 6, 6, 3, ["g", "y", "r"][i]!); box(g, 12, 9 + i * 6, 15, 1, "m"); }
  }) },
} satisfies Record<string, ItemDef>;

export const STAGE4_ITEM_OF = { heart: "tea", house: "chart" } satisfies Record<string, keyof typeof STAGE4_ITEMS>;

/** Table slots (logical px) for knowledge cards: the left of the table, then past the tablet. */
const aroundTablet = [[92, 101], [104, 101], [116, 101], [184, 101], [196, 101], [208, 101]] as const;
export const STAGE4_CARD_SLOTS = {
  consult: Array.from({ length: 6 }, (_, i) => [92 + i * 17, 101] as const),
  livingroom: aroundTablet,
} satisfies Record<string, readonly (readonly [number, number])[]>;
