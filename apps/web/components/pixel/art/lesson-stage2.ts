import { box, disc, done, figure, rect, ring, stamp, blank, type Art, type Cv } from "../lesson-draw";

// Stage 2 lesson illustrations (96x64). Filled by the stage 2 PR; draw with the helpers in ../lesson-draw.
// LESSON_ART_2: illustration kinds. LESSON_UNITS_2: unit id -> one kind per claim, in order.
// Purely illustrative: nothing here shows a procedure or a clinical object. A spot that is not lit yet is drawn in grey.

type Tint = (k: string) => string;
type Glyph = (c: Cv, x: number, y: number, p: Tint) => void;
const tint = (lit: boolean): Tint => (k) => (lit ? k : "m");

const HEART = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."];
const MOON = ["..####..", ".###....", "###.....", "###.....", "###.....", ".###....", "..####.."];
const STAR = [".#.", "###", ".#."];
const QUESTION = [".###.", "#...#", "...#.", "..#..", "..#..", ".....", "..#.."];
const TICK = ["......#", ".....#.", "#...#..", ".#.#...", "..#...."];

const house: Glyph = (c, x, y, p) => {
  rect(c, x + 2, y + 14, 2, 6, p("w")); rect(c, x + 16, y + 14, 2, 6, p("w")); rect(c, x, y + 12, 20, 2, p("w"));
  rect(c, x + 2, y + 6, 16, 6, p("o")); rect(c, x + 8, y + 8, 4, 4, p("d"));
  rect(c, x - 1, y + 4, 22, 2, p("r")); rect(c, x + 2, y + 2, 16, 2, p("r")); rect(c, x + 6, y, 8, 2, p("r"));
};
const scroll: Glyph = (c, x, y, p) => {
  box(c, x, y, 14, 9, p("y")); rect(c, x + 2, y + 2, 10, 1, p("w")); rect(c, x + 2, y + 5, 10, 1, p("w")); rect(c, x + 6, y, 1, 9, p("d"));
};
const book = (cloth: string): Glyph => (c, x, y, p) => {
  box(c, x, y, 16, 13, p(cloth)); for (const j of [3, 6, 9]) rect(c, x + 2, y + j, 12, 1, p("x"));
};
const arrow: Glyph = (c, x, y, p) => {
  rect(c, x, y + 3, 10, 2, p("o")); rect(c, x + 9, y + 1, 1, 6, p("o")); rect(c, x + 10, y + 2, 1, 4, p("o")); rect(c, x + 11, y + 3, 1, 2, p("o"));
};
const person = (cloth: string): Glyph => (c, x, y, p) => {
  rect(c, x, y + 7, 7, 9, p(cloth)); disc(c, x + 3, y + 3, 3, p("s")); rect(c, x, y, 7, 2, p("h"));
};
const heart: Glyph = (c, x, y, p) => stamp(c, x, y, HEART, p("r"));
const stop: Glyph = (c, x, y, p) => { disc(c, x + 8, y + 8, 8, p("r")); ring(c, x + 8, y + 8, 8, "k"); rect(c, x + 3, y + 6, 11, 3, p("x")); };
const bubble: Glyph = (c, x, y, p) => {
  box(c, x, y, 22, 14, p("x")); rect(c, x + 4, y + 14, 2, 1, "k"); rect(c, x + 3, y + 15, 2, 1, "k"); rect(c, x + 2, y + 16, 2, 1, "k");
  stamp(c, x + 7, y + 3, MOON, p("y")); stamp(c, x + 16, y + 3, STAR, p("y")); stamp(c, x + 15, y + 8, STAR, p("y"));
};
const tag: Glyph = (c, x, y, p) => {
  box(c, x + 3, y + 5, 14, 10, p("x")); rect(c, x + 6, y + 8, 8, 1, p("m")); rect(c, x + 6, y + 11, 8, 1, p("m"));
  rect(c, x + 9, y, 1, 5, "k"); rect(c, x + 10, y, 1, 1, "k");
  for (let i = 0; i < 12; i++) rect(c, x + 2 + i, y + 3 + i, 2, 2, p("r"));
};
const ask: Glyph = (c, x, y, p) => {
  rect(c, x, y + 4, 7, 9, p("b")); disc(c, x + 3, y + 3, 3, p("s")); rect(c, x, y, 7, 2, p("h"));
  box(c, x + 9, y - 2, 11, 12, p("x")); stamp(c, x + 12, y, QUESTION, p("k"));
};
const equal: Glyph = (c, x, y, p) => {
  stamp(c, x, y + 2, HEART, p("r")); stamp(c, x + 17, y + 2, HEART, p("r"));
  rect(c, x + 9, y + 3, 6, 1, p("k")); rect(c, x + 9, y + 6, 6, 1, p("k"));
};
const dignity: Glyph = (c, x, y, p) => stamp(c, x + 1, y + 1, HEART, p("r"));
const info: Glyph = (c, x, y, p) => { box(c, x + 1, y, 10, 12, p("x")); for (const j of [3, 6, 9]) rect(c, x + 3, y + j, 6, 1, p("b")); };
const decide: Glyph = (c, x, y, p) => stamp(c, x + 1, y + 2, TICK, p("g"));
const questions: Glyph = (c, x, y, p) => stamp(c, x + 3, y + 1, QUESTION, p("b"));
const different: Glyph = (c, x, y, p) => {
  disc(c, x + 3, y + 3, 3, p("r")); rect(c, x + 7, y + 1, 6, 6, p("b"));
  for (let i = 0; i < 4; i++) rect(c, x + 4 + i, y + 8 + i, 6 - 2 * i, 1, p("g"));
};
const signpost: Glyph = (c, x, y, p) => {
  rect(c, x + 8, y, 3, 20, p("w"));
  rect(c, x + 2, y + 2, 14, 4, p("r")); rect(c, x + 16, y + 3, 2, 2, p("r"));
  rect(c, x + 3, y + 8, 14, 4, p("b")); rect(c, x + 1, y + 9, 2, 2, p("b"));
  rect(c, x + 2, y + 14, 14, 4, p("g")); rect(c, x + 16, y + 15, 2, 2, p("g"));
};
const scales: Glyph = (c, x, y, p) => {
  rect(c, x + 9, y + 1, 2, 16, p("w")); rect(c, x + 3, y + 4, 14, 1, p("k"));
  rect(c, x + 3, y + 5, 1, 4, p("k")); rect(c, x + 16, y + 5, 1, 4, p("k"));
  rect(c, x + 1, y + 9, 6, 2, p("y")); rect(c, x + 13, y + 9, 6, 2, p("o")); rect(c, x + 5, y + 17, 10, 2, p("w"));
};
const pair: Glyph = (c, x, y, p) => {
  rect(c, x, y + 6, 7, 10, p("r")); disc(c, x + 3, y + 3, 3, p("s")); rect(c, x, y, 7, 2, p("h"));
  rect(c, x + 10, y + 10, 6, 6, p("y")); disc(c, x + 13, y + 8, 3, p("s"));
};
const consent: Glyph = (c, x, y, p) => { box(c, x + 2, y, 12, 15, p("x")); rect(c, x + 4, y + 3, 8, 1, p("m")); rect(c, x + 4, y + 6, 8, 1, p("m")); stamp(c, x + 5, y + 9, TICK, p("g")); };
const cup: Glyph = (c, x, y, p) => {
  rect(c, x + 3, y, 10, 7, p("y")); rect(c, x, y + 1, 3, 4, p("y")); rect(c, x + 13, y + 1, 3, 4, p("y"));
  rect(c, x + 7, y + 7, 2, 5, p("o")); rect(c, x + 4, y + 12, 8, 2, p("o"));
  for (let i = 0; i < 14; i++) rect(c, x + 1 + i, y + 1 + i, 2, 2, p("r"));
};

/** A panel with one glyph; it lights up (cream panel, true colours) when its spot is tapped. */
const panel = (c: Cv, x: number, y: number, w: number, h: number, lit: boolean) => box(c, x, y, w, h, lit ? "c" : "x");
const put = (c: Cv, g: Glyph, x: number, y: number, lit: boolean) => g(c, x, y, tint(lit));

const GRID_2X2 = [[2, 2], [50, 2], [2, 27], [50, 27]] as const;
const GRID_3_2 = [[4, 3], [38, 3], [72, 3], [21, 28], [55, 28]] as const;
const AROUND = [[6, 6], [41, 3], [77, 6], [14, 35], [69, 35]] as const;

export const LESSON_ART_2 = {
  ipHeritage: { taps: 4, draw: (on) => {
    const c = blank();
    GRID_2X2.forEach(([x, y], i) => panel(c, x!, y!, 44, 24, !!on[i]));
    put(c, house, 6, 4, !!on[0]); put(c, scroll, 30, 9, !!on[0]);
    put(c, arrow, 54, 10, !!on[1]); put(c, book("b"), 70, 7, !!on[1]);
    put(c, person("r"), 8, 32, !!on[2]); put(c, person("b"), 28, 32, !!on[2]); put(c, heart, 17, 30, !!on[2]);
    put(c, stop, 58, 30, !!on[3]); put(c, book("o"), 76, 34, !!on[3]);
    return done(c);
  } },
  ipTales: { taps: 4, draw: (on) => {
    const c = blank();
    GRID_2X2.forEach(([x, y], i) => panel(c, x!, y!, 44, 24, !!on[i]));
    put(c, bubble, 12, 4, !!on[0]); put(c, tag, 16, 29, !!on[1]); put(c, ask, 62, 8, !!on[2]); put(c, equal, 66, 33, !!on[3]);
    return done(c);
  } },
  ipCentred: { taps: 5, draw: (on) => {
    const c = blank(); figure(c, 48, 22);
    ([dignity, info, decide, questions, different] as const).forEach((g, i) => {
      const [x, y] = AROUND[i]!;
      panel(c, x! - 1, y! - 1, 16, 16, !!on[i]); put(c, g, x!, y!, !!on[i]);
    });
    return done(c);
  } },
  ipOptions: { taps: 5, draw: (on) => {
    const c = blank();
    ([signpost, scales, pair, consent, cup] as const).forEach((g, i) => {
      const [x, y] = GRID_3_2[i]!;
      panel(c, x!, y!, 20, 21, !!on[i]); put(c, g, x! + 1, y! + 1, !!on[i]);
    });
    return done(c);
  } },
} satisfies Record<string, Art>;

export const LESSON_UNITS_2: Record<string, readonly string[]> = {
  "KB-IP-HERITAGE-001": ["ipHeritage", "ipTales", "ipCentred", "ipOptions"],
};
