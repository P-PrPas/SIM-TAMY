"use client";

import { useSyncExternalStore } from "react";

import { getDemoAccount, setDemoAccount } from "./demo-account";

const EVENT = "sim-tamy-demo-account";
const subscribe = (cb: () => void) => {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => { window.removeEventListener(EVENT, cb); window.removeEventListener("storage", cb); };
};

/** Picked mock account ID (ADR-15), or undefined. Re-renders every user when the profile changes. */
export function useDemoAccount(): string | undefined {
  return useSyncExternalStore(subscribe, getDemoAccount, () => undefined);
}

export function pickDemoAccount(id: string | null) {
  setDemoAccount(id);
  window.dispatchEvent(new Event(EVENT));
}
