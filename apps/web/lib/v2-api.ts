// ponytail: plain fetch for the 2.0 endpoints that are not in docs/openapi.yaml yet (ADR-15). Types mirror docs/v2/contracts.md.
import { getDemoAccount } from "./demo-account";

export type PathObjective = { id: string; title_th: string; dimension: string; unit_ids: string[]; story_ids: string[] };
export type PathStage = { stage: number | string; title_th: string; summary_th: string; objectives: PathObjective[] };
export type LearningPaths = { release_id: string; stages: PathStage[] };

export type UnitSummary = { id: string; version: string; title_th: string; care_stage: string; domain: number | string; has_lens: boolean };
export type SourceRef = { source_id: string; title: string; url: string | null; locator: string | null };
export type Hotspot = { id: string; label_th: string; text_th: string };
export type Claim = { id: string; type: string; text_th: string; sources: SourceRef[]; hotspots?: Hotspot[] };
export type Lens = { wisdom_th: string; safety_th: string; rights_th: string };
export type UnitDetail = {
  id: string; version: string; title_th: string; care_stage: string; domain: number | string;
  evidence_status: string; review_basis: string; reviewed_on: string | null;
  claims: Claim[]; lens: Lens | null; contraindications_th: string[]; escalation_th: string | null;
};
export type Source = { id: string; kind: string; title: string; publisher: string | null; year: number | null; url: string | null; rights_status: string };

export type DemoAccount = { id: string; org_id: string; display_name_th: string; role: "org_admin" | "educator" | "reviewer" | "learner" };
export type Attempt = {
  room_id: string; story_id: string; title_th: string; finished_at: string | null;
  safety_status: "SAFETY_MET" | "SAFETY_NOT_MET"; score_total: number | null; objective_ids: string[];
  /** Display only: every decision of this attempt carried a skill. Never a score or a safety result. */
  strong: boolean;
};
export type PassportLesson = { unit_id: string; completed_at: string };
export type Passport = { account: { id: string; display_name_th: string }; attempts: Attempt[]; lessons: PassportLesson[] };

export type StoryCard = { id: string; title_th: string; description_th: string; mode: "coop" | "solo"; chapters_th: string[] };
export type CaseCard = { case_id: string; title_th: string; audience?: string | null };

export class V2ApiError extends Error {
  constructor(readonly code: string, readonly status: number) {
    super(`${code} (${status})`);
    this.name = "V2ApiError";
  }
}

const base = () => process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** `/v1<path>`; sends X-Demo-Account when a profile is picked; throws V2ApiError from the standard envelope. */
async function request<T>(method: "GET" | "POST", path: string, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = {};
  const account = getDemoAccount();
  if (account) headers["X-Demo-Account"] = account;
  let res: Response;
  try {
    res = await fetch(`${base()}/v1${path}`, { method, headers, signal });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new V2ApiError("NETWORK_ERROR", 0);
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: { code?: string } } | null;
    throw new V2ApiError(body?.error?.code ?? "UNKNOWN", res.status);
  }
  return (await res.json()) as T;
}

export const v2Get = <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, signal);

export const v2 = {
  learningPaths: (s?: AbortSignal) => v2Get<LearningPaths>("/learning-paths", s),
  units: (s?: AbortSignal) => v2Get<{ release_id: string; items: UnitSummary[] }>("/knowledge/units", s),
  unit: (id: string, s?: AbortSignal) => v2Get<UnitDetail>(`/knowledge/units/${encodeURIComponent(id)}`, s),
  sources: (s?: AbortSignal) => v2Get<{ items: Source[] }>("/knowledge/sources", s),
  accounts: (s?: AbortSignal) => v2Get<{ items: DemoAccount[] }>("/demo/accounts", s),
  passport: (id: string, s?: AbortSignal) => v2Get<Passport>(`/passport/${encodeURIComponent(id)}`, s),
  completeLesson: (accountId: string, unitId: string) =>
    request<PassportLesson>("POST", `/passport/${encodeURIComponent(accountId)}/lessons/${encodeURIComponent(unitId)}`),
  stories: (s?: AbortSignal) => v2Get<StoryCard[]>("/family/stories", s),
  cases: (s?: AbortSignal) => v2Get<{ items: CaseCard[] }>("/cases", s),
};

/** Featured Golden Scenarios (B). Everything else routes through `/simulate/<id>` except the 1.x stories below. */
export const GOLDEN_STORY_IDS = ["gs-a-postpartum-warning", "gs-b-thai-recovery"] as const;
const LEGACY_STORY_ROUTES: Record<string, string> = {
  "golden-first-night": "/golden", "first-night": "/family", parenthood: "/parenthood", bridge: "/bridge",
};
export const storyHref = (id: string) => LEGACY_STORY_ROUTES[id] ?? `/simulate/${encodeURIComponent(id)}`;
