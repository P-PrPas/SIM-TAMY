/**
 * Stories drawn with the visual-first pixel stage (LP-01). Each stage PR only adds its story id here;
 * every other story keeps the classic layout. Solo and co-op stories are both supported.
 */
export const PIXEL_STORIES: ReadonlySet<string> = new Set(["thai-elements-family"]);

export function isPixelStory(id: string): boolean {
  return PIXEL_STORIES.has(id);
}
