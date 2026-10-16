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
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: t("app.skipToContent") })).toBeFocused();
  const contrast = await page.locator("main [role='alert']").evaluate((element) => {
    const luminance = (value: string) => {
      const [first = 0, second = 0, third = 0] = (value.match(/[\d.]+%?/g) ?? []).slice(0, 3).map(parseFloat);
      if (value.startsWith("lab(") || value.startsWith("lch(")) {
        const light = first > 1 ? first : first * 100;
        return light > 8 ? ((light + 16) / 116) ** 3 : light / 903.3;
      }
      if (value.startsWith("oklch")) {
        const light = first > 1 ? first / 100 : first;
        const angle = third * Math.PI / 180;
        const a = second * Math.cos(angle);
        const b = second * Math.sin(angle);
        const l = (light + 0.3963377774 * a + 0.2158037573 * b) ** 3;
        const m = (light - 0.1055613458 * a - 0.0638541728 * b) ** 3;
        const s = (light - 0.0894841775 * a - 1.2914855480 * b) ** 3;
        const clamp = (channel: number) => Math.min(1, Math.max(0, channel));
        const r = clamp(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s);
        const g = clamp(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s);
        const blue = clamp(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s);
        return 0.2126 * r + 0.7152 * g + 0.0722 * blue;
      }
      const linear = [first, second, third].map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * (linear[0] ?? 0) + 0.7152 * (linear[1] ?? 0) + 0.0722 * (linear[2] ?? 0);
    };
    const style = getComputedStyle(element);
    const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => b - a);
    return { ratio: ((values[0] ?? 0) + 0.05) / ((values[1] ?? 0) + 0.05),
      foreground: style.color, background: style.backgroundColor };
  });
  expect(contrast.ratio, JSON.stringify(contrast)).toBeGreaterThanOrEqual(4.5);
  await expect(page.locator("main [role='alert']")).toContainText(t("report.safetyNotMet"));
  await expect(page.getByText(t("report.safetyMet"))).toHaveCount(0);
  await expect(page.getByText(t("status.draft"))).toBeVisible();
  await expect(page.getByText("54.5")).toBeVisible();
  await page.getByRole("tab", { name: t("report.timeline") }).click();
  await expect(page.getByText("Synthetic timeline event")).toBeVisible();
  await page.getByRole("tab", { name: t("report.review") }).click();
  await expect(page.getByText("Review source")).toBeVisible();
  await expect(page.getByRole("button", { name: t("report.downloadJson") })).toBeVisible();
  await expect(page.getByRole("button", { name: t("report.print") })).toBeVisible();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: t("report.downloadJson") }).click();
  expect((await downloadEvent).suggestedFilename()).toBe("sim-tamy-report-PP-001-session-1.json");
  await page.emulateMedia({ media: "print" });
  await expect(page.getByText("Synthetic timeline event")).toBeVisible();
  await expect(page.getByText("Review source")).toBeVisible();
  await expect(page.getByRole("tablist", { includeHidden: true })).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
  expect(await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize))).toBeGreaterThanOrEqual(16);
});
