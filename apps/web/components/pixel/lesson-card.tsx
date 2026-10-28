"use client";

import { useCallback, useState } from "react";

import { t } from "@/lib/i18n";
import type { Hotspot, SourceRef } from "@/lib/v2-api";

import { ART, type ArtKind } from "./lesson-art";
import { LessonSheet } from "./lesson-sheet";
import { Sprite } from "./sprite";

export type Card = { key: string; heading: string; text: string; art: ArtKind; sources: SourceRef[]; hotspots: Hotspot[] };

function Check() {
  return <svg className="pl-check" viewBox="0 0 7 6" width="14" height="12" shapeRendering="crispEdges" aria-hidden="true">
    {[[5, 0], [4, 1], [3, 2], [0, 3], [2, 3], [1, 4]].map(([x, y]) => <rect key={`${x}${y}`} x={x} y={y} width="1" height="1" fill="currentColor" />)}
  </svg>;
}

const Sources = ({ list, full }: { list: SourceRef[]; full: boolean }) => <ul className="pl-sources" aria-label={t("pixelLesson.source")}>
  {list.map((s) => <li key={`${s.source_id}:${s.locator}`}>{s.source_id}{full ? ` · ${s.title}` : ""}{s.locator ? ` · ${s.locator}` : ""}</li>)}
</ul>;

/** Cards without hotspots (lens cards, other units): the original toggle-the-picture card. */
function PlainCard({ card }: { card: Card }) {
  const art = ART[card.art];
  const [on, setOn] = useState<boolean[]>(() => Array(art.taps).fill(false));
  return <article className="pl-card" aria-label={card.heading}>
    <div className="pl-art"><Sprite frames={[art.draw(on)]} scale={3} /></div>
    <div className="pl-taps" role="group" aria-label={t("pixelLesson.illustration")}>
      {on.map((v, i) => <button key={i} type="button" className="pl-btn pl-tap" aria-pressed={v}
        onClick={() => setOn(on.map((x, j) => (j === i ? !x : x)))}>{t(`pixelLesson.tap_${card.art}_${i}`)}</button>)}
    </div>
    <p className="pl-text">{card.text}</p>
    {card.sources.length > 0 && <Sources list={card.sources} full={false} />}
  </article>;
}

/** Tap a spot: it lights up in the picture and a short explanation opens in a sheet. The full claim and sources stay one tap away. */
function SpotCard({ card }: { card: Card }) {
  const art = ART[card.art];
  const spots = card.hotspots;
  const [lit, setLit] = useState<boolean[]>(() => Array(art.taps).fill(false));
  const [seen, setSeen] = useState<ReadonlySet<number>>(new Set());
  const [open, setOpen] = useState<number | "sources" | null>(null);
  const [more, setMore] = useState(false);
  const closeSheet = useCallback(() => setOpen(null), []);
  const tapSpot = (i: number) => { setLit((cur) => cur.map((x, j) => x || j === i)); setSeen(new Set(seen).add(i)); setOpen(i); };
  const spot = typeof open === "number" ? spots[open] : undefined;
  return <article className="pl-card" aria-label={card.heading}>
    <div className="pl-art"><Sprite frames={[art.draw(lit)]} scale={3} /></div>
    <p className="pl-hint">{t("pixelLesson.spotsHint")} ({t("pixelLesson.spotsSeen")} {seen.size} {t("pixelLesson.cardOfSep")} {spots.length})</p>
    <div className="pl-taps" role="group" aria-label={t("pixelLesson.illustration")}>
      {spots.map((h, i) => <button key={h.id} type="button" className="pl-btn pl-tap" aria-haspopup="dialog" data-sparkle={!seen.has(i)} onClick={() => tapSpot(i)}>
        {h.label_th}{seen.has(i) && <><Check /><span className="pl-sr">{t("pixelLesson.explored")}</span></>}
      </button>)}
    </div>
    <div className="pl-extra">
      <button type="button" className="pl-btn" aria-expanded={more} onClick={() => setMore(!more)}>{more ? t("pixelLesson.readLess") : t("pixelLesson.readMore")}</button>
      {card.sources.length > 0 && <button type="button" className="pl-btn" aria-haspopup="dialog" onClick={() => setOpen("sources")}>
        <span aria-hidden="true">ⓘ </span>{t("pixelLesson.sourcesBtn")}
      </button>}
    </div>
    {more && <p className="pl-text">{card.text}</p>}
    {spot && <LessonSheet titleId="pl-sheet-title" onClose={closeSheet}>
      <h2 id="pl-sheet-title" className="pl-sheet-title">{spot.label_th}</h2>
      <p className="pl-sheet-text">{spot.text_th}</p>
    </LessonSheet>}
    {open === "sources" && <LessonSheet titleId="pl-sheet-title" onClose={closeSheet}>
      <h2 id="pl-sheet-title" className="pl-sheet-title">{t("pixelLesson.sourcesTitle")}</h2>
      <Sources list={card.sources} full />
    </LessonSheet>}
  </article>;
}

export const StoryCard = ({ card }: { card: Card }) => card.hotspots.length > 0 ? <SpotCard card={card} /> : <PlainCard card={card} />;
