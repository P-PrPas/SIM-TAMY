import { expect, test } from "@playwright/test";
import { t } from "../lib/i18n";

test("retired examples have no entry points and old bookmarks open the lab", async ({ page }) => {
  const recordingRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/v1/replay/recordings")) recordingRequests.push(request.url());
  });
  await page.goto("/");
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator('a[href="/replay"]')).toHaveCount(0);
  await page.goto("/replay");
  await expect(page).toHaveURL(/\/lab$/);
  await expect(page.getByRole("heading", { name: t("platform.lab.title"), exact: true })).toBeVisible();
  await page.getByText(t("platform.lab.moreModules"), { exact: true }).click();
  await expect(page.locator('a[href="/replay"]')).toHaveCount(0);
  expect(recordingRequests).toEqual([]);
});
