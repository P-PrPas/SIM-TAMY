"use client";

import { FamilyArtwork, FamilyIcon } from "./family-art";
import { t } from "@/lib/i18n";

/** A public conversation cue, never a visualization of risk or correctness. */
export function PracticeStage({ chapter, speaker, family = false, grandmother = false, sceneKey }: {
  chapter: string; speaker: string; family?: boolean; grandmother?: boolean; sceneKey?: string;
}) {
  return <details open className={`practice-stage ${family ? "is-family" : "is-conversation"}`}>
    <summary><span><FamilyIcon name="chat" />{t("experience.scene")}</span><FamilyIcon name="chevron" /></summary>
    <div className="practice-stage-scene" key={sceneKey ?? chapter}>
      <div className="practice-stage-window" aria-hidden="true"><span /><i /><i /><i /></div>
      <div className="practice-stage-art" aria-hidden="true">{family ? <FamilyArtwork grandmother={grandmother} /> : <svg viewBox="0 0 280 180" fill="none">
        <path d="M32 174v-44a43 43 0 0 1 86 0v44M166 174v-44a43 43 0 0 1 86 0v44" fill="var(--color-brand-900)" />
        <circle cx="75" cy="66" r="27" fill="var(--color-brand-200)" /><circle cx="209" cy="66" r="27" fill="var(--color-brand-200)" />
        <path d="M50 59c-1-38 52-38 51 0-20-13-31-13-51 0M184 59c-1-38 52-38 51 0-20-13-31-13-51 0" fill="var(--color-brand-950)" />
        <path d="M120 54h42v28h-17l-10 9V82h-15Z" fill="var(--color-gold)" /><path d="M133 67h16" stroke="var(--color-brand-900)" strokeWidth="3" />
        <path d="M65 76q10 5 20 0m114 0q10 5 20 0" stroke="var(--color-brand-800)" strokeWidth="2" />
        <path d="M15 174h250" stroke="var(--color-brand-300)" strokeWidth="2" />
      </svg>}</div>
      <div className="practice-stage-caption"><p>{chapter}</p><span className="practice-speaker"><FamilyIcon name="chat" /><span>{t("experience.speaker")}<strong>{speaker}</strong></span></span></div>
    </div>
  </details>;
}
