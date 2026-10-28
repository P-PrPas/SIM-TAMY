import type { Frame } from "./sprite";

/** Pixel art for the family scene, drawn in code (no assets). Logical scene size is 320x180. */
export const SCENE_W = 320;
export const SCENE_H = 180;
export const CHAR_W = 32;
export const CHAR_H = 48;

export type Mood = "warm" | "open";
export type CharacterKey = "ploy" | "ton" | "teacher" | "mom" | "neutral";
export type CharState = "idle" | "talk" | "warm" | "open";
export type Backdrop = "sala" | "kitchen";
export type Rect = readonly [x: number, y: number, w: number, h: number, key: string];

type Grid = string[][];
const blank = (w: number, h: number): Grid => Array.from({ length: h }, () => Array<string>(w).fill("."));
function box(g: Grid, x: number, y: number, w: number, h: number, k: string) {
  for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) if (g[j]?.[i] !== undefined) g[j]![i] = k;
}
const put = (g: Grid, x: number, y: number, k: string) => box(g, x, y, 1, 1, k);
/** 1px dark outline around every filled pixel. */
function outlined(g: Grid): Frame {
  return g.map((row, y) => row.map((c, x) => c !== "." ? c
    : [g[y - 1]?.[x], g[y + 1]?.[x], row[x - 1], row[x + 1]].some((n) => n !== undefined && n !== ".") ? "k" : ".").join(""));
}

type Look = { hair: string; cloth: string; trim: string; long?: boolean; bun?: boolean; glasses?: boolean; skirt?: boolean };
type Pose = { eyes: "open" | "blink" | "happy"; mouth: "flat" | "open" | "smile" | "hmm"; dy?: number; tilt?: number; wave?: boolean; blush?: boolean };

const LOOKS: Record<CharacterKey, Look> = {
  ploy: { hair: "h", cloth: "r", trim: "y", long: true, skirt: true },
  ton: { hair: "h", cloth: "b", trim: "p" },
  teacher: { hair: "l", cloth: "o", trim: "p", glasses: true },
  mom: { hair: "m", cloth: "g", trim: "y", bun: true, skirt: true },
  neutral: { hair: "m", cloth: "l", trim: "p" },
};

function draw(look: Look, pose: Pose): Frame {
  const g = blank(CHAR_W, CHAR_H);
  const dy = pose.dy ?? 0;
  const hx = 8 + (pose.tilt ?? 0);
  const hy = 4 + dy + Math.abs(pose.tilt ?? 0);
  const ty = hy + 19;
  box(g, hx + 6, hy + 16, 4, 4, "S"); // neck
  box(g, 8, ty, 16, 40 - ty, look.cloth); // torso
  box(g, 14, ty, 4, 5, look.trim);
  box(g, 5, ty + 1, 3, 14, look.cloth); // left arm
  box(g, 5, ty + 15, 3, 3, "s");
  const up = pose.wave ? 7 : 0;
  box(g, 24, ty + 1, 3, 14 - up, look.cloth); // right arm (talking gesture raises it)
  box(g, 24, ty + 15 - up, 3, 3, "s");
  if (look.skirt) box(g, 7, 40, 18, 6, look.cloth);
  else { box(g, 9, 40, 6, 6, "d"); box(g, 17, 40, 6, 6, "d"); }
  box(g, 10, 45, 4, 1, "S"); box(g, 18, 45, 4, 1, "S");
  box(g, 9, 46, 6, 2, "d"); box(g, 17, 46, 6, 2, "d");
  box(g, hx, hy, 16, 17, "s"); // head
  for (const [dx, dj] of [[0, 0], [15, 0], [0, 16], [15, 16]] as const) put(g, hx + dx, hy + dj, ".");
  box(g, hx - 1, hy - 1, 18, 6, look.hair);
  box(g, hx - 1, hy + 5, 3, 8, look.hair); box(g, hx + 14, hy + 5, 3, 8, look.hair);
  if (look.long) { box(g, hx - 1, hy + 13, 3, 12, look.hair); box(g, hx + 14, hy + 13, 3, 12, look.hair); }
  if (look.bun) box(g, hx + 5, hy - 5, 6, 5, look.hair);
  const ey = hy + 9;
  for (const ex of [hx + 3, hx + 10]) {
    if (pose.eyes === "open") box(g, ex, ey, 2, 3, "k");
    else if (pose.eyes === "blink") box(g, ex, ey + 2, 3, 1, "k");
    else { put(g, ex, ey + 2, "k"); put(g, ex + 1, ey + 1, "k"); put(g, ex + 2, ey + 2, "k"); }
    if (pose.blush) box(g, ex, ey + 4, 3, 1, "r");
  }
  if (look.glasses) {
    box(g, hx + 2, ey - 1, 6, 1, "k"); box(g, hx + 9, ey - 1, 6, 1, "k"); box(g, hx + 8, ey, 1, 1, "k");
    box(g, hx + 2, ey + 3, 6, 1, "k"); box(g, hx + 9, ey + 3, 6, 1, "k");
  }
  const my = hy + 13;
  if (pose.mouth === "flat") box(g, hx + 6, my, 4, 1, "S");
  else if (pose.mouth === "open") box(g, hx + 6, my, 4, 2, "k");
  else if (pose.mouth === "hmm") box(g, hx + 7, my, 3, 1, "k");
  else { put(g, hx + 5, my, "k"); box(g, hx + 6, my + 1, 4, 1, "k"); put(g, hx + 10, my, "k"); }
  return outlined(g);
}

const POSES: Record<CharState, readonly Pose[]> = {
  idle: [{ eyes: "open", mouth: "flat" }, { eyes: "blink", mouth: "flat", dy: 1 }],
  talk: [{ eyes: "open", mouth: "open", wave: true }, { eyes: "open", mouth: "flat" }],
  warm: [{ eyes: "happy", mouth: "smile", blush: true }, { eyes: "happy", mouth: "smile", blush: true, dy: 1 }],
  open: [{ eyes: "open", mouth: "hmm", tilt: 1 }, { eyes: "blink", mouth: "hmm", tilt: 1 }],
};

const cache = new Map<string, readonly Frame[]>();
export function characterFrames(who: CharacterKey, state: CharState): readonly Frame[] {
  const id = `${who}:${state}`;
  if (!cache.has(id)) cache.set(id, POSES[state].map((pose) => draw(LOOKS[who], pose)));
  return cache.get(id)!;
}

export const HEART: Frame = [".kk.kk.", "krrkrrk", "krrrrrk", ".krrrk.", "..krk..", "...k..."];
export const THINK: Frame = [
  ".kkkkkkkkkkkk.", "kppppppppppppk", "kppppppppppppk", "kppkkpkkpkkppk", "kppkkpkkpkkppk",
  "kppppppppppppk", ".kkkkpkkkkkkk.", ".....kpk......", "......k.......",
];
export const CARD: Frame = ["kkkkkkk", "koooook", "kpppppk", "kpkkkpk", "kpppppk", "kpkkkpk", "kpppppk", "kpkkppk", "kkkkkkk"];
export const NOTEBOOK: Frame = (() => {
  const g = blank(18, 14);
  box(g, 0, 0, 18, 14, "w"); box(g, 3, 2, 13, 10, "p"); box(g, 0, 0, 3, 14, "d"); box(g, 5, 4, 9, 1, "m"); box(g, 5, 7, 9, 1, "m");
  return outlined(g);
})();

const planks = (y: number, h: number, step: number, key: string): Rect[] =>
  Array.from({ length: Math.ceil(h / step) }, (_, i): Rect => [0, y + i * step, SCENE_W, 1, key]);
const slats = (y: number, h: number, step: number, key: string): Rect[] =>
  Array.from({ length: SCENE_W / step }, (_, i): Rect => [i * step, y, 1, h, key]);

export const BACKDROPS: Record<Backdrop, readonly Rect[]> = {
  sala: [
    [0, 0, 320, 128, "c"], ...slats(18, 110, 20, "l"),
    [0, 0, 320, 18, "d"], ...slats(0, 18, 24, "w"),
    [110, 30, 100, 66, "d"], [114, 34, 92, 58, "x"], [114, 62, 92, 30, "g"], [150, 50, 20, 42, "g"], [156, 44, 8, 8, "g"],
    [0, 18, 16, 130, "w"], [304, 18, 16, 130, "w"], [2, 18, 2, 130, "d"], [306, 18, 2, 130, "d"],
    [226, 56, 72, 4, "d"], [230, 44, 5, 12, "y"], [238, 46, 5, 10, "p"], [246, 44, 5, 12, "y"], [254, 47, 5, 9, "o"], [262, 44, 5, 12, "p"],
    [30, 34, 64, 40, "d"], [33, 37, 58, 34, "g"], [40, 44, 30, 1, "x"], [40, 52, 40, 1, "x"], [40, 60, 24, 1, "x"],
    [0, 128, 320, 52, "w"], ...planks(128, 52, 13, "d"),
    [100, 140, 120, 14, "r"], [104, 144, 112, 6, "y"],
  ],
  kitchen: [
    [0, 0, 320, 128, "w"], ...slats(0, 128, 20, "d"),
    [20, 24, 64, 56, "d"], [24, 28, 56, 48, "p"], [24, 28, 56, 20, "b"], [50, 28, 4, 48, "d"], [24, 50, 56, 4, "d"],
    [230, 40, 72, 4, "d"], [236, 28, 10, 12, "y"], [252, 30, 10, 10, "g"], [268, 28, 10, 12, "r"], [284, 30, 10, 10, "c"],
    [0, 128, 320, 52, "o"], ...planks(128, 52, 13, "w"),
    [88, 110, 144, 8, "y"], [88, 118, 144, 3, "w"], [96, 121, 6, 28, "d"], [218, 121, 6, 28, "d"],
    [108, 96, 24, 14, "m"], [105, 92, 30, 4, "l"], [136, 98, 4, 3, "m"], [100, 98, 5, 3, "m"],
    [148, 101, 16, 9, "p"], [150, 101, 12, 3, "r"], [170, 99, 18, 11, "x"], [172, 99, 14, 3, "y"],
    [196, 106, 26, 4, "g"], [200, 103, 18, 3, "c"],
  ],
};

/** Table slots (logical px) for notebook cards on the kitchen backdrop. */
export const TABLE_CARDS: readonly (readonly [number, number])[] = Array.from({ length: 8 }, (_, i) => [92 + i * 17, 101] as const);
