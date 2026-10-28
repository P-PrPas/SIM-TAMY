"use client";

import { useId, useState } from "react";

import { t } from "@/lib/i18n";
import { FamilyIcon } from "../family-art";
import { ICONS, type ChoiceIcon } from "./scene-art";
import { Sprite } from "./sprite";

export type CardChoice = { id: string; text_th: string; short_th?: string | null; icon?: ChoiceIcon | null };

/**
 * Choices as icon cards with a short label. Selecting one shows its full verbatim sentence before the
 * learner commits; the same sentence is the radio's accessible description (not hover-only).
 */
export function ChoiceCards({ choices, disabled, onCommit }: {
  choices: readonly CardChoice[]; disabled: boolean; onCommit: (id: string) => void;
}) {
  const name = useId();
  const [selected, setSelected] = useState("");
  const chosen = choices.find((c) => c.id === selected);
  return <form className="pixel-cards" onSubmit={(event) => { event.preventDefault(); if (selected && !disabled) onCommit(selected); }}>
    <fieldset disabled={disabled}>
      <legend>{t("pixelSim.choose")}</legend>
      <div className="pixel-card-list">
        {choices.map((c) => <div key={c.id} className="pixel-card-item"><label className={`pixel-card ${selected === c.id ? "is-selected" : ""}`}>
          <input type="radio" name={name} value={c.id} checked={selected === c.id} onChange={() => setSelected(c.id)}
            aria-describedby={c.short_th ? `${name}-${c.id}` : undefined} />
          <span className="pixel-card-icon" aria-hidden="true">{c.icon && <Sprite frames={[ICONS[c.icon]]} scale={3} />}</span>
          <span className="pixel-card-label">{c.short_th || c.text_th}</span>
        </label>{c.short_th && <span id={`${name}-${c.id}`} className="sr-only">{c.text_th}</span>}</div>)}
      </div>
      {chosen?.short_th && <p className="pixel-card-detail"><strong>{t("pixelSim.full")}</strong> {chosen.text_th}</p>}
    </fieldset>
    <button className="button-primary pixel-commit" type="submit" disabled={disabled || !selected}>{t("experience.commit")}<FamilyIcon name="arrow" /></button>
  </form>;
}
