import type { components } from "./api/schema";

type CaseStatus = components["schemas"]["CaseStatus"];
type CaseBrief = components["schemas"]["CaseBrief"];

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

/** `brief` is the case as it was when the session was created: the version the engine is using. */
export type ActiveSession = { id: string; token: string; caseId: string; brief: CaseBrief };

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
    const brief = candidate.brief as Partial<CaseBrief> | null | undefined;
    if (typeof brief !== "object" || brief === null || typeof brief.case_id !== "string" || typeof brief.version !== "string") return null;
    return { id: candidate.id, token: candidate.token, caseId: candidate.caseId, brief: brief as CaseBrief };
  } catch {
    return null;
  }
}
