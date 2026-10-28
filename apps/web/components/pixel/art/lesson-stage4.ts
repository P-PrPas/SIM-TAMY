import type { Art } from "../lesson-draw";

// Stage 4 lesson illustrations (96x64). Filled by the stage 4 PR; draw with the helpers in ../lesson-draw.
// LESSON_ART_4: illustration kinds. LESSON_UNITS_4: unit id -> one kind per claim, in order.
export const LESSON_ART_4 = {} satisfies Record<string, Art>;
export const LESSON_UNITS_4: Record<string, readonly string[]> = {};
