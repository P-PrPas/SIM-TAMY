import Link from "next/link";

import { t } from "@/lib/i18n";
import { CORE_PATH } from "@/lib/learning-path";
import type { Attempt, PassportLesson } from "@/lib/v2-api";

import { isPixelLesson, isPixelStory } from "./registry";
import { PALETTE } from "./sprite";
import "./house.css";

const ZONES = ["1", "2", "3", "4"] as const;
// 2x2 rooms inside a 320x180 house: [x, y] of each 130x50 room
const ROOM: Record<(typeof ZONES)[number], [number, number]> = { "1": [20, 120], "2": [20, 70], "3": [170, 120], "4": [170, 70] };

// One lesson + one scenario per stage (lib/learning-path.ts). A zone opens once its pair is drawn as pixel (registry.ts).
const PAIRS = CORE_PATH.map((p) => ({ zone: String(p.stage) as (typeof ZONES)[number], lesson: p.units[0]!, story: p.stories[0]! }));
export const HOUSE_STORY = PAIRS[0]!.story;
export const HOUSE_LESSON = PAIRS[0]!.lesson;
const zoneOpen = (z: (typeof ZONES)[number]) => {
  const pair = PAIRS.find((p) => p.zone === z);
  return Boolean(pair) && isPixelStory(pair!.story) && isPixelLesson(pair!.lesson);
};

/** Everything comes from the passport (server-side records only): finished attempts and completed lessons of one zone's pair. */
export function houseItems(attempts: readonly Attempt[] | null, lessons: readonly PassportLesson[] | null = null, zone: (typeof ZONES)[number] = "1") {
  const pair = PAIRS.find((p) => p.zone === zone) ?? PAIRS[0]!;
  const finished = (attempts ?? []).filter((a) => a.finished_at && a.story_id === pair.story);
  // A finished attempt fills the table; a better one (every decision carried a skill) fills it further. Nothing is removed.
  return {
    book: (lessons ?? []).some((l) => l.unit_id === pair.lesson),
    table: (finished.some((a) => a.strong) ? 2 : finished.length > 0 ? 1 : 0) as 0 | 1 | 2,
  };
}
type Items = ReturnType<typeof houseItems>;

function Art({ items }: { items: Record<(typeof ZONES)[number], Items> }) {
  const P = PALETTE;
  return <svg className="nh-art" viewBox="0 0 320 180" shapeRendering="crispEdges" aria-hidden="true">
    <rect width="320" height="180" fill={P.c} />
    <polygon points="10,70 160,10 310,70" fill={P.r} stroke={P.k} strokeWidth="4" />
    <rect x="10" y="62" width="300" height="8" fill={P.w} />
    {ZONES.map((z) => {
      const [x, y] = ROOM[z];
      const open = zoneOpen(z);
      const { book, table } = items[z];
      return <g key={z} data-zone={z} data-open={open}>
        <rect x={x} y={y} width="130" height="50" fill={open ? P.p : P.d} stroke={P.k} strokeWidth="4" opacity={open ? 1 : 0.85} />
        {!open && <rect x={x + 4} y={y + 4} width="122" height="42" fill={P.k} opacity="0.55" />}
        {open && book && <rect x={x + 20} y={y + 25} width="24" height="10" fill={P.y} stroke={P.k} strokeWidth="2" />}
        {open && table > 0 && <rect x={x + 70} y={y + 20} width="40" height="8" fill={P.o} stroke={P.k} strokeWidth="2" />}
        {open && table > 1 && <><rect x={x + 76} y={y + 12} width="10" height="8" fill={P.g} /><rect x={x + 92} y={y + 12} width="12" height="8" fill={P.r} /></>}
      </g>;
    })}
    <rect x="30" y="170" width="260" height="6" fill={P.w} />
  </svg>;
}

/** Nursery House meta-progress: four stage zones, open as their lesson and scenario are drawn; items come from the passport only. */
export function NurseryHouse({ attempts, lessons = null }: { attempts: readonly Attempt[] | null; lessons?: readonly PassportLesson[] | null }) {
  const items = Object.fromEntries(ZONES.map((z) => [z, houseItems(attempts, lessons, z)])) as Record<(typeof ZONES)[number], Items>;
  return <section className="nh" aria-labelledby="nh-title">
    <h2 id="nh-title">{t("pixelHouse.title")}</h2>
    <p className="pf-muted">{t("pixelHouse.intro")}</p>
    <Art items={items} />
    <ul className="nh-list" aria-label={t("pixelHouse.zonesLabel")}>
      {ZONES.map((z) => {
        const open = zoneOpen(z);
        const have = items[z];
        return <li key={z} className="nh-zone" data-open={open}>
          <strong>{t(`pixelHouse.zones.${z}`)}</strong> <span className="nh-state">{t(open ? "pixelHouse.open" : "pixelHouse.locked")}</span>
          {open && <>
            {" "}<Link href={`/learn/${z}`}>{t("pixelHouse.openZone")}{t(`pixelHouse.zones.${z}`)}</Link>
            <ul>
              <li>{t("pixelHouse.items.book")}: {t(have.book ? "pixelHouse.itemState.have" : "pixelHouse.itemState.book")}</li>
              <li>{t("pixelHouse.items.table")}: {have.table === 0 ? t("pixelHouse.itemState.table")
                : `${t("pixelHouse.itemState.have")}${have.table === 1 ? ` (${t("pixelHouse.itemState.tableMore")})` : ""}`}</li>
            </ul>
          </>}
        </li>;
      })}
    </ul>
  </section>;
}
