// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ValidationDashboard } from "../components/validation-dashboard";
import { t } from "../lib/i18n";

afterEach(cleanup);

it.each([
  [{ passed: 3, failed: 0, errors: 0, skipped: 0 }, "passed"],
  [{ passed: 3, failed: 1, errors: 0, skipped: 0 }, "failed"],
  [{ passed: 3, failed: 0, errors: 1, skipped: 0 }, "failed"],
  [{ passed: 3, failed: 0, errors: 0, skipped: 1 }, "unverified"],
  [{ passed: 0, failed: 0, errors: 0, skipped: 0 }, "unverified"],
] as const)("does not convert missing, skipped or errored measurements into a pass", (counts, expected) => {
  const view = render(<ValidationDashboard report={{ generated_at: "2026-10-18T00:00:00Z", source_revision: "measured-revision", fingerprint: "measured-fingerprint", scope: "offline-unit", groups: [{ id: "safety", ...counts }] }} />);
  expect(view.container.querySelector("section > p")?.textContent).toBe(t(`validation.${expected}`));
  expect(screen.getByText("SHA-256: measured-fingerprint")).toBeTruthy();
  expect(screen.getByRole("link", { name: t("validation.download") }).getAttribute("href")).toBe("/validation-results.json");
});
