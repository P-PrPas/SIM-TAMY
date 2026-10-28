"use client";

import { useEffect, useRef, useState } from "react";

import { t } from "@/lib/i18n";
import type { SourceRef, UnitDetail } from "@/lib/v2-api";

import "./lesson.css";
import { ART, claimArt, type ArtKind } from "./lesson-art";
import { buildSortItems, isSortable, LessonSort } from "./lesson-sort";
import { Sprite } from "./sprite";

type Card = { key: string; heading: string; text: string; art: ArtKind; sources: SourceRef[] };

/** One card per claim in order, then the lens parts. Text is passed through untouched. */
export function buildCards(unit: UnitDetail): Card[] {
  const cards: Card[] = unit.claims.map((c, i) => ({ key: c.id, heading: c.id, text: c.text_th, art: claimArt(unit.id, i), sources: c.sources }));
  if (unit.lens) {
    for (const [k, text] of [["wisdom", unit.lens.wisdom_th], ["safety", unit.lens.safety_th], ["rights", unit.lens.rights_th]] as const) {
      cards.push({ key: `lens-${k}`, heading: t(`platform.knowledge.lens${k[0]!.toUpperCase()}${k.slice(1)}`), text, art: k, sources: [] });
    }
  }
  return cards;
}

function StoryCard({ card }: { card: Card }) {
  const art = ART[card.art];
  const [on, setOn] = useState<boolean[]>(() => Array(art.taps).fill(false));
  return <article className="pl-card" aria-label={card.heading}>
    <div className="pl-art"><Sprite frames={[art.draw(on)]} scale={3} /></div>
    <div className="pl-taps" role="group" aria-label={t("pixelLesson.illustration")}>
      {on.map((v, i) => <button key={i} type="button" className="pl-btn pl-tap" aria-pressed={v}
        onClick={() => setOn(on.map((x, j) => (j === i ? !x : x)))}>{t(`pixelLesson.tap_${card.art}_${i}`)}</button>)}
    </div>
    <p className="pl-text">{card.text}</p>
    {card.sources.length > 0 && <ul className="pl-sources" aria-label={t("pixelLesson.source")}>
      {card.sources.map((s) => <li key={`${s.source_id}:${s.locator}`}>{s.source_id}{s.locator ? ` · ${s.locator}` : ""}</li>)}
    </ul>}
  </article>;
}

/** Story cards, then the sort game when the unit has both kinds of statements. `onComplete` fires once at the end. */
export function PixelLesson({ unit, onComplete }: { unit: UnitDetail; onComplete?: () => void }) {
  const cards = buildCards(unit);
  const items = buildSortItems(unit);
  const game = isSortable(items);
  const [i, setI] = useState(0);
  const [phase, setPhase] = useState<"cards" | "sort" | "done">("cards");
  const fired = useRef(false);
  const complete = () => { if (!fired.current) { fired.current = true; onComplete?.(); } };
  useEffect(() => { if (phase === "done") complete(); });

  if (cards.length === 0) return null;
  if (phase === "sort") return <LessonSort unit={unit} items={items} onDone={() => setPhase("done")} />;
  if (phase === "done") return <p className="pl-complete" role="status">{t("pixelLesson.lessonDone")}</p>;

  const last = i === cards.length - 1;
  return <section className="pl-lesson" aria-roledescription="carousel" aria-label={unit.title_th}
    onKeyDown={(e) => { if (e.key === "ArrowRight" && !last) setI(i + 1); if (e.key === "ArrowLeft" && i > 0) setI(i - 1); }}>
    <p className="pl-count" aria-live="polite">{t("pixelLesson.cardOf")} {i + 1} {t("pixelLesson.cardOfSep")} {cards.length}</p>
    <StoryCard key={cards[i]!.key} card={cards[i]!} />
    <ol className="pl-dots" aria-label={t("pixelLesson.progress")}>
      {cards.map((c, j) => <li key={c.key} className="pl-dot" aria-current={j === i ? "step" : undefined} data-done={j <= i} />)}
    </ol>
    <div className="pl-nav">
      <button type="button" className="pl-btn" disabled={i === 0} onClick={() => setI(i - 1)}>{t("pixelLesson.prev")}</button>
      <button type="button" className="pl-btn pl-primary" onClick={() => (!last ? setI(i + 1) : game ? setPhase("sort") : setPhase("done"))}>
        {!last ? t("pixelLesson.next") : game ? t("pixelLesson.toGame") : t("pixelLesson.finish")}
      </button>
    </div>
  </section>;
}
