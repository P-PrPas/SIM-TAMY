import { expect, test } from "@playwright/test";

import { t } from "../lib/i18n";
import { syntheticReport } from "./fixtures/report";

test("Report prioritizes safety status and shows timeline and review at 360px", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("sim-tamy-session", JSON.stringify({
    id: "session-1", token: "synthetic-token", caseId: "PP-001",
    brief: { case_id: "PP-001", version: "0.1", status: "Draft", title_th: "Synthetic case" },
  })));
  await page.route("**/v1/sessions/session-1/report", (route) => route.fulfill({
    status: 200, contentType: "application/json", headers: { "Access-Control-Allow-Origin": "*" },
    json: syntheticReport,
  }));
  await page.goto("/report");
  await expect(page.locator("main [role='alert']")).toContainText(t("report.safetyNotMet"));
  await expect(page.getByText(t("report.safetyMet"))).toHaveCount(0);
  await expect(page.getByText(t("status.draft"))).toBeVisible();
  await expect(page.getByText("54.5")).toBeVisible();
  await page.getByRole("tab", { name: t("report.timeline") }).click();
  await expect(page.getByText("Synthetic timeline event")).toBeVisible();
  await page.getByRole("tab", { name: t("report.review") }).click();
  await expect(page.getByText("Review source")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
});
