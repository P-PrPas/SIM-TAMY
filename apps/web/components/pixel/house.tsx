import Link from "next/link";

import { t } from "@/lib/i18n";
import type { Attempt, PassportLesson } from "@/lib/v2-api";

import { PALETTE } from "./sprite";
import "./house.css";

const ZONES = ["1", "2", "3", "4"] as const;
// 2x2 rooms inside a 320x180 house: [x, y] of each 130x50 room
const ROOM: Record<(typeof ZONES)[number], [number, number]> = { "1": [20, 120], "2": [20, 70], "3": [170, 120], "4": [170, 70] };

// The stage-1 pair whose records fill the porch (other stages open their zones as they are registered).
export const HOUSE_STORY = "thai-elements-family";
export const HOUSE_LESSON = "KB-TM-ELEMENT-001";

/** Everything comes from the passport (server-side records only): finished chapter-1 attempts and completed lessons. */
export function houseItems(attempts: readonly Attempt[] | null, lessons: readonly PassportLesson[] | null = null) {
  const finished = (attempts ?? []).filter((a) => a.finished_at && a.story_id === HOUSE_STORY);
  // A finished attempt fills the table; a better one (every decision carried a skill) fills it further. Nothing is removed.
  return {
    book: (lessons ?? []).some((l) => l.unit_id === HOUSE_LESSON),
    table: (finished.some((a) => a.strong) ? 2 : finished.length > 0 ? 1 : 0) as 0 | 1 | 2,
  };
}

function Art({ table, book }: { table: number; book: boolean }) {
  const P = PALETTE;
  return <svg className="nh-art" viewBox="0 0 320 180" shapeRendering="crispEdges" aria-hidden="true">
    <rect width="320" height="180" fill={P.c} />
    <polygon points="10,70 160,10 310,70" fill={P.r} stroke={P.k} strokeWidth="4" />
    <rect x="10" y="62" width="300" height="8" fill={P.w} />
    {ZONES.map((z) => {
      const [x, y] = ROOM[z];
      const open = z === "1";
      return <g key={z} data-zone={z} data-open={open}>
        <rect x={x} y={y} width="130" height="50" fill={open ? P.p : P.d} stroke={P.k} strokeWidth="4" opacity={open ? 1 : 0.85} />
        {!open && <rect x={x + 4} y={y + 4} width="122" height="42" fill={P.k} opacity="0.55" />}
      </g>;
    })}
    {book && <rect x="40" y="145" width="24" height="10" fill={P.y} stroke={P.k} strokeWidth="2" />}
    {table > 0 && <rect x="90" y="140" width="40" height="8" fill={P.o} stroke={P.k} strokeWidth="2" />}
    {table > 1 && <><rect x="96" y="132" width="10" height="8" fill={P.g} /><rect x="112" y="132" width="12" height="8" fill={P.r} /></>}
    <rect x="30" y="170" width="260" height="6" fill={P.w} />
  </svg>;
}

/** Nursery House meta-progress: four stage zones, only stage 1 open; items come from the passport only. */
export function NurseryHouse({ attempts, lessons = null }: { attempts: readonly Attempt[] | null; lessons?: readonly PassportLesson[] | null }) {
  const items = houseItems(attempts, lessons);
  return <section className="nh" aria-labelledby="nh-title">
    <h2 id="nh-title">{t("pixelHouse.title")}</h2>
    <p className="pf-muted">{t("pixelHouse.intro")}</p>
    <Art table={items.table} book={items.book} />
    <ul className="nh-list" aria-label={t("pixelHouse.zonesLabel")}>
      {ZONES.map((z) => {
        const open = z === "1";
        return <li key={z} className="nh-zone" data-open={open}>
          <strong>{t(`pixelHouse.zones.${z}`)}</strong> <span className="nh-state">{t(open ? "pixelHouse.open" : "pixelHouse.locked")}</span>
          {open && <>
            {" "}<Link href="/learn/1">{t("pixelHouse.openZone")}{t("pixelHouse.zones.1")}</Link>
            <ul>
              <li>{t("pixelHouse.items.book")}: {t(items.book ? "pixelHouse.itemState.have" : "pixelHouse.itemState.book")}</li>
              <li>{t("pixelHouse.items.table")}: {items.table === 0 ? t("pixelHouse.itemState.table")
                : `${t("pixelHouse.itemState.have")}${items.table === 1 ? ` (${t("pixelHouse.itemState.tableMore")})` : ""}`}</li>
            </ul>
          </>}
        </li>;
      })}
    </ul>
  </section>;
}
