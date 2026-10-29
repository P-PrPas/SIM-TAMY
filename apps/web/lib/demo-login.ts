import { setDemoAccount } from "./demo-account";
import type { DemoAccount } from "./v2-api";

export const LOGIN_KEY = "sim-tamy-login";
export const LOGIN_EVENT = "sim-tamy-login-changed";
// Public, fictional demo credentials; replace this flow with server authentication before real accounts.
export const DEMO_PASSWORD = "SimTamy2026!";

export function isInstitution(account: DemoAccount): account is DemoAccount & { org_id: string } {
  return Boolean(account.org_id) && ["educator", "org_admin"].includes(account.role);
}

export function canLogin(account: DemoAccount) {
  return account.role === "learner" || isInstitution(account);
}

export function readLogin(raw: string | null): DemoAccount | null {
  try {
    const value: unknown = JSON.parse(raw || "null");
    if (!value || typeof value !== "object") return null;
    const a = value as Partial<DemoAccount>;
    if (typeof a.id !== "string" || typeof a.display_name_th !== "string"
      || (a.org_id !== null && typeof a.org_id !== "string")
      || !["learner", "educator", "org_admin"].includes(a.role ?? "")) return null;
    return canLogin(a as DemoAccount) ? a as DemoAccount : null;
  } catch { return null; }
}

export function syncLearningSession(accountId: string | null, explicitLogin = false) {
  if (accountId && sessionStorage.getItem("sim-tamy-session-owner") === accountId) return;
  if (accountId && !explicitLogin && !sessionStorage.getItem("sim-tamy-session-owner")) {
    sessionStorage.setItem("sim-tamy-session-owner", accountId);
    return;
  }
  for (const key of Object.keys(sessionStorage)) {
    if (key.startsWith("sim-tamy-")) sessionStorage.removeItem(key);
  }
  if (accountId) sessionStorage.setItem("sim-tamy-session-owner", accountId);
}

export function setLogin(account: DemoAccount | null) {
  syncLearningSession(account?.id ?? null, true);
  if (account) localStorage.setItem(LOGIN_KEY, JSON.stringify(account));
  else localStorage.removeItem(LOGIN_KEY);
  setDemoAccount(account?.id ?? null);
  window.dispatchEvent(new Event(LOGIN_EVENT));
  window.dispatchEvent(new Event("sim-tamy-demo-account"));
}

export function loginDestination(account: DemoAccount, next: string | null = null) {
  if (isInstitution(account)) return "/institution";
  return next && /^\/(learn|lab|simulate|knowledge|join|profile|briefing|chat|decision|closing|report|replay)(\/|\?|$)/.test(next)
    ? next : "/";
}
