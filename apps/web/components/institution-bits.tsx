"use client";

import { isForbidden } from "@/lib/use-load";
import { t } from "@/lib/i18n";

export function LoadState({
  error,
  loading,
  onRetry,
}: {
  error: Error | null;
  loading: boolean;
  onRetry: () => void;
}) {
  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-red-800 bg-red-50 p-4 text-red-950">
        <p>{isForbidden(error) ? t("institution.forbidden") : t("institution.loadError")}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-11 rounded-lg border border-red-900 px-4 font-semibold"
        >
          {t("institution.retry")}
        </button>
      </div>
    );
  }
  return loading ? <p aria-live="polite">{t("institution.loading")}</p> : null;
}

export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-2xl border border-stone-300 bg-white p-4">
      <dt className="text-stone-700">{label}</dt>
      <dd className="mt-1 text-3xl font-bold text-stone-950">{value}</dd>
      {hint && <p className="mt-1 text-sm text-stone-700">{hint}</p>}
    </div>
  );
}

export const button =
  "inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-900 px-5 font-semibold text-white disabled:opacity-50";
export const field = "mt-2 min-h-11 w-full rounded-lg border border-stone-500 bg-white px-3";
