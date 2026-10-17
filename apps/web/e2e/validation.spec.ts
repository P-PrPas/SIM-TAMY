import { expect, test } from "@playwright/test";
import { t } from "../lib/i18n";

test("measured validation is accessible at 360px with downloadable provenance", async ({ page }) => {
  await page.goto("/validation");
  await expect(page.getByRole("heading", { name: t("validation.title") })).toBeVisible();
  await expect(page.locator("main section")).toHaveCount(4);
  const result = await page.request.get("/validation-results.json");
  expect(result.ok()).toBe(true);
  const data = await result.json();
  expect(data.scope).toBe("offline-unit");
  expect(data.groups.every((group: { passed: number }) => group.passed > 0)).toBe(true);
  await page.getByText(t("validation.provenance")).click();
  await expect(page.getByText(`SHA-256: ${data.fingerprint}`)).toBeVisible();
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (window as typeof window & { axe: typeof import("axe-core") }).axe;
    return (await axe.run()).violations.filter((entry) => ["critical", "serious"].includes(entry.impact ?? ""));
  });
  expect(violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/validation.png", fullPage: true });
});
