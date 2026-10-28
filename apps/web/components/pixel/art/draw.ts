import type { Frame } from "../sprite";

/** Shared drawing helpers for code-drawn pixel art (characters, props, backdrops). */
export const SCENE_W = 320;
export const SCENE_H = 180;
/** A backdrop is a list of filled rects: [x, y, w, h, palette key]. */
export type Rect = readonly [x: number, y: number, w: number, h: number, key: string];

export type Grid = string[][];
export const blank = (w: number, h: number): Grid => Array.from({ length: h }, () => Array<string>(w).fill("."));
export function box(g: Grid, x: number, y: number, w: number, h: number, k: string) {
  for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) if (g[j]?.[i] !== undefined) g[j]![i] = k;
}
export const put = (g: Grid, x: number, y: number, k: string) => box(g, x, y, 1, 1, k);
/** 1px dark outline around every filled pixel. */
export function outlined(g: Grid): Frame {
  return g.map((row, y) => row.map((c, x) => c !== "." ? c
    : [g[y - 1]?.[x], g[y + 1]?.[x], row[x - 1], row[x + 1]].some((n) => n !== undefined && n !== ".") ? "k" : ".").join(""));
}

/** Horizontal lines every `step` px (floor planks). */
export const planks = (y: number, h: number, step: number, key: string): Rect[] =>
  Array.from({ length: Math.ceil(h / step) }, (_, i): Rect => [0, y + i * step, SCENE_W, 1, key]);
/** Vertical lines every `step` px (wall slats). */
export const slats = (y: number, h: number, step: number, key: string): Rect[] =>
  Array.from({ length: SCENE_W / step }, (_, i): Rect => [i * step, y, 1, h, key]);
