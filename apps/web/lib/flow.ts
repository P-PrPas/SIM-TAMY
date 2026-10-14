import type { components } from "./api/schema";

type CaseStatus = components["schemas"]["CaseStatus"];

export function statusKey(status: CaseStatus): string {
  const keys: Record<CaseStatus, string> = {
    Draft: "status.draft",
    "In Review": "status.inReview",
    Approved: "status.approved",
  };
  return keys[status];
}

export function normalizeClassCode(value: string): string | null {
  const code = value.trim().toUpperCase();
  return code === "" || /^[A-Z0-9]{6}$/.test(code) ? code : null;
}

export function sanitizeMessage(value: string): string | null {
  const text = value.replace(/[\x00-\x1f\x7f]/g, "").trim();
  return text.length > 0 && text.length <= 500 ? text : null;
}

const SESSION_KEY = "sim-tamy-session";

export type ActiveSession = { id: string; token: string; caseId: string };

export function saveSession(session: ActiveSession): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function readSession(): ActiveSession | null {
  try {
    const value = sessionStorage.getItem(SESSION_KEY);
    if (!value) return null;
    const parsed: unknown = JSON.parse(value);
    if (typeof parsed !== "object" || parsed === null) return null;
    const candidate = parsed as Record<string, unknown>;
    if (typeof candidate.id !== "string" || typeof candidate.token !== "string" || typeof candidate.caseId !== "string") return null;
    return { id: candidate.id, token: candidate.token, caseId: candidate.caseId };
  } catch {
    return null;
  }
}
