/**
 * What is drawn with the visual-first pixel mode (LP-01). Each stage PR edits only its own block below, so the
 * four stages merge without conflicts. Anything not listed keeps the classic layout. Solo and co-op are both supported.
 */
const STAGE1 = { stories: ["thai-elements-family"], lessons: ["KB-TM-ELEMENT-001"] };

// Stage 2 (thai-birth-conversation + KB-IP-HERITAGE-001)
const STAGE2 = { stories: ["thai-birth-conversation"], lessons: ["KB-IP-HERITAGE-001"] };

// Stage 3 (gs-a-postpartum-warning + KB-PP-WARN-001)
const STAGE3: { stories: string[]; lessons: string[] } = { stories: [], lessons: [] };

// Stage 4 (thai-milk-family + KB-BF-COLOSTRUM-001)
const STAGE4 = { stories: ["thai-milk-family"], lessons: ["KB-BF-COLOSTRUM-001"] };

const STAGES = [STAGE1, STAGE2, STAGE3, STAGE4];

/** Stories drawn as a pixel stage. */
export const PIXEL_STORIES: ReadonlySet<string> = new Set(STAGES.flatMap((s) => s.stories));
/** Lessons shown as pixel story cards with tap-to-learn hotspots. */
export const PIXEL_LESSONS: ReadonlySet<string> = new Set(STAGES.flatMap((s) => s.lessons));

export function isPixelStory(id: string): boolean {
  return PIXEL_STORIES.has(id);
}

export function isPixelLesson(id: string): boolean {
  return PIXEL_LESSONS.has(id);
}
