"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { t } from "@/lib/i18n";

/** Modal dialog (bottom sheet at phone width): focus moves in, Esc / close / backdrop close it, focus returns to the opener. */
export function LessonSheet({ titleId, onClose, children }: { titleId: string; onClose: () => void; children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); opener?.focus(); };
  }, [onClose]);
  const trap = (e: React.KeyboardEvent) => {
    e.stopPropagation(); // arrow keys must not turn the lesson card behind the sheet
    if (e.key !== "Tab") return;
    const items = [...(box.current?.querySelectorAll<HTMLElement>("button, a[href]") ?? [])];
    const first = items[0], last = items[items.length - 1];
    if (!first || !last) return;
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };
  return createPortal(
    <div className="pl-backdrop" onClick={onClose}>
      <div ref={box} className="pl-sheet" role="dialog" aria-modal="true" aria-labelledby={titleId} onClick={(e) => e.stopPropagation()} onKeyDown={trap}>
        {children}
        <button ref={close} type="button" className="pl-btn pl-primary" onClick={onClose}>{t("pixelLesson.close")}</button>
      </div>
    </div>,
    document.body,
  );
}
