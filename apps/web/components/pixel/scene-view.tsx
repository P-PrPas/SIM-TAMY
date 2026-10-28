"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

import { t } from "@/lib/i18n";
import { BACKDROPS, CARD, CARD_SLOTS, CHAR_H, CHAR_W, HEART, ITEMS, NOTEBOOK, SCENE_H, SCENE_W, THINK, characterFrames, itemShownOn } from "./scene-art";
import type { Backdrop, CharacterKey, ItemKey, Mood } from "./scene-art";
import { PALETTE, Sprite } from "./sprite";
import "./scene.css";

export type SceneCard = { id: string; source_id: string; title: string };

const NOTEBOOK_AT = [290, 148] as const;
const LEFT_X = 40, SPEAKER_X = 248, TOP = 100;

/** Speaker display name (from the story) to sprite. Unknown speakers get the neutral sprite. */
export function characterOf(name: string): CharacterKey {
  const known: [string, CharacterKey][] = [["ploy", "ploy"], ["ton", "ton"], ["teacher", "teacher"], ["mom", "mom"], ["mali", "mali"], ["non", "non"],
    ["yai", "yai"], ["yaisai", "yai"], ["counselor", "counselor"], ["pair", "ton"]];
  return known.find(([key]) => t(`pixelSim.name.${key}`) === name)?.[1] ?? "neutral";
}

const fill = (text: string, values: Record<string, string>) =>
  Object.entries(values).reduce((out, [k, v]) => out.replaceAll(`{${k}}`, v), text);

function Rects({ rects }: { rects: readonly (readonly [number, number, number, number, string])[] }) {
  return <>{rects.map(([x, y, w, h, k], i) => <rect key={i} x={x} y={y} width={w} height={h} fill={PALETTE[k]} />)}</>;
}

/**
 * Living pixel scene: 320x180 logical px, integer-scaled to the container. Decorative only (aria-hidden);
 * every visual change is also written in the sr-only status line and the notebook list.
 */
export function PixelScene({ speaker, backdrop, talking = false, mood = null, cards = [], items = [], beat = false, compact = false, scale: fixed, left = "ploy", children }: {
  speaker: string; backdrop: Backdrop; talking?: boolean; mood?: Mood | null; cards?: readonly SceneCard[];
  /** Stage mode: props on the table, the consequence beat, no notebook list below (HUD has it), overlay children. */
  items?: readonly ItemKey[]; beat?: boolean; compact?: boolean; children?: ReactNode;
  /** Integer scale chosen by the caller (the stage lays out around it); omit to fit the container. */
  scale?: number;
  /** The character on the left (the player's side); see cast.ts. */
  left?: CharacterKey;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(1);
  const scale = fixed ?? fit;
  const [initial] = useState(cards.length);
  useEffect(() => {
    const el = box.current;
    if (fixed !== undefined || !el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setFit(Math.min(4, Math.max(1, Math.floor((el.clientWidth - 8) / SCENE_W)))));
    observer.observe(el);
    return () => observer.disconnect();
  }, [fixed]);

  const who = characterOf(speaker);
  const slots = CARD_SLOTS[backdrop] ?? [];
  const state = mood ?? (talking ? "talk" : "idle");
  const latest = cards.at(-1);
  const flying = cards.length > initial ? latest : undefined;
  const name = speaker || t(`pixelSim.name.${who}`);
  const leftName = t(`pixelSim.name.${left}`);
  const announce = [
    fill(t("pixelSim.sr.scene"), { backdrop: t(`pixelSim.backdrop.${backdrop}`), left: leftName, speaker: name }),
    mood && fill(t(`pixelSim.sr.${mood}`), { speaker: name }),
    latest && fill(t("pixelSim.sr.card"), { source: latest.source_id }),
  ].filter(Boolean).join(" ");
  const fly = { "--dx": `${NOTEBOOK_AT[0] - SPEAKER_X}px`, "--dy": `${NOTEBOOK_AT[1] - TOP}px` } as CSSProperties;

  return <section ref={box} className="pixel-scene-wrap">
    <p className="sr-only" role="status">{announce}</p>
    <div className="pixel-stage-frame" style={{ width: SCENE_W * scale + 8 }}>
    <div className={`pixel-scene ${beat ? "is-beat" : ""}`} aria-hidden="true" style={{ height: SCENE_H * scale }}>
      <div className="pixel-scene-stage" data-backdrop={backdrop} style={{ width: SCENE_W, height: SCENE_H, transform: `scale(${scale})` }}>
        <svg width={SCENE_W} height={SCENE_H} viewBox={`0 0 ${SCENE_W} ${SCENE_H}`} shapeRendering="crispEdges"><Rects rects={BACKDROPS[backdrop]} /></svg>
        <span className="pixel-prop" style={{ left: NOTEBOOK_AT[0], top: NOTEBOOK_AT[1] }}><Sprite frames={[NOTEBOOK]} scale={1} /></span>
        {cards.slice(0, slots.length).map((c, i) => <span key={c.id} className="pixel-prop" style={{ left: slots[i]![0], top: slots[i]![1] }}><Sprite frames={[CARD]} scale={1} /></span>)}
        {items.map((k, i) => itemShownOn(k, backdrop) && <span key={k} className={`pixel-prop pixel-item ${beat && i === items.length - 1 ? "is-new" : ""}`} style={{ left: ITEMS[k].at[0], top: ITEMS[k].at[1] }}><Sprite frames={[ITEMS[k].art]} scale={(ITEMS[k] as { scale?: number }).scale ?? 1} /></span>)}
        <span className={`pixel-char ${mood ? `is-${mood}` : ""}`} data-who={left} style={{ left: LEFT_X, top: TOP, width: CHAR_W, height: CHAR_H }}>
          <Sprite key={mood ?? "idle"} frames={characterFrames(left, mood ?? "idle")} scale={1} fps={2} />
        </span>
        <span className={`pixel-char ${mood ? `is-${mood} is-speaker` : ""}`} data-who={who} data-state={state} style={{ left: SPEAKER_X, top: TOP, width: CHAR_W, height: CHAR_H }}>
          <Sprite key={state} frames={characterFrames(who, state)} scale={1} fps={state === "talk" ? 4 : 2} />
        </span>
        {mood === "warm" && <span className="pixel-prop pixel-heart" style={{ left: SPEAKER_X + 10, top: TOP - 12 }}><Sprite frames={[HEART]} scale={1} /></span>}
        {mood === "open" && <span className="pixel-prop" style={{ left: SPEAKER_X - 6, top: TOP - 14 }}><Sprite frames={[THINK]} scale={1} /></span>}
        {flying && <span key={flying.id} className="pixel-prop pixel-fly" style={{ left: SPEAKER_X + 12, top: TOP + 10, ...fly }}><Sprite frames={[CARD]} scale={1} /></span>}
      </div>
    </div>
    {children && <div className="pixel-overlay">{children}</div>}
    </div>
    {!compact && <section className="pixel-notebook" aria-label={t("pixelSim.notebook.title")}>
      <h3>{t("pixelSim.notebook.title")}</h3>
      {cards.length === 0 ? <p>{t("pixelSim.notebook.empty")}</p> : <ul>
        {cards.map((c) => <li key={c.id}><span className="family-source-category">{c.source_id}</span> {c.title}</li>)}
      </ul>}
    </section>}
  </section>;
}
