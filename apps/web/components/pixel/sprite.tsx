import type { CSSProperties } from "react";

/** One frame = rows of palette keys; "." is transparent. All frames of a sprite share one size. */
export type Frame = readonly string[];
export type Palette = Readonly<Record<string, string>>;

/** 16-colour palette derived from the brand tokens in globals.css, so pixel art stays on-brand. */
export const PALETTE: Palette = {
  k: "#231e18", // outline (stone-950)
  d: "#47351f", // dark wood (brand-900)
  w: "#7c5314", // wood (brand-700)
  o: "#c68d1c", // ochre (brand-500)
  y: "#efbd51", // gold
  c: "#efd698", // cream (brand-200)
  p: "#fff9eb", // paper (brand-50)
  s: "#e9b48a", // skin
  S: "#c98b62", // skin shade
  h: "#30261b", // hair (brand-950)
  r: "#b4533a", // red cloth
  g: "#6f8f4e", // leaf green
  b: "#5b7a99", // blue cloth
  l: "#cfc5b6", // light stone (stone-300)
  m: "#776b5c", // mid stone (stone-500)
  x: "#fcfaf6", // canvas / highlight
};

/** Merge horizontal runs of one colour into a single rect: far fewer DOM nodes than one per pixel. */
export function runs(frame: Frame, palette: Palette = PALETTE) {
  const out: { x: number; y: number; w: number; fill: string }[] = [];
  frame.forEach((row, y) => {
    let x = 0;
    while (x < row.length) {
      const key = row[x]!;
      let end = x + 1;
      while (end < row.length && row[end] === key) end++;
      const fill = palette[key];
      if (key !== "." && fill) out.push({ x, y, w: end - x, fill });
      x = end;
    }
  });
  return out;
}

/**
 * Pixel sprite rendered as crisp SVG. Multiple frames are laid side by side and stepped with
 * CSS `steps()`; prefers-reduced-motion freezes on frame 0 (see pixel.css). Always decorative:
 * the text it illustrates must be on screen or in an aria-live region elsewhere.
 */
export function Sprite({ frames, palette = PALETTE, scale = 4, fps = 2, className }: {
  frames: readonly Frame[]; palette?: Palette; scale?: number; fps?: number; className?: string;
}) {
  const w = frames[0]?.[0]?.length ?? 0;
  const h = frames[0]?.length ?? 0;
  const n = frames.length;
  const style = { "--pixel-frames": n, "--pixel-duration": `${n / fps}s` } as CSSProperties;
  return <span className={["pixel-sprite", className].filter(Boolean).join(" ")} style={{ width: w * scale, height: h * scale }} aria-hidden="true">
    <svg className={n > 1 ? "pixel-strip is-animated" : "pixel-strip"} style={style} width={w * n * scale} height={h * scale}
      viewBox={`0 0 ${w * n} ${h}`} shapeRendering="crispEdges">
      {frames.map((frame, i) => <g key={i} transform={`translate(${i * w} 0)`}>
        {runs(frame, palette).map((r) => <rect key={`${r.x},${r.y}`} x={r.x} y={r.y} width={r.w} height={1} fill={r.fill} />)}
      </g>)}
    </svg>
  </span>;
}
