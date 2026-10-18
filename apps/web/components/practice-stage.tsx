"use client";

import { FamilyArtwork, FamilyIcon } from "./family-art";
import { t } from "@/lib/i18n";

/** A public conversation cue, never a visualization of risk or correctness. */
export function PracticeStage({ chapter, speaker, family = false, grandmother = false, sceneIndex = 0 }: {
  chapter: string; speaker: string; family?: boolean; grandmother?: boolean; sceneIndex?: number;
}) {
  return <details open className={`practice-stage ${family ? "is-family" : "is-conversation"}`}>
    <summary><span><FamilyIcon name="chat" />{t("experience.scene")}</span><FamilyIcon name="chevron" /></summary>
    <div className={`practice-stage-scene scene-variation-${sceneIndex % 3}`} key={chapter}>
      <div className="practice-stage-window" aria-hidden="true"><span /><i /><i /><i /></div>
      <svg className="practice-stage-props" viewBox="0 0 150 150" aria-hidden="true" fill="none">
        {sceneIndex % 3 === 1 ? <><path d="M45 128h65M78 128V65M47 65h62L94 25H63Z" fill="var(--color-brand-200)" stroke="var(--color-brand-700)" strokeWidth="3" /><circle cx="79" cy="70" r="8" fill="var(--color-gold)" /></> : <><path d="M25 100h100M40 100v35m70-35v35" stroke="var(--color-brand-700)" strokeWidth="4" /><path d="M52 75h22v20H52Zm45-20v40m-5-32c-15-14-4-25 5-12 8-13 20-2 5 12" fill="var(--color-brand-200)" stroke="var(--color-brand-700)" strokeWidth="2" /></>}
      </svg>
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
