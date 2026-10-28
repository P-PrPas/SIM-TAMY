"use client";

import { useCallback, useEffect, useState } from "react";

import { V2ApiError } from "./v2-api";

export type Loaded<T> = { data: T | null; error: V2ApiError | null; loading: boolean; reload: () => void };

type Result<T> = { id: string; data: T | null; error: V2ApiError | null };

/**
 * Runs `load` on mount and whenever `key` changes or `reload()` is called; `load === null` means "nothing to fetch".
 * State is only set from the async callbacks; "loading" is derived (the stored result belongs to another request).
 */
export function useV2<T>(load: ((signal: AbortSignal) => Promise<T>) | null, key: string): Loaded<T> {
  const [tick, setTick] = useState(0);
  const [result, setResult] = useState<Result<T> | null>(null);
  const reload = useCallback(() => setTick((n) => n + 1), []);
  const id = `${key}#${tick}`;
  const enabled = load !== null;

  useEffect(() => {
    if (!load) return;
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => setResult({ id, data, error: null }))
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setResult({ id, data: null, error: e instanceof V2ApiError ? e : new V2ApiError("UNKNOWN", 0) });
      });
    return () => controller.abort();
    // `load` is recreated each render; `id` decides when to refetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, enabled]);

  const current = enabled && result?.id === id ? result : null;
  return { data: current?.data ?? null, error: current?.error ?? null, loading: enabled && current === null, reload };
}
