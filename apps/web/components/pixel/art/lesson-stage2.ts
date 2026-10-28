import type { Art } from "../lesson-draw";

// Stage 2 lesson illustrations (96x64). Filled by the stage 2 PR; draw with the helpers in ../lesson-draw.
// LESSON_ART_2: illustration kinds. LESSON_UNITS_2: unit id -> one kind per claim, in order.
export const LESSON_ART_2 = {} satisfies Record<string, Art>;
export const LESSON_UNITS_2: Record<string, readonly string[]> = {};
