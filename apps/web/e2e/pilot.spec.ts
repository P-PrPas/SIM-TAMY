import { expect, test } from "@playwright/test";
import { syntheticReport } from "./fixtures/report";
import { t } from "../lib/i18n";

test("completed learners can voluntarily submit pilot feedback at 360px", async ({ page }) => {
  const submissions: object[] = [];
  await page.addInitScript(() => sessionStorage.setItem("sim-tamy-session", JSON.stringify({ id: "session-1", token: "synthetic-token", caseId: "PP-001", brief: { case_id: "PP-001", version: "0.1", status: "Draft", title_th: "Synthetic case" } })));
  await page.route("**/v1/sessions/session-1/**", async (route) => {
    const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers });
    if (route.request().url().endsWith("/feedback")) {
      submissions.push(route.request().postDataJSON());
      return route.fulfill({ status: 201, headers, json: { ...route.request().postDataJSON(), session_id: "session-1", created_at: "2026-10-18T00:00:00Z" } });
    }
    return route.fulfill({ status: 200, headers, json: syntheticReport });
  });
  await page.goto("/report");
  await expect(page.getByRole("heading", { name: t("pilot.title") })).toBeVisible();
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (window as typeof window & { axe: typeof import("axe-core") }).axe;
    return (await axe.run()).violations.filter((entry) => ["critical", "serious"].includes(entry.impact ?? ""));
  });
  expect(violations).toEqual([]);
  await page.getByRole("combobox", { name: t("pilot.role") }).selectOption("learner");
  await page.getByRole("combobox", { name: t("pilot.usefulness") }).selectOption("4");
  await page.getByRole("combobox", { name: t("pilot.realism") }).selectOption("3");
  await page.getByRole("textbox").fill("Synthetic browser feedback");
  await page.getByRole("button", { name: t("pilot.send"), exact: true }).click();
  expect(submissions).toHaveLength(0);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: t("pilot.send"), exact: true }).click();
  await expect(page.getByText(t("pilot.sent"))).toBeVisible();
  expect(submissions).toEqual([{ role: "learner", usefulness: 4, realism: 3, comment: "Synthetic browser feedback", consent: true }]);
  await page.screenshot({ path: "test-results/pilot.png", fullPage: true });
});
