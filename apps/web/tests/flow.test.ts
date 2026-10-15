import { describe, expect, it } from "vitest";

import { normalizeClassCode, sanitizeMessage, statusKey } from "../lib/flow";
import { appendOptimistic, failPending, resolvePending, retryPending } from "../lib/chat-state";

describe("join and chat guards", () => {
  it("normalizes a class code without silently accepting invalid formats", () => {
    expect(normalizeClassCode(" ab12cd ")).toBe("AB12CD");
    expect(normalizeClassCode("abc")).toBeNull();
    expect(normalizeClassCode("" )).toBe("");
  });

  it("strips control characters, trims, and enforces the 500 character limit", () => {
    expect(sanitizeMessage("  hi\u0000\nthere  ")).toBe("hithere");
    expect(sanitizeMessage(" ")).toBeNull();
    expect(sanitizeMessage("x".repeat(501))).toBeNull();
  });

  it("maps every content status to an i18n key", () => {
    expect(statusKey("Draft")).toBe("status.draft");
    expect(statusKey("In Review")).toBe("status.inReview");
    expect(statusKey("Approved")).toBe("status.approved");
  });
});

describe("optimistic chat state", () => {
  it("keeps the learner turn visible across failure and retry with the same ID", () => {
    const pending = appendOptimistic([], "hello", "turn-1234");
    expect(pending).toMatchObject([{ text: "hello", delivery: "pending" }]);
    const failed = failPending(pending, "turn-1234");
    expect(failed).toMatchObject([{ text: "hello", delivery: "failed" }]);
    const retried = retryPending(failed, "turn-1234");
    expect(retried).toMatchObject([{ id: "turn-1234", delivery: "pending" }]);
    const done = resolvePending(retried, "turn-1234", 1, [{ speaker: "patient", text: "reply" }]);
    expect(done).toMatchObject([
      { id: "turn-1234", delivery: "sent", idx: 1 },
      { speaker: "patient", text: "reply", idx: 1 },
    ]);
  });
});
