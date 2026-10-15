import { expect, test } from "@playwright/test";

import { t } from "../lib/i18n";

async function noHorizontalOverflow(page: import("@playwright/test").Page) {
  const metrics = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    fontSize: Number.parseFloat(getComputedStyle(document.documentElement).fontSize),
  }));
  expect(metrics.width).toBe(360);
  expect(metrics.scrollWidth).toBeLessThanOrEqual(360);
  expect(metrics.fontSize).toBeGreaterThanOrEqual(16);
}

test("Join and Briefing render a Draft case at 360px against Prism", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: t("join.title") })).toBeVisible();
  await expect(page.getByText(t("status.draftFull"))).toBeVisible();
  await expect(page.getByText(t("banner.educationOnly"))).toBeVisible();
  await noHorizontalOverflow(page);

  await page.getByRole("textbox", { name: t("join.nickname") }).fill("Learner");
  await page.getByRole("button", { name: t("join.start") }).click();
  await expect(page).toHaveURL(/\/briefing$/);
  await expect(page.getByText(t("status.draftFull"))).toBeVisible();
  await expect(page.getByText(t("banner.educationOnly"))).toBeVisible();
  await expect(page.getByRole("link", { name: t("briefing.begin") })).toBeVisible();
  await noHorizontalOverflow(page);
});

test("Join explains an invalid class code without leaving the page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(t("status.draftFull"))).toBeVisible();
  await page.route("**/v1/sessions", (route) => route.fulfill({
    status: 404,
    contentType: "application/json",
    headers: { "Access-Control-Allow-Origin": "*" },
    json: { error: { code: "CLASS_NOT_FOUND", message: "not found", details: {} } },
  }));
  await page.getByRole("textbox", { name: t("join.nickname") }).fill("Learner");
  await page.getByRole("textbox", { name: t("join.classCode") }).fill("ABC123");
  await page.getByRole("button", { name: t("join.start") }).click();
  await expect(page.getByText(t("join.classNotFound"))).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
});

test("Chat keeps a failed optimistic turn and retries it with the same ID", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("textbox", { name: t("join.nickname") }).fill("Learner");
  await page.getByRole("button", { name: t("join.start") }).click();
  await page.getByRole("link", { name: t("briefing.begin") }).click();
  await expect(page.getByRole("heading", { name: t("chat.title") })).toBeVisible();
  await expect(page.getByText(t("banner.educationOnly"))).toBeVisible();
  await noHorizontalOverflow(page);

  const turnIds: string[] = [];
  await page.route("**/v1/sessions/*/turns", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = route.request().postDataJSON() as { client_turn_id: string };
    turnIds.push(body.client_turn_id);
    if (turnIds.length === 1) {
      await new Promise((resolve) => setTimeout(resolve, 600));
      return route.fulfill({ status: 500, contentType: "application/json", headers: { "Access-Control-Allow-Origin": "*" }, json: { error: { code: "INTERNAL_ERROR", message: "failure", details: {} } } });
    }
    return route.continue();
  });
  await page.getByRole("textbox", { name: t("chat.messageLabel") }).fill("Question?");
  await page.getByRole("button", { name: t("chat.send") }).click();
  await expect(page.getByText("Question?")).toBeVisible();
  await expect(page.getByText(t("chat.typing"))).toBeVisible();
  await page.getByRole("button", { name: t("chat.retry") }).click();
  await expect(page.getByRole("button", { name: t("chat.retry") })).toHaveCount(0);
  expect(turnIds).toHaveLength(2);
  expect(turnIds[0]).toBe(turnIds[1]);
  await noHorizontalOverflow(page);
});
