"use client";

import { useEffect, useRef, type ComponentProps } from "react";

import { t } from "@/lib/i18n";
import { Typed, type Say } from "../family-chat";
import { NOTEBOOK } from "./scene-art";
import { PixelScene } from "./scene-view";
import { Sprite } from "./sprite";

/** Consequence beat text: the chosen sentence and the character's reply. */
export type BeatLines = { you: string; reply: string };

/**
 * Visual-first stage (LP-01): the scene is the page. Speech bubbles sit over the speakers, the HUD holds
 * step pips, the notebook and leave. Long text scrolls inside its bubble; the full text is also in the
 * aria-live regions of the caller. Art stays aria-hidden; every HUD item has a text equivalent.
 */
export function PixelStage({ scene, step, prompt, say, beat, onTalking, onSkip, done, total, onLeave, leaveDisabled }: {
  scene: Omit<ComponentProps<typeof PixelScene>, "compact" | "children" | "beat">;
  step: string; prompt: string; say: Say | null; beat: BeatLines | null;
  onTalking: (talking: boolean) => void; onSkip: () => void;
  done: number; total: number; onLeave: () => void; leaveDisabled: boolean;
}) {
  const focus = useRef<HTMLDivElement>(null);
  const mounted = useRef(false);
  const cards = scene.cards ?? [];
  // Move focus to the speaking bubble when the step changes or a beat starts/ends (not on first paint).
  useEffect(() => {
    if (mounted.current) focus.current?.focus();
    mounted.current = true;
  }, [step, Boolean(beat)]); // eslint-disable-line react-hooks/exhaustive-deps

  const you = beat ? beat.you : say?.you ?? null;
  const line = beat ? beat.reply : say?.reply ? say.reply.text : say?.typing ? null : prompt;
  return <PixelScene {...scene} beat={Boolean(beat)} compact>
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
    {you && <div className="pixel-bubble is-you"><p>{you}</p></div>}
    <div ref={focus} className="pixel-bubble is-speaker" role="group" aria-label={t("pixelSim.stage")} tabIndex={0}>
      {line === null ? <p className="family-typing">{t("lab.chat.typing")}</p>
        : say?.reply && !beat && say.reply.fresh ? <Typed key={line} text={line} onTalking={onTalking} /> : <p>{line}</p>}
    </div>
    {beat && <button type="button" className="pixel-skip" onClick={onSkip}>{t("pixelSim.skip")}</button>}
  </PixelScene>;
}
