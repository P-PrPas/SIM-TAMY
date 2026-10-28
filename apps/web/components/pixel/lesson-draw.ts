import type { Frame } from "./sprite";

/** Code-drawn 96x64 lesson illustrations. Purely illustrative: they carry no facts beyond the card text. */
export const ART_W = 96;
export const ART_H = 64;
export type Cv = string[][];

export const blank = (): Cv => {
  const c = Array.from({ length: ART_H }, () => Array<string>(ART_W).fill("p"));
  for (let y = 52; y < ART_H; y++) c[y]!.fill("c");
  return c;
};
export const rect = (c: Cv, x: number, y: number, w: number, h: number, k: string) => {
  for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) if (c[j]?.[i] !== undefined) c[j]![i] = k;
};
export const box = (c: Cv, x: number, y: number, w: number, h: number, fill: string) => {
  rect(c, x, y, w, h, "k"); rect(c, x + 1, y + 1, w - 2, h - 2, fill);
};
export const disc = (c: Cv, cx: number, cy: number, r: number, k: string) => {
  for (let j = -r; j <= r; j++) for (let i = -r; i <= r; i++) if (i * i + j * j <= r * r + r / 2) rect(c, cx + i, cy + j, 1, 1, k);
};
export const ring = (c: Cv, cx: number, cy: number, r: number, k: string) => {
  for (let j = -r; j <= r; j++) for (let i = -r; i <= r; i++) {
    const d = i * i + j * j;
    if (d <= r * r + r / 2 && d >= (r - 1) * (r - 1) - 1) rect(c, cx + i, cy + j, 1, 1, k);
  }
};
/** Stamp a char map; "#" is repainted with `paint` when given. */
export const stamp = (c: Cv, x: number, y: number, rows: readonly string[], paint?: string) => {
  rows.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") rect(c, x + i, y + j, 1, 1, ch === "#" && paint ? paint : ch); }));
};
export const done = (c: Cv): Frame => c.map((r) => r.join(""));
export const figure = (c: Cv, cx: number, top: number) => {
  rect(c, cx - 5, top + 10, 10, 16, "b"); rect(c, cx - 5, top + 10, 10, 1, "k");
  disc(c, cx, top + 5, 5, "s"); rect(c, cx - 5, top, 10, 3, "h");
};

export type Art = { taps: number; draw: (on: readonly boolean[]) => Frame };
