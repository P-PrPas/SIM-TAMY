"use client";

import { useMemo, useState } from "react";

import { t } from "@/lib/i18n";
import type { UnitDetail } from "@/lib/v2-api";

import "./lesson.css";
import { CELEBRATE } from "./lesson-art";
import { Sprite } from "./sprite";

export type Bin = "tradition" | "scope";
export type SortItem = { id: string; text: string; bin: Bin };

/** Items come from claim `type` and the lens; text is verbatim. Other claim types are left out. */
export function buildSortItems(unit: UnitDetail): SortItem[] {
  const items: SortItem[] = [];
  for (const c of unit.claims) {
    // TODO(content): claim types other than tradition/scope are not sortable yet; the Content team may add short `sort_items_th` statements later.
    if (c.type === "tradition" || c.type === "scope") items.push({ id: c.id, text: c.text_th, bin: c.type });
  }
  if (unit.lens) {
    items.push({ id: "lens-safety", text: unit.lens.safety_th, bin: "scope" });
    items.push({ id: "lens-rights", text: unit.lens.rights_th, bin: "scope" });
  }
  return items;
}

/** The game needs both bins to hold something, otherwise there is nothing to decide. */
export const isSortable = (items: readonly SortItem[]) =>
  items.some((i) => i.bin === "scope") && items.some((i) => i.bin === "tradition");

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = Math.imul(a ^ (a >>> 15), 1 | a);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
const hash = (s: string) => [...s].reduce((h, ch) => Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0, 2166136261);

/** Deterministic Fisher-Yates: same unit id and attempt always give the same order. */
export function seededOrder<T>(list: readonly T[], seed: string): T[] {
  const rand = mulberry32(hash(seed));
  const out = [...list];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

const binLabel = (b: Bin) => t(b === "scope" ? "pixelLesson.binScope" : "pixelLesson.binTradition");

export function LessonSort({ unit, items, attempt = 0, onDone }: {
  unit: UnitDetail; items: readonly SortItem[]; attempt?: number; onDone?: (correct: number, total: number) => void;
}) {
  const [round, setRound] = useState(attempt);
  const order = useMemo(() => seededOrder(items, `${unit.id}:${round}`), [items, unit.id, round]);
  const [placed, setPlaced] = useState<Record<string, boolean>>({});
  const [picked, setPicked] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const pending = order.filter((i) => !(i.id in placed));
  const correct = Object.values(placed).filter(Boolean).length;
  const finished = pending.length === 0;

  const drop = (bin: Bin) => {
    const item = pending.find((i) => i.id === picked);
    if (!item) return;
    const ok = item.bin === bin;
    const next = { ...placed, [item.id]: ok };
    setPlaced(next);
    setPicked(null);
    setFeedback(ok ? t("pixelLesson.correct") : `${t("pixelLesson.miss")} ${binLabel(item.bin)}`);
    if (Object.keys(next).length === order.length) onDone?.(Object.values(next).filter(Boolean).length, order.length);
  };

  return <section className="pl-sort" aria-labelledby="pl-sort-title">
    <h2 id="pl-sort-title">{t("pixelLesson.sortTitle")}</h2>
    {finished ? <div className="pl-finish">
      <Sprite frames={CELEBRATE} scale={3} fps={2} />
      <h3>{t("pixelLesson.doneTitle")}</h3>
      <p>{t("pixelLesson.result")} {correct} {t("pixelLesson.resultOf")} {order.length}</p>
      <button type="button" className="pl-btn" onClick={() => { setRound(round + 1); setPlaced({}); setPicked(null); setFeedback(""); }}>
        {t("pixelLesson.again")}
      </button>
    </div> : <>
      <p className="pl-hint">{t("pixelLesson.sortHint")}</p>
      <div className="pl-bins">
        {(["tradition", "scope"] as const).map((b) =>
          <button key={b} type="button" className="pl-btn pl-bin" disabled={!picked} onClick={() => drop(b)}>{binLabel(b)}</button>)}
      </div>
      <p className="pl-feedback" role="status" aria-live="polite">{feedback}</p>
      <h3 className="pl-sub">{t("pixelLesson.pending")} {pending.length}</h3>
      <ul className="pl-pile">
        {pending.map((i) => <li key={i.id}>
          <button type="button" className="pl-btn pl-item" aria-pressed={picked === i.id} onClick={() => setPicked(picked === i.id ? null : i.id)}>
            {i.text}
          </button>
        </li>)}
      </ul>
    </>}
  </section>;
}
