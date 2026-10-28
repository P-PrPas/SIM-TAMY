import type { Frame } from "../sprite";
import type { Rect } from "./draw";

// Stage 3 pixel scene art. Filled by the stage 3 PR; keep every addition in this file.
// Backdrops need a `pixelSim.backdrop.<key>` string; items are keyed by `ItemKey`; `ITEM_OF` maps a choice icon to an item.
type ItemDef = { art: Frame; at: readonly [x: number, y: number]; scale?: number; on?: readonly string[] };

export const STAGE3_BACKDROPS = {} satisfies Record<string, readonly Rect[]>;
export const STAGE3_ITEMS = {} satisfies Record<string, ItemDef>;
export const STAGE3_ITEM_OF = {} satisfies Record<string, string>;
export const STAGE3_CARD_SLOTS = {} satisfies Record<string, readonly (readonly [number, number])[]>;
