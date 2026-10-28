"use client";

import type { ReactNode } from "react";

import { t } from "@/lib/i18n";
import type { Loaded } from "@/lib/use-v2";

/** Thai label for an enum value, falling back to the raw value when the namespace has no entry. */
export function labelOr(key: string, fallback: string): string {
  try { return t(key); } catch { return fallback; }
}

export function DemoBadge() {
  return <span className="pf-badge">{t("platform.common.demoBadge")}</span>;
}

/** Loading / error-with-retry wrapper around a `useV2` result. */
export function Async<T>({ r, children }: { r: Loaded<T>; children: (data: T) => ReactNode }) {
  if (r.loading) return <p role="status" className="pf-note">{t("platform.common.loading")}</p>;
  if (r.error || r.data === null) {
    return <div role="alert" className="pf-alert">
      <p>{t("platform.common.loadError")}</p>
      <button type="button" onClick={r.reload} className="pf-btn">{t("platform.common.retry")}</button>
    </div>;
  }
  return <>{children(r.data)}</>;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("th-TH", { dateStyle: "medium", timeZone: "Asia/Bangkok" });
}
