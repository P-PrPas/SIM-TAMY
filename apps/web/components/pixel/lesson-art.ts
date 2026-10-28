import type { Frame } from "./sprite";

/** Code-drawn 96x64 lesson illustrations. Purely illustrative: they carry no facts beyond the card text. */
export const ART_W = 96;
export const ART_H = 64;
type Cv = string[][];

const blank = (): Cv => {
  const c = Array.from({ length: ART_H }, () => Array<string>(ART_W).fill("p"));
  for (let y = 52; y < ART_H; y++) c[y]!.fill("c");
  return c;
};
const rect = (c: Cv, x: number, y: number, w: number, h: number, k: string) => {
  for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) if (c[j]?.[i] !== undefined) c[j]![i] = k;
};
const box = (c: Cv, x: number, y: number, w: number, h: number, fill: string) => {
  rect(c, x, y, w, h, "k"); rect(c, x + 1, y + 1, w - 2, h - 2, fill);
};
const disc = (c: Cv, cx: number, cy: number, r: number, k: string) => {
  for (let j = -r; j <= r; j++) for (let i = -r; i <= r; i++) if (i * i + j * j <= r * r + r / 2) rect(c, cx + i, cy + j, 1, 1, k);
};
const ring = (c: Cv, cx: number, cy: number, r: number, k: string) => {
  for (let j = -r; j <= r; j++) for (let i = -r; i <= r; i++) {
    const d = i * i + j * j;
    if (d <= r * r + r / 2 && d >= (r - 1) * (r - 1) - 1) rect(c, cx + i, cy + j, 1, 1, k);
  }
};
/** Stamp a char map; "#" is repainted with `paint` when given. */
const stamp = (c: Cv, x: number, y: number, rows: readonly string[], paint?: string) => {
  rows.forEach((row, j) => [...row].forEach((ch, i) => { if (ch !== ".") rect(c, x + i, y + j, 1, 1, ch === "#" && paint ? paint : ch); }));
};
const done = (c: Cv): Frame => c.map((r) => r.join(""));
const figure = (c: Cv, cx: number, top: number) => {
  rect(c, cx - 5, top + 10, 10, 16, "b"); rect(c, cx - 5, top + 10, 10, 1, "k");
  disc(c, cx, top + 5, 5, "s"); rect(c, cx - 5, top, 10, 3, "h");
};

const GLYPH = ["..#..", ".###.", "#####", ".###.", "..#.."] as const;
const SUN = [".#.#.", "..#..", "#####", "..#..", ".#.#."] as const;
const CLOCK = ["#####", "#.#.#", "#.##.", "#...#", "#####"] as const;
const CANDLE = ["..#..", "..#..", ".###.", ".###.", ".###."] as const;
const HOUSE = ["..#..", ".###.", "#####", "##.##", "#####"] as const;
const SHOE = ["#....", "##...", "#####", "#####", "....."] as const;
const PLATE = ["..######..", ".########.", "##########", ".########.", "..######.."] as const;
const APPROX = ["..##...##.", ".#..#.#..#", "#....#...."] as const;

export type ArtKind = "element" | "wheel" | "calendar" | "context" | "table" | "book" | "wisdom" | "safety" | "rights";
export type Art = { taps: number; draw: (on: readonly boolean[]) => Frame };

const ELEMENT_COLOURS = ["o", "b", "g", "r"] as const;
const ELEMENT_POS = [[6, 8], [78, 8], [6, 38], [78, 38]] as const;
const CONTEXT_ICONS = [SUN, CLOCK, CANDLE, HOUSE, SHOE] as const;
const CONTEXT_POS = [[8, 8], [44, 4], [80, 8], [12, 40], [76, 40]] as const;

export const ART: Record<ArtKind, Art> = {
  element: { taps: 4, draw: (on) => {
    const c = blank(); figure(c, 48, 20);
    ELEMENT_POS.forEach(([x, y], i) => { box(c, x, y, 12, 12, on[i] ? ELEMENT_COLOURS[i]! : "l"); stamp(c, x + 3, y + 3, GLYPH, on[i] ? "k" : "m"); });
    return done(c);
  } },
  wheel: { taps: 1, draw: (on) => {
    const c = blank(); disc(c, 48, 28, 22, "c"); ring(c, 48, 28, 22, "k"); ring(c, 48, 28, 12, "k");
    const pins = on[0] ? [[48, 10], [66, 28], [48, 46]] : [[48, 10], [30, 28], [66, 28]];
    pins.forEach(([x, y], i) => disc(c, x!, y!, 3, ["r", "b", "g"][i]!));
    box(c, 8, 24, 10, 10, on[0] ? "r" : "y"); box(c, 78, 24, 10, 10, on[0] ? "b" : "y");
    return done(c);
  } },
  calendar: { taps: 1, draw: (on) => {
    const c = blank(); box(c, 14, 4, 68, 46, "x"); rect(c, 15, 5, 66, 8, "r");
    for (let j = 0; j < 4; j++) for (let i = 0; i < 7; i++) box(c, 18 + i * 9, 16 + j * 8, 7, 6, on[0] && j >= 1 && j <= 2 && i >= 2 && i <= 5 ? "y" : "l");
    if (on[0]) stamp(c, 43, 53, APPROX, "k");
    return done(c);
  } },
  context: { taps: 5, draw: (on) => {
    const c = blank(); figure(c, 48, 22);
    CONTEXT_ICONS.forEach((icon, i) => { const [x, y] = CONTEXT_POS[i]!; box(c, x! - 2, y! - 2, 9, 9, on[i] ? "y" : "l"); stamp(c, x!, y!, icon, on[i] ? "r" : "m"); });
    return done(c);
  } },
  table: { taps: 3, draw: (on) => {
    const c = blank(); rect(c, 8, 36, 80, 5, "w"); rect(c, 14, 41, 4, 12, "d"); rect(c, 78, 41, 4, 12, "d");
    [10, 33, 56].forEach((x, i) => {
      stamp(c, x + 6, 28, PLATE, on[i] ? "x" : "l");
      if (on[i]) { rect(c, x + 9, 30, 2, 2, "r"); rect(c, x + 13, 31, 2, 2, "g"); rect(c, x + 11, 33, 2, 2, "y"); }
    });
    return done(c);
  } },
  book: { taps: 1, draw: (on) => {
    const c = blank(); box(c, 14, 20, 34, 30, "x"); box(c, 48, 20, 34, 30, "x");
    for (let i = 0; i < 4; i++) { rect(c, 19, 27 + i * 6, 24, 1, "m"); rect(c, 53, 27 + i * 6, 24, 1, "m"); }
    if (on[0]) { disc(c, 48, 10, 5, "g"); rect(c, 47, 14, 2, 6, "d"); }
    return done(c);
  } },
  wisdom: { taps: 1, draw: (on) => {
    const c = blank(); disc(c, 48, 26, 14, on[0] ? "g" : "l"); ring(c, 48, 26, 14, "k"); rect(c, 47, 40, 2, 12, "d");
    return done(c);
  } },
  safety: { taps: 1, draw: (on) => {
    const c = blank(); const fill = on[0] ? "b" : "l";
    rect(c, 34, 8, 28, 24, "k"); rect(c, 35, 9, 26, 22, fill);
    for (let i = 0; i < 12; i++) { rect(c, 34 + i, 32 + i, 28 - 2 * i, 1, "k"); rect(c, 35 + i, 32 + i, 26 - 2 * i, 1, fill); }
    return done(c);
  } },
  rights: { taps: 1, draw: (on) => {
    const c = blank(); box(c, 28, 6, 40, 44, on[0] ? "y" : "l");
    for (let i = 0; i < 5; i++) rect(c, 33, 14 + i * 7, 30, 1, "k");
    return done(c);
  } },
};

/** Which illustration a card gets: by unit and claim index, with a neutral book fallback for any other unit. */
const ART_BY_UNIT: Record<string, readonly ArtKind[]> = {
  "KB-TM-ELEMENT-001": ["element", "wheel", "calendar", "context", "table"],
};
export const claimArt = (unitId: string, index: number): ArtKind => ART_BY_UNIT[unitId]?.[index] ?? "book";

/** Two-frame confetti for the sort-game finish screen. */
export const CELEBRATE: readonly Frame[] = [0, 1].map((f) => {
  const c = blank(); rect(c, 0, 52, ART_W, 12, "p");
  [[8, 10], [26, 30], [44, 6], [62, 34], [80, 12], [18, 46], [50, 44], [74, 48]]
    .forEach(([x, y], i) => rect(c, x!, y! + f * 3, 4, 4, ["y", "r", "b", "g"][i % 4]!));
  stamp(c, 45, 24 + f * 2, ["..#..", ".###.", "#####", ".###.", "..#.."], "y");
  return done(c);
});
