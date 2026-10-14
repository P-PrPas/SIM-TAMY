import { describe, expect, it, vi } from "vitest";

import { ApiError, createApi } from "../lib/api/client";

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
const envelope = (code: string, request_id = "req_1") => ({
  error: { code, message: "m", details: {}, request_id },
});

function setup(...responses: Array<Response | Error>) {
  const fetchImpl = vi.fn(async (...args: [Request]) => {
    void args;
    const next = responses.shift();
    if (next instanceof Error) throw next;
    return next ?? json(200, {});
  });
  const sleeps: number[] = [];
  const api = createApi({
    baseUrl: "http://api.test",
    getToken: () => "tok-123",
    fetchImpl: fetchImpl as unknown as typeof fetch,
    sleep: async (ms) => void sleeps.push(ms),
  });
  return { api, fetchImpl, sleeps };
}

const turn = (api: ReturnType<typeof setup>["api"]) =>
  api.POST("/v1/sessions/{session_id}/turns", {
    params: { path: { session_id: "s1" } },
    body: { text: "hi", client_turn_id: "c-1" },
  });

describe("api client", () => {
  it("sends the session token and returns typed data", async () => {
    const { api, fetchImpl } = setup(
      json(200, { status: "ok", version: "0.1.0", time: "2026-10-12T00:00:00Z" }),
    );

    const { data } = await api.GET("/health");

    expect(data?.status).toBe("ok");
    const sent = fetchImpl.mock.calls[0]?.[0] as unknown as Request;
    expect(sent.headers.get("Authorization")).toBe("Bearer tok-123");
  });

  it("turns the error envelope into ApiError", async () => {
    const { api } = setup(json(409, envelope("SESSION_COMPLETED", "req_9")));

    const err = await api.GET("/health").catch((e: unknown) => e);

    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ code: "SESSION_COMPLETED", status: 409, requestId: "req_9" });
  });

  it("falls back to UNKNOWN with the X-Request-ID header for non-envelope errors", async () => {
    const { api } = setup(new Response("<html>", { status: 502, headers: { "X-Request-ID": "req_7" } }));
    await expect(api.GET("/health")).rejects.toMatchObject({ code: "UNKNOWN", status: 502, requestId: "req_7" });
  });

  it("retries LLM_UNAVAILABLE twice with 1s then 2s backoff, reusing the same client_turn_id", async () => {
    const { api, fetchImpl, sleeps } = setup(
      json(503, envelope("LLM_UNAVAILABLE")),
      json(409, envelope("TURN_IN_PROGRESS")),
      json(200, { reply: "ok" }),
    );

    await turn(api);

    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(sleeps).toEqual([1000, 2000]);
    const bodies = await Promise.all(
      fetchImpl.mock.calls.map((c) => (c[0] as unknown as Request).text()),
    );
    expect(new Set(bodies).size).toBe(1);
    expect(bodies[0]).toContain('"client_turn_id":"c-1"');
  });

  it("gives up after two retries and throws the last error", async () => {
    const { api, fetchImpl } = setup(
      json(503, envelope("LLM_UNAVAILABLE")),
      json(503, envelope("LLM_UNAVAILABLE")),
      json(503, envelope("LLM_UNAVAILABLE")),
      json(200, {}),
    );

    await expect(turn(api)).rejects.toMatchObject({ code: "LLM_UNAVAILABLE" });
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it("does not retry other errors", async () => {
    const { api, fetchImpl } = setup(json(409, envelope("TURN_LIMIT")));
    await expect(turn(api)).rejects.toMatchObject({ code: "TURN_LIMIT" });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("retries a network error for GET and for a turn, but not for other POSTs", async () => {
    const get = setup(new TypeError("down"), json(200, { status: "ok" }));
    await get.api.GET("/health");
    expect(get.fetchImpl).toHaveBeenCalledTimes(2);

    const replayableTurn = setup(new TypeError("down"), json(200, {}));
    await turn(replayableTurn.api);
    expect(replayableTurn.fetchImpl).toHaveBeenCalledTimes(2);

    const create = setup(new TypeError("down"), json(200, {}));
    await expect(
      create.api.POST("/v1/sessions", { body: { case_id: "DEV-001", variant: "A", learner_name: "n" } }),
    ).rejects.toMatchObject({ code: "NETWORK_ERROR" });
    expect(create.fetchImpl).toHaveBeenCalledTimes(1);
  });
});
