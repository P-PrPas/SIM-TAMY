import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

describe("Thai literal lint guard", () => {
  it("rejects Thai literals in components while allowing i18n lookups", async () => {
    const lint = new ESLint();
    const bad = await lint.lintText("const label = '\\u0e01';", { filePath: "app/example.tsx" });
    const good = await lint.lintText("const label = t('join.start');", { filePath: "app/example.tsx" });
    expect(bad[0]?.messages.some((message) => message.ruleId === "sim-tamy/no-thai-literals")).toBe(true);
    expect(good[0]?.messages.some((message) => message.ruleId === "sim-tamy/no-thai-literals")).toBe(false);
  }, 30_000); // loading ESLint and its plugins can exceed the 5 s default on a cold machine
});
