import type { Art } from "../lesson-draw";

// Stage 3 lesson illustrations (96x64). Filled by the stage 3 PR; draw with the helpers in ../lesson-draw.
// LESSON_ART_3: illustration kinds. LESSON_UNITS_3: unit id -> one kind per claim, in order.
export const LESSON_ART_3 = {} satisfies Record<string, Art>;
export const LESSON_UNITS_3: Record<string, readonly string[]> = {};
