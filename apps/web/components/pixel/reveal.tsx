"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import type { components } from "@/lib/api/schema";
import { t } from "@/lib/i18n";

import "./house.css";

type Evidence = components["schemas"]["FamilyEvidence"];
type Meter = "heart" | "clear" | "safe";

/** Which meters one committed choice fills. Empty = a still-open opportunity, never a penalty. */
export function metersFor(e: Pick<Evidence, "skills" | "dimension">): Meter[] {
  const skills = e.skills ?? [];
  const out: Meter[] = [];
  if (skills.includes("communication") || skills.includes("support")) out.push("heart");
  if (e.dimension === "evidence_scope" || skills.includes("responsibility")) out.push("clear");
  if (skills.includes("safety")) out.push("safe");
  return out;
}

const LABEL: Record<Meter, string> = { heart: "pixelHouse.reveal.meterHeart", clear: "pixelHouse.reveal.meterClear", safe: "pixelHouse.reveal.meterSafe" };
const calm = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Post-completion replay of each committed choice; a visual reflection of the report, not a score. */
export function HouseReveal({ evidence, safetyStatus }: { evidence: readonly Evidence[]; safetyStatus: string }) {
  const beats = evidence.filter((e) => e.kind !== "discover").map((e) => ({ e, meters: metersFor(e) }));
  const meters: Meter[] = evidence.some((e) => e.critical) ? ["heart", "clear", "safe"] : ["heart", "clear"];
  const reduced = useSyncExternalStore(() => () => {}, calm, () => false);
  const [step, setShown] = useState(0);
  const shown = reduced ? beats.length : step;
  useEffect(() => {
    if (shown >= beats.length) return;
    const id = setTimeout(() => setShown((n) => n + 1), 1200);
    return () => clearTimeout(id);
  }, [shown, beats.length]);

  const done = shown >= beats.length;
  const seen = beats.slice(0, shown);
  const current = shown > 0 ? beats[shown - 1] : undefined;
  const items = seen.filter((b) => b.meters.length > 0).length;
  return <section className="nr" aria-labelledby="nr-title">
    <h2 id="nr-title">{t("pixelHouse.reveal.title")}</h2>
    <p className="pf-muted">{t("pixelHouse.reveal.note")}</p>
    <div className="nr-meters">{meters.map((m) => <div key={m} className="nr-meter" data-meter={m}>
      <span>{t(LABEL[m])}</span>
      <span className="nr-cells" aria-hidden="true">{beats.map((b, i) =>
        <span key={i} className="nr-cell" data-on={i < shown && b.meters.includes(m)} />)}</span>
    </div>)}</div>
    <p className="pf-muted">{t("pixelHouse.reveal.table")}</p>
    <div className="nr-table" aria-hidden="true">{Array.from({ length: items }, (_, i) => <span key={i} className="nr-item" />)}</div>
    <div className="nr-beat" aria-live="polite">
      {current && <p>{t("pixelHouse.reveal.step")} {current.e.idx}: {current.e.text_th}
        {current.meters.length === 0 && <> <strong>{t("pixelHouse.reveal.open")}</strong></>}
        {current.meters.map((m) => <span key={m}> {t(LABEL[m])}</span>)}</p>}
      {done && <p data-final>{t(safetyStatus === "SAFETY_NOT_MET" ? "pixelHouse.reveal.finalReview" : "pixelHouse.reveal.finalMet")}</p>}
    </div>
    {!done && <button type="button" className="family-button-light" onClick={() => setShown(beats.length)}>{t("pixelHouse.reveal.skip")}</button>}
  </section>;
}
