"use client";

import { useMemo, useSyncExternalStore } from "react";
import { LOGIN_EVENT, LOGIN_KEY, readLogin } from "./demo-login";

const subscribe = (notify: () => void) => {
  window.addEventListener(LOGIN_EVENT, notify);
  window.addEventListener("storage", notify);
  return () => { window.removeEventListener(LOGIN_EVENT, notify); window.removeEventListener("storage", notify); };
};

export function useLogin() {
  const raw = useSyncExternalStore(subscribe, () => localStorage.getItem(LOGIN_KEY) ?? "", () => null);
  const account = useMemo(() => readLogin(raw), [raw]);
  return { account, ready: raw !== null };
}
