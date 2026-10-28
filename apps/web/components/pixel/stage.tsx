"use client";

import { useEffect, useRef, useState, type ComponentProps, type CSSProperties, type ReactNode } from "react";

import { t } from "@/lib/i18n";
import { Typed, type Say } from "../family-chat";
import { NOTEBOOK, SCENE_H, SCENE_W } from "./scene-art";
import { PixelScene } from "./scene-view";
import { Sprite } from "./sprite";

/** Consequence beat text: the chosen sentence and the character's reply. */
export type BeatLines = { you: string; reply: string };

const FRAME = 8, GAP = 24, PANEL_MIN = 360;

/**
 * Integer scale that fits, and whether the dialogue panel can sit beside the scene. The scene only goes
 * side by side when it can still be drawn at 2x or more next to a readable panel; otherwise the panel
 * stacks under it at the scene's width.
 */
export function stageLayout(width: number) {
  const wide = width >= SCENE_W * 2 + FRAME + GAP + PANEL_MIN;
  const room = wide ? width - GAP - PANEL_MIN : width;
  return { wide, scale: Math.min(4, Math.max(1, Math.floor((room - FRAME) / SCENE_W))) };
}

/**
 * Visual-first stage (LP-01): the scene is the page and the dialogue lives in a panel docked beside it
 * (under it on phones). The HUD on the scene holds step pips, the notebook and leave; `children` (chat bar,
 * choice cards) render inside the panel so reading and answering happen in one place. Art stays
 * aria-hidden; every HUD item has a text equivalent.
 */
export function PixelStage({ scene, step, prompt, say, beat, onTalking, onSkip, done, total, onLeave, leaveDisabled, children }: {
  scene: Omit<ComponentProps<typeof PixelScene>, "compact" | "children" | "beat" | "scale">;
  step: string; prompt: string; say: Say | null; beat: BeatLines | null;
  onTalking: (talking: boolean) => void; onSkip: () => void;
  done: number; total: number; onLeave: () => void; leaveDisabled: boolean; children?: ReactNode;
}) {
  const root = useRef<HTMLDivElement>(null);
  const focus = useRef<HTMLDivElement>(null);
  const mounted = useRef(false);
  const [width, setWidth] = useState(0);
  const cards = scene.cards ?? [];
  useEffect(() => {
    const el = root.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setWidth(el.clientWidth));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  // Move focus to the speaking line when the step changes or a beat starts/ends (not on first paint).
  useEffect(() => {
    if (mounted.current) focus.current?.focus();
    mounted.current = true;
  }, [step, Boolean(beat)]); // eslint-disable-line react-hooks/exhaustive-deps

  const { wide, scale } = stageLayout(width);
  const sceneWidth = SCENE_W * scale + FRAME;
  const you = beat ? beat.you : say?.you ?? null;
  const line = beat ? beat.reply : say?.reply ? say.reply.text : say?.typing ? null : prompt;
  return <div ref={root} className={wide ? "pixel-stage is-wide" : "pixel-stage"}
    style={{ "--stage-w": `${sceneWidth}px`, "--stage-h": `${SCENE_H * scale + FRAME}px`, ...(wide ? { gridTemplateColumns: `${sceneWidth}px minmax(0, 1fr)` } : {}) } as CSSProperties}>
    <PixelScene {...scene} beat={Boolean(beat)} compact scale={scale}>
      <div className="pixel-hud">
        <p className="sr-only">{done} / {total} {t("family.decisions")}</p>
        <ol className="pixel-pips" aria-hidden="true">
          {Array.from({ length: total }, (_, i) => <li key={i} className={i < done ? "is-done" : i === done ? "is-now" : ""} />)}
        </ol>
        <details className="pixel-hud-notebook">
          <summary aria-label={t("pixelSim.notebook.count").replace("{n}", String(cards.length))}>
            <Sprite frames={[NOTEBOOK]} scale={2} /><b aria-hidden="true">{cards.length}</b>
          </summary>
          <section aria-label={t("pixelSim.notebook.title")}>
            <h3>{t("pixelSim.notebook.title")}</h3>
            {cards.length === 0 ? <p>{t("pixelSim.notebook.empty")}</p> : <ul>
              {cards.map((c) => <li key={c.id}><span className="family-source-category">{c.source_id}</span> {c.title}</li>)}
            </ul>}
          </section>
        </details>
        <button type="button" className="pixel-leave" onClick={onLeave} disabled={leaveDisabled} aria-label={t("family.leave")}><span aria-hidden="true">×</span></button>
      </div>
      {beat && <button type="button" className="pixel-skip" onClick={onSkip}>{t("pixelSim.skip")}</button>}
    </PixelScene>
    <div className="pixel-panel">
      {scene.speaker && <p className="pixel-nameplate">{scene.speaker}</p>}
      {you && <div className="pixel-line is-you"><strong>{t("lab.chat.you")}</strong><p>{you}</p></div>}
      <div ref={focus} className="pixel-line is-speaker" role="group" aria-label={t("pixelSim.stage")} tabIndex={0}>
        {line === null ? <p className="family-typing">{t("lab.chat.typing")}</p>
          : say?.reply && !beat && say.reply.fresh ? <Typed key={line} text={line} onTalking={onTalking} /> : <p>{line}</p>}
      </div>
      {children && <div className="pixel-panel-body">{children}</div>}
    </div>
  </div>;
}
