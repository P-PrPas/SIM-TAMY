import { blank, box, disc, done, figure, rect, stamp, type Art, type Cv } from "../lesson-draw";

// Stage 4 lesson illustrations (96x64) for KB-BF-COLOSTRUM-001. Purely illustrative: no facts beyond the card text.
// LESSON_ART_4: illustration kinds. LESSON_UNITS_4: unit id -> one kind per claim, in order.
// Each art keeps one tappable tile per hotspot (tile i lights when hotspot i is opened).
const EYE = [".###.", "#.#.#", ".###."] as const;
const DROP = ["..#..", ".###.", "#####", "#####", ".###."] as const;
const SHIELD = ["#####", "#####", "#####", ".###.", "..#.."] as const;
const CLOCK = ["#####", "#.#.#", "#.##.", "#...#", "#####"] as const;
const BOWL = ["#####", "#####", ".###.", "..#.."] as const;
const HEART = [".#.#.", "#####", "#####", ".###.", "..#.."] as const;
const EAR = ["..##.", ".#..#", ".#.#.", "..##.", "..#.."] as const;
const SHARE = ["##...", "##.##", ".####", "##.##", "##..."] as const;
const PERSON = [".##.", ".##.", "####", "####", "#..#"] as const;
const CHAT = ["#####", "#...#", "#####", "..#.."] as const;
const CROSS = ["#...#", ".#.#.", "..#..", ".#.#.", "#...#"] as const;
const NEQ = ["...#.", "#####", "..#..", "#####", ".#..."] as const;
const BOOK = ["#####", "#.#.#", "#####", "#.#.#", "#####"] as const;

/** A 14x14 tile that is grey until its hotspot is opened. */
function tile(c: Cv, x: number, y: number, on: boolean, colour: string, glyph: readonly string[]) {
  box(c, x, y, 14, 14, on ? colour : "l");
  stamp(c, x + 4, y + 4, glyph, on ? "k" : "m");
}
const row = (n: number, gap: number) => Array.from({ length: n }, (_, i) => Math.round((96 - (n * 14 + (n - 1) * gap)) / 2) + i * (14 + gap));

export const LESSON_ART_4 = {
  // c1: an old palm-leaf text, a look at how people watched mother and child, and colour/taste tests that are not used today.
  oldtext: { taps: 3, draw: (on) => {
    const c = blank();
    const xs = row(3, 20);
    tile(c, xs[0]!, 4, !!on[0], "o", BOOK); tile(c, xs[1]!, 4, !!on[1], "b", EYE); tile(c, xs[2]!, 4, !!on[2], "r", CROSS);
    rect(c, 14, 28, 68, 3, "w"); rect(c, 14, 46, 68, 3, "w");
    for (let i = 0; i < 4; i++) { box(c, 18 + i * 16, 31, 14, 15, "c"); for (let j = 0; j < 3; j++) rect(c, 21 + i * 16, 34 + j * 4, 8, 1, "o"); }
    rect(c, 24, 31, 1, 15, "r"); rect(c, 72, 31, 1, 15, "r");
    if (on[0]) for (let i = 0; i < 4; i++) rect(c, 19 + i * 16, 32, 12, 1, "y");
    if (on[1]) { figure(c, 8, 34); disc(c, 88, 49, 3, "s"); }
    if (on[2]) { rect(c, 38, 51, 20, 2, "r"); rect(c, 38, 55, 20, 2, "r"); }
    return done(c);
  } },
  // c2: the first milk, drawn as a bowl with a drop (no feeding scene).
  firstmilk: { taps: 4, draw: (on) => {
    const c = blank();
    const xs = row(4, 8);
    tile(c, xs[0]!, 4, !!on[0], "y", DROP); tile(c, xs[1]!, 4, !!on[1], "b", SHIELD); tile(c, xs[2]!, 4, !!on[2], "r", CROSS); tile(c, xs[3]!, 4, !!on[3], "g", CHAT);
    if (on[3]) { figure(c, 26, 26); figure(c, 70, 26); }
    box(c, 34, 32, 28, 16, "x"); rect(c, 36, 34, 24, 4, on[0] ? "y" : "l"); rect(c, 38, 48, 20, 3, "w");
    if (on[0]) disc(c, 48, 26, 3, "y");
    if (on[1]) { rect(c, 6, 24, 12, 14, "k"); rect(c, 7, 25, 10, 12, "b"); rect(c, 9, 38, 6, 2, "k"); }
    if (on[2]) { rect(c, 78, 36, 12, 10, "o"); rect(c, 78, 34, 12, 2, "w"); rect(c, 82, 38, 4, 4, "y"); }
    return done(c);
  } },
  // c3: a general timeline: first hour, milk only, family foods alongside milk, and support instead of blame.
  timeline: { taps: 4, draw: (on) => {
    const c = blank();
    const xs = row(4, 8);
    const look: [string, readonly string[]][] = [["y", CLOCK], ["b", DROP], ["g", BOWL], ["r", HEART]];
    look.forEach(([colour, glyph], i) => tile(c, xs[i]!, 6, !!on[i], colour, glyph));
    rect(c, 10, 38, 76, 3, "k");
    xs.forEach((x, i) => {
      if (i > 0 && on[i]) rect(c, xs[i - 1]! + 7, 39, x - xs[i - 1]!, 1, "o");
      disc(c, x + 7, 39, 3, on[i] ? "o" : "l"); rect(c, x + 7, 24, 1, 12, "m");
    });
    return done(c);
  } },
  // c4: people around the mother can listen, share the work and walk with her to a counsellor.
  helpers: { taps: 5, draw: (on) => {
    const c = blank();
    const xs = row(5, 6);
    const look: [string, readonly string[]][] = [["y", EAR], ["b", SHARE], ["g", PERSON], ["o", BOWL], ["r", HEART]];
    look.forEach(([colour, glyph], i) => tile(c, xs[i]!, 4, !!on[i], colour, glyph));
    figure(c, 22, 26); figure(c, 48, 26); figure(c, 74, 26);
    if (on[0]) { rect(c, 28, 24, 6, 4, "p"); rect(c, 28, 24, 6, 1, "k"); }
    if (on[1]) { rect(c, 34, 46, 8, 2, "y"); rect(c, 54, 46, 8, 2, "y"); }
    if (on[2]) { rect(c, 70, 33, 8, 3, "g"); }
    if (on[3]) { box(c, 40, 56, 16, 6, "x"); rect(c, 43, 58, 10, 1, "m"); }
    if (on[4]) { rect(c, 46, 20, 5, 2, "r"); rect(c, 45, 21, 7, 2, "r"); rect(c, 46, 23, 5, 1, "r"); rect(c, 47, 24, 3, 1, "r"); }
    return done(c);
  } },
  // c5: milk changes over time, so colour and thickness differ from day to day.
  stages: { taps: 4, draw: (on) => {
    const c = blank();
    const xs = row(4, 8);
    tile(c, xs[0]!, 4, !!on[0], "y", ["#####", ".###.", "..#.."] as const); tile(c, xs[1]!, 4, !!on[1], "c", DROP); tile(c, xs[2]!, 4, !!on[2], "b", NEQ); tile(c, xs[3]!, 4, !!on[3], "g", CHAT);
    const cups: [number, string, boolean][] = [[12, "y", true], [40, "o", !!on[0]], [68, "x", !!on[1]]];
    cups.forEach(([x, colour, lit]) => { box(c, x, 30, 16, 16, lit ? colour : "l"); rect(c, x + 2, 28, 12, 2, "k"); });
    [28, 56].forEach((x) => stamp(c, x, 35, [".#.", "###", ".#."], "m"));
    if (on[2]) { rect(c, 14, 50, 12, 3, "y"); rect(c, 42, 50, 12, 3, "c"); rect(c, 70, 50, 12, 3, "x"); }
    if (on[3]) { box(c, 34, 50, 28, 9, "x"); [40, 47, 54].forEach((x) => rect(c, x, 54, 2, 2, "m")); }
    return done(c);
  } },
} satisfies Record<string, Art>;

export const LESSON_UNITS_4: Record<string, readonly string[]> = {
  "KB-BF-COLOSTRUM-001": ["oldtext", "firstmilk", "timeline", "helpers", "stages"],
};
