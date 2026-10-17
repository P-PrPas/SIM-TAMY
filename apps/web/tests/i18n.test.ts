import { describe, expect, it } from "vitest";

import { patientLabel, t } from "../lib/i18n";

describe("t()", () => {
  it("retains the removed banner wording for negative regression checks", () => {
    expect(t("banner.educationOnly").length).toBeGreaterThan(0);
  });

  it("throws on a missing key instead of rendering blank", () => {
    expect(() => t("nope.missing")).toThrow();
  });
});

it.each([
  ["dad", "chat.wife"],
  ["mom", "chat.friend"],
  ["staff", "chat.patient"],
  [null, "chat.patient"],
  [undefined, "chat.patient"],
] as const)("labels the patient for audience %s", (audience, key) => {
  expect(patientLabel(audience)).toBe(t(key));
});
