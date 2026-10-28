import createClient from "openapi-fetch";

import type { components, paths } from "./schema";
import { getDemoAccount as demoAccount } from "../demo-account";

/** Error envelope from the API (docs/API_DESIGN.md 2.1). Mapped to Thai text via lib/i18n, not shown raw. */
export class ApiError extends Error {
  constructor(
    readonly code: components["schemas"]["ErrorCode"] | "NETWORK_ERROR" | "UNKNOWN",
    readonly status: number,
    readonly requestId?: string,
    readonly details?: unknown,
  ) {
    super(`${code} (${status})`);
    this.name = "ApiError";
  }
}

/** Retried automatically (API_DESIGN 12), at most twice, with the same client_turn_id. */
const RETRYABLE = new Set<string>(["LLM_UNAVAILABLE", "TURN_IN_PROGRESS", "NETWORK_ERROR"]);
const BACKOFF_MS = [1000, 2000];

export type ClientOptions = {
  baseUrl: string;
  /** Session token (sessionStorage) or undefined for public endpoints. */
  getToken?: () => string | undefined;
  /** Instructor secret is supplied interactively and held in memory only. */
  getInstructorSecret?: () => string | undefined;
  /** Mock account picked in the demo (ADR-15); sent as X-Demo-Account. */
  getDemoAccount?: () => string | undefined;
  fetchImpl?: typeof fetch;
  sleep?: (ms: number) => Promise<void>;
};

async function toApiError(res: Response): Promise<ApiError> {
  const requestId = res.headers.get("X-Request-ID") ?? undefined;
  try {
    const body = (await res.json()) as Partial<components["schemas"]["Error"]>;
    const e = body.error;
    if (e?.code) return new ApiError(e.code, res.status, e.request_id ?? requestId, e.details);
  } catch {
    /* not JSON: fall through */
  }
  return new ApiError("UNKNOWN", res.status, requestId);
}

/**
 * Typed client over the generated `paths`. Failed calls throw ApiError instead of returning `{error}`.
 * Network errors are retried only when replaying is safe: GET, or a body carrying `client_turn_id`.
 */
export function createApi({
  baseUrl,
  getToken = () => undefined,
  getInstructorSecret = () => undefined,
  getDemoAccount = demoAccount,
  fetchImpl = (...a) => fetch(...a),
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
}: ClientOptions) {
  const retryingFetch = async (req: Request): Promise<Response> => {
    const token = getToken();
    if (token) req.headers.set("Authorization", `Bearer ${token}`);
    const instructorSecret = getInstructorSecret();
    if (instructorSecret) req.headers.set("X-Instructor-Secret", instructorSecret);
    const account = getDemoAccount();
    if (account) req.headers.set("X-Demo-Account", account);
    const replayable =
      req.method === "GET" || (await req.clone().text()).includes('"client_turn_id"');

    for (let attempt = 0; ; attempt++) {
      req.signal.throwIfAborted();
      let failure: ApiError;
      try {
        const res = await fetchImpl(req.clone());
        if (res.ok) return res;
        failure = await toApiError(res);
      } catch (e) {
        // a cancelled request is not a network failure: never retry it, never wrap it
        if (req.signal.aborted || (e instanceof DOMException && e.name === "AbortError")) throw e;
        failure = new ApiError("NETWORK_ERROR", 0);
        if (!replayable) throw failure;
      }
      if (!RETRYABLE.has(failure.code) || attempt >= BACKOFF_MS.length) throw failure;
      await sleep(BACKOFF_MS[attempt] ?? 2000);
    }
  };

  return createClient<paths>({ baseUrl, fetch: retryingFetch });
}
