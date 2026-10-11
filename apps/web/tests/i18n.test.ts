import { describe, expect, it } from "vitest";

import { t } from "../lib/i18n";

describe("t()", () => {
  it("returns the education-only banner text", () => {
    expect(t("banner.educationOnly").length).toBeGreaterThan(0);
  });

  it("throws on a missing key instead of rendering blank", () => {
    expect(() => t("nope.missing")).toThrow();
  });
});
