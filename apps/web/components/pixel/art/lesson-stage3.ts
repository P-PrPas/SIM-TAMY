import { blank, box, disc, done, figure, rect, stamp, type Art } from "../lesson-draw";

// Stage 3 lesson illustrations (96x64) for KB-PP-WARN-001. Safety unit: neutral symbols only. Nothing here depicts a
// symptom, bleeding, pain, a body or any procedure; the danger signs are named by the claim text and the tap sheet.
// LESSON_ART_3: illustration kinds. LESSON_UNITS_3: unit id -> one kind per claim, in order.
const EXCL = ["##", "##", "##", "..", "##"] as const;
const PHONE = [".#####.", "#.....#", "#.###.#", "#.###.#", "#.###.#", "#.....#", "#..#..#", ".#####."] as const;
const ARROW = ["...#...", "....#..", "#######", "....#..", "...#..."] as const;
const EYE = ["..#####..", ".#.....#.", "#...#...#", "#..###..#", "#...#...#", ".#.....#.", "..#####.."] as const;
const STOP = ["..#####..", ".#######.", "#########", "#xxxxxxx#", "#xxxxxxx#", "#########", "#########", ".#######.", "..#####.."] as const;
const SALA = ["......###......", "....#######....", "..###########..", "###############", "..#.........#..", "..#.........#..", "..#.........#..", "..#.........#.."] as const;
const HEART = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."] as const;
const HOUSE = ["..#..", ".###.", "#####", "##.##", "#####"] as const;

/** Double every pixel of a stamp (symbols that need to read on a larger plate). */
const big = (rows: readonly string[]): string[] => rows.flatMap((r) => { const w = [...r].map((ch) => ch + ch).join(""); return [w, w]; });
/** A square plate that wakes up (colour) when its spot has been tapped. */
const plate = (c: string[][], x: number, y: number, w: number, h: number, on: boolean) => box(c, x, y, w, h, on ? "y" : "l");
const hospital = (c: string[][], x: number, y: number, on: boolean) => {
  box(c, x, y, 22, 24, on ? "x" : "l");
  rect(c, x + 9, y + 6, 4, 12, on ? "r" : "m"); rect(c, x + 5, y + 10, 12, 4, on ? "r" : "m");
};

export const LESSON_ART_3 = {
  // c1: three neutral "alert" plates around a calm person, and a phone for asking for help.
  wd_alert: { taps: 4, draw: (on) => {
    const c = blank(); figure(c, 48, 20);
    ([[10, 6], [72, 6], [10, 32]] as const).forEach(([x, y], i) => { plate(c, x, y, 14, 14, Boolean(on[i])); stamp(c, x + 6, y + 4, EXCL, on[i] ? "k" : "m"); });
    box(c, 72, 28, 14, 20, on[3] ? "g" : "l"); stamp(c, 75, 32, PHONE, on[3] ? "x" : "m");
    if (on[3]) { rect(c, 88, 30, 2, 1, "g"); rect(c, 90, 28, 2, 1, "g"); rect(c, 88, 34, 2, 1, "g"); rect(c, 90, 36, 2, 1, "g"); }
    return done(c);
  } },
  // c2: scope. Know the signs / pass it on to health services / not self-treatment.
  wd_scope: { taps: 3, draw: (on) => {
    const c = blank();
    ([[2, 24], [30, 36], [70, 24]] as const).forEach(([x, w], i) => plate(c, x, 8, w, 36, Boolean(on[i])));
    stamp(c, 5, 18, big(EYE), on[0] ? "b" : "m");
    stamp(c, 32, 18, big(PHONE), on[1] ? "b" : "m"); stamp(c, 46, 23, ARROW, on[1] ? "r" : "m");
    box(c, 54, 20, 8, 12, on[1] ? "x" : "l"); rect(c, 57, 22, 2, 8, on[1] ? "r" : "m"); rect(c, 55, 25, 6, 2, on[1] ? "r" : "m");
    stamp(c, 72, 17, big(STOP), on[2] ? "r" : "m");
    return done(c);
  } },
  // c3: take the warning seriously, pass it on urgently, even when the visit was for Thai recovery care.
  wd_refer: { taps: 3, draw: (on) => {
    const c = blank();
    rect(c, 3, 34, 13, 12, on[2] ? "w" : "l"); rect(c, 8, 38, 4, 8, on[2] ? "d" : "m"); stamp(c, 2, 26, SALA, on[2] ? "r" : "m");
    figure(c, 44, 22);
    plate(c, 37, 3, 14, 14, Boolean(on[0])); stamp(c, 43, 7, EXCL, on[0] ? "k" : "m");
    stamp(c, 56, 32, ARROW, on[1] ? "r" : "m");
    hospital(c, 68, 24, Boolean(on[1]));
    return done(c);
  } },
  // c4: what postpartum care covers: mother and baby, mind, family, the first weeks.
  wd_care: { taps: 4, draw: (on) => {
    const c = blank(); figure(c, 48, 22);
    const spots = [[6, 6], [74, 6], [6, 32], [74, 32]] as const;
    spots.forEach(([x, y], i) => plate(c, x, y, 16, 16, Boolean(on[i])));
    box(c, 9, 15, 5, 6, on[0] ? "r" : "m"); disc(c, 11, 12, 2, on[0] ? "s" : "m"); box(c, 16, 17, 4, 4, on[0] ? "g" : "m"); disc(c, 18, 15, 1, on[0] ? "s" : "m");
    stamp(c, 78, 11, HEART, on[1] ? "r" : "m");
    stamp(c, 11, 38, HOUSE, on[2] ? "r" : "m");
    box(c, 77, 36, 10, 9, on[3] ? "x" : "p"); rect(c, 78, 37, 8, 2, on[3] ? "r" : "m");
    for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) rect(c, 79 + i * 3, 40 + j * 3, 2, 2, on[3] ? "k" : "m");
    return done(c);
  } },
} satisfies Record<string, Art>;

export const LESSON_UNITS_3: Record<string, readonly string[]> = {
  "KB-PP-WARN-001": ["wd_alert", "wd_scope", "wd_refer", "wd_care"],
};
