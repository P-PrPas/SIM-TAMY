import type { Frame } from "../sprite";
import { planks, slats, type Rect } from "./draw";

// Stage 3 pixel scene art (gs-a-postpartum-warning). Calm neutral visuals only: a night room in the family's wooden
// house, a hall with a table, a phone and a little house on the table. Nothing depicts a symptom, a body or a treatment,
// and props depend only on the committed choice's icon (never on hidden state).
// Backdrops need a `pixelSim.backdrop.<key>` string; items are keyed by `ItemKey`; `ITEM_OF` maps a choice icon to an item.
type ItemDef = { art: Frame; at: readonly [x: number, y: number]; scale?: number; on?: readonly string[] };

const PHONE_PROP: Frame = [".kkkkkk.", "kmmmmmmk", "kmyyyymk", "kmyyyymk", "kmyyyymk", "kmyyyymk", "kmyyyymk", "kmyyyymk", "kmmmmmmk", "kmmkkmmk", "kmmmmmmk", ".kkkkkk."];
const HOUSE_PROP: Frame = ["....kkkk....", "..kkrrrrkk..", ".krrrrrrrrk.", "kkkkkkkkkkkk", ".kppppppppk.", ".kppkkppkpk.", ".kppkkppkpk.", ".kppkkddkpk.", ".kkkkkddkkk."];

/** A small crescent moon, drawn as rects so it needs no cut-out colour. */
const moon = (x: number, y: number): Rect[] => [[x + 2, y, 4, 1, "x"], [x + 1, y + 1, 3, 1, "x"], [x, y + 2, 3, 4, "x"], [x + 1, y + 6, 3, 1, "x"], [x + 2, y + 7, 4, 1, "x"]];

export const STAGE3_BACKDROPS = {
  // Night room: moonlit window, a woven cradle hanging from the beam, a mat on the floor.
  postpartumRoom: [
    [0, 0, 320, 128, "w"], ...slats(0, 128, 20, "d"), [0, 0, 320, 16, "d"],
    [118, 24, 76, 58, "d"], [122, 28, 68, 50, "b"], [153, 28, 4, 50, "d"], [122, 50, 68, 4, "d"], [112, 82, 88, 4, "d"],
    ...moon(166, 32), [130, 36, 2, 2, "x"], [140, 62, 2, 2, "y"], [134, 44, 2, 2, "y"], [180, 64, 2, 2, "x"],
    [30, 34, 56, 36, "d"], [33, 37, 50, 30, "g"], [40, 44, 36, 1, "x"], [40, 52, 36, 1, "x"], [40, 60, 36, 1, "x"],
    [217, 16, 2, 36, "m"], [245, 16, 2, 36, "m"], [208, 52, 48, 8, "o"], [208, 52, 48, 2, "y"], [212, 46, 40, 6, "c"],
    [0, 128, 320, 52, "o"], ...planks(128, 52, 13, "w"),
    [96, 140, 128, 16, "r"], [100, 144, 120, 8, "y"],
  ],
  // Hall: lantern, a doorway onto the night, a shelf, and the low table where the phone waits.
  postpartumHall: [
    [0, 0, 320, 128, "c"], ...slats(0, 128, 20, "o"), [0, 0, 320, 16, "d"],
    [16, 24, 72, 104, "d"], [20, 28, 64, 100, "b"], [48, 28, 4, 100, "d"], ...moon(60, 40), [28, 44, 2, 2, "x"], [34, 70, 2, 2, "y"],
    [150, 0, 2, 22, "d"], [142, 22, 18, 18, "d"], [145, 25, 12, 12, "y"],
    [226, 56, 72, 4, "d"], [232, 44, 8, 12, "g"], [246, 46, 8, 10, "r"], [260, 44, 8, 12, "y"],
    [0, 128, 320, 52, "w"], ...planks(128, 52, 13, "d"),
    [88, 110, 144, 8, "y"], [88, 118, 144, 3, "w"], [96, 121, 6, 28, "d"], [218, 121, 6, 28, "d"],
    [206, 102, 18, 8, "g"], [210, 98, 10, 4, "l"],
  ],
} satisfies Record<string, readonly Rect[]>;

const HALL = ["postpartumHall"] as const;
export const STAGE3_ITEMS = {
  gsPhone: { art: PHONE_PROP, at: [148, 86], scale: 2, on: HALL },
  gsHouse: { art: HOUSE_PROP, at: [176, 92], scale: 2, on: HALL },
} satisfies Record<string, ItemDef>;
export const STAGE3_ITEM_OF = { phone: "gsPhone", house: "gsHouse" } as const satisfies Record<string, string>;
export const STAGE3_CARD_SLOTS = {
  postpartumHall: Array.from({ length: 5 }, (_, i) => [94 + i * 9, 101] as const),
} satisfies Record<string, readonly (readonly [number, number])[]>;
