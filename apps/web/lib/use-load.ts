import { useCallback, useEffect, useState } from "react";

import { ApiError } from "./api/client";

type Settled<T> = { id: string; data: T | null; error: Error | null };

/**
 * Load whenever `key` (or a reload) changes. A reply for an older key never shows: the result is
 * tagged with the request id it belongs to, so there is nothing to reset synchronously.
 */
export function useLoad<T>(load: () => Promise<T>, key: string) {
  const [tick, setTick] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const id = `${key}#${tick}`;

  useEffect(() => {
    let stale = false;
    load().then(
      (data) => !stale && setSettled({ id, data, error: null }),
      (cause: unknown) =>
        !stale &&
        setSettled({ id, data: null, error: cause instanceof Error ? cause : new Error("load failed") }),
    );
    return () => {
      stale = true;
    };
    // `load` is a fresh closure every render; `id` names everything it depends on
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const current = settled?.id === id ? settled : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    reload: useCallback(() => setTick((n) => n + 1), []),
  };
}

export function isForbidden(error: Error | null): boolean {
  return error instanceof ApiError && error.status === 403;
}
