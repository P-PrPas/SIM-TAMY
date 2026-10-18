"use client";

import { useId, useState } from "react";
import { FamilyIcon } from "./family-art";
import { t } from "@/lib/i18n";

export function PracticeChoice({ choices, disabled, onCommit }: {
  choices: readonly { id: string; text_th: string }[]; disabled: boolean; onCommit: (id: string) => void;
}) {
  const name = useId();
  const [selected, setSelected] = useState("");
  return <form className="practice-activity" onSubmit={(event) => { event.preventDefault(); if (selected && !disabled) onCommit(selected); }}>
    <fieldset disabled={disabled}><legend>{t("experience.activity")}</legend><p>{t("experience.chooseHelp")}</p>
      <div className="practice-options">{choices.map((choice) => <label key={choice.id} className={selected === choice.id ? "is-selected" : ""}>
        <input type="radio" name={name} value={choice.id} checked={selected === choice.id} onChange={() => setSelected(choice.id)} />
        <span>{choice.text_th}</span><FamilyIcon name={selected === choice.id ? "check" : "chat"} />
      </label>)}</div>
    </fieldset>
    <button className="button-primary practice-commit" type="submit" disabled={disabled || !selected}>{t("experience.commit")}<FamilyIcon name="arrow" /></button>
  </form>;
}
