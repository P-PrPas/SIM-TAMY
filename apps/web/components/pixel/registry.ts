/**
 * Stories drawn with the visual-first pixel stage (LP-01). Each stage PR only adds its story id here;
 * every other story keeps the classic layout. Solo and co-op stories are both supported.
 */
export const PIXEL_STORIES: ReadonlySet<string> = new Set(["thai-elements-family"]);

export function isPixelStory(id: string): boolean {
  return PIXEL_STORIES.has(id);
}

/** Lessons shown as pixel story cards with tap-to-learn hotspots (LP-01). A stage PR adds its unit id once hotspots and art are in. */
export const PIXEL_LESSONS: ReadonlySet<string> = new Set(["KB-TM-ELEMENT-001"]);

export function isPixelLesson(id: string): boolean {
  return PIXEL_LESSONS.has(id);
}
