// ponytail: prototype identity (ADR-15). The picked mock account rides along as a header, no auth.
const KEY = "sim-tamy-demo-account";

export function getDemoAccount(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.localStorage.getItem(KEY) ?? undefined;
}

export function setDemoAccount(accountId: string | null): void {
  if (accountId) window.localStorage.setItem(KEY, accountId);
  else window.localStorage.removeItem(KEY);
}
